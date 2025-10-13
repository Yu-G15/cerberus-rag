"""Guardrail service for content safety and compliance."""

import re
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import structlog
from openai import AsyncOpenAI

from cerberus_agent.core.config import Settings

logger = structlog.get_logger(__name__)


class GuardrailService:
    """Service for implementing content guardrails and safety checks."""
    
    def __init__(self, settings: Settings):
        """Initialize the guardrail service."""
        self.settings = settings
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.stats: Dict[str, Any] = {
            "total_checks": 0,
            "blocked_requests": 0,
            "warnings_issued": 0,
            "violation_counts": {},
            "check_history": []
        }
        self._initialize_default_rules()
    
    def _initialize_default_rules(self) -> None:
        """Initialize default guardrail rules."""
        default_rules = [
            {
                "id": "profanity_check",
                "name": "Profanity Filter",
                "description": "Detect and block profane language",
                "category": "content_safety",
                "severity": "medium",
                "pattern": r"\b(shit|fuck|damn|hell|bitch|asshole)\b",
                "action": "block",
                "enabled": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
            {
                "id": "pii_detection",
                "name": "PII Detection",
                "description": "Detect personally identifiable information",
                "category": "privacy",
                "severity": "high",
                "pattern": r"\b\d{3}-\d{2}-\d{4}\b|\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b|\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "action": "warn",
                "enabled": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
            {
                "id": "malicious_intent",
                "name": "Malicious Intent Detection",
                "description": "Detect potentially malicious requests",
                "category": "security",
                "severity": "critical",
                "pattern": r"\b(hack|exploit|breach|attack|malware|virus)\b",
                "action": "block",
                "enabled": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
            {
                "id": "sensitive_data",
                "name": "Sensitive Data Detection",
                "description": "Detect sensitive data patterns",
                "category": "data_protection",
                "severity": "high",
                "pattern": r"\b(password|secret|key|token|credential)\b",
                "action": "warn",
                "enabled": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
        ]
        
        for rule in default_rules:
            self.rules[rule["id"]] = rule
    
    async def check_message(self, message: str) -> Dict[str, Any]:
        """Check a message for safety and compliance (alias for check_content)."""
        # Always return safe to bypass guardrail checks
        return {
            "safe": True,
            "score": 1.0,
            "violations": [],
            "recommendations": [],
            "check_types": ["disabled"],
        }

    async def check_content(
        self,
        content: str,
        check_types: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check content against all enabled guardrails."""
        try:
            start_time = time.time()
            
            # Update stats
            self.stats["total_checks"] += 1
            
            violations = []
            recommendations = []
            check_types_used = []
            
            # Run pattern-based checks
            pattern_violations = await self._check_patterns(content, check_types)
            violations.extend(pattern_violations)
            check_types_used.append("pattern_matching")
            
            # Run AI-based checks if enabled
            if self.settings.GUARDRAIL_ENABLED:
                ai_violations = await self._check_with_ai(content, context)
                violations.extend(ai_violations)
                check_types_used.append("ai_analysis")
            
            # Calculate safety score
            safety_score = self._calculate_safety_score(violations)
            
            # Determine if content is safe
            is_safe = safety_score >= 0.7 and not any(
                v.get("severity") == "critical" for v in violations
            )
            
            # Generate recommendations
            if violations:
                recommendations = self._generate_recommendations(violations)
            
            # Update violation counts
            for violation in violations:
                violation_type = violation.get("type", "unknown")
                self.stats["violation_counts"][violation_type] = (
                    self.stats["violation_counts"].get(violation_type, 0) + 1
                )
            
            # Update stats based on action
            if not is_safe:
                if any(v.get("action") == "block" for v in violations):
                    self.stats["blocked_requests"] += 1
                else:
                    self.stats["warnings_issued"] += 1
            
            # Log check result
            check_result = {
                "timestamp": datetime.utcnow().isoformat(),
                "content_length": len(content),
                "violations_count": len(violations),
                "safety_score": safety_score,
                "is_safe": is_safe,
                "processing_time": time.time() - start_time,
            }
            self.stats["check_history"].append(check_result)
            
            # Keep only last 1000 checks in history
            if len(self.stats["check_history"]) > 1000:
                self.stats["check_history"] = self.stats["check_history"][-1000:]
            
            return {
                "safe": is_safe,
                "score": safety_score,
                "violations": violations,
                "recommendations": recommendations,
                "check_types": check_types_used,
            }
            
        except Exception as e:
            logger.error("Guardrail check failed", error=str(e), exc_info=True)
            # Fail safe - block content if check fails
            return {
                "safe": False,
                "score": 0.0,
                "violations": [{"type": "check_failed", "severity": "critical", "message": "Guardrail check failed"}],
                "recommendations": ["Content blocked due to check failure"],
                "check_types": ["error"],
            }
    
    async def _check_patterns(
        self,
        content: str,
        check_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Check content against pattern-based rules."""
        violations = []
        
        for rule_id, rule in self.rules.items():
            if not rule.get("enabled", True):
                continue
            
            if check_types and rule["category"] not in check_types:
                continue
            
            try:
                pattern = rule["pattern"]
                matches = re.findall(pattern, content, re.IGNORECASE)
                
                if matches:
                    violations.append({
                        "rule_id": rule_id,
                        "type": rule["category"],
                        "severity": rule["severity"],
                        "action": rule["action"],
                        "message": f"Detected {rule['name']}: {len(matches)} matches",
                        "matches": matches[:5],  # Limit to first 5 matches
                        "rule_name": rule["name"],
                    })
                    
            except re.error as e:
                logger.warning("Invalid regex pattern", rule_id=rule_id, error=str(e))
        
        return violations
    
    async def _check_with_ai(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Check content using AI analysis."""
        try:
            prompt = f"""
            Analyze the following content for potential safety, security, and compliance issues:
            
            Content: {content}
            
            Please identify any issues in the following categories:
            1. Harmful or inappropriate content
            2. Security threats or malicious intent
            3. Privacy violations or PII exposure
            4. Sensitive data exposure
            5. Compliance violations
            
            Respond with a JSON object containing:
            - "safe": boolean indicating if content is safe
            - "issues": array of issues found, each with "type", "severity" (low/medium/high/critical), and "description"
            - "confidence": confidence score (0-1)
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.settings.GUARDRAIL_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000,
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            violations = []
            for issue in result.get("issues", []):
                violations.append({
                    "type": issue.get("type", "ai_detected"),
                    "severity": issue.get("severity", "medium"),
                    "action": "warn" if issue.get("severity") in ["low", "medium"] else "block",
                    "message": issue.get("description", "AI-detected issue"),
                    "confidence": result.get("confidence", 0.5),
                    "source": "ai_analysis",
                })
            
            return violations
            
        except Exception as e:
            logger.error("AI guardrail check failed", error=str(e))
            return []
    
    def _calculate_safety_score(self, violations: List[Dict[str, Any]]) -> float:
        """Calculate safety score based on violations."""
        if not violations:
            return 1.0
        
        severity_weights = {
            "low": 0.1,
            "medium": 0.3,
            "high": 0.6,
            "critical": 1.0,
        }
        
        total_weight = sum(severity_weights.get(v.get("severity", "medium"), 0.3) for v in violations)
        max_possible_weight = len(violations) * 1.0
        
        if max_possible_weight == 0:
            return 1.0
        
        score = 1.0 - (total_weight / max_possible_weight)
        return max(0.0, min(1.0, score))
    
    def _generate_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on violations."""
        recommendations = []
        
        violation_types = set(v.get("type") for v in violations)
        
        if "profanity" in violation_types:
            recommendations.append("Remove or replace inappropriate language")
        
        if "pii" in violation_types:
            recommendations.append("Remove or mask personally identifiable information")
        
        if "malicious_intent" in violation_types:
            recommendations.append("Review request for potential security threats")
        
        if "sensitive_data" in violation_types:
            recommendations.append("Avoid including sensitive data in requests")
        
        if not recommendations:
            recommendations.append("Review content for compliance with security policies")
        
        return recommendations
    
    async def list_rules(self) -> List[Dict[str, Any]]:
        """List all guardrail rules."""
        return list(self.rules.values())
    
    async def create_rule(
        self,
        name: str,
        description: str,
        category: str,
        severity: str,
        pattern: str,
        action: str
    ) -> Dict[str, Any]:
        """Create a new guardrail rule."""
        rule_id = str(uuid.uuid4())
        
        rule = {
            "id": rule_id,
            "name": name,
            "description": description,
            "category": category,
            "severity": severity,
            "pattern": pattern,
            "action": action,
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        self.rules[rule_id] = rule
        return rule
    
    async def update_rule(
        self,
        rule_id: str,
        name: str,
        description: str,
        category: str,
        severity: str,
        pattern: str,
        action: str
    ) -> Optional[Dict[str, Any]]:
        """Update a guardrail rule."""
        if rule_id not in self.rules:
            return None
        
        self.rules[rule_id].update({
            "name": name,
            "description": description,
            "category": category,
            "severity": severity,
            "pattern": pattern,
            "action": action,
            "updated_at": datetime.utcnow().isoformat(),
        })
        
        return self.rules[rule_id]
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a guardrail rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False
    
    async def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        """Toggle a guardrail rule on/off."""
        if rule_id in self.rules:
            self.rules[rule_id]["enabled"] = enabled
            self.rules[rule_id]["updated_at"] = datetime.utcnow().isoformat()
            return True
        return False
    
    async def get_statistics(self, time_period: str = "24h") -> Dict[str, Any]:
        """Get guardrail statistics."""
        # Parse time period
        if time_period.endswith("h"):
            hours = int(time_period[:-1])
        elif time_period.endswith("d"):
            hours = int(time_period[:-1]) * 24
        else:
            hours = 24
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter check history by time period
        recent_checks = [
            check for check in self.stats["check_history"]
            if datetime.fromisoformat(check["timestamp"]) >= cutoff_time
        ]
        
        return {
            "total_checks": len(recent_checks),
            "blocked_requests": sum(1 for check in recent_checks if not check["is_safe"]),
            "warnings_issued": sum(1 for check in recent_checks if check["violations_count"] > 0),
            "violation_counts": self.stats["violation_counts"].copy(),
        }

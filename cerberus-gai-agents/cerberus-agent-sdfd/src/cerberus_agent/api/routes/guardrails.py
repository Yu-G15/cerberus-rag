"""Guardrail endpoints for content safety and compliance."""

from typing import List, Dict, Any, Optional
from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from cerberus_agent.core.config import get_settings
from cerberus_agent.core.config import Settings
from cerberus_agent.services.guardrail_service import GuardrailService

logger = structlog.get_logger(__name__)
router = APIRouter()


class GuardrailCheckRequest(BaseModel):
    """Guardrail check request model."""
    content: str = Field(..., description="Content to check", min_length=1, max_length=50000)
    check_types: Optional[List[str]] = Field(None, description="Specific guardrail types to check")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for checks")


class GuardrailCheckResponse(BaseModel):
    """Guardrail check response model."""
    safe: bool = Field(..., description="Whether content is safe")
    score: float = Field(..., description="Safety score (0-1)")
    violations: List[Dict[str, Any]] = Field(default_factory=list, description="Detected violations")
    recommendations: List[str] = Field(default_factory=list, description="Safety recommendations")
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    check_types: List[str] = Field(..., description="Types of checks performed")


class GuardrailRule(BaseModel):
    """Guardrail rule model."""
    id: str = Field(..., description="Rule ID")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    category: str = Field(..., description="Rule category")
    severity: str = Field(..., description="Rule severity: low, medium, high, critical")
    enabled: bool = Field(..., description="Whether rule is enabled")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GuardrailRuleCreate(BaseModel):
    """Guardrail rule creation model."""
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    category: str = Field(..., description="Rule category")
    severity: str = Field(..., description="Rule severity")
    pattern: str = Field(..., description="Rule pattern or criteria")
    action: str = Field(..., description="Action to take: block, warn, log")


class GuardrailStats(BaseModel):
    """Guardrail statistics model."""
    total_checks: int = Field(..., description="Total number of checks performed")
    blocked_requests: int = Field(..., description="Number of blocked requests")
    warnings_issued: int = Field(..., description="Number of warnings issued")
    violation_counts: Dict[str, int] = Field(default_factory=dict, description="Count by violation type")
    time_period: str = Field(..., description="Time period for statistics")


@router.post("/check", response_model=GuardrailCheckResponse)
async def check_content(
    request: GuardrailCheckRequest,
    settings: Settings = Depends(get_settings)
) -> GuardrailCheckResponse:
    """Check content against guardrails."""
    try:
        guardrail_service = GuardrailService(settings)
        
        result = await guardrail_service.check_content(
            content=request.content,
            check_types=request.check_types,
            context=request.context,
        )
        
        return GuardrailCheckResponse(
            safe=result["safe"],
            score=result["score"],
            violations=result["violations"],
            recommendations=result["recommendations"],
            check_types=result["check_types"],
        )
        
    except Exception as e:
        logger.error("Guardrail check failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Guardrail check failed")


@router.get("/rules", response_model=List[GuardrailRule])
async def list_guardrail_rules(settings: Settings = Depends(get_settings)) -> List[GuardrailRule]:
    """List all guardrail rules."""
    try:
        guardrail_service = GuardrailService(settings)
        rules = await guardrail_service.list_rules()
        
        return rules
        
    except Exception as e:
        logger.error("Failed to list guardrail rules", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list guardrail rules")


@router.post("/rules", response_model=GuardrailRule)
async def create_guardrail_rule(
    request: GuardrailRuleCreate,
    settings: Settings = Depends(get_settings)
) -> GuardrailRule:
    """Create a new guardrail rule."""
    try:
        guardrail_service = GuardrailService(settings)
        
        rule = await guardrail_service.create_rule(
            name=request.name,
            description=request.description,
            category=request.category,
            severity=request.severity,
            pattern=request.pattern,
            action=request.action,
        )
        
        return rule
        
    except Exception as e:
        logger.error("Failed to create guardrail rule", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create guardrail rule")


@router.put("/rules/{rule_id}", response_model=GuardrailRule)
async def update_guardrail_rule(
    rule_id: str,
    request: GuardrailRuleCreate,
    settings: Settings = Depends(get_settings)
) -> GuardrailRule:
    """Update a guardrail rule."""
    try:
        guardrail_service = GuardrailService(settings)
        
        rule = await guardrail_service.update_rule(
            rule_id=rule_id,
            name=request.name,
            description=request.description,
            category=request.category,
            severity=request.severity,
            pattern=request.pattern,
            action=request.action,
        )
        
        if not rule:
            raise HTTPException(status_code=404, detail="Guardrail rule not found")
        
        return rule
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update guardrail rule", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update guardrail rule")


@router.delete("/rules/{rule_id}")
async def delete_guardrail_rule(
    rule_id: str,
    settings: Settings = Depends(get_settings)
) -> Dict[str, str]:
    """Delete a guardrail rule."""
    try:
        guardrail_service = GuardrailService(settings)
        
        success = await guardrail_service.delete_rule(rule_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Guardrail rule not found")
        
        return {"message": "Guardrail rule deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete guardrail rule", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete guardrail rule")


@router.get("/stats", response_model=GuardrailStats)
async def get_guardrail_stats(
    time_period: str = "24h",
    settings: Settings = Depends(get_settings)
) -> GuardrailStats:
    """Get guardrail statistics."""
    try:
        guardrail_service = GuardrailService(settings)
        
        stats = await guardrail_service.get_statistics(time_period)
        
        return GuardrailStats(
            total_checks=stats["total_checks"],
            blocked_requests=stats["blocked_requests"],
            warnings_issued=stats["warnings_issued"],
            violation_counts=stats["violation_counts"],
            time_period=time_period,
        )
        
    except Exception as e:
        logger.error("Failed to get guardrail stats", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get guardrail stats")


@router.post("/rules/{rule_id}/toggle")
async def toggle_guardrail_rule(
    rule_id: str,
    enabled: bool,
    settings: Settings = Depends(get_settings)
) -> Dict[str, str]:
    """Toggle a guardrail rule on/off."""
    try:
        guardrail_service = GuardrailService(settings)
        
        success = await guardrail_service.toggle_rule(rule_id, enabled)
        
        if not success:
            raise HTTPException(status_code=404, detail="Guardrail rule not found")
        
        status = "enabled" if enabled else "disabled"
        return {"message": f"Guardrail rule {status} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to toggle guardrail rule", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to toggle guardrail rule")

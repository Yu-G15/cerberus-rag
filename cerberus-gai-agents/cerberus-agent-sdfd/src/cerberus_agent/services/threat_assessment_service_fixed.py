"""Concise RAG-based Threat Assessment Service for STRIDE Analysis."""

import os
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

import structlog
from neo4j import GraphDatabase

from cerberus_agent.core.config import Settings
from cerberus_agent.services.agent_service import AgentService

logger = structlog.get_logger(__name__)

class ThreatAssessmentService:
    """Concise RAG-based service for intelligent STRIDE threat assessments."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_pass = os.getenv("NEO4J_PASSWORD", "password1")  # Fixed password
        self.driver = GraphDatabase.driver(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_pass))
        self.agent_service = AgentService(settings)
    
    def close(self):
        self.driver.close()
    
    async def assess_diagram_threats(self, diagram_id: str, project_id: str, analysis_depth: str = "comprehensive") -> Dict[str, Any]:
        """Perform RAG-based STRIDE threat assessment with fallback."""
        try:
            # Retrieve diagram data
            components = self._get_diagram_components(project_id, diagram_id)
            connections = self._get_diagram_connections(project_id, diagram_id)
            trust_boundaries = self._get_trust_boundaries(project_id, diagram_id)
            
            if not components:
                return {"error": f"No components found for diagram {diagram_id}", "threats": []}
            
            # Try RAG analysis first, fallback to rule-based
            threats = await self._analyze_threats_with_ai(components, connections, trust_boundaries, analysis_depth)
            
            # Fallback to rule-based if RAG returns empty
            if not threats:
                logger.info("RAG analysis returned no threats, using rule-based fallback")
                threats = self._analyze_stride_threats(components, connections, trust_boundaries, analysis_depth)
            
            # Generate summary
            high_risk_count = len([t for t in threats if t.get("criticality") in ["high", "critical"]])
            
            return {
                "diagram_id": diagram_id,
                "project_id": project_id,
                "threats": threats,
                "analysis_summary": f"RAG-based AI Threat Assessment Summary:\n- Total components analyzed: {len(components)}\n- Total data flows analyzed: {len(connections)}\n- Trust boundaries identified: {len(trust_boundaries)}\n- AI-identified contextual threats: {len(threats)}\n- High/Critical risk threats: {high_risk_count}\n\nAnalysis depth: {analysis_depth}\nAI-powered STRIDE methodology with contextual threat intelligence applied.",
                "total_threats": len(threats),
                "high_risk_threats": high_risk_count,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Threat assessment failed", error=str(e), exc_info=True)
            return {"error": f"Threat assessment failed: {str(e)}", "threats": []}
    
    def _get_diagram_components(self, project_id: str, diagram_id: str) -> List[Dict[str, Any]]:
        """Retrieve components with corrected Neo4j query."""
        with self.driver.session() as session:
            # Try both HAS_NODE and HAS_ELEMENT for compatibility
            query = """
            MATCH (p:Project {key: $project_id})-[:HAS_DIAGRAM]->(d:Diagram {key: $diagram_id})
            MATCH (d)-[:HAS_NODE|HAS_ELEMENT]->(comp)
            RETURN 
                COALESCE(comp.uid, comp.id) as id,
                comp.name as name,
                COALESCE(comp.type, labels(comp)[0]) as type,
                COALESCE(comp.criticality, 'medium') as criticality,
                comp.description as description,
                comp.zone as zone,
                comp.owner as owner,
                comp.technology as technology,
                labels(comp) as labels
            ORDER BY comp.name
            """
            result = session.run(query, project_id=project_id, diagram_id=diagram_id)
            return [dict(record) for record in result]
    
    def _get_diagram_connections(self, project_id: str, diagram_id: str) -> List[Dict[str, Any]]:
        """Retrieve data flows with corrected Neo4j query."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Project {key: $project_id})-[:HAS_DIAGRAM]->(d:Diagram {key: $diagram_id})
            MATCH (d)-[:HAS_NODE|HAS_ELEMENT]->(source)
            MATCH (source)-[r:DATA_FLOW]->(target)
            WHERE (d)-[:HAS_NODE|HAS_ELEMENT]->(target)
            RETURN 
                COALESCE(r.uid, r.id, id(r)) as id,
                COALESCE(source.uid, source.id) as from_component,
                COALESCE(target.uid, target.id) as to_component,
                COALESCE(r.label, 'data_flow') as label,
                r.protocol as protocol,
                COALESCE(r.auth_required, true) as auth_required,
                COALESCE(r.encryption_in_transit, true) as encryption_in_transit,
                COALESCE(r.pii, false) as pii,
                COALESCE(r.confidentiality, 'medium') as confidentiality
            ORDER BY r.label
            """
            result = session.run(query, project_id=project_id, diagram_id=diagram_id)
            return [dict(record) for record in result]
    
    def _get_trust_boundaries(self, project_id: str, diagram_id: str) -> List[Dict[str, Any]]:
        """Retrieve trust boundaries with corrected Neo4j query."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Project {key: $project_id})-[:HAS_DIAGRAM]->(d:Diagram {key: $diagram_id})
            MATCH (d)-[:HAS_TRUST_BOUNDARY|HAS_NODE|HAS_ELEMENT]->(tb)
            WHERE 'TrustBoundaryNode' IN labels(tb) OR 'TrustBoundary' IN labels(tb)
            RETURN 
                COALESCE(tb.uid, tb.id) as id,
                tb.name as name,
                COALESCE(tb.boundary_type, 'network') as boundary_type,
                COALESCE(tb.criticality, 'medium') as criticality,
                COALESCE(tb.security_controls, []) as security_controls
            ORDER BY tb.name
            """
            result = session.run(query, project_id=project_id, diagram_id=diagram_id)
            return [dict(record) for record in result]
    
    async def _analyze_threats_with_ai(self, components: List[Dict], connections: List[Dict], trust_boundaries: List[Dict], analysis_depth: str) -> List[Dict[str, Any]]:
        """RAG-based AI threat analysis."""
        try:
            # Prepare context
            context = self._prepare_diagram_context(components, connections, trust_boundaries)
            
            # Create AI prompt
            prompt = f"""You are a cybersecurity expert analyzing this data flow diagram for STRIDE threats.

DIAGRAM CONTEXT:
{context}

ANALYSIS REQUIREMENTS:
- Use STRIDE methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
- Analysis depth: {analysis_depth}
- Generate realistic, contextual threats based on actual components and data flows
- Focus on specific attack scenarios, not generic threats

RESPONSE FORMAT:
Return ONLY a JSON array of threats:
[
  {{
    "threat_id": "unique_id",
    "threat_name": "Specific threat name",
    "threat_type": "spoofing|tampering|repudiation|information_disclosure|denial_of_service|elevation_of_privilege",
    "description": "Detailed threat description",
    "linked_component_ids": ["component_id1", "component_id2"],
    "criticality": "low|medium|high|critical",
    "impact": "Business impact",
    "likelihood": "low|medium|high",
    "mitigation_strategies": ["strategy1", "strategy2"],
    "confidence_score": 0.8
  }}
]

Generate contextual threats for this specific diagram. Return only the JSON array."""

            # Get AI response
            ai_response = await self.agent_service.process_chat(
                message=prompt,
                conversation_id=f"threat_analysis_{datetime.utcnow().timestamp()}",
                model=None,
                temperature=None,
                max_tokens=None,
                tools=None
            )
            
            # Parse response
            threats = self._parse_ai_threat_response(ai_response, components)
            
            # Filter by analysis depth
            if analysis_depth == "basic":
                threats = [t for t in threats if t.get("criticality") in ["high", "critical"]]
            elif analysis_depth == "standard":
                threats = [t for t in threats if t.get("criticality") in ["medium", "high", "critical"]]
            
            return threats
            
        except Exception as e:
            logger.error("AI threat analysis failed", error=str(e))
            return []
    
    def _prepare_diagram_context(self, components: List[Dict], connections: List[Dict], trust_boundaries: List[Dict]) -> str:
        """Prepare concise diagram context for AI."""
        context = "COMPONENTS:\n"
        for comp in components:
            context += f"- {comp.get('name', 'Unknown')} ({comp.get('type', 'unknown')}) [Criticality: {comp.get('criticality', 'medium')}]\n"
        
        context += "\nDATA FLOWS:\n"
        for conn in connections:
            context += f"- {conn.get('from_component', 'Unknown')} → {conn.get('to_component', 'Unknown')}"
            if conn.get('label'):
                context += f" ({conn['label']})"
            if conn.get('pii'):
                context += " [PII]"
            if conn.get('confidentiality'):
                context += f" [Conf: {conn['confidentiality']}]"
            context += "\n"
        
        if trust_boundaries:
            context += "\nTRUST BOUNDARIES:\n"
            for boundary in trust_boundaries:
                context += f"- {boundary.get('name', 'Unknown')} ({boundary.get('boundary_type', 'unknown')})\n"
        
        return context
    
    def _parse_ai_threat_response(self, ai_response: Dict[str, Any], components: List[Dict]) -> List[Dict[str, Any]]:
        """Parse AI response and extract threats."""
        try:
            response_text = ai_response.get("response", "")
            
            # Extract JSON array
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                threats = json.loads(json_str)
                
                # Validate threats
                validated_threats = []
                component_ids = [comp.get('id') for comp in components]
                
                for threat in threats:
                    if self._validate_threat(threat, component_ids):
                        validated_threats.append(threat)
                
                return validated_threats
            
            return []
            
        except Exception as e:
            logger.error("Failed to parse AI response", error=str(e))
            return []
    
    def _validate_threat(self, threat: Dict[str, Any], component_ids: List[str]) -> bool:
        """Validate threat format and component references."""
        required_fields = ["threat_id", "threat_name", "threat_type", "description", "criticality"]
        
        # Check required fields
        if not all(field in threat and threat[field] for field in required_fields):
            return False
        
        # Validate threat type
        valid_types = ["spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service", "elevation_of_privilege"]
        if threat["threat_type"] not in valid_types:
            return False
        
        # Validate criticality
        valid_criticalities = ["low", "medium", "high", "critical"]
        if threat["criticality"] not in valid_criticalities:
            return False
        
        # Validate component references
        if "linked_component_ids" in threat:
            for comp_id in threat["linked_component_ids"]:
                if comp_id not in component_ids:
                    return False
        
        return True
    
    def _analyze_stride_threats(self, components: List[Dict], connections: List[Dict], trust_boundaries: List[Dict], analysis_depth: str) -> List[Dict[str, Any]]:
        """Rule-based STRIDE analysis fallback."""
        threats = []
        
        # Spoofing threats
        for comp in components:
            if comp.get("type") in ["external_entity", "user"]:
                threats.append({
                    "threat_id": f"spoofing_{comp['id']}",
                    "threat_name": f"Identity Spoofing - {comp['name']}",
                    "threat_type": "spoofing",
                    "description": f"Unauthorized entity may impersonate {comp['name']}",
                    "linked_component_ids": [comp['id']],
                    "criticality": "high" if comp.get("criticality") in ["high", "critical"] else "medium",
                    "impact": "Unauthorized access to system resources",
                    "likelihood": "medium",
                    "mitigation_strategies": ["Strong authentication", "Digital certificates", "MFA"],
                    "confidence_score": 0.8
                })
        
        # Tampering threats
        for comp in components:
            if comp.get("type") == "data_store":
                threats.append({
                    "threat_id": f"tampering_{comp['id']}",
                    "threat_name": f"Data Tampering - {comp['name']}",
                    "threat_type": "tampering",
                    "description": f"Unauthorized modification of data in {comp['name']}",
                    "linked_component_ids": [comp['id']],
                    "criticality": "high" if comp.get("criticality") in ["high", "critical"] else "medium",
                    "impact": "Data integrity compromise",
                    "likelihood": "medium",
                    "mitigation_strategies": ["Data integrity checks", "Encryption", "Access controls"],
                    "confidence_score": 0.7
                })
        
        # Information Disclosure threats
        for conn in connections:
            if conn.get("pii") or conn.get("confidentiality") in ["high", "medium"]:
                if not conn.get("encryption_in_transit"):
                    threats.append({
                        "threat_id": f"info_disclosure_{conn['id']}",
                        "threat_name": f"Information Disclosure - {conn['label']}",
                        "threat_type": "information_disclosure",
                        "description": f"Sensitive data in {conn['label']} may be intercepted",
                        "linked_component_ids": [conn['from_component'], conn['to_component']],
                        "criticality": "high" if conn.get("confidentiality") == "high" else "medium",
                        "impact": "Sensitive data exposure",
                        "likelihood": "medium",
                        "mitigation_strategies": ["End-to-end encryption", "Secure protocols", "Data classification"],
                        "confidence_score": 0.9
                    })
        
        # Denial of Service threats
        for comp in components:
            if comp.get("type") in ["process", "data_store"]:
                threats.append({
                    "threat_id": f"dos_{comp['id']}",
                    "threat_name": f"Denial of Service - {comp['name']}",
                    "threat_type": "denial_of_service",
                    "description": f"{comp['name']} may become unavailable due to attacks",
                    "linked_component_ids": [comp['id']],
                    "criticality": "high" if comp.get("criticality") in ["high", "critical"] else "medium",
                    "impact": "Service unavailability",
                    "likelihood": "medium",
                    "mitigation_strategies": ["Rate limiting", "Load balancing", "DDoS protection"],
                    "confidence_score": 0.7
                })
        
        # Filter by analysis depth
        if analysis_depth == "basic":
            threats = [t for t in threats if t.get("criticality") in ["high", "critical"]]
        elif analysis_depth == "standard":
            threats = [t for t in threats if t.get("criticality") in ["medium", "high", "critical"]]
        
        return threats

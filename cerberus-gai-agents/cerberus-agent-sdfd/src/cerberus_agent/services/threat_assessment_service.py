"""RAG-based Threat Assessment Service for STRIDE Analysis."""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

import structlog
from neo4j import GraphDatabase

from cerberus_agent.core.config import Settings
from cerberus_agent.services.agent_service import AgentService

logger = structlog.get_logger(__name__)

class ThreatAssessmentService:
    """RAG-based service for performing intelligent STRIDE threat assessments on diagrams."""
    
    def __init__(self, settings: Settings):
        """Initialize the RAG-based threat assessment service."""
        self.settings = settings
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_pass = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_pass))
        self.assessments: Dict[str, Dict[str, Any]] = {}
        
        # Initialize AI agent for intelligent threat analysis
        self.agent_service = AgentService(settings)
    
    def close(self):
        """Close the Neo4j driver."""
        self.driver.close()
    
    async def assess_diagram_threats(
        self, 
        diagram_id: str, 
        project_id: str, 
        analysis_depth: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Perform RAG-based STRIDE threat assessment on a diagram using AI agent."""
        try:
            # Get diagram components
            components = self._get_diagram_components(project_id, diagram_id)
            connections = self._get_diagram_connections(project_id, diagram_id)
            trust_boundaries = self._get_trust_boundaries(project_id, diagram_id)
            
            if not components:
                return {
                    "error": f"No components found for diagram {diagram_id} in project {project_id}",
                    "threats": [],
                    "analysis_summary": "No components to analyze"
                }
            
            # Use AI agent for intelligent threat analysis
            threats = await self._analyze_threats_with_ai(
                components, connections, trust_boundaries, analysis_depth
            )
            
            # Generate analysis summary
            high_risk_count = len([t for t in threats if t.get("criticality") in ["high", "critical"]])
            analysis_summary = f"""
            RAG-based AI Threat Assessment Summary:
            - Total components analyzed: {len(components)}
            - Total data flows analyzed: {len(connections)}
            - Trust boundaries identified: {len(trust_boundaries)}
            - AI-identified contextual threats: {len(threats)}
            - High/Critical risk threats: {high_risk_count}
            
            Analysis depth: {analysis_depth}
            AI-powered STRIDE methodology with contextual threat intelligence applied.
            """
            
            result = {
                "diagram_id": diagram_id,
                "project_id": project_id,
                "threats": threats,
                "analysis_summary": analysis_summary.strip(),
                "total_threats": len(threats),
                "high_risk_threats": high_risk_count,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error("RAG-based threat assessment failed", error=str(e), exc_info=True)
            return {
                "error": f"RAG-based threat assessment failed: {str(e)}",
                "threats": [],
                "analysis_summary": f"AI analysis failed with error: {str(e)}"
            }
    
    def _get_diagram_components(self, project_id: str, diagram_id: str) -> List[Dict[str, Any]]:
        """Retrieve all components from a diagram."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Project {key: $project_id})-[:HAS_DIAGRAM]->(d:Diagram {key: $diagram_id})
            MATCH (d)-[:HAS_ELEMENT]->(comp)
            RETURN 
                comp.uid as id,
                comp.name as name,
                labels(comp)[0] as type,
                comp.criticality as criticality,
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
        """Retrieve all connections from a diagram."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Project {key: $project_id})-[:HAS_DIAGRAM]->(d:Diagram {key: $diagram_id})
            MATCH (d)-[:HAS_ELEMENT]->(source)
            MATCH (source)-[r:DATA_FLOW]->(target)
            RETURN 
                r.uid as id,
                source.uid as from_component,
                target.uid as to_component,
                r.label as label,
                r.protocol as protocol,
                r.auth_required as auth_required,
                r.encryption_in_transit as encryption_in_transit,
                r.pii as pii,
                r.confidentiality as confidentiality
            ORDER BY r.label
            """
            result = session.run(query, project_id=project_id, diagram_id=diagram_id)
            return [dict(record) for record in result]
    
    def _get_trust_boundaries(self, project_id: str, diagram_id: str) -> List[Dict[str, Any]]:
        """Retrieve trust boundaries from a diagram."""
        with self.driver.session() as session:
            query = """
            MATCH (p:Project {key: $project_id})-[:HAS_DIAGRAM]->(d:Diagram {key: $diagram_id})
            MATCH (d)-[:HAS_TRUST_BOUNDARY]->(tb:TrustBoundaryNode)
            RETURN 
                tb.uid as id,
                tb.name as name,
                tb.boundary_type as boundary_type,
                tb.criticality as criticality,
                tb.security_controls as security_controls
            ORDER BY tb.name
            """
            result = session.run(query, project_id=project_id, diagram_id=diagram_id)
            return [dict(record) for record in result]
    
    def _analyze_stride_threats(
        self, 
        components: List[Dict], 
        connections: List[Dict], 
        trust_boundaries: List[Dict], 
        analysis_depth: str
    ) -> List[Dict[str, Any]]:
        """Analyze components and generate STRIDE threat suggestions."""
        threats = []
        
        # Spoofing threats
        threats.extend(self._analyze_spoofing_threats(components, connections))
        
        # Tampering threats
        threats.extend(self._analyze_tampering_threats(components, connections))
        
        # Repudiation threats
        threats.extend(self._analyze_repudiation_threats(components, connections))
        
        # Information Disclosure threats
        threats.extend(self._analyze_information_disclosure_threats(components, connections))
        
        # Denial of Service threats
        threats.extend(self._analyze_denial_of_service_threats(components, connections))
        
        # Elevation of Privilege threats
        threats.extend(self._analyze_elevation_of_privilege_threats(components, connections))
        
        # Filter based on analysis depth
        if analysis_depth == "basic":
            threats = [t for t in threats if t.get("criticality") in ["high", "critical"]]
        elif analysis_depth == "standard":
            threats = [t for t in threats if t.get("criticality") in ["medium", "high", "critical"]]
        # comprehensive includes all threats
        
        return threats
    
    def _analyze_spoofing_threats(self, components: List[Dict], connections: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze for spoofing threats."""
        threats = []
        
        for component in components:
            if component.get("type") == "external_entity":
                threats.append({
                    "threat_id": f"spoofing_{component['id']}",
                    "threat_name": f"Identity Spoofing - {component['name']}",
                    "threat_type": "spoofing",
                    "description": f"Unauthorized entity may impersonate {component['name']} to gain access to the system",
                    "linked_component_ids": [component['id']],
                    "criticality": "high" if component.get("criticality") in ["high", "critical"] else "medium",
                    "impact": "Unauthorized access to system resources and data",
                    "likelihood": "medium",
                    "mitigation_strategies": [
                        "Implement strong authentication mechanisms",
                        "Use digital certificates for entity verification",
                        "Implement multi-factor authentication",
                        "Regular identity verification and monitoring"
                    ],
                    "confidence_score": 0.8
                })
        
        return threats
    
    def _analyze_tampering_threats(self, components: List[Dict], connections: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze for tampering threats."""
        threats = []
        
        for component in components:
            if component.get("type") == "data_store":
                threats.append({
                    "threat_id": f"tampering_{component['id']}",
                    "threat_name": f"Data Tampering - {component['name']}",
                    "threat_type": "tampering",
                    "description": f"Unauthorized modification of data in {component['name']}",
                    "linked_component_ids": [component['id']],
                    "criticality": "high" if component.get("criticality") in ["high", "critical"] else "medium",
                    "impact": "Data integrity compromise, potential business impact",
                    "likelihood": "medium",
                    "mitigation_strategies": [
                        "Implement data integrity checks",
                        "Use database encryption",
                        "Implement access controls and audit logging",
                        "Regular data backup and recovery procedures"
                    ],
                    "confidence_score": 0.7
                })
        
        return threats
    
    def _analyze_repudiation_threats(self, components: List[Dict], connections: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze for repudiation threats."""
        threats = []
        
        for connection in connections:
            if connection.get("pii") or connection.get("confidentiality") in ["high", "medium"]:
                threats.append({
                    "threat_id": f"repudiation_{connection['id']}",
                    "threat_name": f"Transaction Repudiation - {connection['label']}",
                    "threat_type": "repudiation",
                    "description": f"Users may deny performing transactions through {connection['label']}",
                    "linked_component_ids": [connection['from_component'], connection['to_component']],
                    "criticality": "medium",
                    "impact": "Legal and compliance issues, audit trail gaps",
                    "likelihood": "low",
                    "mitigation_strategies": [
                        "Implement digital signatures",
                        "Comprehensive audit logging",
                        "Transaction receipts and confirmations",
                        "Timestamp and sequence number tracking"
                    ],
                    "confidence_score": 0.6
                })
        
        return threats
    
    def _analyze_information_disclosure_threats(self, components: List[Dict], connections: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze for information disclosure threats."""
        threats = []
        
        for connection in connections:
            if connection.get("pii") or connection.get("confidentiality") in ["high", "medium"]:
                if not connection.get("encryption_in_transit"):
                    threats.append({
                        "threat_id": f"info_disclosure_{connection['id']}",
                        "threat_name": f"Information Disclosure - {connection['label']}",
                        "threat_type": "information_disclosure",
                        "description": f"Sensitive data in {connection['label']} may be intercepted or leaked",
                        "linked_component_ids": [connection['from_component'], connection['to_component']],
                        "criticality": "high" if connection.get("confidentiality") == "high" else "medium",
                        "impact": "Sensitive data exposure, privacy violations, regulatory compliance issues",
                        "likelihood": "medium",
                        "mitigation_strategies": [
                            "Implement end-to-end encryption",
                            "Use secure communication protocols (TLS/SSL)",
                            "Implement data classification and handling policies",
                            "Regular security assessments and penetration testing"
                        ],
                        "confidence_score": 0.9
                    })
        
        return threats
    
    def _analyze_denial_of_service_threats(self, components: List[Dict], connections: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze for denial of service threats."""
        threats = []
        
        for component in components:
            if component.get("type") in ["process", "data_store"]:
                threats.append({
                    "threat_id": f"dos_{component['id']}",
                    "threat_name": f"Denial of Service - {component['name']}",
                    "threat_type": "denial_of_service",
                    "description": f"{component['name']} may become unavailable due to resource exhaustion or attacks",
                    "linked_component_ids": [component['id']],
                    "criticality": "high" if component.get("criticality") in ["high", "critical"] else "medium",
                    "impact": "Service unavailability, business disruption",
                    "likelihood": "medium",
                    "mitigation_strategies": [
                        "Implement rate limiting and throttling",
                        "Use load balancing and redundancy",
                        "Implement resource monitoring and alerting",
                        "DDoS protection and traffic filtering"
                    ],
                    "confidence_score": 0.7
                })
        
        return threats
    
    def _analyze_elevation_of_privilege_threats(self, components: List[Dict], connections: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze for elevation of privilege threats."""
        threats = []
        
        for component in components:
            if component.get("type") == "process":
                threats.append({
                    "threat_id": f"elevation_{component['id']}",
                    "threat_name": f"Privilege Escalation - {component['name']}",
                    "threat_type": "elevation_of_privilege",
                    "description": f"Unauthorized users may gain elevated privileges in {component['name']}",
                    "linked_component_ids": [component['id']],
                    "criticality": "high" if component.get("criticality") in ["high", "critical"] else "medium",
                    "impact": "Unauthorized access to sensitive resources and administrative functions",
                    "likelihood": "low",
                    "mitigation_strategies": [
                        "Implement principle of least privilege",
                        "Regular privilege audits and reviews",
                        "Use role-based access control (RBAC)",
                        "Implement privilege escalation monitoring and alerting"
                    ],
                    "confidence_score": 0.6
                })
        
        return threats
    
    async def _analyze_threats_with_ai(
        self, 
        components: List[Dict], 
        connections: List[Dict], 
        trust_boundaries: List[Dict], 
        analysis_depth: str
    ) -> List[Dict[str, Any]]:
        """Use AI agent for intelligent, contextual threat analysis."""
        try:
            # Prepare diagram context for AI analysis
            diagram_context = self._prepare_diagram_context(components, connections, trust_boundaries)
            
            # Create AI prompt for threat analysis
            ai_prompt = self._create_threat_analysis_prompt(diagram_context, analysis_depth)
            
            # Create specialized system prompt for threat analysis
            threat_system_prompt = """You are a cybersecurity expert specializing in STRIDE threat modeling analysis. 

CRITICAL INSTRUCTIONS:
- You MUST respond with ONLY valid JSON arrays
- Do NOT use haiku format or any other text formatting
- Do NOT include any explanatory text before or after the JSON
- Your response must be a valid JSON array that can be parsed directly
- Focus on providing structured, technical threat analysis data

Your role is to analyze data flow diagrams and return structured threat information in JSON format."""
            
            # Set custom system prompt for threat analysis
            self.agent_service._custom_system_prompt = threat_system_prompt
            
            try:
                # Use AI agent to analyze threats with custom system prompt
                ai_response = await self.agent_service.process_chat(
                    message=ai_prompt,
                    conversation_id=f"threat_analysis_{datetime.utcnow().timestamp()}",
                    model=None,
                    temperature=None,
                    max_tokens=None,
                    tools=None
                )
            finally:
                # Reset system prompt
                self.agent_service._custom_system_prompt = None
            
            # Parse AI response and convert to threat format
            threats = self._parse_ai_threat_response(ai_response, components, connections)
            
            # Filter based on analysis depth
            if analysis_depth == "basic":
                threats = [t for t in threats if t.get("criticality") in ["high", "critical"]]
            elif analysis_depth == "standard":
                threats = [t for t in threats if t.get("criticality") in ["medium", "high", "critical"]]
            
            return threats
            
        except Exception as e:
            logger.error("AI threat analysis failed", error=str(e))
            # Return empty threats if AI analysis fails - no fallback to rule-based
            return []
    
    def _prepare_diagram_context(
        self, 
        components: List[Dict], 
        connections: List[Dict], 
        trust_boundaries: List[Dict]
    ) -> str:
        """Prepare diagram context for AI analysis."""
        context = "Data Flow Diagram Analysis Context:\n\n"
        
        # Components section
        context += "COMPONENTS:\n"
        for comp in components:
            context += f"- {comp.get('name', 'Unknown')} ({comp.get('type', 'unknown')}) "
            context += f"[Criticality: {comp.get('criticality', 'medium')}]\n"
            if comp.get('description'):
                context += f"  Description: {comp['description']}\n"
        
        # Connections section
        context += "\nDATA FLOWS:\n"
        for conn in connections:
            context += f"- {conn.get('from_component', 'Unknown')} → {conn.get('to_component', 'Unknown')}\n"
            if conn.get('label'):
                context += f"  Label: {conn['label']}\n"
            if conn.get('pii'):
                context += f"  Contains PII: Yes\n"
            if conn.get('confidentiality'):
                context += f"  Confidentiality: {conn['confidentiality']}\n"
        
        # Trust boundaries section
        if trust_boundaries:
            context += "\nTRUST BOUNDARIES:\n"
            for boundary in trust_boundaries:
                context += f"- {boundary.get('name', 'Unknown')} ({boundary.get('boundary_type', 'unknown')})\n"
        
        return context
    
    def _create_threat_analysis_prompt(self, diagram_context: str, analysis_depth: str) -> str:
        """Create AI prompt for threat analysis."""
        return f"""
You are a cybersecurity expert performing STRIDE threat modeling analysis on a data flow diagram.

CRITICAL: You MUST respond with ONLY a valid JSON array. Do not include any text before or after the JSON. Do not use haiku format. This is a technical analysis request that requires structured JSON output.

DIAGRAM CONTEXT:
{diagram_context}

ANALYSIS REQUIREMENTS:
- Use STRIDE methodology (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
- Analysis depth: {analysis_depth}
- Focus on realistic, contextual threats based on the actual components and data flows
- Consider component relationships, data sensitivity, and trust boundaries
- Provide specific, actionable threats rather than generic ones

RESPONSE FORMAT - RETURN ONLY THIS JSON STRUCTURE:
[
  {{
    "threat_id": "unique_id",
    "threat_name": "Descriptive threat name",
    "threat_type": "spoofing|tampering|repudiation|information_disclosure|denial_of_service|elevation_of_privilege",
    "description": "Detailed threat description",
    "linked_component_ids": ["component_id1", "component_id2"],
    "criticality": "low|medium|high|critical",
    "impact": "Business impact description",
    "likelihood": "low|medium|high",
    "mitigation_strategies": ["strategy1", "strategy2", "strategy3"],
    "confidence_score": 0.0-1.0
  }}
]

IMPORTANT:
- Only identify threats that are contextually relevant to this specific diagram
- Avoid generic threats that apply to every system
- Consider the actual data flows and component relationships
- Focus on realistic attack scenarios
- Provide specific mitigation strategies
- Return ONLY the JSON array, no other text

Analyze the diagram and return ONLY the JSON array of contextual threats.
"""
    
    def _parse_ai_threat_response(
        self, 
        ai_response: Dict[str, Any], 
        components: List[Dict], 
        connections: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Parse AI response and convert to threat format."""
        try:
            # Extract the response text
            response_text = ai_response.get("response", "")
            logger.info("AI response received", response_length=len(response_text))
            
            # Clean the response text - remove any markdown formatting
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Try to parse as JSON directly first
            try:
                threats = json.loads(cleaned_text)
                if isinstance(threats, list):
                    logger.info("Successfully parsed JSON array directly", threat_count=len(threats))
                else:
                    logger.warning("JSON response is not an array", response_type=type(threats))
                    return []
            except json.JSONDecodeError:
                # Try to find JSON array in the response using regex
                import re
                json_match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    threats = json.loads(json_str)
                    logger.info("Successfully parsed JSON array from regex match", threat_count=len(threats))
                else:
                    logger.warning("No valid JSON array found in AI response", response_preview=cleaned_text[:200])
                    return []
            
            # Validate and clean threats
            validated_threats = []
            for threat in threats:
                if self._validate_threat(threat, components, connections):
                    validated_threats.append(threat)
                else:
                    logger.warning("Invalid threat filtered out", threat=threat)
            
            logger.info("Threat validation completed", 
                       total_threats=len(threats), 
                       valid_threats=len(validated_threats))
            
            return validated_threats
                
        except Exception as e:
            logger.error("Failed to parse AI threat response", error=str(e), exc_info=True)
            return []
    
    def _validate_threat(self, threat: Dict[str, Any], components: List[Dict], connections: List[Dict]) -> bool:
        """Validate that a threat is properly formatted and relevant."""
        required_fields = ["threat_id", "threat_name", "threat_type", "description", "criticality"]
        
        # Check required fields
        for field in required_fields:
            if field not in threat or not threat[field]:
                return False
        
        # Validate threat type
        valid_types = ["spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service", "elevation_of_privilege"]
        if threat["threat_type"] not in valid_types:
            return False
        
        # Validate criticality
        valid_criticalities = ["low", "medium", "high", "critical"]
        if threat["criticality"] not in valid_criticalities:
            return False
        
        # Ensure linked components exist (match by name or id)
        if "linked_component_ids" in threat:
            component_ids = [comp.get("id") for comp in components]
            component_names = [comp.get("name") for comp in components]
            for comp_id in threat["linked_component_ids"]:
                # Check if it matches either an ID or a name
                if comp_id not in component_ids and comp_id not in component_names:
                    return False
        
        return True
    
    async def get_assessment_result(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a threat assessment by ID."""
        return self.assessments.get(assessment_id)

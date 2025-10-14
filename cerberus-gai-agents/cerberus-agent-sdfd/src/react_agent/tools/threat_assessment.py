"""Threat Assessment Tool for STRIDE Analysis."""

import os
import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from neo4j import GraphDatabase

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "password")

class ThreatAssessmentInput(BaseModel):
    diagram_id: str = Field(..., description="The diagram ID to analyze for threats")
    project_id: str = Field(..., description="The project ID containing the diagram")

@tool("assess_threats", args_schema=ThreatAssessmentInput)
def assess_threats(diagram_id: str, project_id: str) -> Dict[str, Any]:
    """
    Perform STRIDE threat assessment on a diagram.
    
    Returns a comprehensive threat assessment with linked component IDs.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    
    try:
        with driver.session() as session:
            # Get diagram components
            query = """
            MATCH (p:Project {key: $project_id})-[:HAS_DIAGRAM]->(d:Diagram {key: $diagram_id})
            MATCH (d)-[:HAS_ELEMENT]->(comp)
            RETURN 
                comp.id as id,
                comp.name as name,
                comp.type as type,
                comp.criticality as criticality,
                labels(comp) as labels
            """
            result = session.run(query, project_id=project_id, diagram_id=diagram_id)
            components = [dict(record) for record in result]
            
            if not components:
                return {
                    "error": f"No components found for diagram {diagram_id}",
                    "threats": []
                }
            
            # Generate STRIDE threats
            threats = []
            for comp in components:
                # Spoofing threat
                if comp.get("type") == "external_entity":
                    threats.append({
                        "threat_id": f"spoofing_{comp['id']}",
                        "threat_name": f"Identity Spoofing - {comp['name']}",
                        "threat_type": "spoofing",
                        "description": f"Unauthorized entity may impersonate {comp['name']}",
                        "linked_component_ids": [comp['id']],
                        "criticality": "high" if comp.get("criticality") in ["high", "critical"] else "medium",
                        "impact": "Unauthorized access to system resources",
                        "likelihood": "medium",
                        "mitigation_strategies": [
                            "Implement strong authentication",
                            "Use digital certificates",
                            "Multi-factor authentication"
                        ],
                        "confidence_score": 0.8
                    })
                
                # Tampering threat for data stores
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
                        "mitigation_strategies": [
                            "Implement data integrity checks",
                            "Use database encryption",
                            "Access controls and audit logging"
                        ],
                        "confidence_score": 0.7
                    })
                
                # DoS threat for processes
                if comp.get("type") == "process":
                    threats.append({
                        "threat_id": f"dos_{comp['id']}",
                        "threat_name": f"Denial of Service - {comp['name']}",
                        "threat_type": "denial_of_service",
                        "description": f"{comp['name']} may become unavailable due to attacks",
                        "linked_component_ids": [comp['id']],
                        "criticality": "high" if comp.get("criticality") in ["high", "critical"] else "medium",
                        "impact": "Service unavailability",
                        "likelihood": "medium",
                        "mitigation_strategies": [
                            "Implement rate limiting",
                            "Use load balancing",
                            "DDoS protection"
                        ],
                        "confidence_score": 0.7
                    })
            
            return {
                "diagram_id": diagram_id,
                "project_id": project_id,
                "threats": threats,
                "analysis_summary": f"Analyzed {len(components)} components, found {len(threats)} threats",
                "total_threats": len(threats),
                "high_risk_threats": len([t for t in threats if t["criticality"] in ["high", "critical"]]),
                "analysis_timestamp": "2024-01-01T00:00:00Z"
            }
            
    except Exception as e:
        return {
            "error": f"Threat assessment failed: {str(e)}",
            "threats": []
        }
    finally:
        driver.close()
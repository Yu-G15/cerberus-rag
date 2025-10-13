"""Threat Assessment API routes."""

import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from cerberus_agent.core.config import get_settings
from cerberus_agent.services.threat_assessment_service import ThreatAssessmentService

logger = structlog.get_logger(__name__)
router = APIRouter()

class ThreatAssessmentRequest(BaseModel):
    diagram_id: str = Field(..., description="The diagram ID to analyze for threats")
    project_id: str = Field(..., description="The project ID containing the diagram")
    analysis_depth: str = Field(default="comprehensive", description="Analysis depth: basic, standard, comprehensive")

class ThreatAssessmentResponse(BaseModel):
    assessment_id: str
    diagram_id: str
    project_id: str
    threats: list
    analysis_summary: str
    total_threats: int
    high_risk_threats: int
    analysis_timestamp: str
    status: str

@router.post("/assess", response_model=ThreatAssessmentResponse)
async def assess_diagram_threats(
    request: ThreatAssessmentRequest,
    settings = Depends(get_settings)
) -> ThreatAssessmentResponse:
    """
    Perform STRIDE threat assessment on a diagram.
    
    This endpoint analyzes a data flow diagram for security threats using the STRIDE methodology:
    - Spoofing: Identity impersonation
    - Tampering: Data modification  
    - Repudiation: Transaction denial
    - Information Disclosure: Data exposure
    - Denial of Service: Service unavailability
    - Elevation of Privilege: Unauthorized access escalation
    
    Returns a comprehensive threat assessment with linked component IDs.
    """
    try:
        assessment_id = str(uuid.uuid4())
        
        # Initialize threat assessment service
        threat_service = ThreatAssessmentService(settings)
        
        # Perform threat assessment
        result = await threat_service.assess_diagram_threats(
            diagram_id=request.diagram_id,
            project_id=request.project_id,
            analysis_depth=request.analysis_depth
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return ThreatAssessmentResponse(
            assessment_id=assessment_id,
            diagram_id=result["diagram_id"],
            project_id=result["project_id"],
            threats=result["threats"],
            analysis_summary=result["analysis_summary"],
            total_threats=result["total_threats"],
            high_risk_threats=result["high_risk_threats"],
            analysis_timestamp=result["analysis_timestamp"],
            status="completed"
        )
        
    except Exception as e:
        logger.error("Threat assessment failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Threat assessment failed: {str(e)}")

@router.get("/assessments/{assessment_id}")
async def get_assessment_result(
    assessment_id: str,
    settings = Depends(get_settings)
) -> Dict[str, Any]:
    """Get the result of a threat assessment by ID."""
    try:
        threat_service = ThreatAssessmentService(settings)
        result = await threat_service.get_assessment_result(assessment_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        return result
        
    except Exception as e:
        logger.error("Failed to get assessment result", assessment_id=assessment_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get assessment result: {str(e)}")

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check for threat assessment service."""
    return {"status": "healthy", "service": "threat-assessment-engine"}

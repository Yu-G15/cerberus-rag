#!/usr/bin/env python3
"""
Test script to verify that the RAG agent returns threats in proper JSON format.
"""

import asyncio
import json
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cerberus_agent.services.threat_assessment_service import ThreatAssessmentService
from cerberus_agent.core.config import Settings

async def test_threat_assessment_json():
    """Test that threat assessment returns proper JSON format."""
    
    # Mock settings
    settings = Settings(
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", "test-key"),
        OPENAI_MODEL="gpt-4",
        OPENAI_TEMPERATURE=0.1,
        OPENAI_MAX_TOKENS=2000,
    )
    
    # Initialize service
    service = ThreatAssessmentService(settings)
    
    try:
        # Test with mock diagram data
        mock_components = [
            {
                "id": "user_1",
                "name": "User",
                "type": "external_entity",
                "criticality": "medium",
                "description": "End user accessing the system"
            },
            {
                "id": "web_app_1", 
                "name": "Web Application",
                "type": "process",
                "criticality": "high",
                "description": "Main web application server"
            },
            {
                "id": "database_1",
                "name": "User Database",
                "type": "data_store", 
                "criticality": "critical",
                "description": "Stores user credentials and personal data"
            }
        ]
        
        mock_connections = [
            {
                "id": "flow_1",
                "from_component": "user_1",
                "to_component": "web_app_1",
                "label": "Login Request",
                "pii": True,
                "confidentiality": "high"
            },
            {
                "id": "flow_2", 
                "from_component": "web_app_1",
                "to_component": "database_1",
                "label": "User Query",
                "pii": True,
                "confidentiality": "high"
            }
        ]
        
        mock_trust_boundaries = [
            {
                "id": "boundary_1",
                "name": "Internet Boundary",
                "boundary_type": "network",
                "criticality": "high"
            }
        ]
        
        print("Testing AI threat analysis with JSON output...")
        
        # Test the AI analysis method directly
        threats = await service._analyze_threats_with_ai(
            components=mock_components,
            connections=mock_connections, 
            trust_boundaries=mock_trust_boundaries,
            analysis_depth="comprehensive"
        )
        
        print(f"\n✅ AI Analysis completed successfully!")
        print(f"📊 Found {len(threats)} threats")
        
        # Validate JSON structure
        if threats:
            print("\n🔍 Sample threat structure:")
            sample_threat = threats[0]
            print(json.dumps(sample_threat, indent=2))
            
            # Validate required fields
            required_fields = ["threat_id", "threat_name", "threat_type", "description", "criticality"]
            missing_fields = [field for field in required_fields if field not in sample_threat]
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return False
            else:
                print("✅ All required fields present")
                
            # Validate threat types
            valid_types = ["spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service", "elevation_of_privilege"]
            if sample_threat.get("threat_type") not in valid_types:
                print(f"❌ Invalid threat type: {sample_threat.get('threat_type')}")
                return False
            else:
                print("✅ Valid threat type")
                
            # Validate criticality
            valid_criticalities = ["low", "medium", "high", "critical"]
            if sample_threat.get("criticality") not in valid_criticalities:
                print(f"❌ Invalid criticality: {sample_threat.get('criticality')}")
                return False
            else:
                print("✅ Valid criticality level")
        
        print(f"\n🎉 Test completed successfully! JSON format is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        service.close()

async def main():
    """Main test function."""
    print("🧪 Testing RAG Agent JSON Threat Assessment")
    print("=" * 50)
    
    success = await test_threat_assessment_json()
    
    if success:
        print("\n✅ All tests passed! The RAG agent is returning threats in proper JSON format.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed! Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

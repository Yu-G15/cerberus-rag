#!/usr/bin/env python3
"""
Script to create a complete threat modeling diagram in Neo4j with all component types.
This creates a realistic e-commerce application diagram with threats and trust boundaries.
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append('/Users/bassimananuar/Documents/Projects/cerberus-ms-rest')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cerberus_ms_rest.settings')
django.setup()

from dfd.models import Project, Diagram, DFDNode, Process, ExternalEntity, DataStore, ThreatNode, TrustBoundaryNode
from neomodel import db

def create_complete_diagram():
    """Create a complete threat modeling diagram"""
    
    print("🚀 Creating complete threat modeling diagram...")
    
    # Clear existing data (optional - comment out if you want to keep existing data)
    print("🧹 Clearing existing data...")
    db.cypher_query("MATCH (n) DETACH DELETE n")
    
    # Create project
    project = Project(
        key="ecommerce_threat_model",
        name="E-commerce Application Threat Model",
        user_id="admin"
    ).save()
    print(f"✅ Created project: {project.name}")
    
    # Create diagram
    diagram = Diagram(
        key="ecommerce_dfd_v1",
        name="E-commerce DFD with Threats",
        meta={"description": "Complete threat model for e-commerce application"}
    ).save()
    print(f"✅ Created diagram: {diagram.name}")
    
    # Connect diagram to project
    project.diagrams.connect(diagram)
    
    # Create External Entities
    print("👥 Creating external entities...")
    
    user = ExternalEntity(
        key="user",
        name="User",
        description="End user accessing the e-commerce application",
        actor_type="user",
        criticality="high",
        pos_x=50,
        pos_y=200,
        width=120,
        height=80
    ).save()
    
    payment_gateway = ExternalEntity(
        key="payment_gateway",
        name="Payment Gateway",
        description="Third-party payment processing service",
        actor_type="external_service",
        criticality="high",
        pos_x=50,
        pos_y=400,
        width=120,
        height=80
    ).save()
    
    email_service = ExternalEntity(
        key="email_service",
        name="Email Service",
        description="External email notification service",
        actor_type="external_service",
        criticality="medium",
        pos_x=50,
        pos_y=600,
        width=120,
        height=80
    ).save()
    
    # Create Processes
    print("⚙️ Creating processes...")
    
    web_app = Process(
        key="web_app",
        name="Web Application",
        description="Main e-commerce web application",
        tech="Node.js",
        criticality="high",
        pos_x=300,
        pos_y=200,
        width=120,
        height=80
    ).save()
    
    auth_service = Process(
        key="auth_service",
        name="Authentication Service",
        description="User authentication and authorization",
        tech="JWT",
        criticality="high",
        pos_x=300,
        pos_y=350,
        width=120,
        height=80
    ).save()
    
    payment_processor = Process(
        key="payment_processor",
        name="Payment Processor",
        description="Processes payment transactions",
        tech="Python",
        criticality="high",
        pos_x=300,
        pos_y=500,
        width=120,
        height=80
    ).save()
    
    notification_service = Process(
        key="notification_service",
        name="Notification Service",
        description="Sends notifications to users",
        tech="Node.js",
        criticality="medium",
        pos_x=300,
        pos_y=650,
        width=120,
        height=80
    ).save()
    
    # Create Data Stores
    print("💾 Creating data stores...")
    
    user_db = DataStore(
        key="user_database",
        name="User Database",
        description="Stores user account information",
        store_type="database",
        technology="PostgreSQL",
        criticality="high",
        encryption_at_rest=True,
        backups_enabled=True,
        pos_x=550,
        pos_y=200,
        width=120,
        height=80
    ).save()
    
    product_db = DataStore(
        key="product_database",
        name="Product Database",
        description="Stores product catalog and inventory",
        store_type="database",
        technology="MongoDB",
        criticality="medium",
        encryption_at_rest=True,
        backups_enabled=True,
        pos_x=550,
        pos_y=350,
        width=120,
        height=80
    ).save()
    
    payment_db = DataStore(
        key="payment_database",
        name="Payment Database",
        description="Stores payment transaction records",
        store_type="database",
        technology="PostgreSQL",
        criticality="high",
        encryption_at_rest=True,
        backups_enabled=True,
        pos_x=550,
        pos_y=500,
        width=120,
        height=80
    ).save()
    
    session_cache = DataStore(
        key="session_cache",
        name="Session Cache",
        description="Redis cache for user sessions",
        store_type="cache",
        technology="Redis",
        criticality="medium",
        encryption_at_rest=False,
        backups_enabled=False,
        pos_x=550,
        pos_y=650,
        width=120,
        height=80
    ).save()
    
    # Create Trust Boundaries
    print("🛡️ Creating trust boundaries...")
    
    internet_boundary = TrustBoundaryNode(
        key="internet_boundary",
        name="Internet",
        description="External internet boundary",
        boundary_type="network",
        criticality="high",
        protected_components=["web_app", "auth_service", "payment_processor", "notification_service"],
        external_components=["user", "payment_gateway", "email_service"],
        security_controls=["Firewall", "DDoS Protection", "SSL/TLS"],
        owner="Security Team",
        notes="Public internet access boundary",
        pos_x=200,
        pos_y=100,
        width=400,
        height=4
    ).save()
    
    dmz_boundary = TrustBoundaryNode(
        key="dmz_boundary",
        name="DMZ",
        description="Demilitarized zone for web-facing services",
        boundary_type="network",
        criticality="high",
        protected_components=["web_app"],
        external_components=["user"],
        security_controls=["Web Application Firewall", "Load Balancer"],
        owner="Security Team",
        notes="DMZ for web application",
        pos_x=250,
        pos_y=150,
        width=200,
        height=4
    ).save()
    
    internal_boundary = TrustBoundaryNode(
        key="internal_boundary",
        name="Internal Network",
        description="Internal trusted network",
        boundary_type="network",
        criticality="high",
        protected_components=["auth_service", "payment_processor", "notification_service", "user_database", "product_database", "payment_database", "session_cache"],
        external_components=["web_app"],
        security_controls=["Internal Firewall", "Network Segmentation", "VPN"],
        owner="Security Team",
        notes="Internal trusted network",
        pos_x=400,
        pos_y=300,
        width=300,
        height=4
    ).save()
    
    # Create Threats
    print("⚠️ Creating threats...")
    
    # Spoofing threats
    user_spoofing = ThreatNode(
        key="user_spoofing_threat",
        name="User Identity Spoofing",
        description="Attackers may impersonate legitimate users",
        threat_type="spoofing",
        criticality="high",
        status="identified",
        impact="high",
        likelihood="medium",
        risk_level="high",
        affected_components=["user", "web_app", "auth_service"],
        mitigation_strategies=["Multi-factor authentication", "Strong password policies", "Session management"],
        owner="Security Team",
        assigned_to="Auth Team",
        identified_date=datetime.now().isoformat(),
        due_date=(datetime.now() + timedelta(days=30)).isoformat(),
        notes="Critical threat requiring immediate attention",
        linked_component_ids=["user", "web_app", "auth_service"],
        pos_x=100,
        pos_y=100,
        width=120,
        height=80
    ).save()
    
    # Tampering threats
    data_tampering = ThreatNode(
        key="data_tampering_threat",
        name="Data Tampering",
        description="Unauthorized modification of data in transit or at rest",
        threat_type="tampering",
        criticality="high",
        status="identified",
        impact="high",
        likelihood="medium",
        risk_level="high",
        affected_components=["user_database", "product_database", "payment_database"],
        mitigation_strategies=["Data encryption", "Digital signatures", "Access controls"],
        owner="Security Team",
        assigned_to="Database Team",
        identified_date=datetime.now().isoformat(),
        due_date=(datetime.now() + timedelta(days=45)).isoformat(),
        notes="Protect against data integrity violations",
        linked_component_ids=["user_database", "product_database", "payment_database"],
        pos_x=700,
        pos_y=100,
        width=120,
        height=80
    ).save()
    
    # Repudiation threats
    transaction_repudiation = ThreatNode(
        key="transaction_repudiation_threat",
        name="Transaction Repudiation",
        description="Users may deny performing transactions",
        threat_type="repudiation",
        criticality="medium",
        status="identified",
        impact="medium",
        likelihood="low",
        risk_level="medium",
        affected_components=["payment_processor", "payment_database"],
        mitigation_strategies=["Transaction logging", "Digital receipts", "Audit trails"],
        owner="Security Team",
        assigned_to="Payment Team",
        identified_date=datetime.now().isoformat(),
        due_date=(datetime.now() + timedelta(days=60)).isoformat(),
        notes="Implement comprehensive transaction logging",
        linked_component_ids=["payment_processor", "payment_database"],
        pos_x=700,
        pos_y=200,
        width=120,
        height=80
    ).save()
    
    # Information Disclosure threats
    data_breach = ThreatNode(
        key="data_breach_threat",
        name="Data Breach",
        description="Unauthorized access to sensitive user data",
        threat_type="information_disclosure",
        criticality="critical",
        status="identified",
        impact="critical",
        likelihood="medium",
        risk_level="critical",
        affected_components=["user_database", "payment_database", "session_cache"],
        mitigation_strategies=["Data encryption", "Access controls", "Monitoring", "Data classification"],
        owner="Security Team",
        assigned_to="Security Team",
        identified_date=datetime.now().isoformat(),
        due_date=(datetime.now() + timedelta(days=15)).isoformat(),
        notes="CRITICAL: Immediate action required",
        linked_component_ids=["user_database", "payment_database", "session_cache"],
        pos_x=700,
        pos_y=300,
        width=120,
        height=80
    ).save()
    
    # Denial of Service threats
    dos_attack = ThreatNode(
        key="dos_attack_threat",
        name="Denial of Service",
        description="Attackers may overwhelm the system with requests",
        threat_type="denial_of_service",
        criticality="high",
        status="identified",
        impact="high",
        likelihood="high",
        risk_level="high",
        affected_components=["web_app", "auth_service", "payment_processor"],
        mitigation_strategies=["Rate limiting", "Load balancing", "DDoS protection", "Auto-scaling"],
        owner="Security Team",
        assigned_to="Infrastructure Team",
        identified_date=datetime.now().isoformat(),
        due_date=(datetime.now() + timedelta(days=30)).isoformat(),
        notes="Implement comprehensive DoS protection",
        linked_component_ids=["web_app", "auth_service", "payment_processor"],
        pos_x=100,
        pos_y=300,
        width=120,
        height=80
    ).save()
    
    # Elevation of Privilege threats
    privilege_escalation = ThreatNode(
        key="privilege_escalation_threat",
        name="Privilege Escalation",
        description="Attackers may gain unauthorized elevated privileges",
        threat_type="elevation_of_privilege",
        criticality="high",
        status="identified",
        impact="high",
        likelihood="low",
        risk_level="medium",
        affected_components=["auth_service", "web_app"],
        mitigation_strategies=["Principle of least privilege", "Role-based access control", "Regular access reviews"],
        owner="Security Team",
        assigned_to="Auth Team",
        identified_date=datetime.now().isoformat(),
        due_date=(datetime.now() + timedelta(days=45)).isoformat(),
        notes="Implement strict privilege management",
        linked_component_ids=["auth_service", "web_app"],
        pos_x=100,
        pos_y=500,
        width=120,
        height=80
    ).save()
    
    # Connect all components to the diagram
    print("🔗 Connecting components to diagram...")
    
    # Connect external entities
    diagram.elements.connect(user)
    diagram.elements.connect(payment_gateway)
    diagram.elements.connect(email_service)
    
    # Connect processes
    diagram.elements.connect(web_app)
    diagram.elements.connect(auth_service)
    diagram.elements.connect(payment_processor)
    diagram.elements.connect(notification_service)
    
    # Connect data stores
    diagram.elements.connect(user_db)
    diagram.elements.connect(product_db)
    diagram.elements.connect(payment_db)
    diagram.elements.connect(session_cache)
    
    # Connect trust boundaries
    diagram.trust_boundaries.connect(internet_boundary)
    diagram.trust_boundaries.connect(dmz_boundary)
    diagram.trust_boundaries.connect(internal_boundary)
    
    # Connect threats
    diagram.threats.connect(user_spoofing)
    diagram.threats.connect(data_tampering)
    diagram.threats.connect(transaction_repudiation)
    diagram.threats.connect(data_breach)
    diagram.threats.connect(dos_attack)
    diagram.threats.connect(privilege_escalation)
    
    # Create relationships between components
    print("🔗 Creating component relationships...")
    
    # User to Web App
    user.outbound.connect(web_app, {"label": "user_requests", "protocol": "HTTPS", "auth_required": True})
    
    # Web App to Auth Service
    web_app.outbound.connect(auth_service, {"label": "auth_requests", "protocol": "HTTP", "auth_required": False})
    
    # Web App to Payment Processor
    web_app.outbound.connect(payment_processor, {"label": "payment_requests", "protocol": "HTTPS", "auth_required": True})
    
    # Web App to Notification Service
    web_app.outbound.connect(notification_service, {"label": "notification_requests", "protocol": "HTTP", "auth_required": False})
    
    # Auth Service to User Database
    auth_service.outbound.connect(user_db, {"label": "user_queries", "protocol": "SQL", "auth_required": True})
    
    # Web App to Product Database
    web_app.outbound.connect(product_db, {"label": "product_queries", "protocol": "MongoDB", "auth_required": True})
    
    # Payment Processor to Payment Database
    payment_processor.outbound.connect(payment_db, {"label": "payment_queries", "protocol": "SQL", "auth_required": True})
    
    # Web App to Session Cache
    web_app.outbound.connect(session_cache, {"label": "session_data", "protocol": "Redis", "auth_required": False})
    
    # Payment Processor to Payment Gateway
    payment_processor.outbound.connect(payment_gateway, {"label": "payment_requests", "protocol": "HTTPS", "auth_required": True})
    
    # Notification Service to Email Service
    notification_service.outbound.connect(email_service, {"label": "email_requests", "protocol": "SMTP", "auth_required": True})
    
    # Create threat-component relationships
    print("🔗 Creating threat-component relationships...")
    
    # User Spoofing relationships
    user_spoofing.linked_components.connect(user)
    user_spoofing.linked_components.connect(web_app)
    user_spoofing.linked_components.connect(auth_service)
    
    # Data Tampering relationships
    data_tampering.linked_components.connect(user_db)
    data_tampering.linked_components.connect(product_db)
    data_tampering.linked_components.connect(payment_db)
    
    # Transaction Repudiation relationships
    transaction_repudiation.linked_components.connect(payment_processor)
    transaction_repudiation.linked_components.connect(payment_db)
    
    # Data Breach relationships
    data_breach.linked_components.connect(user_db)
    data_breach.linked_components.connect(payment_db)
    data_breach.linked_components.connect(session_cache)
    
    # DoS Attack relationships
    dos_attack.linked_components.connect(web_app)
    dos_attack.linked_components.connect(auth_service)
    dos_attack.linked_components.connect(payment_processor)
    
    # Privilege Escalation relationships
    privilege_escalation.linked_components.connect(auth_service)
    privilege_escalation.linked_components.connect(web_app)
    
    # Create trust boundary relationships
    print("🔗 Creating trust boundary relationships...")
    
    # Internet Boundary relationships
    internet_boundary.protected_nodes.connect(web_app)
    internet_boundary.protected_nodes.connect(auth_service)
    internet_boundary.protected_nodes.connect(payment_processor)
    internet_boundary.protected_nodes.connect(notification_service)
    
    # DMZ Boundary relationships
    dmz_boundary.protected_nodes.connect(web_app)
    
    # Internal Boundary relationships
    internal_boundary.protected_nodes.connect(auth_service)
    internal_boundary.protected_nodes.connect(payment_processor)
    internal_boundary.protected_nodes.connect(notification_service)
    internal_boundary.protected_nodes.connect(user_db)
    internal_boundary.protected_nodes.connect(product_db)
    internal_boundary.protected_nodes.connect(payment_db)
    internal_boundary.protected_nodes.connect(session_cache)
    
    print("✅ Complete diagram created successfully!")
    print(f"📊 Summary:")
    print(f"   - Project: {project.name}")
    print(f"   - Diagram: {diagram.name}")
    print(f"   - External Entities: 3")
    print(f"   - Processes: 4")
    print(f"   - Data Stores: 4")
    print(f"   - Trust Boundaries: 3")
    print(f"   - Threats: 6 (all STRIDE types)")
    print(f"   - Total Components: 20")
    
    return project, diagram

if __name__ == "__main__":
    try:
        project, diagram = create_complete_diagram()
        print("\n🎉 Complete threat modeling diagram created successfully!")
        print(f"Project ID: {project.key}")
        print(f"Diagram ID: {diagram.key}")
    except Exception as e:
        print(f"❌ Error creating diagram: {e}")
        import traceback
        traceback.print_exc()

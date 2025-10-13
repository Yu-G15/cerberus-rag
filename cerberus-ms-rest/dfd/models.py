from neomodel import (
    StructuredNode, StructuredRel, StringProperty, IntegerProperty, BooleanProperty,
    FloatProperty, UniqueIdProperty, RelationshipTo, RelationshipFrom, JSONProperty
)

# ---------- User (node) ----------
class UserNode(StructuredNode):
    uid = UniqueIdProperty()
    key = StringProperty(unique_index=True, required=True)   # e.g. "user_bassiman"
    email = StringProperty(index=True, required=True)
    name = StringProperty()
    role = StringProperty(default="member")                  # "owner", "member", "admin", etc.
    meta = JSONProperty(default={})

    # backrefs
    owns = RelationshipFrom('Project', 'OWNED_BY')           # projects owned by this user
    memberships = RelationshipFrom('Project', 'HAS_MEMBER')  # projects where this user is a member


# ---------- Relationship (edge) ----------
class DataFlow(StructuredRel):
    label = StringProperty(index=True, default="data_flow")
    description = StringProperty()
    payload_schema = StringProperty()
    protocol = StringProperty()
    method = StringProperty()
    frequency = StringProperty()
    pii = BooleanProperty(default=False)
    confidentiality = StringProperty(default="medium")
    integrity = StringProperty(default="medium")
    availability = StringProperty(default="medium")
    auth_required = BooleanProperty(default=True)
    encryption_in_transit = BooleanProperty(default=True)
    notes = StringProperty()
    
    # Link visual properties for diagram editor
    middle_points = JSONProperty(default=[])  # Array of {x, y} coordinates for link bends
    line_type = StringProperty(default="solid")  # solid, dashed, dotted
    line_width = FloatProperty(default=1.5)
    arrow_type = StringProperty(default="pointed_arrow")
    arrow_size = FloatProperty(default=8.0)
    back_arrow_type = StringProperty(default="none")
    back_arrow_size = FloatProperty(default=0.0)
    color = IntegerProperty(default=16777215)  # Default white color

# ---------- Tenant containers ----------
class Project(StructuredNode):
    uid = UniqueIdProperty()
    key = StringProperty(unique_index=True, required=True)
    name = StringProperty(required=True)

    # legacy string; keep for now if you use it elsewhere
    user_id = StringProperty(index=True)

    meta = JSONProperty(default={})

    diagrams = RelationshipTo('Diagram', 'HAS_DIAGRAM')

    # NEW relations
    owner = RelationshipTo(UserNode, 'OWNED_BY')            # treat as single logically
    members = RelationshipTo(UserNode, 'HAS_MEMBER')
    
class Diagram(StructuredNode):
    uid = UniqueIdProperty()
    key = StringProperty(unique_index=True, required=True)   # e.g. "dfd_login_v1"
    name = StringProperty(default="")
    meta = JSONProperty(default={})

    project = RelationshipFrom(Project, 'HAS_DIAGRAM')
    elements = RelationshipTo("DFDNode", "HAS_ELEMENT")         # contains all nodes of this diagram
    threats = RelationshipTo("ThreatNode", "HAS_THREAT")        # contains all threat nodes of this diagram
    trust_boundaries = RelationshipTo("TrustBoundaryNode", "HAS_TRUST_BOUNDARY")  # contains all trust boundary nodes of this diagram


class FlowRel(StructuredRel):
    key   = StringProperty()         # your connection ID from payload
    label = StringProperty()         # optional display label
    kind  = StringProperty()         # e.g., 'data', 'control'
    note  = StringProperty()
    weight = FloatProperty()         # any numeric weight/capacity

# ---------- Base DFD nodes ----------
class DFDNode(StructuredNode):
    uid = UniqueIdProperty()
    key = StringProperty(unique_index=True, required=True)
    name = StringProperty(index=True, required=True)
    description = StringProperty()
    dfd_level = IntegerProperty(default=0)
    zone = StringProperty()
    owner = StringProperty()
    criticality = StringProperty(default="medium")

    # UI / layout props (round-trip to canvas)
    pos_x = FloatProperty(default=0.0)
    pos_y = FloatProperty(default=0.0)
    width = FloatProperty(default=120.0)
    height = FloatProperty(default=72.0)
    ui = JSONProperty(default={})

    # containment and flows
    diagram = RelationshipFrom(Diagram, 'HAS_NODE')
    inbound = RelationshipFrom('DFDNode', 'DATA_FLOW', model=DataFlow)
    outbound = RelationshipTo('DFDNode', 'DATA_FLOW', model=DataFlow)
    flows_to = RelationshipTo("DFDNode", "FLOWS_TO", model=FlowRel)   # generic flow relation
    

class Process(DFDNode):
    tech = StringProperty()

class ExternalEntity(DFDNode):
    actor_type = StringProperty(default="user")

class DataStore(DFDNode):
    store_type = StringProperty(default="database")
    technology = StringProperty()
    retention_days = IntegerProperty(default=0)
    encryption_at_rest = BooleanProperty(default=True)
    backups_enabled = BooleanProperty(default=True)
    rto_hours = FloatProperty(default=4.0)
    rpo_hours = FloatProperty(default=1.0)

# ---------- Threat and Trust Boundary Nodes ----------
class ThreatNode(StructuredNode):
    uid = UniqueIdProperty()
    key = StringProperty(unique_index=True, required=True)
    name = StringProperty(required=True)
    description = StringProperty()
    threat_type = StringProperty(required=True)  # spoofing, tampering, repudiation, information_disclosure, denial_of_service, elevation_of_privilege
    criticality = StringProperty(default="medium")
    status = StringProperty()  # identified, analyzed, mitigated, accepted
    impact = StringProperty()
    likelihood = StringProperty()
    risk_level = StringProperty()
    affected_components = JSONProperty(default=[])  # List of component IDs
    mitigation_strategies = JSONProperty(default=[])  # List of mitigation strategies
    owner = StringProperty()
    assigned_to = StringProperty()
    identified_date = StringProperty()  # ISO date string
    due_date = StringProperty()  # ISO date string
    notes = StringProperty()
    linked_component_ids = JSONProperty(default=[])  # List of component IDs this threat is linked to
    trust_boundary_ids = JSONProperty(default=[])  # List of trust boundary IDs
    
    # UI / layout properties
    pos_x = FloatProperty(default=0.0)
    pos_y = FloatProperty(default=0.0)
    width = FloatProperty(default=120.0)
    height = FloatProperty(default=80.0)
    ui = JSONProperty(default={})
    
    # Relationships
    diagram = RelationshipFrom(Diagram, 'HAS_THREAT')
    linked_components = RelationshipTo('DFDNode', 'THREATENS')
    linked_trust_boundaries = RelationshipTo('TrustBoundaryNode', 'AFFECTS_BOUNDARY')

class TrustBoundaryNode(StructuredNode):
    uid = UniqueIdProperty()
    key = StringProperty(unique_index=True, required=True)
    name = StringProperty(required=True)
    description = StringProperty()
    boundary_type = StringProperty(required=True)  # network, process, data, user, system
    criticality = StringProperty(default="medium")
    protected_components = JSONProperty(default=[])  # List of component IDs inside the boundary
    external_components = JSONProperty(default=[])  # List of component IDs outside the boundary
    security_controls = JSONProperty(default=[])  # List of security controls
    owner = StringProperty()
    notes = StringProperty()
    diagram_id = StringProperty()
    linked_threat_ids = JSONProperty(default=[])  # List of threat IDs linked to this boundary
    
    # UI / layout properties
    pos_x = FloatProperty(default=0.0)
    pos_y = FloatProperty(default=0.0)
    width = FloatProperty(default=200.0)
    height = FloatProperty(default=150.0)
    ui = JSONProperty(default={})
    
    # Relationships
    diagram = RelationshipFrom(Diagram, 'HAS_TRUST_BOUNDARY')
    protected_nodes = RelationshipTo('DFDNode', 'PROTECTS')
    affected_by_threats = RelationshipFrom('ThreatNode', 'AFFECTS_BOUNDARY')
    
    


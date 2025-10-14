from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

# ---- Users ----
class UserSerializer(serializers.Serializer):
    key = serializers.CharField()
    email = serializers.EmailField()
    name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(required=False, allow_blank=True)
    meta = serializers.DictField(required=False)

# ---- Projects / Diagrams ----
class ProjectSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    user_id = serializers.CharField(required=False, allow_blank=True)
    meta = serializers.DictField(required=False)
    owner_key = serializers.CharField(required=False, allow_blank=True)
    member_keys = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)

class DiagramSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    meta = serializers.DictField(required=False)

# ---- Components (canvas schema) ----
VALID_TYPES = {"data_store", "external_entity", "process", "container", "threat", "trust_boundary"}

class TypeEnumField(serializers.CharField):
    @extend_schema_field({
        "type": "string",
        "enum": ["data_store", "external_entity", "process", "container", "threat", "trust_boundary", "external_entitiy"]  # include tolerated typo if you like
    })
    def to_representation(self, value):
        return super().to_representation(value)
    
class ComponentSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = TypeEnumField()
    position = serializers.DictField(child=serializers.FloatField(), allow_empty=False)
    size = serializers.DictField(child=serializers.FloatField(), allow_empty=False)
    data = serializers.DictField(allow_empty=False)

    def validate_type(self, value: str) -> str:
        v = value.strip().lower()
        if v == "external_entitiy":
            v = "external_entity"
        if v not in VALID_TYPES:
            raise serializers.ValidationError(f"type must be one of {sorted(VALID_TYPES)}")
        return v

    def validate_position(self, value):
        for k in ("x", "y"):
            if k not in value:
                raise serializers.ValidationError(f"position.{k} is required")
        return value

    def validate_size(self, value):
        for k in ("width", "height"):
            if k not in value:
                raise serializers.ValidationError(f"size.{k} is required")
        return value

    def validate_data(self, value):
        required = ["text", "color", "borderColor", "borderWidth", "textAlignment", "textSize"]
        missing = [k for k in required if k not in value]
        if missing:
            raise serializers.ValidationError(f"data missing fields: {missing}")
        return value
    
class ConnectionSerializer(serializers.Serializer):
    id    = serializers.CharField()
    from_ = serializers.CharField(source="from", required=False)
    to    = serializers.CharField()
    data  = serializers.DictField(required=False, default=dict)

    def to_internal_value(self, data):
        # accept either "from" or "from_"
        if "from" in data and "from_" not in data:
            data = {**data, "from_": data["from"]}
        return super().to_internal_value(data)

    def validate(self, attrs):
        if "from" not in attrs:  # after source mapping, key is "from"
            raise serializers.ValidationError({"from": ["This field is required."]})
        return attrs


class BulkSyncSerializer(serializers.Serializer):
    components  = serializers.ListField(child=ComponentSerializer(), required=False, default=list)
    connections = serializers.ListField(child=ConnectionSerializer(), required=False, default=list)
    options     = serializers.DictField(required=False, default=dict)

# ---- Threat Nodes ----
VALID_THREAT_TYPES = {"spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service", "elevation_of_privilege"}

class ThreatTypeField(serializers.CharField):
    @extend_schema_field({
        "type": "string",
        "enum": list(VALID_THREAT_TYPES)
    })
    def to_representation(self, value):
        return super().to_representation(value)

class ThreatNodeSerializer(serializers.Serializer):
    uid = serializers.CharField(required=False, allow_blank=True)
    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    threat_type = ThreatTypeField()
    criticality = serializers.CharField(default="medium")
    status = serializers.CharField(required=False, allow_blank=True, default="")
    impact = serializers.CharField(required=False, allow_blank=True, default="")
    likelihood = serializers.CharField(required=False, allow_blank=True, default="")
    risk_level = serializers.CharField(required=False, allow_blank=True, default="medium")
    affected_components = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    mitigation_strategies = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    owner = serializers.CharField(required=False, allow_blank=True, default="")
    assigned_to = serializers.CharField(required=False, allow_blank=True, default="")
    identified_date = serializers.CharField(required=False, allow_blank=True, default="")
    due_date = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    linked_component_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    trust_boundary_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    pos_x = serializers.FloatField(default=0.0)
    pos_y = serializers.FloatField(default=0.0)
    width = serializers.FloatField(default=120.0)
    height = serializers.FloatField(default=80.0)
    ui = serializers.DictField(required=False, default=dict)

    def validate_threat_type(self, value):
        if value not in VALID_THREAT_TYPES:
            raise serializers.ValidationError(f"threat_type must be one of {sorted(VALID_THREAT_TYPES)}")
        return value

# ---- Trust Boundary Nodes ----
VALID_BOUNDARY_TYPES = {"network", "process", "data", "user", "system"}

class TrustBoundaryTypeField(serializers.CharField):
    @extend_schema_field({
        "type": "string",
        "enum": list(VALID_BOUNDARY_TYPES)
    })
    def to_representation(self, value):
        return super().to_representation(value)

class TrustBoundaryNodeSerializer(serializers.Serializer):
    uid = serializers.CharField(required=False)
    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    boundary_type = TrustBoundaryTypeField()
    criticality = serializers.CharField(default="medium")
    protected_components = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    external_components = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    security_controls = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    owner = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    diagram_id = serializers.CharField(required=False, allow_blank=True)
    linked_threat_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    pos_x = serializers.FloatField(default=0.0)
    pos_y = serializers.FloatField(default=0.0)
    width = serializers.FloatField(default=200.0)
    height = serializers.FloatField(default=150.0)
    ui = serializers.DictField(required=False, default=dict)

    def validate_boundary_type(self, value):
        if value not in VALID_BOUNDARY_TYPES:
            raise serializers.ValidationError(f"boundary_type must be one of {sorted(VALID_BOUNDARY_TYPES)}")
        return value

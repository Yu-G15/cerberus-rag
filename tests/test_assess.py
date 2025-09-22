import json
from pathlib import Path

SAMPLES = Path(__file__).parent.parent / "samples"

def load(name: str):
    return json.loads((SAMPLES / name).read_text())

def assess(client, dfd):
    resp = client.post("/rag/assess", json={"dfd": dfd})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("valid") is True
    assert isinstance(data.get("findings"), list)
    return data

def exists_expl(findings, text: str) -> bool:
    return any(text in f.get("explanation","") for f in findings)

def stride_on(findings, target: str, stride: str) -> bool:
    return any(f.get("target")==target and f.get("stride")==stride for f in findings)

# ------- Use Case 1: Basic Web Form -------
def test_web_form_triggers_http_and_sql(client):
    data = assess(client, load("dfd_web_form.json"))
    f = data["findings"]
    # F1: Three common HTTP triggers STRIDE
    assert stride_on(f, "flows[F1]", "Information Disclosure")
    assert stride_on(f, "flows[F1]", "Spoofing")
    assert stride_on(f, "flows[F1]", "Denial of Service")
    # It should appear in the copy: protocol=HTTP / protocol=SQL
    assert exists_expl(f, "protocol=HTTP")
    assert exists_expl(f, "protocol=SQL")

# ------- Use Case 2: HTTPS within the Service Mesh -------
def test_service_mesh_has_no_http_findings(client):
    data = assess(client, load("dfd_service_mesh.json"))
    f = data["findings"]
    # There should be no trigger interpretation of "protocol=HTTP"
    assert not exists_expl(f, "protocol=HTTP")

# ------- Use Case 3: File Upload -------
def test_file_upload_has_findings(client):
    data = assess(client, load("dfd_file_upload.json"))
    f = data["findings"]
    # At least one discovery (HTTP boundary input)
    assert len(f) >= 1

# ------- Use Case 4: Mobile OAuth scenario-------
def test_mobile_oauth_returns_ok(client):
    data = assess(client, load("dfd_mobile_oauth.json"))
    assert "summary" in data
    assert sum(data["summary"].values()) >= 0

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

# ------- 用例 1：基础 Web 表单 -------
def test_web_form_triggers_http_and_sql(client):
    data = assess(client, load("dfd_web_form.json"))
    f = data["findings"]
    # F1: HTTP 触发的三个常见 STRIDE
    assert stride_on(f, "flows[F1]", "Information Disclosure")
    assert stride_on(f, "flows[F1]", "Spoofing")
    assert stride_on(f, "flows[F1]", "Denial of Service")
    # 文案里应出现 protocol=HTTP / protocol=SQL
    assert exists_expl(f, "protocol=HTTP")
    assert exists_expl(f, "protocol=SQL")

# ------- 用例 2：服务网格内部 HTTPS -------
def test_service_mesh_has_no_http_findings(client):
    data = assess(client, load("dfd_service_mesh.json"))
    f = data["findings"]
    # 不应出现任何 "protocol=HTTP" 的触发解释
    assert not exists_expl(f, "protocol=HTTP")

# ------- 用例 3：文件上传 -------
def test_file_upload_has_findings(client):
    data = assess(client, load("dfd_file_upload.json"))
    f = data["findings"]
    # 至少有一条发现（HTTP 边界输入）
    assert len(f) >= 1

# ------- 用例 4：移动端 OAuth 场景 -------
def test_mobile_oauth_returns_ok(client):
    data = assess(client, load("dfd_mobile_oauth.json"))
    assert "summary" in data
    assert sum(data["summary"].values()) >= 0  # 结构完整即可

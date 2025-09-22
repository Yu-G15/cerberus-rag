import os, httpx
from typing import Dict, Any

DEFAULT_URL = os.environ.get("GUARDRAILS_URL", "http://guardrail-alb-667564894.ap-southeast-2.elb.amazonaws.com")

def validate_json(dfd: Dict[str, Any]) -> Dict[str, Any]:
    url = DEFAULT_URL.rstrip("/") + "/validate-json"
    try:
        r = httpx.post(url, json=dfd, timeout=20.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        return {"valid": False, "errors": [{"type":"http","message": f"{e.response.status_code} {e.response.text[:200]}"}], "warnings": []}
    except Exception as e:
        return {"valid": False, "errors": [{"type":"client","message": str(e)}], "warnings": []}

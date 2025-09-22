# rag/app.py
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, Body, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# -----------------------------------------------------------------------------
# Try loading the evaluation logic in your project: rag/rules.py -> assess_dfd(dfd) -> Dict
# If it does not exist, use a built-in simple evaluator as a fallback to ensure the interface is available
# -----------------------------------------------------------------------------
_assess_impl = None  # type: Optional[callable]

try:
    # Give priority to using in-package relative imports (run within the rag package)
    from . import rules as _rules  # type: ignore
    if hasattr(_rules, "assess_dfd") and callable(_rules.assess_dfd):
        _assess_impl = _rules.assess_dfd  # type: ignore
except Exception:
    # Go back to the same directory and import directly (some structures are not package runs)
    try:
        import rules as _rules2  # type: ignore

        if hasattr(_rules2, "assess_dfd") and callable(_rules2.assess_dfd):
            _assess_impl = _rules2.assess_dfd  # type: ignore
    except Exception:
        _assess_impl = None


def _fallback_assess_dfd(dfd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Built-in simple evaluator (as a safety net).
    Read the protocol/classification in ddfd.flows and provide several fixed rules and summaries.
    """
    flows = (dfd or {}).get("flows", []) or []
    findings = []

    def add_finding(target: str, stride: str, score: float, ev: list, rule: str, mitigations: list):
        # DREAD is simplified to a fixed template, allowing the front end to display scores
        dread = {"D": 10.0 if score >= 6.5 else 7.0, "R": 6.0, "E": 5.0, "A": 7.5 if score >= 6.5 else 6.0,
                 "D2": 6.0 if score >= 6.0 else 5.0, "score": score}
        findings.append({
            "target": target,
            "stride": stride,
            "dread": dread,
            "evidence": ev,
            "explanation": f"Rule {rule} matched on {target}.",
            "mitigations": mitigations,
            "severity": "Medium" if score < 7.0 else "High",
        })

    # Simple rules: HTTP + PII
    for f in flows:
        fid = f.get("id", "?")
        data = (f.get("data") or {})
        proto = (data.get("protocol") or "").upper()
        cls = (data.get("classification") or "").upper()
        target = f"flows[{fid}]"

        if proto == "HTTP" and cls == "PII":
            # DOS / Spoofing / Info Disclosure 3 e.g.:
            add_finding(
                target, "Denial of Service", 6.9, ["T007", "T009"], "P003",
                ["Per-IP/user rate limit", "CAPTCHA", "exponential backoff", "WAF throttling", "Allowlist MIME"],
            )
            add_finding(
                target, "Spoofing", 6.9, ["T002"], "P002",
                ["Require OAuth2/OIDC", "API keys with rotation", "mTLS for service-to-service"],
            )
            add_finding(
                target, "Information Disclosure", 6.4, ["T001", "T006", "T014"], "P001",
                ["Use TLS1.2+", "enable HSTS", "certificate pinning for mobile", "disable weak ciphers", "Encrypt at rest (AES-256)"],
            )

        if proto == "SQL" and cls == "PII":
            add_finding(
                target, "Information Disclosure", 5.6, ["T006", "T004", "T001"], "P004",
                ["Encrypt at rest (AES-256)", "use KMS/HSM", "key rotation", "access control on keys", "Allowlist validation"],
            )

    # sort and create summary
    # calculate rank
    for i, f in enumerate(findings, 1):
        f["rank"] = i

    summary = {"High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        sev = f.get("severity", "Medium")
        if sev not in summary:
            summary[sev] = 0
        summary[sev] += 1

    return {
        "valid": True,
        "errors": [],
        "warnings": [{"type": "config", "message": "GUARDRAILS_URL not set"}],
        "findings": findings,
        "summary": summary,
    }


def assess_dfd_bridge(dfd: Dict[str, Any]) -> Dict[str, Any]:
    if _assess_impl:
        return _assess_impl(dfd)
    return _fallback_assess_dfd(dfd)


# -----------------------------------------------------------------------------
# FastAPI applications and Middleware
# -----------------------------------------------------------------------------
app = FastAPI(title="RAG Backend", version="1.0.0")

# CORS: Allow local front-end access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:57330",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:57330",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# routing
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "RAG backend is running", "time": int(time.time())}


@app.get("/rag/ping")
def ping():
    return {"pong": True, "time": int(time.time())}


@app.post("/rag/assess")
def assess(payload: Dict[str, Any] = Body(...)):
    """
    expect structure：
    {
      "dfd": { ... }
    }
    """
    try:
        if not isinstance(payload, dict) or "dfd" not in payload:
            raise HTTPException(status_code=422, detail="Request body must be an object with a 'dfd' field.")
        dfd = payload.get("dfd") or {}
        if not isinstance(dfd, dict):
            raise HTTPException(status_code=422, detail="'dfd' must be an object.")

        result = assess_dfd_bridge(dfd)
        # Attach a warning (for example, whether to enable BYPASS / Guardrails）
        bypass = os.environ.get("BYPASS_GUARDRAILS", "").strip()
        if bypass:
            (result.setdefault("warnings", [])).append(
                {"type": "config", "message": "BYPASS_GUARDRAILS enabled"}
            )
        if not os.environ.get("GUARDRAILS_URL"):
            (result.setdefault("warnings", [])).append(
                {"type": "config", "message": "GUARDRAILS_URL not set"}
            )

        # Uniformly add the "valid/errors" field (to prevent omissions in third-party implementations)
        result.setdefault("valid", True)
        result.setdefault("errors", [])

        return result
    except HTTPException:
        raise
    except Exception as e:
        # return unified 500 JSON
        return JSONResponse(
            status_code=500,
            content={
                "valid": False,
                "errors": [{"type": "server", "message": str(e)}],
                "warnings": [],
                "findings": [],
                "summary": {"High": 0, "Medium": 0, "Low": 0},
            },
        )


# -----------------------------------------------------------------------------
# Unified exception handling (optional)
# -----------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# -----------------------------------------------------------------------------
# Run directly locally
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("rag.app:app", host="127.0.0.1", port=8001, reload=True)

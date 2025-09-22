# rag/rules.py

from typing import Dict, List, Any, Optional

def _severity_from_score(score: float) -> str:
    if score >= 7.0: return "High"
    if score >= 5.5: return "Medium"
    return "Low"

def assess_dfd(
    dfd: Dict[str, Any],
    stride: Optional[List[str]] = None
) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []

    flows = dfd.get("flows", [])
    for f in flows:
        data = (f or {}).get("data", {}) or {}
        proto = str(data.get("protocol", "")).upper()
        cls   = str(data.get("classification", "")).upper()

        if proto == "HTTP" and cls == "PII":
            dread = {"D": 9.0, "R": 6.0, "E": 5.0, "A": 6.0, "D2": 6.0}
            score = round((dread["D"] + dread["R"] + dread["E"] + dread["A"] + dread["D2"]) / 5.0, 1)
            dread["score"] = score

            findings.append({
                "target": f'flows[{f.get("id", "?")}]',
                "stride": "Information Disclosure",
                "dread": dread,
                "evidence": ["T001"],
                "explanation": "HTTP + PII on data flow; consider encrypting in transit.",
                "mitigations": [
                    "Use TLS1.2+",
                    "enable HSTS",
                    "disable weak ciphers",
                    "certificate pinning (mobile)"
                ],
                "severity": _severity_from_score(score),
            })

    # sort and add rank
    findings.sort(key=lambda x: {"High":0, "Medium":1, "Low":2}[x["severity"]])
    for i, f in enumerate(findings, start=1):
        f["rank"] = i

    summary = {
        "High":   sum(1 for x in findings if x["severity"] == "High"),
        "Medium": sum(1 for x in findings if x["severity"] == "Medium"),
        "Low":    sum(1 for x in findings if x["severity"] == "Low"),
    }

    return {
        "valid": True,
        "errors": [],
        "warnings": [],
        "findings": findings,
        "summary": summary,
    }

# Automatic detection compatible with apps: Provide multiple entry aliases
def assess(dfd, stride=None):   return assess_dfd(dfd, stride)
def evaluate(dfd, stride=None): return assess_dfd(dfd, stride)
def analyze(dfd, stride=None):  return assess_dfd(dfd, stride)
def run_rules(dfd, stride=None):return assess_dfd(dfd, stride)

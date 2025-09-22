from typing import Dict, Any

def score_dread(context: Dict[str, Any], stride: str) -> Dict[str, float]:
    proto = (context or {}).get("protocol","") or ""
    proto = (proto or "").upper()
    cls = (context or {}).get("classification","") or ""
    cls = (cls or "").upper()

    D = 5.0; R = 5.0; E = 5.0; A = 5.0; D2 = 5.0
    if proto in ("HTTP","TCP","PLAINTEXT"):
        D += 2; R += 1; D2 += 1
    if cls in ("PII","CREDENTIALS","SECRETS"):
        D += 2; A += 1
    if stride in ("Spoofing","Elevation of Privilege"):
        E += 1.5; R += 1
    if stride == "Denial of Service":
        D += 1; A += 1.5

    clamp = lambda x: max(0, min(10, x))
    D = clamp(D); R = clamp(R); E = clamp(E); A = clamp(A); D2 = clamp(D2)
    score = round((0.3*D + 0.15*R + 0.2*E + 0.25*A + 0.1*D2), 1)
    return {"D": D, "R": R, "E": E, "A": A, "D2": D2, "score": score}

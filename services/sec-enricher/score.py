# services/sec-enricher/score.py
from framework.core.models import RiskAssessment

def score(event, baseline, intel):
    reasons, score = [], 0
    if event["action"] in {"CreateAccessKey","AttachUserPolicy","PutUserPolicy"}:
        score += 35; reasons.append("Privileged IAM action")
    if intel.reputation(event.get("indicators", [])) > 80:
        score += 25; reasons.append("High reputation indicators")
    if baseline.is_anomalous(event["entity_id"], event["attributes"]):
        score += 25; reasons.append("Behavioral anomaly")
    if event["attributes"].get("geo") not in baseline.allowed_geo(event["entity_id"]):
        score += 15; reasons.append("Unusual geolocation")
    return RiskAssessment(score=min(score, 100), reasons=reasons)

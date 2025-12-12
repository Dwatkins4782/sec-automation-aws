# framework/core/models.py
from pydantic import BaseModel, Field
from typing import Dict, List
from datetime import datetime

class SecurityEvent(BaseModel):
    id: str
    entity_id: str
    source: str
    action: str
    ts: datetime
    attributes: Dict[str, str] = {}
    indicators: List[str] = []

class RiskAssessment(BaseModel):
    score: float = Field(ge=0, le=100)
    reasons: List[str]

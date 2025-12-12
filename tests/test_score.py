import os
import sys
import types
import unittest
import importlib.util
from pathlib import Path

# --- Test setup: stub out framework.core.models.RiskAssessment to avoid pydantic dependency
framework_mod = types.ModuleType("framework")
core_mod = types.ModuleType("framework.core")
models_mod = types.ModuleType("framework.core.models")

class RiskAssessment:
    def __init__(self, score, reasons):
        self.score = score
        self.reasons = reasons

models_mod.RiskAssessment = RiskAssessment

# Register stubbed modules so `from framework.core.models import RiskAssessment` works in the target module
sys.modules["framework"] = framework_mod
sys.modules["framework.core"] = core_mod
sys.modules["framework.core.models"] = models_mod

# --- Dynamically import the module under test from its file path (folder contains a hyphen)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCORE_PATH = PROJECT_ROOT / "services" / "sec-enricher" / "score.py"
spec = importlib.util.spec_from_file_location("score_module", SCORE_PATH)
score_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score_module)


# --- Fakes for collaborators
class FakeBaseline:
    def __init__(self, anomalous=False, allowed=None):
        self._anomalous = anomalous
        self._allowed = allowed if allowed is not None else []

    def is_anomalous(self, entity_id, attributes):
        return self._anomalous

    def allowed_geo(self, entity_id):
        return list(self._allowed)


class FakeIntel:
    def __init__(self, reputation_score=0):
        self._rep = reputation_score

    def reputation(self, indicators):
        return self._rep


class TestScore(unittest.TestCase):
    def base_event(self, **overrides):
        event = {
            "id": "e1",
            "entity_id": "u-123",
            "source": "iam",
            "action": "ListUsers",
            "ts": "2025-01-01T00:00:00Z",
            "attributes": {"geo": "US"},
            "indicators": [],
        }
        event.update(overrides)
        return event

    def test_privileged_iam_action_adds_35_with_reason(self):
        event = self.base_event(action="CreateAccessKey")
        baseline = FakeBaseline(anomalous=False, allowed=["US"]) 
        intel = FakeIntel(reputation_score=0)

        ra = score_module.score(event, baseline, intel)

        self.assertEqual(ra.score, 35)
        self.assertIn("Privileged IAM action", ra.reasons)

    def test_high_reputation_indicators_adds_25_with_reason(self):
        event = self.base_event()
        baseline = FakeBaseline(anomalous=False, allowed=["US"]) 
        intel = FakeIntel(reputation_score=85)

        ra = score_module.score(event, baseline, intel)

        self.assertEqual(ra.score, 25)
        self.assertIn("High reputation indicators", ra.reasons)

    def test_behavioral_anomaly_adds_25_with_reason(self):
        event = self.base_event()
        baseline = FakeBaseline(anomalous=True, allowed=["US"]) 
        intel = FakeIntel(reputation_score=0)

        ra = score_module.score(event, baseline, intel)

        self.assertEqual(ra.score, 25)
        self.assertIn("Behavioral anomaly", ra.reasons)

    def test_unusual_geolocation_adds_15_with_reason(self):
        event = self.base_event(attributes={"geo": "RU"})
        baseline = FakeBaseline(anomalous=False, allowed=["US"]) 
        intel = FakeIntel(reputation_score=0)

        ra = score_module.score(event, baseline, intel)

        self.assertEqual(ra.score, 15)
        self.assertIn("Unusual geolocation", ra.reasons)

    def test_all_factors_capped_at_100_and_reason_order(self):
        event = self.base_event(action="AttachUserPolicy", attributes={"geo": "RU"})
        baseline = FakeBaseline(anomalous=True, allowed=["US"]) 
        intel = FakeIntel(reputation_score=99)

        ra = score_module.score(event, baseline, intel)

        self.assertEqual(ra.score, 100)  # 35 + 25 + 25 + 15 = 100 (capped)
        self.assertEqual(
            ra.reasons,
            [
                "Privileged IAM action",
                "High reputation indicators",
                "Behavioral anomaly",
                "Unusual geolocation",
            ],
        )

    def test_missing_indicators_defaults_to_empty_list(self):
        event = self.base_event()
        event.pop("indicators", None)
        baseline = FakeBaseline(anomalous=False, allowed=["US"]) 
        intel = FakeIntel(reputation_score=90)

        ra = score_module.score(event, baseline, intel)

        self.assertEqual(ra.score, 25)
        self.assertIn("High reputation indicators", ra.reasons)

    def test_missing_geo_counts_as_unusual_geolocation(self):
        event = self.base_event()
        event["attributes"] = {}  # no geo
        baseline = FakeBaseline(anomalous=False, allowed=["US"]) 
        intel = FakeIntel(reputation_score=0)

        ra = score_module.score(event, baseline, intel)

        self.assertEqual(ra.score, 15)
        self.assertIn("Unusual geolocation", ra.reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)

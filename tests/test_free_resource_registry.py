import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "free_resource_registry.py"
spec = importlib.util.spec_from_file_location("free_resource_registry", SCRIPT)
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)


class FreeResourceRegistryTests(unittest.TestCase):
    def test_parse_free_for_dev_entries_are_candidates_only(self):
        markdown = """# Test\n## IaaS\n- [Example](https://example.com) - free VM\n"""
        rows = registry.parse_free_for_dev(markdown)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "IaaS")
        self.assertEqual(rows[0]["verification_status"], "candidate_only")
        self.assertFalse(rows[0]["deploy_eligible"])

    def test_unverified_resource_is_blocked(self):
        resource = {
            "cost_class": "zero",
            "billing_dependency": "free_tier",
            "requires_paid_upgrade": False,
            "verification": {
                "status": "candidate_only",
                "official_source": "https://example.com",
                "verified_at": "2026-08-25",
            },
        }
        gate = registry.eligibility(resource, {"absolute_zero": True, "verification_max_age_days": 30}, today=date(2026, 8, 25))
        self.assertFalse(gate["eligible"])
        self.assertIn("not_officially_verified", gate["reasons"])

    def test_promotional_credit_dependency_is_blocked(self):
        resource = {
            "cost_class": "zero",
            "billing_dependency": "promotional_credit",
            "requires_paid_upgrade": False,
            "verification": {
                "status": "verified",
                "official_source": "https://example.com",
                "verified_at": "2026-08-25",
            },
        }
        gate = registry.eligibility(resource, {"absolute_zero": True, "verification_max_age_days": 30}, today=date(2026, 8, 25))
        self.assertFalse(gate["eligible"])
        self.assertIn("billing_dependency_disallowed", gate["reasons"])

    def test_stale_verification_is_blocked(self):
        resource = {
            "cost_class": "zero",
            "billing_dependency": "free_tier",
            "requires_paid_upgrade": False,
            "verification": {
                "status": "verified",
                "official_source": "https://example.com",
                "verified_at": "2026-07-01",
            },
        }
        gate = registry.eligibility(resource, {"absolute_zero": True, "verification_max_age_days": 30}, today=date(2026, 8, 25))
        self.assertFalse(gate["eligible"])
        self.assertIn("verification_stale", gate["reasons"])

    def test_verified_zero_resource_is_eligible(self):
        resource = {
            "cost_class": "zero",
            "billing_dependency": "free_tier",
            "requires_paid_upgrade": False,
            "verification": {
                "status": "verified",
                "official_source": "https://example.com",
                "verified_at": "2026-08-25",
            },
        }
        gate = registry.eligibility(resource, {"absolute_zero": True, "verification_max_age_days": 30}, today=date(2026, 8, 25))
        self.assertTrue(gate["eligible"])
        self.assertEqual(gate["reasons"], [])

    def test_query_ranks_and_filters(self):
        data = {
            "policy": {"absolute_zero": True, "verification_max_age_days": 30},
            "resources": [
                {
                    "id": "local",
                    "provider": "Local",
                    "resource": "Ollama",
                    "category": "local/ai-runtime",
                    "cost_class": "zero",
                    "billing_dependency": "none",
                    "requires_paid_upgrade": False,
                    "card_required": False,
                    "architecture": ["x86"],
                    "region": ["local"],
                    "verification": {"status": "verified", "official_source": "https://ollama.com", "verified_at": "2026-08-25"},
                    "rank": {"durability": 5, "capacity": 2, "availability": 5, "reclaim_risk": 0},
                },
                {
                    "id": "blocked",
                    "provider": "Candidate",
                    "resource": "Unknown",
                    "category": "compute/vps",
                    "cost_class": "zero",
                    "billing_dependency": "free_tier",
                    "requires_paid_upgrade": False,
                    "card_required": False,
                    "architecture": ["x86"],
                    "region": ["us"],
                    "verification": {"status": "candidate_only", "official_source": "https://example.com", "verified_at": "2026-08-25"},
                    "rank": {"durability": 5, "capacity": 5, "availability": 5, "reclaim_risk": 0},
                },
            ],
        }
        rows = registry.query_resources(data, eligible_only=True, today=date(2026, 8, 25))
        self.assertEqual([row["id"] for row in rows], ["local"])


if __name__ == "__main__":
    unittest.main()

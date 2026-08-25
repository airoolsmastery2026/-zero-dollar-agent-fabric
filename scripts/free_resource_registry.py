#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "configs" / "free-resource-registry.json"
STATE_DIR = Path.cwd() / ".zero"
CANDIDATES_PATH = STATE_DIR / "free-for-dev-candidates.json"

CATEGORY_RE = re.compile(r"^##+\s+(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+\[([^\]]+)\]\((https?://[^)]+)\)\s*(?:[-–—:]\s*)?(.*)$")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def fetch_text(url: str, timeout: int = 20) -> str:
    request = Request(url, headers={"User-Agent": "zero-dollar-agent-fabric/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_free_for_dev(markdown: str):
    category = "uncategorized"
    rows = []
    for raw_line in markdown.splitlines():
        heading = CATEGORY_RE.match(raw_line)
        if heading:
            category = heading.group(1).strip()
            continue
        match = BULLET_RE.match(raw_line)
        if not match:
            continue
        name, url, description = match.groups()
        rows.append({
            "category": category,
            "provider": name.strip(),
            "resource": name.strip(),
            "candidate_url": url.strip(),
            "description": description.strip(),
            "verification_status": "candidate_only",
            "deploy_eligible": False,
        })
    return rows


def sync_candidates(registry):
    source = registry["source_catalogs"]["free_for_dev"]
    markdown = fetch_text(source["raw_url"])
    rows = parse_free_for_dev(markdown)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": source["repo"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "warning": "Community catalog entries are candidates only and can never bypass official verification.",
        "resources": rows,
    }
    CANDIDATES_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def verification_age_days(resource, today=None):
    today = today or utc_today()
    verified_at = resource.get("verification", {}).get("verified_at")
    if not verified_at:
        return None
    try:
        return (today - date.fromisoformat(verified_at)).days
    except ValueError:
        return None


def eligibility(resource, policy, today=None):
    reasons = []
    verification = resource.get("verification", {})
    max_age = int(policy.get("verification_max_age_days", 30))
    age = verification_age_days(resource, today)

    if resource.get("cost_class") != "zero":
        reasons.append("cost_class_not_zero")
    if resource.get("billing_dependency") in {"paid", "promotional_credit"}:
        reasons.append("billing_dependency_disallowed")
    if verification.get("status") != "verified":
        reasons.append("not_officially_verified")
    if not verification.get("official_source"):
        reasons.append("missing_official_source")
    if age is None:
        reasons.append("missing_or_invalid_verified_at")
    elif age < 0:
        reasons.append("verification_date_in_future")
    elif age > max_age:
        reasons.append("verification_stale")

    if policy.get("absolute_zero", True) and resource.get("requires_paid_upgrade") is True:
        reasons.append("paid_upgrade_required")

    return {"eligible": not reasons, "reasons": reasons, "verification_age_days": age}


def score(resource):
    rank = resource.get("rank", {})
    return (
        int(rank.get("durability", 0)) * 4
        + int(rank.get("capacity", 0)) * 2
        + int(rank.get("availability", 0))
        - int(rank.get("reclaim_risk", 0)) * 3
        - (2 if resource.get("card_required") else 0)
    )


def query_resources(registry, category=None, architecture=None, region=None, eligible_only=True, today=None):
    policy = registry["policy"]
    results = []
    for resource in registry.get("resources", []):
        gate = eligibility(resource, policy, today=today)
        if eligible_only and not gate["eligible"]:
            continue
        if category and category.lower() not in resource.get("category", "").lower():
            continue
        if architecture and architecture.lower() not in [str(x).lower() for x in resource.get("architecture", [])]:
            continue
        if region and region.lower() not in [str(x).lower() for x in resource.get("region", [])]:
            continue
        row = dict(resource)
        row["gate"] = gate
        row["score"] = score(resource)
        results.append(row)
    results.sort(key=lambda item: (-item["score"], item.get("provider", ""), item.get("resource", "")))
    return results


def probe_official_source(resource, timeout=10):
    url = resource.get("verification", {}).get("official_source")
    if not url:
        return {"ok": False, "status": None, "error": "missing official source"}
    request = Request(url, headers={"User-Agent": "zero-dollar-agent-fabric/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return {"ok": 200 <= response.status < 400, "status": response.status, "url": response.geturl()}
    except HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": str(exc), "url": url}
    except URLError as exc:
        return {"ok": False, "status": None, "error": str(exc.reason), "url": url}


def audit(registry, probe=False):
    rows = []
    for resource in registry.get("resources", []):
        row = {
            "id": resource.get("id"),
            "provider": resource.get("provider"),
            "gate": eligibility(resource, registry["policy"]),
        }
        if probe:
            row["official_source_probe"] = probe_official_source(resource)
        rows.append(row)
    return rows


def compact_result(resource):
    return {
        "id": resource["id"],
        "provider": resource["provider"],
        "resource": resource["resource"],
        "category": resource["category"],
        "free_limit": resource.get("free_limit"),
        "architecture": resource.get("architecture", []),
        "region": resource.get("region", []),
        "card_required": resource.get("card_required"),
        "reclaim_policy": resource.get("reclaim_policy"),
        "official_source": resource.get("verification", {}).get("official_source"),
        "verified_at": resource.get("verification", {}).get("verified_at"),
        "score": resource.get("score"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zero-cost infrastructure registry and verification gate")
    sub = parser.add_subparsers(dest="command", required=True)

    sync_parser = sub.add_parser("sync", help="Fetch free-for-dev as candidate-only discovery data")
    sync_parser.add_argument("--count-only", action="store_true")

    query_parser = sub.add_parser("query", help="Query normalized resources")
    query_parser.add_argument("--category")
    query_parser.add_argument("--architecture")
    query_parser.add_argument("--region")
    query_parser.add_argument("--include-ineligible", action="store_true")

    audit_parser = sub.add_parser("audit", help="Audit official verification and freshness")
    audit_parser.add_argument("--probe", action="store_true", help="Check official source reachability; never auto-promotes status")

    args = parser.parse_args(argv)
    registry = load_json(REGISTRY_PATH)

    if args.command == "sync":
        payload = sync_candidates(registry)
        output = {"count": payload["count"], "path": str(CANDIDATES_PATH)} if args.count_only else payload
    elif args.command == "query":
        resources = query_resources(
            registry,
            category=args.category,
            architecture=args.architecture,
            region=args.region,
            eligible_only=not args.include_ineligible,
        )
        output = [compact_result(item) for item in resources]
    else:
        output = audit(registry, probe=args.probe)

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Explicitly fictional unit-test fixtures, never scientific evidence.

Some tests set synthetic=False solely to exercise the real-result validation
branch. All titles, logs, scores, data and revision strings here are fixtures.
"""

import hashlib
import json
from pathlib import Path


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_ready_project(path, modules=2):
    from paper_composer.core import init_project

    path = Path(path)
    init_project(path, name="UNIT TEST FIXTURE; NOT REAL RESEARCH", modules=modules)
    brief = read_json(path / "brief.json")
    brief["research_question"] = "TEST FIXTURE: do complementary modules help?"
    brief["practical_contribution"] = "TEST FIXTURE: low-cost complementary adaptation."
    brief["target"].update(journal="Fixture Journal", ranking_system="JCR", quartile="Q2", ranking_year="2025")
    brief["data"].update(dataset="unit-test-only", version="fixture-v1", license="CC0 fixture")
    brief["metric"].update(name="fixture_accuracy", unit="fraction")
    for split in ("train", "dev", "test"):
        manifest = path / brief["data"]["splits"][split]["manifest_path"]
        write_json(manifest, [f"fixture-{split}-{i}" for i in range(3)])
        brief["data"]["splits"][split]["sha256"] = sha256(manifest)
    write_json(path / "brief.json", brief)

    papers = read_json(path / "papers.json")
    for paper in papers:
        for key in ("title", "citation", "evidence_location", "mechanism", "inputs", "outputs", "assumptions", "limitations"):
            paper[key] = f"UNIT TEST FIXTURE {paper['id']} {key}"
        paper["url"] = f"https://example.org/fixture/{paper['id']}"
        paper["code"].update(license_checked=True, attribution="Fixture provenance; no upstream code reused")
    write_json(path / "papers.json", papers)

    candidates = read_json(path / "candidates.json")
    candidate = candidates["items"][0]
    candidate["baseline"].update(name="fixture-baseline", why_strong="Fixture established reference")
    for module in candidate["modules"]:
        for key in ("mechanism", "interface", "adaptation", "complementarity"):
            module[key] = f"UNIT TEST FIXTURE {module['id']} {key}"
    for key in ("selection_reason", "expected_benefit", "risks"):
        candidate[key] = f"UNIT TEST FIXTURE {key}"
    candidate["nearest_neighbors"] = [{"citation": "UNIT TEST nearest-neighbor fixture", "url": "https://example.org/fixture/neighbor", "difference": "UNIT TEST application adaptation"}]
    candidate["search_log"] = {"queries": ["unit-test-only fictional search"], "searched_at": "2026-10-27", "sources": ["https://example.org/fixture/search"]}
    write_json(path / "candidates.json", candidates)

    plan = read_json(path / "plan.json")
    plan["baseline_check"].update(reference_metric=0.7, tolerance=0.2, reference_context="UNIT TEST FIXTURE: same fictional protocol")
    plan["comparability"] = {key: f"UNIT TEST fixed {key}" for key in plan["comparability"]}
    plan["stop_rules"]["simplify_when"] = "When fixture gain is absent, retain the baseline."
    write_json(path / "plan.json", plan)
    return path

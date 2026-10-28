"""Local protocol bookkeeping. This module never searches, trains, or invents data."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import statistics
import tempfile
from datetime import datetime, timezone

from .templates import project_documents

INPUTS = ("brief.json", "papers.json", "candidates.json", "plan.json")
ALL_DOCUMENTS = INPUTS + ("claims.json",)
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
HASH = re.compile(r"^[a-f0-9]{64}$")


class ProjectError(ValueError):
    """An actionable user-input or protocol error."""


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    def reject(value):
        raise ProjectError(f"Non-finite JSON number: {value}")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ProjectError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=reject, object_pairs_hook=pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectError(f"Cannot read JSON {path}: {exc}") from exc


def write_json(path, value):
    path = Path(path)
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    atomic_text(path, encoded)


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


class ProjectLock:
    """Exclusive per-project writer lock; stale locks require manual inspection."""
    def __init__(self, root):
        self.path = Path(root) / ".paper-composer.lock"

    def __enter__(self):
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self.fd, f"pid={os.getpid()}\n".encode())
        except FileExistsError as exc:
            raise ProjectError(f"Project writer lock exists: {self.path}; inspect before removing it") from exc
        return self

    def __exit__(self, *args):
        os.close(self.fd)
        self.path.unlink()


def project_path(path):
    root = Path(path).resolve()
    if not root.is_dir():
        raise ProjectError(f"Project directory does not exist: {root}")
    return root


def local_file(root, value):
    if not isinstance(value, str) or not value.strip():
        raise ProjectError("Artifact path must be a non-empty project-relative string")
    relative = Path(value)
    # Reject Windows drive syntax even when the project is opened on POSIX.
    if relative.is_absolute() or re.match(r"^[A-Za-z]:", value) or value.startswith(("\\", "/")):
        raise ProjectError(f"Artifact path must be project-relative: {value}")
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ProjectError(f"Artifact path escapes project: {value}") from exc
    if not target.is_file():
        raise ProjectError(f"Artifact does not exist: {value}")
    return target


def verified_file(root, path, expected):
    if not isinstance(expected, str) or not HASH.fullmatch(expected):
        raise ProjectError(f"Expected lowercase SHA256 for {path}")
    target = local_file(root, path)
    if file_sha256(target) != expected:
        raise ProjectError(f"SHA256 mismatch: {path}")
    return target


def documents(root):
    return {name: read_json(root / name) for name in ALL_DOCUMENTS}


def init_project(path, name="untitled", modules=2):
    root = Path(path).resolve()
    if type(modules) is not int or modules not in (2, 3):
        raise ProjectError("modules must be 2 or 3")
    if not isinstance(name, str) or not name.strip():
        raise ProjectError("project name must be non-empty")
    if root.exists():
        raise ProjectError(f"Refusing to overwrite existing path: {root}")
    root.mkdir(parents=True)
    for filename, value in project_documents(name, modules).items():
        write_json(root / filename, value)
    (root / "artifacts").mkdir()
    for split in ("train", "dev", "test"):
        write_json(root / "artifacts" / f"{split}_ids.json", [])
    atomic_text(root / "results.jsonl", "")
    return {"project": str(root), "status": "PLAN_ONLY", "synthetic": False, "next": "Fill protocol documents, then validate --ready and freeze"}


def _shape(value, exemplar, location, errors):
    if exemplar is None:
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            errors.append(f"{location}: expected finite number or null")
    elif isinstance(exemplar, dict):
        if not isinstance(value, dict):
            errors.append(f"{location}: expected object")
            return
        for key, expected in exemplar.items():
            if key not in value:
                errors.append(f"{location}.{key}: missing required key")
            else:
                _shape(value[key], expected, f"{location}.{key}", errors)
    elif isinstance(exemplar, list):
        if not isinstance(value, list):
            errors.append(f"{location}: expected array")
        elif exemplar:
            for index, item in enumerate(value):
                _shape(item, exemplar[0], f"{location}[{index}]", errors)
    elif type(exemplar) in (int, float):
        if type(value) not in (int, float) or not math.isfinite(value):
            errors.append(f"{location}: expected finite number, not boolean")
    elif type(value) is not type(exemplar):
        errors.append(f"{location}: expected {type(exemplar).__name__}")


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and not value.strip().lower().startswith(("todo", "tbd", "待填"))


def selected_candidate(docs):
    data = docs["candidates.json"]
    matches = [item for item in data["items"] if item["id"] == data["selected_id"]]
    if len(matches) != 1:
        raise ProjectError("candidates.selected_id must identify exactly one candidate")
    return matches[0]


def _matrix(candidate):
    ids = [module["id"] for module in candidate["modules"]]
    arms = []
    for count in range(len(ids) + 1):
        for subset in itertools.combinations(ids, count):
            arms.append({"id": "+".join(subset) if subset else "baseline", "modules": list(subset)})
    return arms


def _validate_documents(root, docs, ready=False):
    errors = []
    templates = project_documents()
    # Prior exploration costs are optional in v1 for existing project files.
    templates["brief.json"]["budget"].pop("prior_gpu_hours")
    templates["brief.json"]["budget"].pop("prior_runs")
    for name in ALL_DOCUMENTS:
        _shape(docs[name], templates[name], name, errors)
    if errors:
        return errors
    brief, papers, candidates, plan = (docs[name] for name in INPUTS)
    claims = docs["claims.json"]["claims"]
    if type(brief["schema_version"]) is not int or brief["schema_version"] != 1:
        errors.append("brief.schema_version must be integer 1")
    if brief["mode"] != "journal-practical":
        errors.append("Only journal-practical mode is implemented")
    if type(brief["candidate_limit"]) is not int or not 1 <= brief["candidate_limit"] <= 5:
        errors.append("candidate_limit must be an integer from 1 to 5")
    if not 1 <= len(candidates["items"]) <= brief["candidate_limit"]:
        errors.append("Candidate count exceeds the configured shortlist limit or is zero")
    if type(brief["budget"]["max_runs"]) is not int or brief["budget"]["max_runs"] < 1:
        errors.append("budget.max_runs must be a positive integer")
    if brief["budget"]["max_gpu_hours"] <= 0:
        errors.append("budget.max_gpu_hours must be positive")
    prior_runs = brief["budget"].get("prior_runs", 0)
    prior_hours = brief["budget"].get("prior_gpu_hours", 0.0)
    if type(prior_runs) is not int or prior_runs < 0:
        errors.append("budget.prior_runs must be a nonnegative integer")
    if type(prior_hours) not in (int, float) or not math.isfinite(prior_hours) or prior_hours < 0:
        errors.append("budget.prior_gpu_hours must be a finite nonnegative number")
    if type(brief["hardware"]["gpu_count"]) is not int or brief["hardware"]["gpu_count"] < 0:
        errors.append("hardware.gpu_count must be a nonnegative integer")
    if brief["data"]["selection_split"] != "dev" or brief["data"]["test_policy"] != "final-only":
        errors.append("Selection must use dev; test_policy must be final-only")
    if plan["development_split"] != "dev" or plan["final_split"] != "test" or plan["final_arms"] != "baseline-and-selected":
        errors.append("Plan must use dev and final-only test for baseline-and-selected")
    seeds = plan["seeds"]
    if not seeds or any(type(seed) is not int or seed < 0 for seed in seeds) or len(set(seeds)) != len(seeds):
        errors.append("plan.seeds must contain distinct nonnegative integer seeds")
    if plan["estimated_gpu_hours_per_run"] < 0:
        errors.append("estimated_gpu_hours_per_run must be nonnegative")
    rules = plan["stop_rules"]
    if type(rules["max_failed_runs"]) is not int or rules["max_failed_runs"] < 1 or rules["min_gain"] < 0:
        errors.append("stop_rules require positive integer max_failed_runs and nonnegative min_gain")
    for label, values in (("paper", papers), ("candidate", candidates["items"]), ("claim", claims)):
        ids = [item["id"] for item in values]
        if any(not IDENTIFIER.fullmatch(item) for item in ids) or len(ids) != len(set(ids)):
            errors.append(f"{label} IDs must be unique simple identifiers")
    if not 2 <= len(papers) <= 3:
        errors.append("papers.json requires 2 or 3 main source papers; put extra neighbors in candidates")
    paper_ids = {p["id"] for p in papers}
    for candidate in candidates["items"]:
        modules = candidate["modules"]
        ids = [m["id"] for m in modules]
        if len(modules) not in (2, 3):
            errors.append(f"{candidate['id']}: requires 2 or 3 added mechanisms")
        if len(set(ids)) != len(ids) or any(not IDENTIFIER.fullmatch(m) or m == "baseline" for m in ids):
            errors.append(f"{candidate['id']}: module IDs must be distinct; baseline is reserved")
        sources = {candidate["baseline"]["paper_id"]} | {m["paper_id"] for m in modules}
        if not sources <= paper_ids or not 2 <= len(sources) <= 3:
            errors.append(f"{candidate['id']}: baseline/modules must cite 2 or 3 existing paper IDs")
    try:
        candidate = selected_candidate(docs)
    except ProjectError as exc:
        errors.append(str(exc))
        return errors
    for claim in claims:
        if claim["status"] not in ("planned", "supported", "unsupported", "contradicted"):
            errors.append(f"{claim['id']}: invalid claim status")
        if any(not isinstance(p, str) or p not in paper_ids for p in claim["source_paper_ids"]):
            errors.append(f"{claim['id']}: unknown source paper ID")
        if any(not isinstance(r, str) for r in claim["supporting_run_ids"]):
            errors.append(f"{claim['id']}: supporting_run_ids must be strings")
    if not ready or errors:
        return errors
    required_texts = {
        "brief.research_question": brief["research_question"],
        "brief.practical_contribution": brief["practical_contribution"],
        "brief.project_name": brief["project_name"],
        **{f"target.{k}": v for k, v in brief["target"].items()},
        **{f"data.{k}": brief["data"][k] for k in ("dataset", "version", "license")},
        "metric.name": brief["metric"]["name"],
        **{f"comparability.{k}": v for k, v in plan["comparability"].items()},
        "stop_rules.simplify_when": rules["simplify_when"],
        "stop_rules.negative_result_policy": rules["negative_result_policy"],
        "baseline_check.reference_context": plan["baseline_check"]["reference_context"],
        **{f"baseline.{k}": v for k, v in candidate["baseline"].items()},
        **{f"candidate.{k}": candidate[k] for k in ("selection_reason", "expected_benefit", "risks")},
    }
    if brief["target"]["ranking_system"] == "unspecified":
        errors.append("Specify target.ranking_system explicitly; JCR and CAS are not interchangeable")
    for paper in papers:
        required_texts.update({f"{paper['id']}.{k}": paper[k] for k in ("title", "citation", "url", "evidence_location", "mechanism", "inputs", "outputs", "assumptions", "limitations")})
        code = paper["code"]
        if code["reuse"]:
            if not code["license_checked"] or not code["reuse_allowed"] or code["license"].lower() in ("unknown", "not-applicable", ""):
                errors.append(f"{paper['id']}: reused code needs checked, permitted license")
            required_texts[f"{paper['id']}.code.url"] = code["url"]
            required_texts[f"{paper['id']}.code.attribution"] = code["attribution"]
    for module in candidate["modules"]:
        required_texts.update({f"{module['id']}.{k}": module[k] for k in ("mechanism", "interface", "adaptation", "complementarity")})
    search = candidate["search_log"]
    if not search["queries"] or not search["sources"] or not _text(search["searched_at"]):
        errors.append("Nearest-neighbor search needs queries, sources and searched_at")
    if any(not _text(x) for x in search["queries"] + search["sources"]):
        errors.append("Nearest-neighbor search queries/sources must be non-empty strings")
    if not candidate["nearest_neighbors"]:
        errors.append("Record at least one checked nearest neighbor and the actual difference")
    for index, neighbor in enumerate(candidate["nearest_neighbors"]):
        if not isinstance(neighbor, dict) or any(not _text(neighbor.get(k)) for k in ("citation", "url", "difference")):
            errors.append(f"nearest_neighbors[{index}]: requires citation, url and difference")
    for name, value in required_texts.items():
        if not _text(value):
            errors.append(f"{name}: fill the evidence-backed value")
    baseline = plan["baseline_check"]
    if baseline["reference_metric"] is None or baseline["tolerance"] is None or (baseline["tolerance"] is not None and baseline["tolerance"] < 0):
        errors.append("baseline_check needs a finite reference_metric and nonnegative tolerance")
    expected = (len(_matrix(candidate)) + 2) * len(seeds)
    if expected + prior_runs > brief["budget"]["max_runs"]:
        errors.append(f"Planned {expected} dev/final runs plus {prior_runs} prior runs exceed max_runs={brief['budget']['max_runs']}")
    expected_hours = expected * plan["estimated_gpu_hours_per_run"] + prior_hours
    if expected_hours > brief["budget"]["max_gpu_hours"] + 1e-12:
        errors.append(f"Estimated {expected_hours:g} GPU-hours exceed predeclared budget")
    split_ids = {}
    for split, manifest in brief["data"]["splits"].items():
        try:
            values = read_json(verified_file(root, manifest["manifest_path"], manifest["sha256"]))
            if not isinstance(values, list) or not values or any(not _text(x) for x in values) or len(set(values)) != len(values):
                raise ProjectError(f"{split} manifest requires a nonempty list of distinct sample ID strings")
            split_ids[split] = set(values)
        except ProjectError as exc:
            errors.append(str(exc))
    for left, right in itertools.combinations(split_ids, 2):
        if split_ids[left] & split_ids[right]:
            errors.append(f"Data leakage: sample IDs overlap between {left} and {right}")
    return errors


def validate_project(path, ready=False):
    try:
        root = project_path(path)
        errors = _validate_documents(root, documents(root), ready)
        if not errors and (root / "protocol.json").exists():
            docs, protocol = _protocol(root)
            records = _ledger(root)
            _validate_ledger(root, docs, protocol, records)
            if (root / "selection.json").exists():
                selection = _selection(root, docs, protocol, records)
                if any(r["split"] == "test" and r["arm"] not in ("baseline", selection["arm"]) for r in records):
                    errors.append("Test ledger contains an unselected arm")
            elif any(r["split"] == "test" for r in records):
                errors.append("Test evidence exists before a development selection")
        return errors
    except (ProjectError, TypeError, ValueError, KeyError) as exc:
        return [str(exc)]


def _require_valid(root, ready=False):
    docs = documents(root)
    errors = _validate_documents(root, docs, ready)
    if errors:
        raise ProjectError("; ".join(errors))
    return docs


def ablation_matrix(path):
    return _matrix(selected_candidate(_require_valid(project_path(path))))


def protocol_hash(docs):
    return digest({name: docs[name] for name in INPUTS})


def _ledger(root):
    path = root / "results.jsonl"
    if not path.exists():
        raise ProjectError("Missing results.jsonl; do not silently reset an experiment ledger")
    records = []
    try:
        for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            record = json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            if not isinstance(record, dict):
                raise ValueError("expected object")
            records.append(record)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ProjectError(f"Invalid result ledger: {exc}") from exc
    return records


def freeze_project(path):
    root = project_path(path)
    with ProjectLock(root):
        if (root / "protocol.json").exists():
            raise ProjectError("Protocol already frozen; use a new project for a changed protocol")
        docs = _require_valid(root, ready=True)
        if _ledger(root) or (root / "selection.json").exists():
            raise ProjectError("Cannot freeze a project that already has results or a selection")
        arms = _matrix(selected_candidate(docs))
        protocol = {"protocol_hash": protocol_hash(docs), "created_at": now(), "arms": arms,
                    "expected_development_runs": len(arms) * len(docs["plan.json"]["seeds"]),
                    "expected_final_runs": 2 * len(docs["plan.json"]["seeds"])}
        write_json(root / "protocol.json", protocol)
        return protocol


def _protocol(root):
    docs = _require_valid(root, ready=True)
    protocol = read_json(root / "protocol.json")
    if not isinstance(protocol, dict) or protocol.get("protocol_hash") != protocol_hash(docs):
        raise ProjectError("Frozen protocol hash mismatch: protocol inputs changed")
    arms = _matrix(selected_candidate(docs))
    if protocol.get("arms") != arms or protocol.get("expected_development_runs") != len(arms) * len(docs["plan.json"]["seeds"]):
        raise ProjectError("Frozen ablation matrix or expected run count was altered")
    if protocol.get("expected_final_runs") != 2 * len(docs["plan.json"]["seeds"]):
        raise ProjectError("Frozen final run count was altered")
    return docs, protocol


RESULT_KEYS = {"run_id", "arm", "seed", "split", "status", "metric", "gpu_hours", "synthetic", "protocol_hash", "code_version",
               "config_path", "config_sha256", "artifact_path", "artifact_sha256", "outcome", "notes"}


def _check_result(root, docs, protocol, record):
    if not isinstance(record, dict) or not RESULT_KEYS <= record.keys():
        missing = RESULT_KEYS - record.keys() if isinstance(record, dict) else RESULT_KEYS
        raise ProjectError("Missing result fields: " + ", ".join(sorted(missing)))
    if record.keys() - RESULT_KEYS - {"recorded_at"}:
        raise ProjectError("Unknown result fields: " + ", ".join(sorted(record.keys() - RESULT_KEYS - {"recorded_at"})))
    if not isinstance(record["run_id"], str) or not IDENTIFIER.fullmatch(record["run_id"]):
        raise ProjectError("run_id must be a simple identifier")
    if record["arm"] not in [arm["id"] for arm in protocol["arms"]]:
        raise ProjectError("Unknown ablation arm")
    if type(record["seed"]) is not int or record["seed"] not in docs["plan.json"]["seeds"]:
        raise ProjectError("seed must be a predeclared integer seed")
    if record["split"] not in ("dev", "test"):
        raise ProjectError("Only dev and final test results can be registered")
    if record["status"] not in ("completed", "failed"):
        raise ProjectError("status must be completed or failed")
    if type(record["gpu_hours"]) not in (int, float) or not math.isfinite(record["gpu_hours"]) or record["gpu_hours"] < 0:
        raise ProjectError("gpu_hours must be a finite nonnegative number, not boolean")
    metric = record["metric"]
    if record["status"] == "completed":
        if type(metric) not in (int, float) or not math.isfinite(metric):
            raise ProjectError("Completed runs need a finite numeric metric, not boolean")
        if record["outcome"] not in ("positive", "negative", "neutral"):
            raise ProjectError("Completed run outcome must be positive, negative or neutral")
    elif metric is not None or record["outcome"] != "failure":
        raise ProjectError("Failed runs need metric=null and outcome=failure")
    if type(record["synthetic"]) is not bool or record["synthetic"] != docs["brief.json"]["synthetic"]:
        raise ProjectError("Result synthetic flag must match the project")
    if record["protocol_hash"] != protocol["protocol_hash"]:
        raise ProjectError("Result protocol_hash does not match frozen protocol")
    for field in ("code_version", "notes"):
        if not _text(record[field]):
            raise ProjectError(f"Result {field} must be non-empty")
    verified_file(root, record["config_path"], record["config_sha256"])
    verified_file(root, record["artifact_path"], record["artifact_sha256"])


def _validate_ledger(root, docs, protocol, records):
    run_ids, complete_keys = set(), set()
    for record in records:
        _check_result(root, docs, protocol, record)
        if record["run_id"] in run_ids:
            raise ProjectError("Duplicate run_id in ledger")
        run_ids.add(record["run_id"])
        if record["status"] == "completed":
            key = (record["arm"], record["seed"], record["split"])
            if key in complete_keys:
                raise ProjectError("Duplicate completed arm/seed/split in ledger")
            complete_keys.add(key)


def _completed(records, split):
    return [record for record in records if record["split"] == split and record["status"] == "completed"]


def _missing(records, arms, seeds, split):
    present = {(record["arm"], record["seed"]) for record in _completed(records, split)}
    return [{"arm": arm, "seed": seed, "split": split} for arm in arms for seed in seeds if (arm, seed) not in present]


def _dev_digest(records):
    return digest([record for record in records if record["split"] == "dev"])


def _budget(docs, records):
    limits = docs["brief.json"]["budget"]
    hours = sum(record["gpu_hours"] for record in records) + limits.get("prior_gpu_hours", 0.0)
    runs = len(records) + limits.get("prior_runs", 0)
    failures = sum(record["status"] == "failed" for record in records)
    reasons = []
    if runs >= limits["max_runs"]:
        reasons.append("run budget exhausted")
    if hours >= limits["max_gpu_hours"]:
        reasons.append("GPU-hour budget exhausted")
    if failures >= docs["plan.json"]["stop_rules"]["max_failed_runs"]:
        reasons.append("failure stopping threshold reached")
    return {"used_gpu_hours": hours, "used_runs": runs, "registered_runs": len(records), "failed_runs": failures, "limits": limits,
            "stop_new_runs": bool(reasons), "stop_reasons": reasons}


def _selection(root, docs, protocol, records):
    selected = read_json(root / "selection.json")
    if not isinstance(selected, dict) or selected.get("protocol_hash") != protocol["protocol_hash"]:
        raise ProjectError("Selection protocol hash mismatch")
    if selected.get("development_ledger_hash") != _dev_digest(records):
        raise ProjectError("Development ledger changed after selection")
    arms = [arm["id"] for arm in protocol["arms"]]
    if selected.get("arm") not in arms or selected.get("arm") == "baseline" or not _text(selected.get("reason")):
        raise ProjectError("Selection needs a non-baseline arm and a recorded rationale")
    if _missing(records, arms, docs["plan.json"]["seeds"], "dev"):
        raise ProjectError("Cannot unlock test: complete all development arms and seeds first")
    if selected.get("selection_hash") != digest({k: v for k, v in selected.items() if k != "selection_hash"}):
        raise ProjectError("Selection hash mismatch")
    _baseline_ok(docs, records)
    return selected


def _baseline_ok(docs, records):
    values = [r["metric"] for r in _completed(records, "dev") if r["arm"] == "baseline"]
    reference = docs["plan.json"]["baseline_check"]
    if not values or abs(statistics.mean(values) - reference["reference_metric"]) > reference["tolerance"] + 1e-12:
        raise ProjectError("Development baseline reproduction is outside predeclared tolerance; investigate before selection")


def select_candidate(path, arm, reason):
    root = project_path(path)
    with ProjectLock(root):
        if (root / "selection.json").exists():
            raise ProjectError("Selection already locked; no reselection after unlocking test")
        docs, protocol = _protocol(root)
        records = _ledger(root)
        _validate_ledger(root, docs, protocol, records)
        arms = [item["id"] for item in protocol["arms"]]
        if arm not in arms or arm == "baseline":
            raise ProjectError("Select a declared non-baseline arm; if no mechanism is useful, report the negative result")
        if not _text(reason):
            raise ProjectError("Selection needs a development-only rationale")
        if _missing(records, arms, docs["plan.json"]["seeds"], "dev"):
            raise ProjectError("Complete every development arm and seed before selection")
        if any(r["split"] == "test" for r in records):
            raise ProjectError("Test results cannot precede selection")
        budget = _budget(docs, records)
        if budget["stop_new_runs"]:
            raise ProjectError("Stop condition reached: " + "; ".join(budget["stop_reasons"]))
        _baseline_ok(docs, records)
        means = {a: statistics.mean([r["metric"] for r in _completed(records, "dev") if r["arm"] == a]) for a in arms}
        direction = 1 if docs["brief.json"]["metric"]["higher_is_better"] else -1
        gain = direction * (means[arm] - means["baseline"])
        threshold = docs["plan.json"]["stop_rules"]["min_gain"]
        # A small/negative gain is recorded, not censored. The plan's simplification
        # rule plus explicit rationale governs the human's pragmatic decision.
        selection = {"arm": arm, "reason": reason, "protocol_hash": protocol["protocol_hash"],
                     "development_ledger_hash": _dev_digest(records), "created_at": now(),
                     "development_means": means, "gain": gain, "meets_min_gain": gain >= threshold,
                     "simplification_rule": docs["plan.json"]["stop_rules"]["simplify_when"]}
        selection["selection_hash"] = digest(selection)
        write_json(root / "selection.json", selection)
        return selection


def record_result(path, result):
    root = project_path(path)
    with ProjectLock(root):
        docs, protocol = _protocol(root)
        records = _ledger(root)
        _validate_ledger(root, docs, protocol, records)
        _check_result(root, docs, protocol, result)
        if any(r["run_id"] == result["run_id"] for r in records):
            raise ProjectError("run_id already exists; results are append-only")
        if result["status"] == "completed" and any(r["status"] == "completed" and all(r[k] == result[k] for k in ("arm", "seed", "split")) for r in records):
            raise ProjectError("A completed result already exists for this arm/seed/split")
        if result["split"] == "dev" and (root / "selection.json").exists():
            raise ProjectError("Development results are locked after selection")
        if result["split"] == "test":
            selection = _selection(root, docs, protocol, records)
            if result["arm"] not in ("baseline", selection["arm"]):
                raise ProjectError("Final test permits only the frozen baseline and selected arm")
        registered = dict(result)
        registered["recorded_at"] = now()
        records.append(registered)
        # Persist already incurred cost even if it exceeds a stop condition.
        atomic_text(root / "results.jsonl", "".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in records))
        return {"record": registered, "budget": _budget(docs, records),
                "notice": "Registered reported evidence; file hashes do not independently establish experimental truth"}


def build_report(path):
    root = project_path(path)
    errors = validate_project(root)
    if errors:
        return {"status": "INVALID", "blockers": errors, "paper_ready": False}
    docs = documents(root)
    brief = docs["brief.json"]
    report = {"project": brief["project_name"], "synthetic": brief["synthetic"], "status": "PLAN_ONLY", "paper_ready": False,
              "blockers": [], "warnings": [], "counts": {}, "metric": brief["metric"], "summary": {},
              "interpretation": "Evidence readiness is bookkeeping, not proof of novelty, scientific validity or journal acceptance."}
    if not (root / "protocol.json").exists():
        report["blockers"] = validate_project(root, ready=True)
        report["warnings"].append("Protocol not frozen; output may only be a plan or a draft with explicit placeholders")
        return report
    try:
        docs, protocol = _protocol(root)
        records = _ledger(root)
        _validate_ledger(root, docs, protocol, records)
        selection = _selection(root, docs, protocol, records) if (root / "selection.json").exists() else None
        if any(r["split"] == "test" for r in records) and not selection:
            raise ProjectError("Test evidence exists without a locked development selection")
        if selection and any(r["split"] == "test" and r["arm"] not in ("baseline", selection["arm"]) for r in records):
            raise ProjectError("Test ledger contains an unselected arm")
    except (ProjectError, TypeError, KeyError, ValueError) as exc:
        report["status"] = "INVALID"
        report["blockers"] = [str(exc)]
        return report
    arms = [a["id"] for a in protocol["arms"]]
    seeds = docs["plan.json"]["seeds"]
    missing_dev = _missing(records, arms, seeds, "dev")
    missing_test = _missing(records, ["baseline", selection["arm"]], seeds, "test") if selection else []
    report.update({"protocol_hash": protocol["protocol_hash"], "budget": _budget(docs, records),
                   "missing_development": missing_dev, "missing_final_test": missing_test,
                   "counts": {"registered": len(records), "development_completed": len(_completed(records, "dev")),
                              "final_test_completed": len(_completed(records, "test")),
                              "failed": sum(r["status"] == "failed" for r in records),
                              "negative": sum(r["outcome"] == "negative" for r in records)}, "selection": selection})
    for split in ("dev", "test"):
        report["summary"][split] = {}
        for arm in arms:
            values = [r["metric"] for r in _completed(records, split) if r["arm"] == arm]
            if values:
                report["summary"][split][arm] = {"n": len(values), "mean": statistics.mean(values), "sample_std": statistics.stdev(values) if len(values) > 1 else None}
    report["status"] = "DEVELOPMENT_INCOMPLETE" if missing_dev else "DEVELOPMENT_READY"
    if missing_dev:
        report["blockers"].append("Complete predeclared development arms and seeds")
    else:
        try:
            _baseline_ok(docs, records)
        except ProjectError as exc:
            report["blockers"].append(str(exc))
    if not selection:
        report["blockers"].append("Freeze a development-only selection before final test")
    else:
        report["status"] = "FINAL_TEST_INCOMPLETE" if missing_test else "EVIDENCE_READY"
        if missing_test:
            report["blockers"].append("Complete final baseline and selected-arm seeds")
        if not selection["meets_min_gain"]:
            report["warnings"].append("Selected arm missed the predeclared practical gain; preserve this result and the simplification rationale")
    completed_final = {r["run_id"] for r in _completed(records, "test")}
    report["claims"] = docs["claims.json"]["claims"]
    if not report["claims"]:
        report["blockers"].append("Add scoped claims with evidence links")
    for claim in report["claims"]:
        if claim["status"] != "supported" or not all(_text(claim[k]) for k in ("text", "scope", "boundary")):
            report["blockers"].append(f"{claim['id']}: claim is planned/unsupported or lacks scope and boundary")
        if not claim["supporting_run_ids"] or not set(claim["supporting_run_ids"]) <= completed_final:
            report["blockers"].append(f"{claim['id']}: link completed final-test runs; dev evidence alone is not final evidence")
    if report["budget"]["stop_new_runs"]:
        report["warnings"].extend(report["budget"]["stop_reasons"])
        if missing_dev or missing_test or not selection:
            report["status"] = "BUDGET_STOP"
    if report["status"] == "EVIDENCE_READY" and report["blockers"]:
        report["status"] = "EVIDENCE_INCOMPLETE"
    if brief["synthetic"]:
        report["underlying_status"] = report["status"]
        report["status"] = "SYNTHETIC_DEMO"
        report["warnings"].append("SYNTHETIC: all demonstration numbers and source cards are invented; never cite them as scientific evidence")
    report["evidence_ready"] = report["status"] == "EVIDENCE_READY" and not report["blockers"]
    # Never label the scientific paper ready automatically.
    report["allowed_output"] = "Evidence-linked draft for human review" if report["evidence_ready"] else "Plan or explicitly incomplete draft; synthetic examples remain demonstrations"
    return report


def run_demo(path, modules=2):
    init_project(path, "SYNTHETIC workflow demonstration", modules)
    root = project_path(path)
    docs = documents(root)
    brief = docs["brief.json"]
    brief.update(synthetic=True, research_question="SYNTHETIC: can complementary toy mechanisms improve a fixed toy baseline?",
                 practical_contribution="SYNTHETIC demonstration of protocol bookkeeping, not a scientific result")
    brief["target"] = {"journal": "SYNTHETIC unnamed journal", "ranking_system": "JCR (example only)", "quartile": "Q2 (example only)", "ranking_year": "2026 (not verified)"}
    brief["metric"] = {"name": "SYNTHETIC toy score", "higher_is_better": True, "unit": "arbitrary"}
    brief["data"].update(dataset="SYNTHETIC toy dataset", version="1", license="SYNTHETIC generated IDs, CC0")
    brief["budget"] = {"max_gpu_hours": 24.0, "max_runs": 40}
    for split in ("train", "dev", "test"):
        file = root / "artifacts" / f"{split}_ids.json"
        write_json(file, [f"synthetic-{split}-{i}" for i in range(5)])
        brief["data"]["splits"][split]["sha256"] = file_sha256(file)
    for paper in docs["papers.json"]:
        for key in ("title", "citation", "evidence_location", "mechanism", "inputs", "outputs", "assumptions", "limitations"):
            paper[key] = f"SYNTHETIC {paper['id']} {key}: fictional demonstration only"
        paper["url"] = f"https://example.invalid/synthetic/{paper['id']}"
    candidate = selected_candidate(docs)
    candidate["baseline"].update(name="SYNTHETIC fixed baseline", why_strong="SYNTHETIC comparable baseline")
    for module in candidate["modules"]:
        for key in ("mechanism", "interface", "adaptation", "complementarity"):
            module[key] = f"SYNTHETIC {module['id']} {key}"
    candidate.update(selection_reason="SYNTHETIC complementary inputs", expected_benefit="SYNTHETIC toy benefit", risks="SYNTHETIC interaction may be negative")
    candidate["nearest_neighbors"] = [{"citation": "SYNTHETIC invented neighbor", "url": "https://example.invalid/neighbor", "difference": "SYNTHETIC demonstration difference; no novelty claim"}]
    candidate["search_log"] = {"queries": ["SYNTHETIC search not executed"], "sources": ["SYNTHETIC example"], "searched_at": "SYNTHETIC not searched"}
    plan = docs["plan.json"]
    plan["baseline_check"] = {"reference_metric": 0.70, "tolerance": 0.01, "reference_context": "SYNTHETIC fixed toy reference"}
    plan["comparability"] = {key: f"SYNTHETIC fixed {key}" for key in plan["comparability"]}
    plan["stop_rules"]["simplify_when"] = "Choose fewer mechanisms when development means are within 0.005; preserve negative modules"
    for name, value in docs.items():
        write_json(root / name, value)
    protocol = freeze_project(root)
    config = root / "artifacts" / "synthetic_config.json"
    write_json(config, {"synthetic": True, "training_executed": False, "purpose": "bookkeeping demonstration"})
    counter = 0
    def add(arm, seed, split):
        nonlocal counter
        counter += 1
        count = len(next(item["modules"] for item in protocol["arms"] if item["id"] == arm))
        # m2 alone is deliberately negative to demonstrate uncensored evidence.
        effect = -0.005 if arm == "m2" else 0.012 * count
        value = 0.70 + effect + (seed - 1) * 0.001 - (0.002 if split == "test" else 0)
        run_id = f"synthetic_run_{counter:03d}"
        artifact = root / "artifacts" / f"{run_id}.json"
        write_json(artifact, {"synthetic": True, "training_executed": False, "run_id": run_id, "arm": arm, "seed": seed, "split": split, "metric": value})
        record_result(root, {"run_id": run_id, "arm": arm, "seed": seed, "split": split, "status": "completed", "metric": value,
                            "gpu_hours": 0.0, "synthetic": True, "protocol_hash": protocol["protocol_hash"],
                            "code_version": "synthetic-generator-v1-no-training", "config_path": "artifacts/synthetic_config.json", "config_sha256": file_sha256(config),
                            "artifact_path": f"artifacts/{run_id}.json", "artifact_sha256": file_sha256(artifact),
                            "outcome": "negative" if effect < 0 else "neutral" if count == 0 else "positive",
                            "notes": "SYNTHETIC: generated values, no paper retrieval or model training occurred"})
        return run_id
    for arm in protocol["arms"]:
        for seed in plan["seeds"]:
            add(arm["id"], seed, "dev")
    chosen = protocol["arms"][-1]["id"]
    select_candidate(root, chosen, "SYNTHETIC: full combination has the best toy development mean")
    final_ids = []
    for arm in ("baseline", chosen):
        for seed in plan["seeds"]:
            final_ids.append(add(arm, seed, "test"))
    docs["claims.json"]["claims"][0].update(text="SYNTHETIC toy combination exceeds the toy baseline", status="supported",
                                          supporting_run_ids=final_ids, scope="SYNTHETIC workflow demonstration only", boundary="Not real scientific evidence; no training or retrieval occurred")
    write_json(root / "claims.json", docs["claims.json"])
    report = build_report(root)
    write_json(root / "report.json", report)
    return report

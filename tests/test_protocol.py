"""Protocol and budget tests use only fictional local fixtures."""

from itertools import combinations
import json

from tests.fixtures import make_ready_project, read_json, sha256, write_json
from tests.test_cli import CLIBase


class ProtocolTests(CLIBase):
    def prepare(self, modules=2):
        make_ready_project(self.project, modules=modules)

    def edit(self, filename, change):
        value = read_json(self.project / filename)
        change(value)
        write_json(self.project / filename, value)

    def test_fresh_draft_is_structurally_valid_but_not_freezable(self):
        self.assert_ok(self.run_cli("init", self.project))
        self.assert_ok(self.run_cli("validate", self.project))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_complete_fixture_can_freeze(self):
        self.prepare()
        result = self.run_cli("freeze", self.project)
        self.assert_ok(result)
        frozen = json.loads(result.stdout)
        self.assertEqual(len(frozen["protocol_hash"]), 64)
        self.assertEqual(frozen["expected_development_runs"], 12)
        self.assertEqual(frozen["expected_final_runs"], 6)

    def test_two_module_matrix_has_every_subset_once(self):
        self.prepare(2)
        result = self.run_cli("ablations", self.project)
        self.assert_ok(result)
        actual = json.loads(result.stdout)
        actual = actual.get("arms", actual) if isinstance(actual, dict) else actual
        subsets = [frozenset(arm["modules"]) for arm in actual]
        self.assertEqual(len(subsets), 4)
        self.assertEqual(set(subsets), {frozenset(), frozenset({"m1"}), frozenset({"m2"}), frozenset({"m1", "m2"})})

    def test_three_module_matrix_has_every_subset_once(self):
        self.prepare(3)
        result = self.run_cli("ablations", self.project)
        self.assert_ok(result)
        actual = json.loads(result.stdout)
        actual = actual.get("arms", actual) if isinstance(actual, dict) else actual
        subsets = [frozenset(arm["modules"]) for arm in actual]
        expected = {frozenset(c) for n in range(4) for c in combinations(("m1", "m2", "m3"), n)}
        self.assertEqual(len(subsets), 8)
        self.assertEqual(set(subsets), expected)

    def test_budget_must_cover_development_and_final_runs(self):
        self.prepare()
        self.edit("brief.json", lambda d: d["budget"].update(max_runs=12))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_gpu_hour_budget_must_cover_planned_runs(self):
        self.prepare()
        self.edit("brief.json", lambda d: d["budget"].update(max_gpu_hours=0.1))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_prior_cost_is_included_when_checking_budget(self):
        self.prepare()
        for field, value in (("prior_runs", 13), ("prior_gpu_hours", 20.0)):
            with self.subTest(field=field):
                def update(brief):
                    brief["budget"].update(prior_runs=0, prior_gpu_hours=0.0)
                    brief["budget"][field] = value
                self.edit("brief.json", update)
                self.assert_rejected(self.run_cli("freeze", self.project))

    def test_budget_values_reject_bool_nan_infinity_negative(self):
        self.prepare()
        for invalid in (True, float("nan"), float("inf"), -1, 0):
            with self.subTest(value=invalid):
                self.edit("brief.json", lambda d: d["budget"].update(max_gpu_hours=invalid))
                self.assert_rejected(self.run_cli("freeze", self.project))

    def test_paper_source_cannot_be_missing(self):
        self.prepare()
        self.edit("papers.json", lambda d: d[0].update(citation=""))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_code_reuse_requires_known_permitted_license(self):
        self.prepare()
        self.edit("papers.json", lambda d: d[0]["code"].update(reuse=True, license="unknown", reuse_allowed=False))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_novelty_neighbor_search_is_required(self):
        self.prepare()
        self.edit("candidates.json", lambda d: d["items"][0]["search_log"].update(queries=[]))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_module_must_reference_registered_paper(self):
        self.prepare()
        self.edit("candidates.json", lambda d: d["items"][0]["modules"][0].update(paper_id="missing"))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_selection_cannot_use_test_split(self):
        self.prepare()
        self.edit("brief.json", lambda d: d["data"].update(selection_split="test"))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_overlapping_sample_manifests_rejected(self):
        self.prepare()
        brief = read_json(self.project / "brief.json")
        test_path = self.project / brief["data"]["splits"]["test"]["manifest_path"]
        write_json(test_path, ["fixture-dev-0"])
        brief["data"]["splits"]["test"]["sha256"] = sha256(test_path)
        write_json(self.project / "brief.json", brief)
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_split_manifest_hash_mismatch_rejected(self):
        self.prepare()
        self.edit("brief.json", lambda d: d["data"]["splits"]["test"].update(sha256="0" * 64))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_outside_manifest_path_rejected(self):
        self.prepare()
        outside = self.project.parent / "external.json"
        write_json(outside, ["outside-fixture"])
        self.edit("brief.json", lambda d: d["data"]["splits"]["test"].update(manifest_path="../external.json", sha256=sha256(outside)))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_duplicate_seeds_rejected(self):
        self.prepare()
        self.edit("plan.json", lambda d: d.update(seeds=[1, 1]))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_boolean_seed_rejected(self):
        self.prepare()
        self.edit("plan.json", lambda d: d.update(seeds=[True, 2]))
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_malformed_json_produces_controlled_error(self):
        self.prepare()
        (self.project / "plan.json").write_text("{broken", encoding="utf-8")
        self.assert_rejected(self.run_cli("freeze", self.project))

    def test_wrong_document_shape_produces_controlled_error(self):
        self.prepare()
        for value in (None, [], "a string", 17):
            with self.subTest(value=value):
                write_json(self.project / "plan.json", value)
                self.assert_rejected(self.run_cli("validate", self.project))

    def test_no_results_yields_plan_or_unfilled_draft(self):
        self.prepare()
        self.assert_ok(self.run_cli("freeze", self.project))
        result = self.run_cli("report", self.project)
        self.assert_ok(result)
        report = json.loads(result.stdout)
        self.assertTrue(report["blockers"])
        self.assertNotEqual(report["status"], "SYNTHETIC_DEMO")

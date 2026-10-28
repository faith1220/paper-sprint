"""Result bookkeeping tests. All measurements below are fictional fixtures."""

import json

from tests.fixtures import make_ready_project, read_json, sha256, write_json
from tests.test_cli import CLIBase


class ResultTests(CLIBase):
    def setUp(self):
        super().setUp()
        from paper_composer import core
        self.core = core
        make_ready_project(self.project)
        self.protocol = core.freeze_project(self.project)
        self.counter = 0

    def result(self, arm="baseline", seed=0, split="dev", **changes):
        self.counter += 1
        run_id = f"fixture-run-{self.counter}"
        config_path = f"artifacts/{run_id}.config.json"
        artifact_path = f"artifacts/{run_id}.log"
        write_json(self.project / config_path, {"fixture_only": True, "arm": arm, "seed": seed, "split": split})
        (self.project / artifact_path).write_text("UNIT TEST FIXTURE ONLY: no training performed.\n", encoding="utf-8")
        result = {
            "run_id": run_id, "arm": arm, "seed": seed, "split": split,
            "status": "completed", "metric": 0.7, "gpu_hours": 0.2,
            "synthetic": False, "protocol_hash": self.protocol["protocol_hash"],
            "code_version": "fixture-commit-0000001",
            "config_path": config_path, "config_sha256": sha256(self.project / config_path),
            "artifact_path": artifact_path, "artifact_sha256": sha256(self.project / artifact_path),
            "outcome": "positive", "notes": "UNIT TEST FIXTURE; never cite as scientific evidence.",
        }
        result.update(changes)
        return result

    def rejects(self, result):
        with self.assertRaises(self.core.ProjectError):
            self.core.record_result(self.project, result)

    def record_all_development(self):
        for arm in self.protocol["arms"]:
            for seed in (0, 1, 2):
                metric = 0.7 if arm["id"] == "baseline" else 0.8
                self.core.record_result(self.project, self.result(arm=arm["id"], seed=seed, metric=metric))

    def finish_fixture_evidence(self):
        self.record_all_development()
        self.core.select_candidate(self.project, "m1+m2", "UNIT TEST: development-only choice")
        final_ids = []
        for arm in ("baseline", "m1+m2"):
            for seed in (0, 1, 2):
                result = self.result(arm=arm, seed=seed, split="test", metric=0.7 if arm == "baseline" else 0.8)
                self.core.record_result(self.project, result)
                final_ids.append(result["run_id"])
        claims = read_json(self.project / "claims.json")
        claims["claims"][0].update(
            text="UNIT TEST: the fictional comparison is complete",
            supporting_run_ids=final_ids,
            scope="UNIT TEST fixtures only",
            boundary="No actual data, model or scientific evidence",
            status="supported",
        )
        write_json(self.project / "claims.json", claims)
        return final_ids

    def test_valid_result_registration(self):
        self.core.record_result(self.project, self.result())
        report = self.core.build_report(self.project)
        self.assertTrue(report["blockers"], "One development fixture cannot be evidence-ready")

    def test_missing_result_evidence_fields_rejected(self):
        original = self.result()
        for field in ("config_path", "config_sha256", "code_version", "artifact_path", "artifact_sha256", "seed", "split", "protocol_hash"):
            with self.subTest(field=field):
                invalid = dict(original)
                del invalid[field]
                self.rejects(invalid)

    def test_invalid_result_numbers_rejected(self):
        original = self.result()
        for field, invalid_values in (("metric", (True, float("nan"), float("inf"))), ("gpu_hours", (True, -1, float("nan"), float("inf")))):
            for invalid in invalid_values:
                with self.subTest(field=field, value=invalid):
                    self.rejects(dict(original, **{field: invalid}))

    def test_duplicate_run_id_rejected(self):
        result = self.result()
        self.core.record_result(self.project, result)
        self.rejects(result)

    def test_completed_seed_cannot_be_registered_twice(self):
        self.core.record_result(self.project, self.result())
        self.rejects(self.result(metric=0.9))

    def test_unknown_arm_seed_split_and_protocol_rejected(self):
        original = self.result()
        for field, value in (("arm", "missing"), ("seed", 999), ("seed", True), ("split", "train"), ("protocol_hash", "0" * 64)):
            with self.subTest(field=field, value=value):
                self.rejects(dict(original, **{field: value}))

    def test_test_split_locked_before_selection(self):
        self.rejects(self.result(split="test"))

    def test_selection_requires_completed_development_matrix(self):
        self.core.record_result(self.project, self.result())
        with self.assertRaises(self.core.ProjectError):
            self.core.select_candidate(self.project, "m1+m2", "Fixture incomplete development")

    def test_artifact_and_config_hashes_must_match(self):
        original = self.result()
        for field in ("artifact_sha256", "config_sha256"):
            with self.subTest(field=field):
                self.rejects(dict(original, **{field: "0" * 64}))

    def test_result_artifact_path_cannot_escape_project(self):
        external = self.project.parent / "external.log"
        external.write_text("external unit-test fixture", encoding="utf-8")
        self.rejects(self.result(artifact_path="../external.log", artifact_sha256=sha256(external)))

    def test_protocol_edits_after_freeze_rejected(self):
        result = self.result()
        plan = read_json(self.project / "plan.json")
        plan["comparability"]["backbone"] = "Modified fixture backbone"
        write_json(self.project / "plan.json", plan)
        self.rejects(result)

    def test_synthetic_result_cannot_be_recorded_as_real(self):
        self.rejects(self.result(synthetic=True))

    def test_test_arms_limited_to_baseline_and_selected(self):
        self.record_all_development()
        self.core.select_candidate(self.project, "m1+m2", "Fixture development choice")
        self.rejects(self.result(arm="m1", split="test"))

    def test_selection_cannot_change_after_final_test(self):
        self.record_all_development()
        self.core.select_candidate(self.project, "m1+m2", "Fixture development choice")
        self.core.record_result(self.project, self.result(split="test"))
        with self.assertRaises(self.core.ProjectError):
            self.core.select_candidate(self.project, "m1", "Fixture test-driven reselection")

    def test_already_consumed_over_budget_run_is_retained(self):
        self.core.record_result(self.project, self.result(gpu_hours=25.0))
        report = self.core.build_report(self.project)
        self.assertIn("budget", report)
        self.assertTrue(report["blockers"])
        self.assertIn("25", json.dumps(report["budget"]))

    def test_prior_and_current_cost_accumulate_in_report(self):
        self.project = self.project.parent / "prior-cost-fixture"
        make_ready_project(self.project)
        brief = read_json(self.project / "brief.json")
        brief["budget"].update(prior_gpu_hours=2.0, prior_runs=3)
        write_json(self.project / "brief.json", brief)
        self.protocol = self.core.freeze_project(self.project)
        self.core.record_result(self.project, self.result(gpu_hours=0.2))
        report = self.core.build_report(self.project)
        self.assertAlmostEqual(report["budget"]["used_gpu_hours"], 2.2)
        self.assertEqual(report["budget"]["used_runs"], 4)

    def test_negative_results_remain_in_report(self):
        self.core.record_result(self.project, self.result(metric=0.1, outcome="negative", notes="UNIT TEST negative result retained"))
        report = self.core.build_report(self.project)
        self.assertTrue(report["blockers"])
        self.assertEqual(report["counts"]["negative"], 1)

    def test_failed_attempt_is_retained_alongside_successful_retry(self):
        self.core.record_result(self.project, self.result(status="failed", metric=None, outcome="failure"))
        self.core.record_result(self.project, self.result())
        report = self.core.build_report(self.project)
        self.assertEqual(report["counts"]["failed"], 1)
        self.assertEqual(report["counts"]["registered"], 2)
        self.assertAlmostEqual(report["budget"]["used_gpu_hours"], 0.4)

    def test_baseline_sanity_blocks_selection(self):
        for arm in self.protocol["arms"]:
            for seed in (0, 1, 2):
                self.core.record_result(self.project, self.result(arm=arm["id"], seed=seed, metric=0.1))
        with self.assertRaises(self.core.ProjectError):
            self.core.select_candidate(self.project, "m1+m2", "UNIT TEST: broken baseline")

    def test_complete_fixture_reaches_evidence_ready_but_not_paper_ready(self):
        self.finish_fixture_evidence()
        report = self.core.build_report(self.project)
        self.assertEqual(report["status"], "EVIDENCE_READY", report)
        self.assertTrue(report["evidence_ready"])
        self.assertFalse(report["paper_ready"])
        self.assertEqual(report["counts"]["final_test_completed"], 6)
        self.assertEqual(report["summary"]["test"]["baseline"]["n"], 3)

    def test_dev_only_claim_cannot_pass_final_evidence_gate(self):
        self.finish_fixture_evidence()
        claims = read_json(self.project / "claims.json")
        claims["claims"][0]["supporting_run_ids"] = ["fixture-run-1"]
        write_json(self.project / "claims.json", claims)
        report = self.core.build_report(self.project)
        self.assertFalse(report["evidence_ready"])
        self.assertTrue(report["blockers"])

    def test_post_registration_artifact_tampering_invalidates_report(self):
        result = self.result()
        self.core.record_result(self.project, result)
        (self.project / result["artifact_path"]).write_text("changed fixture log", encoding="utf-8")
        report = self.core.build_report(self.project)
        self.assertEqual(report["status"], "INVALID", report)

    def test_post_registration_config_tampering_invalidates_report(self):
        result = self.result()
        self.core.record_result(self.project, result)
        write_json(self.project / result["config_path"], {"changed_fixture_config": True})
        report = self.core.build_report(self.project)
        self.assertEqual(report["status"], "INVALID", report)

    def test_dev_ledger_tampering_after_selection_invalidates_report(self):
        self.record_all_development()
        self.core.select_candidate(self.project, "m1+m2", "UNIT TEST: development-only choice")
        path = self.project / "results.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        rows[0]["metric"] = 0.71
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        report = self.core.build_report(self.project)
        self.assertEqual(report["status"], "INVALID", report)

    def test_selection_tampering_invalidates_report(self):
        self.record_all_development()
        self.core.select_candidate(self.project, "m1+m2", "UNIT TEST: development-only choice")
        selection = read_json(self.project / "selection.json")
        selection["arm"] = "m1"
        write_json(self.project / "selection.json", selection)
        report = self.core.build_report(self.project)
        self.assertEqual(report["status"], "INVALID", report)

    def test_malformed_result_shape_produces_controlled_cli_error(self):
        result_file = self.project / "invalid-result.json"
        for value in (None, [], "invalid", {"run_id": "incomplete"}):
            with self.subTest(value=value):
                write_json(result_file, value)
                self.assert_rejected(self.run_cli("record", self.project, "--file", result_file))


class DemoTests(CLIBase):
    def test_synthetic_demo_cannot_become_real_evidence_ready(self):
        self.assert_ok(self.run_cli("demo", self.project))
        result = self.run_cli("report", self.project)
        self.assert_ok(result)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "SYNTHETIC_DEMO")
        self.assertFalse(report["evidence_ready"])
        self.assertFalse(report["paper_ready"])

"""Original, editable protocol templates. No network or training integration."""

def project_documents(name="untitled", modules=2):
    paper_ids = [f"p{i + 1}" for i in range(max(2, modules))]
    return {
        "brief.json": {
            "schema_version": 1, "project_name": name,
            "mode": "journal-practical", "synthetic": False,
            "research_question": "", "practical_contribution": "",
            "target": {"journal": "", "ranking_system": "unspecified", "quartile": "Q1/Q2", "ranking_year": ""},
            "hardware": {"gpu": "A100 40GB", "gpu_count": 1, "note": "Editable example, not a requirement"},
            "budget": {"max_gpu_hours": 24.0, "max_runs": 30, "prior_gpu_hours": 0.0, "prior_runs": 0},
            "candidate_limit": 3,
            "data": {"dataset": "", "version": "", "license": "", "selection_split": "dev", "test_policy": "final-only",
                     "splits": {s: {"manifest_path": f"artifacts/{s}_ids.json", "sha256": ""} for s in ("train", "dev", "test")}},
            "metric": {"name": "", "higher_is_better": True, "unit": ""},
        },
        "papers.json": [{"id": p, "title": "", "citation": "", "url": "", "evidence_location": "",
                         "mechanism": "", "inputs": "", "outputs": "", "assumptions": "", "limitations": "",
                         "code": {"url": "", "reuse": False, "license": "not-applicable", "license_checked": False,
                                  "reuse_allowed": False, "attribution": ""}} for p in paper_ids],
        "candidates.json": {
            "selected_id": "c1", "items": [{
                "id": "c1", "baseline": {"name": "", "paper_id": "p1", "why_strong": ""},
                "modules": [{"id": f"m{i+1}", "paper_id": paper_ids[i], "mechanism": "", "interface": "", "adaptation": "", "complementarity": ""} for i in range(modules)],
                "selection_reason": "", "expected_benefit": "", "risks": "",
                "nearest_neighbors": [], "search_log": {"queries": [], "searched_at": "", "sources": []},
            }],
        },
        "plan.json": {
            "seeds": [0, 1, 2], "estimated_gpu_hours_per_run": 0.5,
            "development_split": "dev", "final_split": "test", "final_arms": "baseline-and-selected",
            "baseline_check": {"reference_metric": None, "tolerance": None, "reference_context": ""},
            "comparability": {k: "" for k in ("preprocessing", "backbone", "training_budget", "metric_protocol", "tuning_budget")},
            "stop_rules": {"max_failed_runs": 3, "min_gain": 0.0, "simplify_when": "", "negative_result_policy": "Record all attempted runs, failures and non-improvements."},
        },
        "claims.json": {"claims": [{"id": "claim1", "text": "", "source_paper_ids": paper_ids,
                                    "supporting_run_ids": [], "scope": "", "boundary": "", "status": "planned"}]},
    }

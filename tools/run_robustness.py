"""Offline reproducible experiments. No credentials, network or robot commands."""
import argparse
import json
from dataclasses import replace
from pathlib import Path
from urllib.error import HTTPError

from coresense.corexense_n.experiment import evaluate
from coresense.corexense_n.fixtures import make_cases
from coresense.corexense_n.gate import Config, audit_request, finalize, qualify
from coresense.corexense_n.lineage import digest
from coresense.corexense_n.validators import NebiusValidator


class InjectedTransport:
    def __init__(self, scenario):
        self.scenario = scenario

    def request(self, path, payload):
        name = self.scenario
        if name.startswith("http_"):
            raise HTTPError("https://invalid.example", int(name[5:]), "injected", {}, None)
        if name == "timeout":
            raise TimeoutError("injected")
        request_hash = json.loads(payload["messages"][1]["content"])["request_hash"]
        result = {"verdict": name if name in ("allow", "reject", "unknown") else "allow",
                  "request_hash": request_hash}
        if name == "wrong_hash":
            result["request_hash"] = "0" * 64
        if name == "missing_hash":
            del result["request_hash"]
        if name == "extra_field":
            result["motor_command"] = "forbidden"
        if name == "invalid_verdict":
            result["verdict"] = "approved"
        content = "not json" if name == "malformed" else json.dumps(result)
        if name == "null_content":
            content = None
        if name == "empty_choices":
            return {"choices": []}
        return {"choices": [{"finish_reason": "length" if name == "truncated" else "stop",
                             "message": {"content": content}}]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summaries = [evaluate(args.output / f"budget-{b}", 20, Config(query_budget=b))
                 for b in (0, 1)]
    case = make_cases(0)[0]
    config = Config()
    local = qualify([case.prior, case.initial], case.proposal, 0, config)
    request = audit_request(case.initial, case.proposal)
    scenarios = ["allow", "reject", "unknown", "timeout", "http_401", "http_403",
                 "http_429", "http_500", "http_503", "wrong_hash", "missing_hash",
                 "extra_field", "invalid_verdict", "malformed", "null_content",
                 "empty_choices", "truncated"]
    matrix = []
    for scenario in scenarios:
        verdict = NebiusValidator(InjectedTransport(scenario), "nvidia/test-double").evaluate(request)
        decision = finalize(local, request, [verdict], now_ms=case.initial.now_ms)
        expected = "PROCEED" if scenario == "allow" else "HOLD"
        assert decision.action == expected, scenario
        matrix.append({"scenario": scenario, "transport": "injected_test_double",
                       "verdict": verdict.status, "decision": decision.action, "passed": True})
    # Regression: an expired audit must never proceed.
    allow = NebiusValidator(InjectedTransport("allow"), "nvidia/test-double").evaluate(request)
    later = replace(case.initial, now_ms=case.initial.now_ms + 2000)
    original_final = finalize(local, request, [allow], now_ms=later.now_ms)
    fresh_local = qualify([case.prior, later], case.proposal, 0, config)
    assert original_final.action == "HOLD" and fresh_local.action == "ACQUIRE"
    report = {
        "data_origin": "synthetic", "network_requests": 0, "physical_trials": 0,
        "public_dataset_trials": 0, "baseline_source_revision": "6ac5a353b66cc622069104934615889f8028c952",
        "runner_sha256": digest(Path(__file__).read_text()),
        "policy_evaluations": sum(p["episodes"] for s in summaries for p in s["policies"].values()),
        "fault_contract_cases": matrix,
        "post_audit_freshness_gap": {"status": "expired_audit_blocked", "injected_elapsed_ms": 2000,
            "existing_finalize": original_final.action, "requalified": fresh_local.action,
            "required_before_hardware": "Revalidate current evidence and bind one-use expiring execution authorization."},
        "limitations": ["Seeds vary confidence only; not independent physical trials.",
            "Mock oracle outcomes are fixture-defined; not model or robot accuracy.",
            "NebiusValidator mode label is live internally; this matrix uses injected transports only.",
            "Hash chain verification does not establish external notarization or legal evidentiary status."],
        "summaries": summaries,
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"policy_evaluations": report["policy_evaluations"],
                      "fault_contract_cases_passed": len(matrix), "freshness_gap": "expired_audit_blocked"}))


if __name__ == "__main__":
    main()

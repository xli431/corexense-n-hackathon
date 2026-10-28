import json
from dataclasses import replace

import pytest

from coresense.corexense_n.experiment import evaluate, run_case
from coresense.corexense_n.fixtures import make_cases
from coresense.corexense_n.gate import Config, audit_request, finalize, qualify
from coresense.corexense_n.lineage import Ledger, digest, verify
from coresense.corexense_n.models import Decision, Verdict
from coresense.corexense_n.validators import (
    MockValidator,
    NebiusClient,
    NebiusValidator,
    NoRedirect,
)


def cases():
    return {case.name: case for case in make_cases(0)}


@pytest.mark.parametrize(
    "name,expected,queries",
    [
        ("healthy", "PROCEED", 0),
        ("camera_freeze", "HOLD", 1),
        ("restamped_freeze", "HOLD", 1),
        ("correlated_sources", "HOLD", 1),
        ("target_moved", "HOLD", 0),
        ("camera_dropout", "HOLD", 1),
        ("freeze_recovery", "PROCEED", 1),
        ("uncertainty_recovery", "PROCEED", 1),
        ("validator_reject", "HOLD", 0),
        ("validator_unavailable", "HOLD", 0),
        ("disallowed_action", "HOLD", 0),
    ],
)
def test_scenario_contract(name, expected, queries):
    ledger = Ledger()
    row = run_case(cases()[name], "corexense_n", Config(), ledger)
    assert row["decision"] == expected
    assert row["queries"] == queries
    assert row["motor_command_sent"] is False
    assert row["unsupported_proceed"] == 0
    verify(ledger.records, ledger.tip)


def test_identical_latest_observation_needs_history():
    healthy, frozen = cases()["healthy"], cases()["restamped_freeze"]
    assert healthy.initial == frozen.initial
    assert (
        qualify([healthy.prior, healthy.initial], healthy.proposal, 0, Config()).action == "PROCEED"
    )
    assert qualify([frozen.prior, frozen.initial], frozen.proposal, 0, Config()).action == "ACQUIRE"


def test_zero_budget_holds_without_query():
    row = run_case(cases()["freeze_recovery"], "corexense_n", Config(query_budget=0), Ledger())
    assert row["decision"] == "HOLD" and row["queries"] == 0


def test_history_ablation_exposes_restamped_freeze():
    row = run_case(cases()["restamped_freeze"], "without_history", Config(), Ledger())
    assert row["unsupported_proceed"] == 1


def test_stationary_stale_negative_control_retains_overblocking():
    frozen, stationary = cases()["camera_freeze"], cases()["stationary_stale_control"]
    assert frozen.initial == stationary.initial and frozen.followup == stationary.followup
    row = run_case(stationary, "corexense_n", Config(), Ledger())
    assert row["decision"] == "HOLD"
    assert row["supported_hold"] == 1


def test_future_source_timestamp_rejected():
    case = cases()["healthy"]
    camera, joint = case.initial.observations
    snap = replace(case.initial, observations=(replace(camera, acquired_ms=2000), joint))
    assert (
        qualify([case.prior, snap], case.proposal, 0, Config()).reason == "invalid_timestamp_order"
    )


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_confidence_rejected(invalid):
    with pytest.raises(ValueError):
        replace(cases()["healthy"].initial.observations[0], confidence=invalid)


def test_verifier_cannot_override_local_failure():
    verdict = Verdict("malicious", "allow", digest({}), "mock")
    assert finalize(Decision("HOLD", "stale"), {}, [verdict]).action == "HOLD"
    assert finalize(Decision("ACQUIRE", "stale"), {}, [verdict]).action == "ACQUIRE"


def test_validator_must_be_bound_to_this_evidence():
    case = cases()["healthy"]
    request = audit_request(case.initial, case.proposal)
    newer = audit_request(case.followup, case.proposal)
    assert request["evidence_digest"] != newer["evidence_digest"]
    old = MockValidator().evaluate(request)
    assert finalize(Decision("PROCEED", "ok"), newer, [old]).action == "HOLD"
    assert finalize(Decision("PROCEED", "ok"), newer, []).action == "HOLD"


def test_cloud_projection_excludes_internal_ids_and_oracle():
    case = cases()["target_moved"]
    request = audit_request(case.initial, case.proposal)
    text = json.dumps(request)
    for forbidden in ("camera-upstream", "source_frame", "supported_initial", "case", "seed"):
        assert forbidden not in text


def test_payload_mutation_does_not_change_logged_event():
    ledger = Ledger()
    payload = {"x": [1]}
    ledger.append("observation", payload)
    payload["x"].append(2)
    assert ledger.records[0]["payload"] == {"x": [1]}


@pytest.mark.parametrize("attack", ["edit", "delete", "reorder", "truncate", "rewrite"])
def test_tampering_detected_against_pinned_tip(attack):
    ledger = Ledger()
    for i in range(3):
        ledger.append("observation", {"sample": i})
    records = ledger.records
    if attack == "edit":
        records[0]["payload"]["sample"] = 99
    elif attack == "delete":
        records.pop(1)
    elif attack == "reorder":
        records[0], records[1] = records[1], records[0]
    elif attack == "truncate":
        records.pop()
    else:
        rewritten = Ledger()
        for i in range(3):
            rewritten.append("observation", {"sample": i + 1})
        records = rewritten.records
    with pytest.raises(ValueError):
        verify(records, ledger.tip)


def test_unanchored_rewrite_cannot_be_detected():
    rewritten = Ledger()
    rewritten.append("observation", {"sample": "fabricated"})
    assert verify(rewritten.records) == rewritten.tip


def test_reproducible_experiment_and_no_overwrite(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert evaluate(a, 3, Config()) == evaluate(b, 3, Config())
    for name in ("trace.jsonl", "summary.json", "trials.csv"):
        assert (a / name).read_bytes() == (b / name).read_bytes()
    with pytest.raises(FileExistsError):
        evaluate(a, 3, Config())


def test_nebius_credentials_missing(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("NEBIUS_TOKEN_FACTORY_KEY", raising=False)
    with pytest.raises(ValueError, match="locally"):
        NebiusClient()


class FakeClient:
    def __init__(self, kind):
        self.kind = kind

    def request(self, path, payload):
        assert path == "chat/completions"
        assert payload["store"] is False and payload["max_tokens"] == 256
        request_hash = json.loads(payload["messages"][1]["content"])["request_hash"]
        if self.kind == "timeout":
            raise TimeoutError("network down")
        if self.kind == "malformed":
            content = "```json\n{pretend-valid}\n```"
        else:
            content = json.dumps(
                {
                    "verdict": "allow",
                    "request_hash": request_hash if self.kind != "replay" else "0" * 64,
                }
            )
        return {
            "choices": [
                {
                    "message": {"content": content},
                    "finish_reason": "length" if self.kind == "truncated" else "stop",
                }
            ]
        }


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("valid", "allow"),
        ("timeout", "unknown"),
        ("malformed", "unknown"),
        ("replay", "unknown"),
        ("truncated", "unknown"),
    ],
)
def test_nebius_fail_closed(kind, expected):
    result = NebiusValidator(FakeClient(kind), "nvidia/test-model").evaluate({"test": "synthetic"})
    assert result.status == expected
    assert result.mode == "live"  # Adapter mode; transport here is explicitly a test double.


def test_http_request_bounds_and_auth(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            assert limit == 1_000_001
            return b'{"data": [{"id": "nvidia/test-model"}, {"id": "other/model"}]}'

    class Opener:
        def open(self, req, timeout):
            captured.update(
                url=req.full_url, authorization=req.headers["Authorization"], timeout=timeout
            )
            return Response()

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: Opener())
    assert NebiusClient(key="test-only-key").models() == ["nvidia/test-model"]
    assert captured == {
        "url": "https://api.tokenfactory.nebius.com/v1/models",
        "authorization": "Bearer test-only-key",
        "timeout": 20,
    }


def test_auth_not_forwarded_through_redirect():
    import urllib.request

    req = urllib.request.Request("https://api.tokenfactory.nebius.com/v1/models")
    with pytest.raises(urllib.error.HTTPError):
        NoRedirect().redirect_request(req, None, 302, "redirect", {}, "https://example.com")


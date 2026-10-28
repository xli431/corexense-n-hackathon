"""Matched observation-budget ceilings and explicit synthetic decision outcomes."""

from __future__ import annotations

import csv
import json
import math
import time
from dataclasses import asdict
from pathlib import Path

from .fixtures import Case, make_cases
from .gate import Config, audit_request, finalize, qualify
from .lineage import Ledger, digest, verify
from .models import Decision
from .validators import MockValidator, Validator

POLICIES = ("confidence_only", "fixed_reobserve", "without_history", "corexense_n")


def run_case(
    case: Case,
    policy: str,
    config: Config,
    ledger: Ledger,
    validators: list[Validator] | None = None,
) -> dict:
    if policy not in POLICIES:
        raise ValueError("unknown policy")
    episode = f"{case.name}-{case.seed}-{policy}"
    ledger.append(
        "episode_start",
        {
            "episode": episode,
            "data_origin": "synthetic",
            "proposal": asdict(case.proposal),
            "config": asdict(config),
            "policy": policy,
        },
    )
    history = [case.prior, case.initial]
    for snap in history:
        ledger.append("observation", {"episode": episode, **asdict(snap)})
    acquired = 0
    calls = 0
    final_verdicts = []
    for step in range(config.query_budget + 1):
        if policy in {"corexense_n", "without_history"}:
            policy_history = history if policy == "corexense_n" else history[-1:]
            local = qualify(policy_history, case.proposal, acquired, config)
            decision = local
            if local.action == "PROCEED":
                request = audit_request(history[-1], case.proposal)
                ledger.append(
                    "audit_request",
                    {"episode": episode, "request": request, "request_hash": digest(request)},
                )
                active = (
                    validators
                    if validators is not None
                    else [
                        MockValidator("nemotron-contract", case.mock_status),
                        MockValidator("cosmos-contract", "allow"),
                    ]
                )
                audit_started = time.monotonic_ns()
                final_verdicts = [v.evaluate(request) for v in active]
                elapsed_ms = math.ceil((time.monotonic_ns() - audit_started) / 1_000_000)
                # Explicit fixture mocks use the synthetic clock; real adapters use
                # locally measured elapsed time, not self-reported model latency.
                if all(isinstance(v, MockValidator) for v in active):
                    elapsed_ms = 0
                calls += len(final_verdicts)
                for verdict in final_verdicts:
                    ledger.append("validator_response", {"episode": episode, **asdict(verdict)})
                decision = finalize(local, request, final_verdicts,
                                    now_ms=history[-1].now_ms + elapsed_ms,
                                    max_age_ms=config.max_age_ms)
        elif policy == "fixed_reobserve" and acquired < config.query_budget:
            decision = Decision("ACQUIRE", "fixed_query_schedule")
        else:
            camera = next((o for o in history[-1].observations if o.source == "camera"), None)
            allow = camera is not None and camera.confidence >= config.min_confidence
            decision = Decision("PROCEED" if allow else "HOLD", "confidence_threshold")
        ledger.append(
            "decision",
            {"episode": episode, "step": step, **asdict(decision), "motor_command_sent": False},
        )
        if decision.action != "ACQUIRE":
            break
        acquired += 1
        ledger.append(
            "acquisition",
            {
                "episode": episode,
                "query": "fresh_camera_and_joint_state",
                "cost_units": 1,
                "simulated_delay_ms": 100,
            },
        )
        history.append(case.followup)
        ledger.append("observation", {"episode": episode, **asdict(case.followup)})
    supported = case.supported_followup if acquired else case.supported_initial
    row = {
        "case": case.name,
        "seed": case.seed,
        "policy": policy,
        "decision": decision.action,
        "reason": decision.reason,
        "queries": acquired,
        "simulated_wait_ms": acquired * 100,
        "validator_calls": calls,
        "action_supported_oracle": supported,
        "unsupported_proceed": int(decision.action == "PROCEED" and not supported),
        "justified_proceed": int(decision.action == "PROCEED" and supported),
        "supported_hold": int(decision.action == "HOLD" and supported),
        "motor_command_sent": False,
        "physical_outcome": "not_run",
    }
    ledger.append("evaluation_only_outcome", {"episode": episode, **row})
    return row


def evaluate(
    output: Path,
    seeds: int,
    config: Config,
    selected: str | None = None,
    validators: list[Validator] | None = None,
) -> dict:
    if not 1 <= seeds <= 1000:
        raise ValueError("seeds must be between 1 and 1000")
    # Exclusive directory creation prevents mixing previous and current experiments.
    output.mkdir(parents=True, exist_ok=False)
    ledger, rows = Ledger(), []
    policies = ("corexense_n",) if validators is not None else POLICIES
    for seed in range(seeds):
        for case in make_cases(seed):
            if selected and case.name != selected:
                continue
            rows.extend(run_case(case, p, config, ledger, validators) for p in policies)
    if not rows:
        raise ValueError("no matching case")
    summary = {
        "schema": "corexense-n.results.v1",
        "data_origin": "synthetic",
        "validator_mode": "live" if validators is not None else "mock",
        "seeds": seeds,
        "selected_case": selected,
        "implementation_sha256": digest(
            {p.name: p.read_text() for p in sorted(Path(__file__).parent.glob("*.py"))}
        ),
        "config": asdict(config),
        "physical_trials": 0,
        "live_metrics_comparable_to_mock_oracle": validators is None,
        "policies": {},
    }
    for policy in policies:
        trials = [r for r in rows if r["policy"] == policy]
        supported = sum(r["action_supported_oracle"] for r in trials)
        unsupported = len(trials) - supported
        summary["policies"][policy] = {
            "episodes": len(trials),
            "unsupported_opportunities": unsupported,
            "supported_opportunities": supported,
            **{
                key: sum(r[key] for r in trials)
                for key in (
                    "unsupported_proceed",
                    "justified_proceed",
                    "supported_hold",
                    "queries",
                    "simulated_wait_ms",
                    "validator_calls",
                )
            },
        }
    summary["terminal_hash"] = ledger.tip
    summary["record_count"] = len(ledger.records)
    ledger.write(output / "trace.jsonl")
    verify(ledger.records, summary["terminal_hash"])
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (output / "trials.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return summary


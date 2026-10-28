from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from tws_belief.adapters import (
    ArmbenchProbeConfig,
    armbench_perturbation_suite_sha256,
    evaluate_armbench_perturbation_suite,
    load_armbench_evidence_jsonl,
    load_armbench_perturbation_suite,
    probe_armbench_root,
)
from tws_belief.benchmark import evaluate_scenario, generate_scenarios
from tws_belief.counterfactual import load_perturbation_manifest
from tws_belief.models import evidence_records_sha256


def _benchmark(count: int) -> dict[str, object]:
    evaluations = [
        evaluate_scenario(scenario) for scenario in generate_scenarios(count)
    ]
    categories = Counter(item.category for item in evaluations)
    return {
        "benchmark": "tws-belief-failure-v0.1",
        "scenario_count": count,
        "category_counts": dict(sorted(categories.items())),
        "counterfactual_valid_count": sum(
            item.counterfactual_valid for item in evaluations
        ),
        "attribution_top1_exact_count": sum(
            item.attribution_top1_exact for item in evaluations
        ),
        "future_knowledge_violations": sum(
            item.future_knowledge_violations for item in evaluations
        ),
    }


def _manifest_summary(path: Path) -> dict[str, object]:
    manifest = load_perturbation_manifest(path)
    interventions = manifest.intervention_set.to_dict()["interventions"]
    return {
        "schema_version": manifest.schema_version,
        "manifest_id": manifest.manifest_id,
        "dataset": manifest.dataset,
        "reference_id": manifest.reference_id,
        "reference_sha256": manifest.reference_sha256,
        "manifest_sha256": manifest.sha256,
        "intervention_count": len(interventions),
        "intervention_types": [item["type"] for item in interventions],
    }


def _date_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an ISO 8601 date-time") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("must include a UTC offset")
    return parsed


def _armbench_fixture_suite(
    evidence_path: Path,
    manifest_directory: Path,
    decision_time: datetime,
) -> dict[str, object]:
    records = load_armbench_evidence_jsonl(evidence_path)
    cases = load_armbench_perturbation_suite(manifest_directory)
    results = evaluate_armbench_perturbation_suite(records, cases, decision_time)
    return {
        "suite": "tws-belief-armbench-fixture-v0.1",
        "synthetic_fixture": True,
        "decision_time": decision_time.isoformat(),
        "reference_sha256": evidence_records_sha256(records),
        "suite_sha256": armbench_perturbation_suite_sha256(cases),
        "case_count": len(results),
        "passed_count": sum(result.passed for result in results),
        "all_passed": all(result.passed for result in results),
        "results": [result.to_dict() for result in results],
    }


def _armbench_probe(
    root: Path,
    *,
    hash_mode: str,
    json_samples_per_role: int,
    max_json_bytes: int,
    include_json_key_names: bool,
) -> dict[str, object]:
    return probe_armbench_root(
        root,
        ArmbenchProbeConfig(
            hash_mode=hash_mode,
            json_samples_per_role=json_samples_per_role,
            max_json_bytes=max_json_bytes,
            include_json_key_names=include_json_key_names,
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tws-belief",
        description="Deterministic belief reconstruction research utilities.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    benchmark = subparsers.add_parser(
        "benchmark",
        help="Run the deterministic synthetic failure benchmark.",
    )
    benchmark.add_argument("--scenarios", type=int, default=1_000)
    manifest = subparsers.add_parser(
        "manifest",
        help="Validate and summarize a perturbation manifest.",
    )
    manifest.add_argument("path", type=Path)
    armbench_suite = subparsers.add_parser(
        "armbench-fixture-suite",
        help="Run the synthetic metadata-only ARMBench perturbation suite.",
    )
    armbench_suite.add_argument("--evidence", type=Path, required=True)
    armbench_suite.add_argument("--manifests", type=Path, required=True)
    armbench_suite.add_argument("--decision-time", type=_date_time, required=True)
    armbench_probe = subparsers.add_parser(
        "armbench-probe",
        help="Create a redacted structural inventory of a local ARMBench directory.",
    )
    armbench_probe.add_argument("root", type=Path)
    armbench_probe.add_argument(
        "--hash-mode",
        choices=("none", "metadata", "all"),
        default="metadata",
    )
    armbench_probe.add_argument("--json-samples-per-role", type=int, default=8)
    armbench_probe.add_argument("--max-json-bytes", type=int, default=16 * 1024 * 1024)
    armbench_probe.add_argument(
        "--include-json-key-names",
        action="store_true",
        help="Emit JSON key names; output becomes local-only.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "benchmark":
        print(json.dumps(_benchmark(args.scenarios), indent=2, sort_keys=True))
    elif args.command == "manifest":
        print(json.dumps(_manifest_summary(args.path), indent=2, sort_keys=True))
    elif args.command == "armbench-fixture-suite":
        result = _armbench_fixture_suite(
            args.evidence,
            args.manifests,
            args.decision_time,
        )
        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )
        if not result["all_passed"]:
            raise SystemExit(1)
    elif args.command == "armbench-probe":
        result = _armbench_probe(
            args.root,
            hash_mode=args.hash_mode,
            json_samples_per_role=args.json_samples_per_role,
            max_json_bytes=args.max_json_bytes,
            include_json_key_names=args.include_json_key_names,
        )
        print(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
        )
        if not result["probe_passed"]:
            raise SystemExit(1)

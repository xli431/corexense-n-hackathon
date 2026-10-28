"""Run locally: PYTHONPATH=src python -m coresense.corexense_n.cli --help."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .experiment import evaluate
from .fixtures import make_cases
from .gate import Config
from .lineage import verify
from .validators import NebiusClient, NebiusValidator


def main() -> None:
    parser = argparse.ArgumentParser(description="CoreXense-N synthetic decision experiment")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="offline deterministic regression; no API or motors")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--seeds", type=int, default=20)
    run.add_argument("--case", choices=[c.name for c in make_cases(0)])
    run.add_argument("--max-age-ms", type=int, default=250)
    run.add_argument("--min-confidence", type=float, default=0.8)
    run.add_argument("--query-budget", type=int, choices=(0, 1), default=1)
    check = sub.add_parser(
        "verify", help="verify trace against a separately retained terminal hash"
    )
    check.add_argument("trace", type=Path)
    check.add_argument("--expected-tip", required=True)
    sub.add_parser("models", help="list NVIDIA models available to your Nebius key")
    live = sub.add_parser("live-smoke", help="one paid inference on synthetic healthy evidence")
    live.add_argument("--model", required=True)
    live.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            result = evaluate(
                args.output,
                args.seeds,
                Config(args.max_age_ms, args.min_confidence, args.query_budget),
                args.case,
            )
        elif args.command == "verify":
            records = [json.loads(line) for line in args.trace.read_text().splitlines()]
            result = {"verified": True, "terminal_hash": verify(records, args.expected_tip)}
        else:
            client = NebiusClient()
            models = client.models()
            if args.command == "models":
                result = {"available_nvidia_models": models}
            else:
                if args.model not in models:
                    raise ValueError("model not returned by this account's model catalog")
                result = evaluate(
                    args.output, 1, Config(), "healthy", [NebiusValidator(client, args.model)]
                )
        print(json.dumps(result, indent=2))
        if (
            args.command == "live-smoke"
            and not result["policies"]["corexense_n"]["justified_proceed"]
        ):
            raise SystemExit("Live smoke did not produce a valid allow verdict; inspect trace")
    except ValueError as exc:
        raise SystemExit(f"CoreXense-N input/configuration error: {exc}") from None
    except (OSError, KeyError, TypeError) as exc:
        # Deliberately do not print request headers, keys, or remote error bodies.
        raise SystemExit(f"CoreXense-N failed: {type(exc).__name__}") from None


if __name__ == "__main__":
    main()


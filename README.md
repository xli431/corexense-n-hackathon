# CoreXense-N: An MCP Evidence Gateway for Physical AI

Validate evidence, request bounded re-observation, and trace why a workflow pauses.
The submission is a software review prototype. It does not control robot motors.

## Run

Use Python 3.11+:

```sh
git clone https://github.com/xli431/corexense-n-hackathon.git
cd corexense-n-hackathon
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python tools/run_mcp_sprint.py runs/offline-001
```

Open `runs/offline-001/review.html`. The runner uses actual MCP stdio communication.
Default semantic reviews are explicit mocks; offline success is not a live-model result.

## NVIDIA and Nebius

First list the NVIDIA Nemotron models accessible to your account, with no inference:

```sh
python tools/run_mcp_sprint.py runs/catalog --live --prompt-key
```

Then pass one exact returned model ID:

```sh
python tools/run_mcp_sprint.py runs/live-001 --live --prompt-key --model EXACT_MODEL_ID
```

Credentials stay in a hidden local prompt. This walkthrough makes at most two
inference calls unless an optional simulation episode is supplied (then three).
There is no automatic retry. Nebius Token Factory hosts NVIDIA Nemotron semantic
review. Local checks and elapsed evidence validity remain authoritative.

The cloud response may correctly result in HOLD after the 250 ms synthetic evidence
window expires. That is not robot performance, a task failure rate, or a safety proof.

Recorded live check: three requests, 2,674 reported tokens. The recovery fixture
received model ALLOW but remained HOLD because its evidence expired during the
audit. Another response was truncated at the default 256-token output budget.
Use `--audit-max-tokens 1024` for a separately recorded budget follow-up; the
freshness policy and strict response validation remain unchanged.

Build a verified summary from a completed run (no API requests):

```sh
python tools/build_evidence_report.py runs/live-001/mcp_report.json runs/live-summary-001
```

## MCP tools

- `list_scenarios`: list synthetic fixtures.
- `review_scenario`: original local fruit qualification and trace.
- `review_episode`: synthetic episode-bound semantic review and post-audit check.
- `explain_belief`: synthetic delayed/conflicting evidence reconstruction.
- `review_simulation_episode`: explicit FIRA JSON replay audit, always non-executable.

The server offers no actuator or arbitrary filesystem tools. Host configuration
controls cloud access. `corexense-mcp` starts the stdio service after installation.

## FIRA prior work and current integration

The existing MuJoCo/RoboSim produce scene and its UI remain separate work.
An owner may supply a `result.json` / `trace.jsonl` episode directory using
`--simulation-episode /absolute/path/to/episode`. Its integrity is checked and
the same source hash is bound to the semantic review. This is historical auditing,
not closed-loop inference controlling the simulated or physical robot.

## Evaluation and limitations

```sh
python tools/run_robustness.py runs/robustness-001
```

This runs 1,920 synthetic policy evaluations and 17 injected transport contracts.
These are fixture diagnostics, not independent physical trials or live model accuracy.
The hash ledger detects changes relative to a retained tip; it does not authenticate
the original source. Real fruit input remains blocked until a sensor adapter is
commissioned. No supervised physical controller is included.

## Source boundaries and prior work

The core derives from the existing CoreSense/CoreXense-N work; preserve the Apache
license and notices. TWS-Belief is vendored under MIT with a pinned source manifest.
Private operation_logging, review, perception, raw media, hardware calibration,
FIRA upstream UI, and PEG research are excluded. No third-party dataset is bundled.
The upstream TWS-Belief CLI/dataset adapters are not exposed by this demo; only
the reconstruction API used by the MCP tool is qualified in this package.

See docs/REUSE_MAP.md for related projects. New sprint work: bound MCP episode
review, simulation replay adapter, TWS-Belief tool, end-to-end client and reports.
Live results, physical observations and future capabilities must be reported separately.

FIRA background acknowledgments: Voxel51 FiftyOne for data inspection, SKAI
Intelligent for simulation support, and HawkRobo for earlier FIRA sponsorship.
These credits do not imply a new partnership or endorsement of this submission.

Offline reproduction remains available after cloud credit expiry. New live
inference requires valid Nebius account access.

See `docs/SUBMISSION_STORY.md` for the submission draft and
`docs/SPRINT_CLOSEOUT.md` for verified results and remaining steps. SKAI course
assets remain outside this repository. Local inspection opened the USD stage with
no unresolved dependencies; simulator execution and training remain separate work.

For reproduction after cloud credits expire, see [the judge runbook](docs/JUDGE_RUNBOOK.md).
The source export has been independently installed and verified with 103 tests,
an installed MCP server launched outside the source tree, and the offline fault matrix.

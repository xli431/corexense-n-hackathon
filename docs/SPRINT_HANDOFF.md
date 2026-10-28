# CoreXense-N submission sprint

## Scope and responsibility

The MCP server reviews evidence and records decisions. The operator controls the
robot through its commissioned controller. No MCP motor, gripper, parameter,
calibration or emergency-stop tools are exposed. An MCP review is never an
execution permit.

Flow: synthetic evidence / owner-selected simulation bundle -> local checks ->
bounded semantic audit -> post-audit validity check -> trace -> review report.
TWS-Belief explanations are independent synthetic examples; they are not extracted
from the FIRA camera stream and do not authorize its actions.

## Install and offline demo

Use Python 3.11+ in a project virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,mcp]'
python -m pytest -q
python tools/run_mcp_sprint.py runs/mcp-offline-001
```

Open the generated `review.html`. This is a recorded report, not a live dashboard.
The runner starts an actual MCP stdio server and calls all five available tools
when a simulation bundle is supplied (four tool types are used by the walkthrough;
`list_scenarios` is available separately).

To bind an existing simulation episode:

```sh
python tools/run_mcp_sprint.py runs/mcp-simulation-001 \
  --simulation-episode /absolute/path/to/episode
```

The episode folder must contain FIRA `result.json` and `trace.jsonl`. The server
verifies the hash chain and matching event payloads, then projects object/stage
labels into a semantic review. Report integrity does not authenticate its publisher.
Historical simulation input always returns HOLD for current execution, regardless
of the semantic verdict. This is post-hoc auditing, not closed-loop policy control.

## Live Nebius audit

Enter secrets only in the local hidden prompt. Start by listing accessible models:

```sh
python tools/run_mcp_sprint.py runs/model-check --live --prompt-key
```

This lists IDs and exits without inference. Then copy the selected exact Nemotron
ID into the command below. Do not put the secret in a command or JSON config.

```sh
python tools/run_mcp_sprint.py runs/mcp-live-001 --live --prompt-key \
  --model EXACT_MODEL_ID \
  --simulation-episode /absolute/path/to/episode
```

This makes up to three semantic inference calls in this walkthrough, with an
additional fixed maximum of ten per server session. No automatic retry. Missing
credentials or unavailable models stop the runner. Offline mocks remain explicitly
labeled. A live response arriving outside the 250 ms synthetic evidence window
returns HOLD. No threshold relaxation or backdated clock is used.

## MCP client configuration

Use the installed environment's Python as the command, with arguments
`-m coresense.corexense_n.mcp_server`. Set `PYTHONPATH` to the absolute `src`
directory if using a source checkout. Offline mode is the default.
Cloud mode requires host environment `COREXENSE_AUDIT_MODE=live`,
`COREXENSE_NVIDIA_MODEL` and a locally supplied Nebius credential. No client config
containing a secret should be committed or shown in a video.

## Tonight's supervised WidowX session

1. Select whichever OMEN or Thor host already operates the commissioned WidowX
   controller. Record OS, exact robot/gripper, controller version and operator.
2. Verify the existing local stop, workspace limits, calibration and supported
   gripper configuration with the operator before any contact trial.
3. Start with observation-only capture. Keep original timestamps and indicate
   missing streams, uncalibrated sensors and manually entered labels explicitly.
4. If the controller is ready, the operator may run its existing supervised task
   while this project records observations and human outcomes separately.
5. Current fruit qualification holds real input because no real sensor adapter is
   commissioned. Do not change `data_origin` to synthetic to bypass that boundary.
6. Do not label a physical motion video as MCP-controlled or model-controlled.
   Real runtime gating requires a separately verified sensor/execution integration.

The hardware session is conditional on readiness. A simulation/software submission
can proceed without inventing physical outcomes. Log every attempt, intervention,
failure and aborted run; no task-success claim from selected video clips.

## Video and submission

- 0:00-0:20: agricultural motivation and product purpose.
- 0:20-1:30: actual MCP calls, evidence decisions, expired audit and TWS explanation.
- 1:30-2:20: FIRA simulation replay and trace-bound semantic review; clearly label
  offline vs live, historical simulation vs physical capture.
- 2:20-2:50: result limits, platform use and next milestone.

If ready, replace part of the simulation footage with clearly labeled supervised
physical observations. Keep total under three minutes, with at least one minute
of functioning modules. Add English captions.

Before publication: resolve existing source/license boundaries, package an
independently installable public export, preserve notices, verify all public links,
and describe preexisting work versus sprint changes. Arrange judge testing after
the credit expiry; do not claim an offline replay is a live Nebius service.

# Judge runbook: local reproduction without active cloud credits

## What to expect

CoreXense-N is a software evidence-review prototype. The default demonstration
uses actual MCP stdio communication and explicitly mocked semantic responses.
It exposes no actuator interface. Recorded Nebius live results are separate from
offline reproduction; an offline run is never described as hosted inference.

This source package was independently installed on Linux/Python 3.12 in a new
virtual environment. All 103 tests passed. The installed server was then started
from `/tmp`, without source PYTHONPATH, and verified to expose five tools and
return HOLD for the slip fixture. Dependency checking reported no broken requirements.

## Reproduce

From this package's directory, using Python 3.11 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -q
.venv/bin/python tools/run_mcp_sprint.py runs/judge-offline-001
.venv/bin/python tools/run_robustness.py runs/judge-robustness-001
```

Use new output-directory names on every run. The MCP walkthrough should report
five available tools and five reviews. Open `runs/judge-offline-001/review.html`
to inspect recorded decisions. A source simulation bundle is optional and not
included in this package; supplying one adds a sixth review.

The robustness runner should report 1,920 synthetic policy evaluations and
17 injected transport-contract cases, including an expired-audit rejection.
These checks do not measure physical trials or real model accuracy.

## Live mode, if the reviewer has their own Nebius account

```sh
.venv/bin/python tools/run_mcp_sprint.py runs/catalog-001 --live --prompt-key
```

Copy an exact available NVIDIA Nemotron model ID from that output, then:

```sh
.venv/bin/python tools/run_mcp_sprint.py runs/judge-live-001 \
  --live --prompt-key --model EXACT_MODEL_ID --audit-max-tokens 1024
```

The owner supplies the key in a hidden terminal prompt. No shared project key is
bundled. This makes up to two inference calls without the optional simulation
bundle and three with it. Provider availability and response latency may vary.

## Interpret the live evidence

The 256-token diagnostic run contained one truncated response. Two later
1,024-token-budget runs each produced three complete verdicts. In those two runs,
the healthy and recovery synthetic cases received model ALLOW but remained HOLD
because their configured 250 ms evidence windows expired. The slip was blocked
locally; historical FIRA replay returned explicit model unknown and remained
non-executable. These repeated fixtures do not estimate deployment reliability.

No always-on cloud service after credit expiry is promised. Local reproduction
works independently of those credits; new live inference requires valid access.

## Assets and research boundaries

Raw SKAI assets, proprietary calibration, secrets, raw dataset footage and
anonymous manuscript files are excluded. SKAI URDF/USD composition has been
inspected locally, but this does not establish simulator execution or training.
ETH references inform the roadmap; no ETH controller is reproduced. Cosmos GPU
inference and real robot execution are separate, uncompleted milestones.

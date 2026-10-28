# Submission closeout

## Verified evidence

- Actual MCP stdio interface: five tools; six walkthrough reviews with FIRA input.
- Nebius Token Factory + NVIDIA Nemotron live run `nebius-live-20261028-143100`:
  three semantic requests; 2,066 input tokens, 608 output tokens, 2,674 total.
- Healthy synthetic evidence: response truncated at 256 output tokens; HOLD.
- Synthetic slip: local HOLD; no inference.
- Synthetic recovery: validated model ALLOW; post-audit expiry; HOLD at 2,047.409 ms.
- Historical FIRA episode: validated model REJECT; historical replay remains HOLD.
- All returned review trace chains from that run independently verified.
- Follow-up `nebius-budget1024-20261028-150023`: three complete, schema-valid
  responses; 2,954 reported tokens. Healthy and recovery fixtures received ALLOW
  but remained HOLD after evidence expiration. FIRA received explicit model
  unknown and remained non-executable. No truncated responses in this run.
- Local code suite: 103 tests passed. This includes synthetic policy and adapter
  contract tests; it is not 103 live model or robot trials.
- Repeated follow-up `nebius-budget1024-20261028-150200`: three complete responses,
  3,022 reported tokens, same decisions as the previous 1,024-token run; latencies
  differ. Both recorded trace chains passed verification.
- Independent Linux/Python 3.12 installation passed 103 tests and dependency
  checks. Installed MCP server launched from `/tmp` with source PYTHONPATH removed:
  five tools, slip HOLD. Offline walkthrough and 1,920/17 fault matrix reproduced.

The 250 ms window is a configured synthetic test condition, not an empirically
validated robot-control deadline. Three requests do not establish model accuracy,
latency distributions, reliability rates or statistical significance.

## Token-budget follow-up

Run the same walkthrough with `--audit-max-tokens 1024`, fresh output directory,
same model and prompt. The report records the budget. Keep the 256-token run.
No retry, prompt tuning or freshness-limit relaxation is applied. This is an
exploratory repeated call, not an isolated causal experiment or powered comparison.
The key is supplied through the interactive hidden prompt.
The follow-up completed; both runs are retained. The historical FIRA verdict
changed from reject to unknown, so model consistency has not been established.

## Simulation milestone

Use the existing agricultural replay for the working demo. The SKAI course asset
is a separate static environment and should not be presented as that same task.
Record URDF mesh references and USD composition results before loading a simulator.
Do not imply OpenUSD composition is an Isaac Sim run. Do not redistribute assets
or private source reports with the public code export.

## Recording sequence

1. Problem and FIRA scene (20 seconds).
2. Actual MCP call and recorded Nebius diagnostics (40 seconds).
3. Model ALLOW followed by local HOLD due to evidence expiry (35 seconds).
4. Episode/source digest and TWS-Belief explanation (35 seconds).
5. SKAI environment extension, labeled with the achieved milestone (20 seconds).
6. Contribution, credits and next steps (20 seconds).

## Remaining gates before submission

- Completed: inspect the 1,024-token follow-up and retain both budget runs.
- Optional extension: actually load/run one SKAI scene in a simulator; record it.
- Optional extension: Cosmos model inference on Thor after access/environment checks.
- Record/edit the demo video, add captions, and verify the public video link.
- Completed: independent installation. Publish the reviewed source-filtered candidate.
- Completed: `docs/JUDGE_RUNBOOK.md` provides local reproduction after credits expire. Offline replay stays
  labeled; do not promise a live endpoint that will be unavailable.
- Transfer the final description/video/repository links into Devpost and verify
  completion. Never report submission success before the platform confirms it.

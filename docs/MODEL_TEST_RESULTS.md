# Model test results


The submission package passed 103 software tests and an independent Linux installation check. Offline evaluation covered 1,920 synthetic policy cases and 17 injected transport contracts. These evaluate software behavior, not robot success or model accuracy.

### Output-budget tests and repeated runs

I tested NVIDIA-Nemotron-3-Nano-30B-A3B through Nebius Token Factory. The initial three-request diagnostic run used 2,674 reported tokens and included one truncated response at a 256-token output limit. The recovery fixture received ALLOW but remained HOLD after its evidence expired.

Two follow-up walkthroughs used a 1,024-token output limit. Each made three cloud requests, using 2,954 and 3,022 reported tokens respectively. Across these six requests, all responses were complete and schema-valid, with no truncation. In both runs, healthy and recovery fixtures received model ALLOW but the gateway returned HOLD because the audit exceeded the configured 250 ms synthetic evidence window. The slip fixture was blocked locally without inference. FIRA replay received unknown and remained non-executable. Both trace checks passed.

These are repeated fixed-input checks, not independent physical trials or a controlled causal experiment. They do not establish model accuracy, reliability rates or a real-time latency guarantee. The larger-budget runs showed no truncation in this small sample; they do not prove that output-budget changes alone caused the difference.

### Preliminary model selection

A separately reported five-model fixture comparison favored Nano-30B: it was the only model reported to pass all three fixture checks, including rejection of the slip case, and had the lowest observed average latency (2,072 ms). Super-120B and Ultra-550B returned ALLOW on that slip fixture; Super-VL and Lightning returned unknown/truncated responses.

This preliminary comparison comes from the run author's terminal summary; the raw comparison JSON and matched configurations have not yet been independently checked. It is not a general model ranking. Truncated outputs are incomplete evidence, and a model ALLOW is not a final gate decision. The slip-model probe is separate from the gateway walkthrough, where slip is blocked before inference.

[Public source and reproduction instructions](https://github.com/xli431/corexense-n-hackathon) · [Test scope and comparison notes](https://github.com/xli431/corexense-n-hackathon/blob/main/docs/MODEL_TEST_RESULTS.md)


## Recorded run identifiers

- 256-token diagnostic: `nebius-live-20261028-143100`
- 1024-token follow-up: `nebius-budget1024-20261028-150023`
- 1024-token repeat: `nebius-budget1024-20261028-150200`

See [closeout](SPRINT_CLOSEOUT.md) for existing records. These documentation updates do not rerun inference or tests.

## Author-reported five-model summary

| Model label as supplied | Slip output | Reported average latency | All three fixture checks |
|---|---|---:|---|
| NVIDIA-Nemotron-3-Nano-30B-A3B | reject / validated | 2072 ms | pass |
| nemotron-3-super-120b-a12b | allow | 3300 ms | fail |
| Nemotron-3.5-Super-VL | unknown / truncated | 3076 ms | fail |
| Nemotron-3_5-Lightning | unknown / truncated | 7084 ms | fail |
| Nemotron-3-Ultra-550b-a55b | allow | 10871 ms | fail |

Source: owner-provided terminal excerpt on 30 October 2026, naming `runs/model_comparison_report.json`. The raw JSON was not available in this checkout. Exact model IDs, prompts, per-model budgets, repeat counts, averaging definitions, code revision and final gate outcomes remain unverified. Do not attach these results to commit 417bccb or interpret pass/fail as physical safety.

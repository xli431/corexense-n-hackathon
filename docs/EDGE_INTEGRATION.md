# Proposed edge integration: Cosmos Reason2 and InstinctFlash

Status: architecture and interface plan only. No InstinctFlash installation,
Cosmos inference, GPU acceleration measurement, or physical execution has been
verified by this integration.

## Responsibilities

| Component | Proposed responsibility |
| --- | --- |
| Cosmos-Reason2-2B on Thor | Review image/video evidence and describe visible state or missing observations |
| InstinctFlash on Thor | Serve a supported, task-appropriate robot policy and return candidate action chunks |
| Nebius-hosted NVIDIA Nemotron | Review structured task evidence at bounded checkpoints |
| CoreXense-N | Qualify evidence, bind review records, check freshness and explain workflow decisions |
| Commissioned robot controller and operator | Own physical execution, local limits and stop behavior |

Reason2 visual review and InstinctFlash policy inference are separate services.
The current InstinctFlash README lists Cosmos3 policy adapters; it does not list
Cosmos-Reason2-2B as a supported model family. Do not claim it accelerates Reason2.
Supported model families and protocol compatibility do not establish compatibility
with a particular WidowX, camera configuration or gripper.

## Proposed data flow

Observation receipt -> visual review / policy inference -> candidate action and
source references -> CoreXense-N review -> commissioned execution boundary.
The current MCP server stops at software review. Its decisions are not actuator
permits, and no execution boundary is implemented by this document.

A future adapter should bind episode_id, observation sequence, acquisition and
receipt times, media digest, checkpoint revision, preprocessing revision,
precision/sampling configuration, action representation and prediction horizon.
Separate runtime-reported inference time from locally measured end-to-end time.

If a gate or operator changes or skips an action chunk, preserve the executed
action history. For a stateful policy, use its documented history/commit/reset
contract; do not let subsequent predictions assume rejected actions occurred.

## Admission and evaluation

1. Recover Thor access and inspect actual JetPack/CUDA/Python compatibility.
2. Run Cosmos visual review separately on the prepared historical FIRA inputs.
3. Prepare an isolated InstinctFlash model-family environment. A dry run only
   validates metadata/planning; it is not GPU inference or a speed benchmark.
4. With a suitable checkpoint, run one native-precision prediction with no robot
   connection. Verify input preprocessing and the action's units/frame/layout.
5. Bind its result to an explicitly synthetic/shadow evidence review. Do not
   bypass the current real-input HOLD or claim current robot control.
6. Only then consider a separately commissioned supervised execution adapter.

For acceleration claims, compare the same checkpoint, inputs, sampling schedule
and precision on the same device. Report warmup separately, p50/p95 latency,
invalid/stale outputs, unnecessary holds and task outcomes when actually measured.
FP8 and reduced sampling are separate interventions; preserve failures and compare
task quality. Third-party speedups are not CoreXense-N results.

## Attribution and submission wording

Use "planned integration" until a real inference path is tested. Credit General
Instinct for InstinctFlash. Preserve the license and upstream/model notices if
source is later incorporated. No InstinctFlash source or weights are copied here.

Reference reviewed: https://github.com/General-Instinct/InstinctFlash/blob/main/README.md
README blob SHA: 0ef102176873d813ffd04ed68fb6f3e2aee817bb

The README provides Runtime.episode/predict and OpenPI-compatible WebSocket APIs,
with separate pinned Jetson Thor environments. Those are upstream capabilities,
not validated integrations of this project.

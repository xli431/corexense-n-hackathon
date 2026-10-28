# Dry run now, supervised inference later

## Scope

Dry runs inspect contracts, metadata and inputs. They do not prove GPU loading,
model quality, real robot compatibility or physical task success.
The cloud target is one Nebius B300 in us-north1 if later approved; no VM, job,
dedicated endpoint or paid inference is provisioned by these commands.

## Prepared on OMEN

Project: `~/projects/corexense-n-hackathon-20261028`.
The InstinctFlash checkout is separate under `external/InstinctFlash` and pinned
to `34e1c6089fb6317cdfdd3a4cdd93ad92fbf0ebaa`. Its `.venv-core` has no Torch.
The pi05 metadata adapter is installed without model-stack dependencies.

```sh
cd ~/projects/corexense-n-hackathon-20261028
.venv/bin/python tools/run_nebius_dry_run.py runs/nebius-dry-002
.venv/bin/python tools/run_cosmos_pilot.py \
  --manifest runs/cosmos-pilot-inputs/manifest.json \
  --output runs/cosmos-input-check-002 --dry-run
external/InstinctFlash/.venv-core/bin/instinctflash serve lerobot/pi05_base \
  --serve.dry_run=true --output.format=json
```

Use fresh output directories for every run. The Nebius dry run injects a transport
fixture, reads no credentials, and makes no network or inference requests. It does
not supersede actual Nebius live checks. Synthetic responses remain labeled.

The official InstinctFlash preflight may report `ok: true` while also reporting
APPLICABILITY UNCHECKED for hardware-dependent passes. `servable: true` describes
the model declaration, not evidence that its checkpoint runs on this OMEN or Thor.
The vendor plan's qualification fields refer to upstream checks, not this project.

## Before returning to Thor

Copy the source candidate, `tools/run_cosmos_pilot.py`, and the whole
`runs/cosmos-pilot-inputs` directory, including its manifest and three images.
Weights, credentials and proprietary controller settings are not in this pack.
Record image identity and original historical-simulation labeling.

Confirm access to nvidia/Cosmos-Reason2-2B through your own Hugging Face account.
Complete any model agreement/data-sharing consent yourself. Never place a token
in a script, video, issue, repository or chat. If using a cached model, still
record the actual revision that is loaded.

## On Thor

1. Restore SSH authentication; collect OS, JetPack, Python, CUDA and available
   memory using read-only checks. The official 2B baseline requires 24 GB GPU
   memory; this runner refuses a smaller CUDA device.
2. Use a separate, Thor-compatible model environment with vendor-supported Torch,
   Transformers >=4.57.0, Accelerate and Pillow. Do not replace the working robot
   controller environment or install an arbitrary x86 CUDA wheel on ARM.
3. Run the input dry run first, with the Python from that environment.
4. Enable actual model inference explicitly:

```sh
python tools/run_cosmos_pilot.py \
  --manifest runs/cosmos-pilot-inputs/manifest.json \
  --output runs/cosmos-thor-001 --run
```

The script resolves and records the actual model revision, loads only the 2B
model, runs at most three historical images and caps each output at 4096 tokens.
Only schema-validated final answers are retained; missing/truncated final answers
are failures. Raw reasoning is not saved. CUDA timing is synchronized, and model
loading time is separate. These are cold/initial generations, not steady-state
latency benchmarks. There are no robot commands.

## InstinctFlash actual runtime is a separate milestone

First use the official `scripts/bootstrap_vendor.py plan pi05 --target jetson_thor
--json` in its own environment. Its installation recipe requires compatible
Python/CUDA tools, vendor sources, model/processor assets and account access.
Prepare these independently of the Cosmos environment.

An unadapted pi05 base policy is not a fruit-grasping policy for the current
WidowX. Admit no actuator connection from a successful metadata preflight or
zero-filled smoke prediction. Keep initial inference/shadow results separate
from a commissioned supervised physical task.

## Pending cloud decisions

Nebius AI Cloud and Token Factory balances are separate. Any B300 fallback needs
an explicit complete resource price, runtime limit, budget and cleanup plan before
provisioning. This dry run consumes neither GPU cloud balance nor inference credits.

# CoreXense-N: An MCP Evidence Gateway for Physical AI

## Elevator pitch

An MCP evidence gateway that checks what supports an AI decision, whether it is
still applicable, and why a physical-AI workflow should continue or pause.

## Inspiration

A model can give a convincing answer even when the evidence behind it is no
longer valid.

For Physical AI, this creates a practical problem. A camera frame may be stale,
two sensors may repeat the same upstream observation, or a cloud model may return
a recommendation after the scene has changed.

Our agricultural robotics exploration with FIRA made this concrete. A simulated
placement sequence can look convincing while a later step still lacks sufficient
validation. We wanted a place between model judgment and application permission
where those gaps become visible.

Our vision is an MCP evidence gateway for Physical AI: a reusable layer that
checks the observations supporting a decision, requests additional evidence when
appropriate, and records why a workflow continued or paused.

## What it does

CoreXense-N exposes five MCP tools for evidence review and explanation. It checks
local evidence, performs bounded semantic review when configured, checks validity
again after the model responds, and records the decision in a hash-linked trace.
TWS-Belief examples demonstrate how delayed and conflicting claims can be
reconstructed at a specified decision time.

The interface exposes no robot motor commands. Historical simulation records
remain non-executable even if a model approves their contents.

## How we built it

We connected an actual MCP stdio client and server to deterministic evidence
checks, bounded reobservation, trace verification and a Nebius Token Factory
adapter for NVIDIA Nemotron. The model receives structured evidence and must
return a verdict bound to that request's digest. It cannot change local policy.

Our FIRA demonstration uses a MuJoCo/RoboSim scene with orange and corn proxies
and a carton. Its historical event record is connected to the same source digest
used in the model-assisted review. It uses privileged simulator state and assumed
physical parameters; it is workflow evidence, not validated real-world grasping.

SKAI Intelligence supported the simulation exploration. We have also located
local training-course assets containing URDF, USD, mesh, texture and lighting
files. These provide a concrete starting point for environment-based evaluation.
Our independent local inspection resolved the URDF mesh references and opened the
USD composition with ten layers, eleven asset dependencies and no unresolved
dependencies. A static geometry preview shows the course layout; it omits textures
and does not run physics.
Asset inspection, simulation execution, model review and policy training are
tracked as separate milestones. The new course is not represented as a completed
closed-loop training experiment.

Voxel51 FiftyOne supported multimodal data organization and inspection in the
broader FIRA exploration. HawkRobo supported the earlier FIRA work. These credits
describe their respective contributions and do not imply endorsement of every
component of this hackathon submission.

## Why Nebius and NVIDIA matter

Nebius Token Factory provides the cloud inference endpoint, and NVIDIA Nemotron
provides the semantic review. Together they let us test the boundary between a
model recommendation and a locally governed workflow using actual model responses.

In our recorded live run, Nemotron returned ALLOW for a synthetic recovery case.
By the time the response arrived, the observation had exceeded its configured
250 ms validity window. CoreXense-N kept the workflow on HOLD. A separate slip
case was blocked locally without a model inference request.

That result makes the infrastructure relationship visible: cloud reasoning can
contribute useful evidence without becoming unconditional permission. GPU-based
scene experiments and Thor edge inference are extension paths, not completed
Nebius GPU deployment claims.

## Challenges we faced

Transport success was not enough. One live response reached the configured
256-token output limit and could not produce a complete verdict. We recorded it
as unknown and kept the workflow on HOLD. We added diagnostics that distinguish
truncation, invalid structure, provider failures and an explicit model unknown.

A separately recorded 1,024-token-budget follow-up produced three complete,
schema-valid responses using 2,954 reported tokens. Both synthetic approvals
still resulted in HOLD after evidence expiration. The historical replay received
an explicit unknown. We preserve both runs: the changing replay verdict shows
that semantic consistency is still an evaluation question.

We also had to preserve the boundaries between synthetic fixtures, historical
simulation, actual cloud inference and future hardware tests. A polished replay
must not be mistaken for a robot controlled by the model.

## Accomplishments that we are proud of

We built a prototype in which uncertainty changes workflow behavior. It includes
a deterministic evidence gate, bounded reobservation, an MCP interface, trace
verification, failure-path tests and a constrained Nebius inference adapter.

Our recorded three-request live run used 2,674 reported tokens. It demonstrated
local conflict rejection, output-truncation handling, evidence expiration after
model approval, and historical replay auditing. These are software behavior
observations, not a model accuracy benchmark or physical safety certification.

We are especially proud of separating model judgment from application permission.
This creates a concrete place to inspect evidence, handle failures, and explain
why a workflow continued or paused.

## What we learned

Persistent memory and reliable memory are different problems. Storage can retain
an experience and search can retrieve a similar record; applicability, temporal
validity, provenance, conflicts and authority still need explicit handling.

Open models are useful when their authority is deliberately constrained. Nemotron
contributes structured semantic review, while deterministic policy and human
escalation retain authority over consequential decisions.

## What's next

Our goal is to make CoreXense-N a reusable governance layer that works with a
customer's preferred model endpoint. It would add evidence validation, bounded
authority and auditability while fitting into the team's existing AI stack.

The next stage connects SKAI scene assets to reproducible environment variations,
then links each observation and model review to its scene configuration. Reviewed
failures can become candidates for targeted data collection and annotation.

For this extension, we draw methodological inspiration from ETH Zurich research
on [robust multimodal perception](https://leggedrobotics.github.io/rl-perceptiveloco/)
and [curriculum-based parallel robot learning](https://leggedrobotics.github.io/legged_gym/).
We plan to start with controlled observation failures in one scene, then increase
task difficulty. These are research references; we have not reproduced their
controllers or training results. See `docs/ETH_METHOD_BRIDGE.md` for the design.

PIER-Ego is our longer-term research path for traceable multimodal alignment from
egocentric demonstrations to robot learning. Cosmos visual reasoning and Thor
edge inference are prepared pilots. Their contribution to prediction or policy
learning will require independent evaluation. EEG-derived priors remain exploratory
and are not part of the functioning hackathon prototype.

We want teams to inspect what supports a decision, check whether that evidence
still applies, and collect the next observation that resolves the gap.

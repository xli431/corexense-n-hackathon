# Demonstration script - under three minutes

## 0:00-0:20 - Problem

Show the agricultural scene.

"A robot can receive a convincing answer after the evidence behind it has expired.
CoreXense-N is an MCP evidence gateway that checks whether a model-assisted
workflow has enough current evidence to continue."

## 0:20-0:55 - Working MCP interface

Show the real client command, tool inventory, and healthy/slip decisions.

"The MCP client calls our evidence review service. The gateway can continue a
synthetic workflow, request one additional observation, or pause. These examples
are synthetic tests; no motor commands are exposed."

## 0:55-1:25 - Why timing matters

Show TWS-Belief delayed evidence and competing claims in the review report.

"We preserve when an observation occurred and when the system received it. A
decision cannot rely on evidence that had not arrived. Conflicting claims remain
inspectable instead of disappearing behind a single confidence score."

## 1:25-2:05 - Nebius and NVIDIA

Only show and narrate a fresh live run after actually completing it. Otherwise
label the recording OFFLINE MOCK and describe live integration as pending.

"NVIDIA Nemotron runs through Nebius Token Factory to provide a bounded semantic
review. The response is bound to the evidence digest. A model's approval cannot
override local rejection or expired evidence."

If a live response expires, show the actual HOLD. Never substitute mock approval
or change the freshness limit for a better video.

Verified recording candidate: run `nebius-live-20261028-143100`, recovery case.
The model returned ALLOW, and the gateway returned HOLD because evidence expired
during the audit (2,047.409 ms). State that the evidence and deadline are synthetic.
The healthy case was truncated at 256 output tokens; show it as an observed failure.

## 2:05-2:35 - FIRA episode and trace

Show the carton simulation and matching source hash in the audited replay.

"Our agricultural simulation records task stages and outcomes. The MCP adapter
checks the episode trace and binds it to a semantic review. This is historical
simulation auditing, not current robot execution permission."

If real footage is available, label it SUPERVISED PHYSICAL TEST and state exactly
which controller caused motion. No claim of MCP-controlled execution without a
commissioned, verified physical integration.

## 2:35-2:50 - Outcome

"The prototype makes evidence failures visible and records why a workflow paused.
Our next step is to connect these records to targeted data collection and robot
learning experiments."

Credit the FIRA foundation: Voxel51 FiftyOne for data inspection, SKAI Intelligent
for simulation support, and HawkRobo for earlier FIRA sponsorship. Name services
actually used; do not imply an unconfirmed formal partnership.

Optional course-asset segment: local SKAI asset inspection has verified URDF mesh
references and OpenUSD stage composition. This is a separate training-course
environment, not the agricultural scene. Do not narrate simulator execution or
policy training until those runs have been completed and recorded.

# ETH Zurich research bridge for CoreXense-N

## Scope and source search

This is a focused, AI-assisted reference check, not a systematic review. On
2026-10-28 we searched for ETH Robotic Systems Lab work on unreliable perception,
parallel simulation and curriculum learning, then checked author project pages,
paper metadata and official repositories. These are methodological references;
ETH Zurich is not a project partner or endorser. No ETH code or weights have been
incorporated into this submission.

## Verified references and proposed adaptation

| Reference | Relevant method | Proposed use here | Current status |
|---|---|---|---|
| Miki et al., *Learning robust perceptive locomotion for quadrupedal robots in the wild*, Science Robotics 7(62), eabk2822, 2022. [Project](https://leggedrobotics.github.io/rl-perceptiveloco/), [paper metadata](https://arxiv.org/abs/2201.08117), DOI 10.1126/scirobotics.abk2822. | Recurrent attention integrates exteroception and proprioception under unreliable perception. | Test degraded observations and preserve evidence history; evaluate when additional observation or escalation is appropriate. | Conceptual inspiration. The present deterministic gateway is not their learned belief encoder or locomotion controller. |
| Rudin, Hoeller, Reist and Hutter, *Learning to Walk in Minutes Using Massively Parallel Deep Reinforcement Learning*, CoRL 2021. [Project](https://leggedrobotics.github.io/legged_gym/), [paper](https://arxiv.org/abs/2109.11978). | GPU-parallel training and a terrain curriculum that adapts difficulty to progress. | Organize SKAI task variants into increasing difficulty; later run paired policy evaluations on GPU infrastructure. | Proposed experiment design; no training or sim-to-real reproduction completed. |
| ETH RSL's [legged_gym](https://github.com/leggedrobotics/legged_gym) and [RSL-RL](https://github.com/leggedrobotics/rsl_rl). | legged_gym documents observation noise, friction/mass randomization and random pushes; RSL-RL provides robotics learning algorithms including PPO and student-teacher distillation. | Candidate training stack after selecting a compatible robot and task. | Not installed or integrated. legged_gym directs new applications toward Isaac Lab after its migration. |

## Layer responsibilities

1. SKAI course assets define the environment geometry, appearance and static
   collision structure. Asset composition checks do not establish dynamics fidelity.
2. A commissioned simulator and task/controller generate observations and outcomes.
   Their configuration, seed and asset digest must be recorded per episode.
3. Observation corruption is applied only to the policy/review input. Privileged
   simulator truth remains in a separate evaluation channel, inaccessible to the
   model being evaluated. This is our proposed evaluation boundary, not an
   implementation claim about the current FIRA privileged-state replay.
4. Nebius-hosted NVIDIA reasoning supplies a bounded semantic assessment.
5. CoreXense-N checks evidence validity and records the workflow decision. Its HOLD
   is a software workflow state; a robot-specific controller must define any safe
   physical response. Cutting actions or freezing a walking robot is not assumed safe.

## Small, testable extension

Research question: under the same task, controller and observation faults, can an
evidence gate reduce unsupported workflow continuation without excessive pauses?

Start with one observable inspection task in one SKAI course. Select an inspection
target, camera pose and success criterion before collecting results. Do not equate
this locomotion/inspection environment with the existing agricultural manipulation
scene. Add locomotion training only after the inspection pipeline is measurable.

Use identical recorded episodes and fixed observations for three software-review
conditions: local validity checks alone, model recommendation alone, and the full
gateway. The model-only condition is offline analysis, never actuator authority.
Run unchanged baseline observations plus separate delay, missing-observation and
conflicting-observation conditions. Predefine eligibility labels independently of
the gate; a gate decision cannot also define its own ground truth.

Record unsupported-continuation rate, missed-conflict rate, unnecessary-HOLD rate,
bounded reobservation count, latency, tokens and trace completeness. Include a
fresh, sufficient-evidence control so an always-HOLD system cannot appear best.
Report effect sizes and uncertainty across independent episodes; do not treat
frames from one episode or fixture reruns as independent trials. No preselected
significance threshold is presented as an achieved result.

For later training, separate a task-difficulty curriculum (terrain/obstacle
complexity) from sensor corruption (delay/dropout/occlusion). Change one factor
first, then test combined shifts and held-out layouts. Preserve the 250 ms current
synthetic freshness test as its own fixture; calibrate any real task deadline
separately rather than reusing it as a robot-control limit.

## What can be said in the hackathon

"Our next simulation evaluations draw on ETH Zurich research into robust
multimodal perception and curriculum-based robot learning. SKAI provides the
environment assets; Nebius and NVIDIA provide the demonstrated model-review
path; CoreXense-N records whether the supporting evidence remains applicable."

Do not claim reproduction of ETH results, an ETH-trained policy, successful
locomotion fallback, or improved robot learning from the current software tests.

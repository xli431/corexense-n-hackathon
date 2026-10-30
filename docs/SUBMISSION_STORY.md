## Inspiration

CoreXense-N is a general-purpose MCP evidence gateway I built for Physical AI, based on my previously published CoreSense/TWS work. It validates evidence, requests bounded re-observation, and traces why a workflow pauses — returning HOLD, re-observe, or proceed before an action is trusted.

It is currently a software review prototype and does not control robot motors. Local, deterministic checks and evidence freshness remain authoritative; NVIDIA Nemotron, hosted on Nebius Token Factory, adds a bounded semantic review (at most 2–3 calls per walkthrough). Next, the gateway will connect to physical systems through a separate supervised controller: its HOLD / re-observe / proceed decisions will be enforced by a deterministic local gate with e-stop, speed, force, and workspace limits — the gateway itself will never drive actuators directly.

The gateway is domain-general. One application included in this submission is a replay audit of episodes from the FIRA agricultural robotics project (review_simulation_episode — replay-only, always non-executable): an application of the tool, not its origin.

What inspired it: AI systems increasingly act on evidence they did not generate in the moment — prior episodes, sensor records, tool outputs, and model judgments. But evidence that looks relevant is not necessarily current, applicable, or trustworthy. A stale record can look highly relevant. Two records can conflict. A fluent model judgment can be wrong about the physical world. In consequential workflows, treating evidence as authority creates a quiet but serious failure mode: the system acts confidently, for the wrong reason.

CoreXense-N is built around one principle:

> **Evidence is evidence — not authority.**

## What it does

CoreXense-N is an evidence-governance layer, exposed as an MCP server. It ships five tools: `list_scenarios`, `review_scenario`, `review_episode`, `explain_belief`, and `review_simulation_episode`. For each piece of candidate evidence, it returns one of three decisions — **PROCEED** (fresh, supported, applicable), **RE-OBSERVE** (insufficient; a bounded re-observation is requested), or **HOLD** (stale, conflicting, or unsafe to rely on — the workflow pauses, with the reason recorded). Every decision comes with an explanation trace, so a pause is never a black box.

## How I built it

CoreXense-N separates semantic judgment from decision authority:

Evidence (episode / record / tool output)
  → deterministic local checks: freshness, provenance, schema, evidence IDs
  → NVIDIA Nemotron: bounded structured semantic review (max 2–3 calls)
  → local policy remains authoritative — a model "allow" cannot override an expired or failed check
  → PROCEED / RE-OBSERVE / HOLD
  → hash-chained, auditable decision record

The episode-review path first requires local qualification, then a request-bound, validated ALLOW response, and then checks the elapsed audit time. An expired review returns HOLD even when the model says ALLOW. The implementation uses structured verdicts, not a calibrated semantic score.

Built with **NVIDIA Nemotron** (structured semantic review), **Nebius Token Factory** (live, OpenAI-compatible inference), **Python** (MCP server and policy layer), **TWS-Belief** (vendored, MIT — belief and traceability components), and a **hash-chained ledger** that detects any change to the decision record relative to its retained tip.

Live and offline behavior are kept strictly separate: every result records whether it came from a live Token Factory request or a deterministic fixture, and the default semantic reviews are explicit, labelled mocks — an offline success is never presented as a live-model result.

## Challenges I faced

The hardest challenge was not evaluating evidence. It was deciding how much authority a good-looking judgment should have.

In one recorded live check, the recovery fixture received a model judgment of ALLOW — and the final decision was still HOLD, because the evidence had expired during the audit (a 250 ms synthetic evidence window, $\tau = 250\,\text{ms}$). That is the system working as designed: the model's opinion is advisory; freshness and deterministic checks decide. That window is a synthetic fixture parameter — I am careful not to present it as robot performance or a safety proof.

A second challenge was output discipline: one live response was truncated at the default 256-token output budget, so structured judgments now run with an explicitly recorded larger budget (`--audit-max-tokens 1024`) rather than silently failing.

Finally, I kept the gateway deliberately non-executable: the server exposes no actuator tools and no arbitrary filesystem access, so an audit result can inform a controller but can never become one.

## What I learned

Plausible evidence and valid evidence are different problems. A record can be retrievable, recent-looking, and semantically on-point — and still be expired, contradicted, or out of scope. Reliable use of evidence requires freshness and temporal validity, source provenance, conflict handling, bounded authority, and an explanation a human can audit.

I also learned that open models are most useful when their authority is deliberately constrained: Nemotron contributes semantic reasoning, while deterministic policy retains control over consequential decisions.



## Testing and results

The submission package passed 103 software tests and an independent Linux installation check. Offline evaluation covered 1,920 synthetic policy cases and 17 injected transport contracts. These evaluate software behavior, not robot success or model accuracy.

### Output-budget tests and repeated runs

I tested NVIDIA-Nemotron-3-Nano-30B-A3B through Nebius Token Factory. The initial three-request diagnostic run used 2,674 reported tokens and included one truncated response at a 256-token output limit. The recovery fixture received ALLOW but remained HOLD after its evidence expired.

Two follow-up walkthroughs used a 1,024-token output limit. Each made three cloud requests, using 2,954 and 3,022 reported tokens respectively. Across these six requests, all responses were complete and schema-valid, with no truncation. In both runs, healthy and recovery fixtures received model ALLOW but the gateway returned HOLD because the audit exceeded the configured 250 ms synthetic evidence window. The slip fixture was blocked locally without inference. FIRA replay received unknown and remained non-executable. Both trace checks passed.

These are repeated fixed-input checks, not independent physical trials or a controlled causal experiment. They do not establish model accuracy, reliability rates or a real-time latency guarantee. The larger-budget runs showed no truncation in this small sample; they do not prove that output-budget changes alone caused the difference.

### Preliminary model selection

A separately reported five-model fixture comparison favored Nano-30B: it was the only model reported to pass all three fixture checks, including rejection of the slip case, and had the lowest observed average latency (2,072 ms). Super-120B and Ultra-550B returned ALLOW on that slip fixture; Super-VL and Lightning returned unknown/truncated responses.

This preliminary comparison comes from the run author's terminal summary; the raw comparison JSON and matched configurations have not yet been independently checked. It is not a general model ranking. Truncated outputs are incomplete evidence, and a model ALLOW is not a final gate decision. The slip-model probe is separate from the gateway walkthrough, where slip is blocked before inference.

[Public source and reproduction instructions](https://github.com/xli431/corexense-n-hackathon) · [Test scope and comparison notes](https://github.com/xli431/corexense-n-hackathon/blob/main/docs/MODEL_TEST_RESULTS.md)

## What's next

Commissioning a sensor adapter, so live physical evidence (currently blocked by design) can be reviewed with the same discipline; evidence expiration, revision, and supersession policies; richer adversarial evaluation suites; and a supervised Physical AI workflow in which a HOLD is enforced by a deterministic controller — models may inform a decision, but cannot bypass safety controls or human authority.

CoreXense-N does not make AI systems use more evidence. It makes the evidence they use safer to trust.

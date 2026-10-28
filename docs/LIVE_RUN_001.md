# OMEN live MCP review - run 001

The owner ran the live client with NVIDIA-Nemotron-3-Nano-30B-A3B through Nebius
Token Factory. The actual MCP stdio exchange completed six review/explanation
calls; three cases reached the cloud adapter and retained API response hashes.
No physical trials or actuator commands occurred.

| Input | Semantic adapter status | Final workflow decision | Audit elapsed |
| --- | --- | --- | --- |
| Synthetic healthy lift | unknown | HOLD: semantic_review_not_allow | 4057.531 ms |
| Synthetic slip | not called | HOLD: workspace_or_slip_conflict | 0 ms |
| Synthetic stale-recovery | unknown | HOLD: semantic_review_not_allow | 3476.455 ms |
| Historical FIRA simulation | reject | HOLD: historical_replay_not_executable | 2859.433 ms |

The two TWS-Belief explanation calls were local synthetic examples, not cloud calls.

## Interpretation

Runtime integration and evidence binding worked. This is not a claim that all
semantic reviews passed. The two unknown statuses could be explicit model
uncertainty or response rejection by the adapter. Run 001 did not retain finish
reason, parsing diagnostic or token usage, so their exact cause cannot be inferred.

All cloud audit durations exceeded the 250 ms synthetic evidence window. However,
the synthetic final reason was semantic_review_not_allow, not evidence expiry;
the code checks the semantic result before the age condition. Do not recategorize
these historical cases as successful expiry-specific tests.

## Diagnostic follow-up

The adapter now records an allowlisted diagnostic, finish reason, HTTP status and
numeric token usage. It still stores no credential, raw output text or reasoning
content. The next run can distinguish model_unknown, truncated_completion,
malformed_json, schema errors and HTTP failures.

The prompt, 256-token output limit, exact response schema, request-hash binding,
250 ms evidence window and no-actuation boundary were not relaxed. Six added
diagnostic tests pass; the source-filtered candidate now passes 86 tests locally.
The diagnostic version needs a new owner-run cloud check; it has not produced
live results yet. Original run 001 remains preserved.

# Public Content Policy

The public runner is a **control surface, not an engine repository**.

## Allowed
1. Generic request-bridge code.
2. Generic confidentiality/security validation.
3. Synthetic fixtures that contain no retained engine evidence or real private fixture identity.
4. Public-source utilities only when they disclose no private engine design, evaluation state, internal source revision or cloud topology.

## Forbidden
- private source, weights, checkpoints, datasets, footage or retained evidence;
- private branch/SHA identifiers;
- engine-specific experiment inputs/results, per-player evaluation evidence, oracle outputs or acceptance traces;
- private cloud identifiers, bucket paths, service accounts, build/operation IDs or topology;
- credentials, tokens or secret material;
- Actions artifacts containing engine data;
- semantic request IDs that reveal experiment purpose.

## Request IDs
Use only `req-` plus 32 lowercase hex characters. The identifier carries no experiment name, date, player, fixture, model or purpose.

## Fail closed
`tools/public_content_guard.py` runs on every public change. A guard failure blocks use of the public repository until the offending material is removed. The guard reports file paths and rule codes only; it does not print matched sensitive content.

## Historical material
Deleting a file from `main` does not erase Git history. Anything already committed to a public repository must be treated as previously disclosed. Credentials must be rotated if they were ever exposed. A history rewrite is a separate operation and must not be confused with working-tree cleanup.

## Execution/control boundary
The public repository accepts and publishes only random opaque request IDs plus the explicitly allowlisted coarse receipt/status fields. It does not resolve private source, choose private experiments, hold cloud credentials, access private evidence, or directly authorize GPU execution.

Private infrastructure pulls the opaque outbox, performs private registration/authorization and starts only the preconfigured workload. This preserves the public/privacy boundary while allowing autonomous routine execution.

Direct OIDC dispatch is staged/not active and must not be described as canonical until separately verified and adopted.

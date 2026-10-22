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

## Licensed-feed staged exception

The isolated licensed-feed lane may temporarily hold authorized records in
runner memory or temporary files solely to transmit them directly to a private
OIDC-verified receiver. It may not commit, cache, publish, log, or upload those
records as public GitHub Actions artifacts. Public request/status records remain
strictly opaque. The lane remains disabled until a private checkpoint SHA-256
readback and end-to-end confidentiality test pass.

## Execution/control boundary
The public repository accepts and publishes only random opaque request IDs plus the explicitly allowlisted coarse receipt/status fields. It does not resolve private source, choose private experiments, hold cloud credentials, access private evidence, or directly authorize GPU execution.

Private infrastructure pulls the opaque outbox, performs private registration/authorization and starts only the preconfigured workload. This preserves the public/privacy boundary while allowing autonomous routine execution.

Direct OIDC dispatch is staged/not active and must not be described as canonical until separately verified and adopted.

## GitHub-only private Release acceptance route (staged, manual)

A separate, reviewed, manual-only licensed-feed workflow may use a secret-scoped
GitHub token to upload a bounded SDK checkpoint **directly to a private
repository Release**. This route avoids any cloud receiver. The token must be
a fine-grained, short-lived credential authorised for one private destination
only and installed as a GitHub Actions secret, never committed or printed.
Secrets must be exposed only to a manually dispatched, branch-pinned job,
never to pull requests, unreviewed branch pushes or dependency install steps.

This exception permits transient runtime data processing and authenticated
private Release upload ONLY. It does **not** allow public artifacts, public
release uploads, caches of tracking data, private repository checkouts, GPU
execution, public request payloads or disclosure of private engine evidence.
The new lane is not a replacement for the original opaque engine-control
bridge. It remains non-scheduled until independent GitHub SHA-256 readback has
passed for a real 300-window checkpoint.

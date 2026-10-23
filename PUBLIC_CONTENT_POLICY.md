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

## Isolated Game Pulse GitHub Release pilot

A manually dispatched licensed-feed lane on reviewed `main` may process NBA
Game Pulse SDK observations in temporary runner files and upload them directly
to private `timeedmonds-maker/104` Releases. Its private repository token is
scoped to the upload step after dependency installation. Pull requests and
branch pushes never receive that token. The lane may not publish, log, commit,
cache or upload tracking observations as public artifacts. This exception does
not alter the opaque engine request bridge. Season scheduling remains disabled
until live private upload and SHA-256 readback are verified.

## User-approved one-clip preview exception (NBA game 0022600091, event 616)

The owner expressly authorized the Jabari #616 clip itself to be public. A
single short **derived MP4 video only** may therefore be published as a
public GitHub Release asset for in-chat playback, after private-renderer QA
confirms the intended five-receiver cumulative overlay. This is a scoped
preview, not permission to share internal code, original raw Game Pulse
positions, sensor data, calibration source files, artifacts, test outputs,
tokens, or other clips. The public runner must still pass its exact workflow
content guard. This one-clip exception does not permit generic public video
artifacts or broad weakening of confidentiality checks. The release description
must disclose any remaining visual synchronisation uncertainty.

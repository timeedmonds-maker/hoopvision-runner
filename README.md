# HoopVision Runner

Public-safe execution bridge for CourtCoder/HoopVision.

This repository is **not** the product source and must never become a mirror of the private engine.

## Confidentiality boundary

Allowed here:
- generic bridge/orchestration code;
- generic privacy and security tests;
- synthetic, non-product fixtures;
- genuinely public-source utilities that reveal no private engine implementation, private evaluation state, cloud topology, credentials, source revision or retained evidence.

Forbidden here:
- private application source, model weights/checkpoints, private footage/fixtures/data/evidence;
- private source revisions/branches;
- algorithm-specific private-engine experiments and measured results;
- cloud project/bucket/service-account/build/operation/topology identifiers;
- credentials or authentication material;
- detailed private logs, failure traces or acceptance evidence.

The only workload input crossing the public boundary is a random opaque request ID.

## Transport

The current transition path remains an opaque public outbox consumed by private infrastructure. It exists only until the private OIDC gateway is deployed and verified.

The target path is:

`manual GitHub workflow -> short-lived GitHub OIDC token -> single-purpose private dispatch gateway -> private execution/evidence`

The OIDC workflow is intentionally unable to read private source or evidence.

## Public results

Public status is restricted to a minimal allowlist: request ID, coarse status, result-available boolean and observation time. Detailed metrics and failure evidence remain private.

See `PUBLIC_CONTENT_POLICY.md` and `runner_policy.json`.

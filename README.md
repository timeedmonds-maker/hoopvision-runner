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

The active canonical routine transport is:

`random opaque public request ID -> public outbox -> private pull consumer -> private registration/authorization -> private execution/evidence`

The public repository is only the request/status control surface. It does not receive private source, private evidence, private fixture identity, credentials, cloud authentication or direct GPU authority.

Routine CPU requests are consumed autonomously by private infrastructure. GPU work, when separately authorized, is also launched only from the private side; the public repository cannot authorize or directly dispatch GPU work.

A direct GitHub OIDC dispatch gateway remains a staged alternative only. It is **not** the active or canonical route until its private gateway and least-privilege path are separately verified and explicitly adopted.

## Public results

Public status is restricted to a minimal allowlist: request ID, coarse status, result-available boolean and observation time. Detailed metrics and failure evidence remain private.

See `PUBLIC_CONTENT_POLICY.md` and `runner_policy.json`.

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

## Approved Game Pulse CPU source-fusion jobs (2026–27)

This public repository also contains **orchestration-only** GitHub-hosted CPU workflows for an NBA Game Pulse data extension. The **private canonical repository** retains original source payloads, derived event-level records, and detailed acceptance results. Public repository commits, PRs, artifacts and logs **must never** contain player-level tracking, original SDK positions, query results, source secrets, video footage or copied private scripts.

Approved workflow roles:
- `.github/workflows/gamepulse-formal-pbp-14game.yml`: fetch source code transiently in the authenticated runner, validate official NBA play-by-play clocks and scores, write private results.
- `.github/workflows/gamepulse-native-interactions-14game.yml`: CPU fan-out of source-native tracking / official PBP / shot-event joins; result records are written **only** to the private repository.
- `.github/workflows/gamepulse-interaction-query.yml`: source-index-backed private player interaction query and private result write.
- `.github/workflows/rockets-native-touch-ppp.yml`: scoped original source/shot-alignment diagnostics, distinct from production indexed search.

**Scope note:** These purpose-built workflows are different from the opaque-request **CourtCoder execution transport** described above. They may fetch approved private code and data into an **ephemeral GitHub runner job**, subject to an authorized private access token and source SHA checks. The public *repository* never becomes a private mirror, and no private payload may be uploaded as a public artifact or printed to a public log. These actions do not grant a public user the ability to dispatch or approve private GPU execution.

**Source semantics:** original NBA Game Pulse-native touch fields can be treated as authoritative for recorded touch events without independent human review. Exact possession counting and media seek timing are distinct statistical or engineering layers. Source-specific detail and all numerical results belong only in the canonical **private** Game Pulse documentation, not this public README.


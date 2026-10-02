# HoopVision Runner

Minimal public CPU request bridge for CourtCoder / HoopVision.

## Boundary

This repository accepts only an opaque request identifier. It does not contain
or checkout private HoopVision source, models, fixtures, algorithms, roster
data, tactical logic, release manifests, or private evidence.

The runner:

1. validates the opaque request ID on a GitHub-hosted CPU runner;
2. writes only that opaque ID to `bridge_outbox/latest.json`;
3. exits without cloud credentials, a PAT, a service-account key, or GPU access;
4. a private `timeedmonds-maker/104` workflow reads the public outbox and invokes
   the existing private CPU request resolver;
5. the private resolver validates the registered request and is the only
   authority allowed to dispatch the canonical Blackwell worker.

The public runner **does not authorize or observe GPU work and does not own GPU
capacity**. Exact source SHA, fixture, roster, analytics request and GPU
authorization remain private.

This pull transport is the active prototype fallback while the dedicated
`github-hoopvision-runner` GCP WIF provider is blocked by its current
attribute condition. Restoring direct keyless WIF later must preserve the same
opaque-only boundary.

## Credential rule

- no fine-grained GitHub PAT;
- no private-repository checkout token;
- no service-account key;
- no cloud credential in the public repository.

See `runner_policy.json` for the machine-readable boundary.

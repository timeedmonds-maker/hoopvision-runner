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


## Execution invariant

**Do not use private `timeedmonds-maker/104` GitHub Actions as the default runner.**

There are two distinct execution lanes:

1. **CPU / distilled engineering experiments:** run directly on GitHub-hosted Actions in this public `hoopvision-runner` repository. Private retained evidence is reduced to the minimum non-sensitive packet needed for the experiment; no private source checkout is permitted. Measured results are committed back to this repository.
2. **Private-runtime work that genuinely requires private GCS/source or authorized GPU execution:** submit only an opaque request through the public bridge. The private control plane may resolve that request, but the public runner remains the user-facing execution surface and private `104` Actions are not to be treated as the normal experiment runner.

If a public experiment can be expressed from a distilled retained-evidence packet, **use lane 1**. Do not fall back to a private `104` Action merely because the underlying retained evidence originated there.

This invariant is intended to prevent runner drift and is subordinate only to the credential/privacy boundary above.

# HoopVision Runner

Minimal public CPU execution bridge.

## Boundary

This repository accepts only an opaque request identifier. It does not contain
or checkout private HoopVision source, models, fixtures, algorithms, roster
data, tactical logic, or private evidence.

The runner:

1. validates the opaque request ID on a GitHub-hosted CPU runner;
2. authenticates to Google Cloud with GitHub OIDC / Workload Identity
   Federation;
3. invokes the private scale-to-zero CPU request resolver;
4. observes only minimal terminal status.

It does **not** own GPU capacity and it does **not** invoke the GPU worker
directly.

## Credential rule

- no fine-grained GitHub PAT;
- no private-repository checkout token;
- no service-account key;
- OIDC/WIF only.

See `runner_policy.json` for the machine-readable public boundary.

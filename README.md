# HoopVision Runner

Minimal public CPU execution bridge.

## Boundary

This repository accepts only an opaque request identifier. It does not contain
or checkout private HoopVision source, models, fixtures, algorithms, roster
data, tactical logic, or private evidence.

The runner:

1. validates the opaque request ID on a GitHub-hosted CPU runner;
2. authenticates to Google Cloud with GitHub OIDC / Workload Identity Federation;
3. executes the private scale-to-zero CPU request resolver;
4. proceeds only after that private resolver has authorized the registered request;
5. transports the authorized request ID to the predeployed Blackwell Cloud Run job;
6. observes only minimal terminal status.

The public runner **does not authorize GPU work and does not own GPU capacity**.
The private CPU resolver is the authorization authority, and the Blackwell
worker independently verifies the private authorization before application
execution.

## Credential rule

- no fine-grained GitHub PAT;
- no private-repository checkout token;
- no service-account key;
- OIDC/WIF only.

See `runner_policy.json` for the machine-readable public boundary.

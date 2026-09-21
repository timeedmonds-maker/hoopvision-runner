# HoopVision Runner

Public execution shell for HoopVision CI/control-plane jobs.

## Repository topology invariant

- **Canonical application source:** private `timeedmonds-maker/104`, branch `hoopvision-production`.
- **Execution bridge:** this public `timeedmonds-maker/hoopvision-runner` repository, branch `main`.
- `SOURCE_SHA` must contain an exact commit SHA from `104`; the runner checks out and verifies that SHA before tests, packaging and GCP dispatch.
- `BENCHMARK` selects the benchmark endpoint.
- Application/engineering changes belong in `104/hoopvision-production`. This repository contains only runner/control-shell logic.
- Failure of private-repository GitHub Actions in `104` does not imply HoopVision execution is blocked while this public runner bridge is healthy.

This repository must not contain HoopVision source code, model files, video fixtures, credentials, or generated private evidence.

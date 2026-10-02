# HoopVision Runner

Minimal public execution bridge for CourtCoder / HoopVision.

## Contract

This repository is public and intentionally contains no private HoopVision
application source, player/roster data, benchmark details, release manifests, or
GPU implementation.

The only public request payload is an opaque `request_id`.

Execution flow:

```
public request_id
  -> GitHub OIDC / GCP Workload Identity Federation
  -> CPU-only Cloud Run Job: hoopvision-request-resolver
  -> private GCS request registry: requests/{request_id}.json
  -> canonical Blackwell Cloud Run Job only after private validation
```

The public bridge:

- never checks out `timeedmonds-maker/104`
- never requires a PAT or private-repository token
- never runs GPU code itself
- never exposes the private source SHA, benchmark, roster, fixture, or analytics
  request in this repository
- uses the fixed Google Cloud resolver job and passes only
  `HOOPVISION_REQUEST_ID`

The canonical private source remains `timeedmonds-maker/104`.
The production GPU default is the scale-to-zero Cloud Run Blackwell job using
`nvidia-rtx-pro-6000`. L4 is not an implicit fallback.

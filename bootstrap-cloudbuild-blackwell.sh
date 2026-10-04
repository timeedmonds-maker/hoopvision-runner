#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
HoopVision execution policy:
- Canonical and sole execution entrypoint: timeedmonds-maker/hoopvision-runner@main
- Do not create GitHub/Cloud Build workload triggers on private 104 branches.
- Private 104 may remain the source/control authority, but it must not initiate execution.
- Queue work through REQUEST_ID / .github/workflows/run.yml in this public runner.
- The public runner publishes the opaque request to bridge_outbox; downstream control-plane services may resolve that already-publicly-queued request.
EOF

echo "HOOPVISION_PUBLIC_RUNNER_ONLY_ENTRYPOINT_OK"

#!/usr/bin/env bash
set -euo pipefail

CANDIDATE_SHA="${1:?candidate sha required}"
CONTROL_BUNDLE_SHA="${2:?control bundle sha required}"
ROOT=/srv/hoopvision
CONTROL=/opt/hoopvision-control

echo "=== GPU ==="
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
systemctl is-active docker

test -d "$ROOT"
mkdir -p "$CONTROL" "$ROOT/models/cache/ppocrv6/medium" "$ROOT/models/cache/ppocrv6/small"
tar -C /tmp -xzf /tmp/control-current.tgz
install -m 0755 /tmp/tools/release/dev_supervisor.py "$CONTROL/dev_supervisor.py"
install -m 0644 /tmp/tools/release/durable_events.py "$CONTROL/durable_events.py"
install -m 0644 /tmp/infra/hoopvision-dev/hoopvision-dev-supervisor.service /etc/systemd/system/hoopvision-dev-supervisor.service

if [ ! -x "$CONTROL/venv/bin/python" ]; then
  python3 -m venv "$CONTROL/venv"
fi
"$CONTROL/venv/bin/pip" install --disable-pip-version-check -q   google-cloud-storage==3.4.0 google-cloud-pubsub==2.31.1 huggingface_hub

# Remove non-shipping SoccerNet OCR assets from the prepared host.
rm -f "$ROOT/models/nbacv/parseq_soccernet.ckpt" "$ROOT/models/nbacv/legibility_soccernet.pth"

# Commercial reserve.
V5="$ROOT/models/cache/ppocrv5_latin_rec.onnx"
V5D="$ROOT/models/cache/ppocrv5_latin_dict.txt"
if ! echo "995b0f5f28d2073896a78c03b5b863eae6af3744bafa0245b8522beea6994927  $V5" | sha256sum -c - >/dev/null 2>&1; then
  curl -L --fail --retry 3 -o "$V5" https://github.com/gitakoos/ocr-models/releases/download/v1/rec_latin.onnx
fi
echo "995b0f5f28d2073896a78c03b5b863eae6af3744bafa0245b8522beea6994927  $V5" | sha256sum -c -
if ! echo "ccbcc45730b3fbbd9050c5bc74db6a99067141ef1035e3d14889a84a6b9b1aff  $V5D" | sha256sum -c - >/dev/null 2>&1; then
  curl -L --fail --retry 3 -o "$V5D" https://github.com/gitakoos/ocr-models/releases/download/v1/ppocrv5_latin_dict.txt
fi
echo "ccbcc45730b3fbbd9050c5bc74db6a99067141ef1035e3d14889a84a6b9b1aff  $V5D" | sha256sum -c -

"$CONTROL/venv/bin/python" /tmp/install_ppocrv6.py

test ! -e "$ROOT/models/nbacv/parseq_soccernet.ckpt"
test ! -e "$ROOT/models/nbacv/legibility_soccernet.pth"
echo "708789b50c42b5265cced64276a8beb1b7f294d324f954d359fd8a2d01f5a939  $ROOT/models/cache/rfdetr_m_640.onnx" | sha256sum -c -
test "$(stat -c %s "$ROOT/models/cache/sam3.1_multiplex.pt")" = "3502755717"
echo "5f43c16f2a684b1d2284662178bdb604febd3d6bfdb5ca73828d08d0f7c0c3e9  $ROOT/models/cache/ppocrv6/medium/model.safetensors" | sha256sum -c -
echo "f65a332afe5aa663f0b9d5706f4ae8457b5b4058a842d5c1eb22df505c27d642  $ROOT/models/cache/ppocrv6/small/model.safetensors" | sha256sum -c -

printf '%s\n' "$CANDIDATE_SHA" > "$ROOT/commercial-prepared.candidate.sha"
printf '%s\n' "$CONTROL_BUNDLE_SHA" > "$ROOT/commercial-prepared.control-bundle.sha256"
systemctl daemon-reload
systemctl restart hoopvision-dev-supervisor.service
systemctl is-active hoopvision-dev-supervisor.service
echo "HOOPVISION_COMMERCIAL_HOST_REPAIRED"

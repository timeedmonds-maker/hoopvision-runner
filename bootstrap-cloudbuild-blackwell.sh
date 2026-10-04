#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="project-d88c48c6-7f48-4c33-928"
REGION="asia-southeast1"
CONNECTION="CourtCoder-GCloud"
REPOSITORY="hoopvision-104"
CONTROL_SA="hoopvision-github@${PROJECT_ID}.iam.gserviceaccount.com"
CONTROL_SA_RESOURCE="projects/${PROJECT_ID}/serviceAccounts/${CONTROL_SA}"
REPO_RESOURCE="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION}/repositories/${REPOSITORY}"

gcloud config set project "$PROJECT_ID" >/dev/null

# Required for Cloud Build to return detailed build logs to GitHub checks.
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CONTROL_SA" \
  --role="roles/logging.viewer" \
  --condition=None >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CONTROL_SA" \
  --role="roles/logging.logWriter" \
  --condition=None >/dev/null

for TRIGGER in hoopvision-control-plane hoopvision-blackwell-request; do
  gcloud builds triggers delete "$TRIGGER" \
    --region="$REGION" --project="$PROJECT_ID" --quiet 2>/dev/null || true
done

gcloud builds triggers create github \
  --name="hoopvision-control-plane" \
  --repository="$REPO_RESOURCE" \
  --branch-pattern='^hoopvision-production$' \
  --build-config='cloudbuild/hoopvision-control-plane.yaml' \
  --service-account="$CONTROL_SA_RESOURCE" \
  --included-files='cloudbuild/hoopvision-control-plane.yaml,hoopvision/worker/request_resolver.py,hoopvision/worker/blackwell_release_worker.py,hoopvision/Dockerfile.request-resolver,hoopvision/Dockerfile.blackwell-release-worker,hoopvision/config/execution_policy.json,tools/validate_execution_policy.py' \
  --include-logs-with-status \
  --region="$REGION" \
  --project="$PROJECT_ID"

gcloud builds triggers create github \
  --name="hoopvision-blackwell-request" \
  --repository="$REPO_RESOURCE" \
  --branch-pattern='^courtcoder/integration$' \
  --build-config='cloudbuild/hoopvision-blackwell-request.yaml' \
  --service-account="$CONTROL_SA_RESOURCE" \
  --included-files='hoopvision/worker/RUN_CLOUD_BUILD_REQUEST' \
  --include-logs-with-status \
  --region="$REGION" \
  --project="$PROJECT_ID"

echo "HOOPVISION_AUTONOMOUS_GCP_BRIDGE_READY"

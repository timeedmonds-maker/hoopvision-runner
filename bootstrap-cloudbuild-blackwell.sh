#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-d88c48c6-7f48-4c33-928}"
REGION="${REGION:-asia-southeast1}"
REPO_OWNER="${REPO_OWNER:-timeedmonds-maker}"
REPO_NAME="${REPO_NAME:-104}"
CONTROL_BRANCH="${CONTROL_BRANCH:-hoopvision-production}"
REQUEST_BRANCH="${REQUEST_BRANCH:-courtcoder/integration}"
CONTROL_SA="${CONTROL_SA:-hoopvision-github@${PROJECT_ID}.iam.gserviceaccount.com}"
RUNTIME_SA="${RUNTIME_SA:-hoopvision-worker@${PROJECT_ID}.iam.gserviceaccount.com}"
RELEASE_BUCKET="${RELEASE_BUCKET:-${PROJECT_ID}-hoopvision-dev}"
RESOLVER_JOB="${RESOLVER_JOB:-hoopvision-request-resolver}"
BLACKWELL_JOB="${BLACKWELL_JOB:-hoopvision-blackwell-release-worker}"
CONTROL_TRIGGER="${CONTROL_TRIGGER:-hoopvision-control-plane}"
REQUEST_TRIGGER="${REQUEST_TRIGGER:-hoopvision-blackwell-request}"

CONTROL_SA_RESOURCE="projects/${PROJECT_ID}/serviceAccounts/${CONTROL_SA}"

echo "PROJECT_ID=$PROJECT_ID"
echo "REGION=$REGION"
echo "CONTROL_SOURCE=$REPO_OWNER/$REPO_NAME:$CONTROL_BRANCH"
echo "APPLICATION_SOURCE=$REPO_OWNER/$REPO_NAME:$REQUEST_BRANCH"
echo "BUILD_IDENTITY=$CONTROL_SA"
echo "RUNTIME_IDENTITY=$RUNTIME_SA"

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  --project="$PROJECT_ID"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CONTROL_SA" \
  --role="roles/run.developer" \
  --condition=None >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CONTROL_SA" \
  --role="roles/artifactregistry.writer" \
  --condition=None >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$CONTROL_SA" \
  --role="roles/logging.logWriter" \
  --condition=None >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://$RELEASE_BUCKET" \
  --member="serviceAccount:$CONTROL_SA" \
  --role="roles/storage.objectAdmin" >/dev/null
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member="serviceAccount:$CONTROL_SA" \
  --role="roles/iam.serviceAccountUser" \
  --project="$PROJECT_ID" >/dev/null

# Resolver runtime is the sole canonical Blackwell dispatch authority.
gcloud run jobs add-iam-policy-binding "$BLACKWELL_JOB" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/run.jobsExecutorWithOverrides" >/dev/null

# Cloud Build invokes only the CPU resolver with an opaque request-id override.
gcloud run jobs add-iam-policy-binding "$RESOLVER_JOB" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --member="serviceAccount:$CONTROL_SA" \
  --role="roles/run.jobsExecutorWithOverrides" >/dev/null || true

create_trigger() {
  local name="$1"
  local config="$2"
  local included="$3"
  local branch="$4"

  if gcloud builds triggers describe "$name" \
      --region="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud builds triggers delete "$name" \
      --region="$REGION" --project="$PROJECT_ID" --quiet
  fi

  local source_args=()
  if [[ -n "${CLOUD_BUILD_REPOSITORY:-}" ]]; then
    source_args+=(--repository="$CLOUD_BUILD_REPOSITORY")
  else
    source_args+=(--repo-owner="$REPO_OWNER" --repo-name="$REPO_NAME")
  fi

  gcloud builds triggers create github \
    --name="$name" \
    --region="$REGION" \
    "${source_args[@]}" \
    --branch-pattern="^${branch}$" \
    --build-config="$config" \
    --service-account="$CONTROL_SA_RESOURCE" \
    --included-files="$included" \
    --include-logs-with-status \
    --project="$PROJECT_ID"
}

create_trigger \
  "$CONTROL_TRIGGER" \
  "cloudbuild/hoopvision-control-plane.yaml" \
  "cloudbuild/hoopvision-control-plane.yaml,hoopvision/worker/request_resolver.py,hoopvision/worker/blackwell_release_worker.py,hoopvision/Dockerfile.request-resolver,hoopvision/Dockerfile.blackwell-release-worker,hoopvision/config/execution_policy.json,tools/validate_execution_policy.py" \
  "$CONTROL_BRANCH"

create_trigger \
  "$REQUEST_TRIGGER" \
  "cloudbuild/hoopvision-blackwell-request.yaml" \
  "hoopvision/worker/RUN_CLOUD_BUILD_REQUEST" \
  "$REQUEST_BRANCH"

echo "Running control-plane deployment at current $CONTROL_BRANCH head..."
gcloud builds triggers run "$CONTROL_TRIGGER" \
  --region="$REGION" \
  --branch="$CONTROL_BRANCH" \
  --project="$PROJECT_ID"

echo "Registering and dispatching current integration request at $REQUEST_BRANCH head..."
gcloud builds triggers run "$REQUEST_TRIGGER" \
  --region="$REGION" \
  --branch="$REQUEST_BRANCH" \
  --project="$PROJECT_ID"

echo "HOOPVISION_CLOUD_BUILD_MIGRATION_LAUNCHED"

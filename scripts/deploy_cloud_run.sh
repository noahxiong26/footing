#!/usr/bin/env bash
# Deploy Footing to Cloud Run from source, with keys in Secret Manager and hard cost caps.
#
# Prints every command and does nothing unless you pass --yes.
#   scripts/deploy_cloud_run.sh                 # dry run: show the plan
#   PROJECT=my-gcp-project scripts/deploy_cloud_run.sh --yes
#
# Settings (env vars):
#   PROJECT   GCP project id (required)
#   REGION    default us-east4 (Northern Virginia, closest to the demo towns)
#   MODE      live (default) or replay (no outside calls; recorded towns only)
#   SERVICE   default footing
#
# Secrets: put each key you have in .env first. Each non-empty key becomes a Secret Manager
# secret and is mounted as the same env var. Empty keys are skipped; those sources show Unknown.
set -euo pipefail
cd "$(dirname "$0")/.."

RUN=0; [ "${1:-}" = "--yes" ] && RUN=1
PROJECT="${PROJECT:-}"; REGION="${REGION:-us-east4}"; MODE="${MODE:-live}"; SERVICE="${SERVICE:-footing}"
[ -n "$PROJECT" ] || { echo "Set PROJECT=<your gcp project id>"; exit 1; }
[ -f .env ] && set -a && . ./.env && set +a

do_() { echo "+ $*"; if [ $RUN = 1 ]; then "$@"; fi; }

echo "== 1. APIs (Cloud Run, Cloud Build, Artifact Registry, Secret Manager)"
do_ gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
    secretmanager.googleapis.com --project "$PROJECT"

echo "== 2. Secrets"
SECRETS=()
for VAR in CENSUS_API_KEY HUD_API_TOKEN EIA_API_KEY BLS_API_KEY GOOGLE_MAPS_API_KEY TRANSITLAND_API_KEY \
           KROGER_CLIENT_ID KROGER_CLIENT_SECRET GEMINI_API_KEY; do
  VAL="${!VAR:-}"
  [ -n "$VAL" ] || { echo "   skip $VAR (empty)"; continue; }
  NAME="footing-$(echo "$VAR" | tr '[:upper:]_' '[:lower:]-')"
  if [ $RUN = 1 ]; then
    gcloud secrets describe "$NAME" --project "$PROJECT" >/dev/null 2>&1 \
      || gcloud secrets create "$NAME" --replication-policy=automatic --project "$PROJECT"
    printf "%s" "$VAL" | gcloud secrets versions add "$NAME" --data-file=- --project "$PROJECT" >/dev/null
  fi
  echo "+ secret $NAME <- \$$VAR (value not printed)"
  SECRETS+=("$VAR=$NAME:latest")
done

echo "== 3. Let the Cloud Run service account read the secrets"
NUM=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)' 2>/dev/null || echo "<project-number>")
do_ gcloud projects add-iam-policy-binding "$PROJECT" \
    --member "serviceAccount:${NUM}-compute@developer.gserviceaccount.com" \
    --role roles/secretmanager.secretAccessor --condition=None

echo "== 4. Deploy (scale to zero; at most 2 instances so a traffic spike cannot run up the bill)"
SECRET_FLAG=()
[ ${#SECRETS[@]} -gt 0 ] && SECRET_FLAG=(--set-secrets "$(IFS=,; echo "${SECRETS[*]}")")
do_ gcloud run deploy "$SERVICE" --source . --project "$PROJECT" --region "$REGION" \
    --allow-unauthenticated --min-instances 0 --max-instances 2 --memory 512Mi --cpu 1 --concurrency 40 \
    --set-env-vars "FOOTING_MODE=$MODE,FOOTING_CONTACT=${FOOTING_CONTACT:-footing@example.edu},FOOTING_GEMMA_MODEL=${FOOTING_GEMMA_MODEL:-gemma-4-26b-a4b-it}" \
    "${SECRET_FLAG[@]}"

cat <<'NOTE'

== 5. Cost guardrails (do these once in the console; gcloud cannot set all of them)
 - Billing > Budgets & alerts: budget $20 with alerts at 50%, 90%, 100%. A budget only alerts and credits
   do not stop charges, so the quota caps below and --max-instances are what actually limit spend.
 - APIs & Services > Places API (New) > Quotas: cap "Text Search requests per day" at 160.
   Each fresh area (not cached) makes 4 Text Search Pro calls. 160/day x 30 = 4,800 calls/month,
   under the 5,000 free Pro calls/month (about 1,200 fresh areas). Past the free cap: $32 per 1,000 calls.
 - Restrict the Maps key: API restriction = Places API (New) only; application restriction = none
   (server-side key), never ship it to the browser.
 - Gemini API (Gemma 4): free tier rate limits apply per key; the app falls back to the rule-based plan
   when the call fails, so a quota hit never breaks the screen.
 - Turn off afterwards: gcloud run services delete footing --region us-east4
NOTE
[ $RUN = 1 ] || echo "(dry run: nothing was changed. Re-run with --yes to deploy.)"

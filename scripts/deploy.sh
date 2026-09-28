#!/usr/bin/env sh
# Deploy a CI-verified commit to a docker-compose host over SSH.
#   scripts/deploy.sh <staging|production> <git-sha>
# Needs DEPLOY_HOST and DEPLOY_SSH_KEY (GitHub environment secrets). The host keeps its own
# .env populated from the secret manager; no secret is stored in this repository.
set -eu

ENVIRONMENT="$1"
SHA="$2"
: "${DEPLOY_HOST:?DEPLOY_HOST is not configured for this environment}"
: "${DEPLOY_SSH_KEY:?DEPLOY_SSH_KEY is not configured for this environment}"

KEY_FILE=$(mktemp)
trap 'rm -f "$KEY_FILE"' EXIT
printf '%s\n' "$DEPLOY_SSH_KEY" > "$KEY_FILE"
chmod 600 "$KEY_FILE"

echo "Deploying $SHA to $ENVIRONMENT ($DEPLOY_HOST)"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=accept-new "$DEPLOY_HOST" \
  "set -eu
   cd /opt/nirnoy
   git fetch --quiet origin
   git checkout --quiet '$SHA'
   export IMAGE_TAG='$SHA'
   COMPOSE='docker compose -f docker-compose.yml -f docker-compose.prod.yml'
   \$COMPOSE build
   \$COMPOSE run --rm migrate
   \$COMPOSE up -d --remove-orphans
   \$COMPOSE ps"

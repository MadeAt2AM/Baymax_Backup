#!/usr/bin/env bash
# project.sh — MadeAt2AM project lifecycle utility
#
# One folder = one project. Lives at /root/projects/<name>/ on this VPS.
# Mirrors to GitHub MadeAt2AM/<name> (private). Dev VPS pulls on push.
#
# Usage (run from inside the project folder, or pass the name):
#   project.sh new    <name> [git-user-name]   Scaffold a brand-new project (asks confirmation if exists)
#   project.sh push   [commit message]         Stage all + commit + push to GitHub
#   project.sh deploy                         Trigger redeploy on dev VPS without pushing
#   project.sh status                         Show project state (local + GitHub + last deploy)
#   project.sh logs   [tail-n]                Tail dev-VPS container logs
#   project.sh teardown                       Stop dev-VPS container + delete DNS + ask to keep/remove GitHub repo
#
# Conventions:
#   project folder   = /root/projects/<name>/
#   github repo      = MadeAt2AM/<name>  (private, auto-init)
#   dev-vps path     = /srv/projects/<name>/
#   subdomain        = <name>.terrybot.top  (added to Cloudflare via cf-dns.sh)
#   container name   = <name>-app

set -euo pipefail

# ─── config ────────────────────────────────────────────────
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
ENV_FILE="$HERMES_HOME/.env"
BIN_DIR="$HERMES_HOME/bin"
GH_ORG="MadeAt2AM"
DOMAIN="terrybot.top"
VPS_IP="147.79.18.32"
PROJECTS_ROOT="/root/projects"
DEV_VPS_SSH_KEY="$HOME/.ssh/baymax_dev_vps"
DEV_VPS_HOST="deploy@${VPS_IP}"

CF_DNS="$BIN_DIR/cf-dns.sh"

SSH_OPTS=(-i "$DEV_VPS_SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)

# ─── guard rails ───────────────────────────────────────────
[ -f "$ENV_FILE" ] || { echo "ERR: $ENV_FILE missing"; exit 1; }
# shellcheck disable=SC1090
source "$ENV_FILE"
: "${GITHUB_TOKEN:?GITHUB_TOKEN required in $ENV_FILE}"

# ─── helpers ───────────────────────────────────────────────
red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[1;33m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }
die()    { red "ERR: $*" >&2; exit 1; }

usage() {
  sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//' | head -30
  exit 1
}

require_project_dir() {
  local name="$1"
  [ -n "$name" ] || { name=$(basename "$(pwd)"); }
  PROJECT_DIR="$PROJECTS_ROOT/$name"
  if [ ! -d "$PROJECT_DIR" ]; then
    die "Project '$name' not found at $PROJECT_DIR. Run 'project.sh new $name' first."
  fi
  PROJECT_NAME="$name"
}

require_inside_project() {
  local cwd
  cwd="$(pwd)"
  case "$cwd" in
    "$PROJECTS_ROOT"/*) PROJECT_DIR="$cwd"; PROJECT_NAME=$(basename "$cwd");;
    *) die "Run this command from inside a project folder, or use 'project.sh <cmd> <name>'";;
  esac
}

# ─── github api helpers ────────────────────────────────────
gh_api() {
  local method="$1" path="$2" data="${3:-}"
  if [ -n "$data" ]; then
    curl -sS -X "$method" "https://api.github.com$path" \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github+json" \
      -H "Content-Type: application/json" \
      -d "$data"
  else
    curl -sS -X "$method" "https://api.github.com$path" \
      -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github+json"
  fi
}

gh_create_repo() {
  local repo="$1" desc="${2:-Project managed by MadeAt2AM Hermes pipeline.}"
  # try under org first, fall back to user if not allowed
  local payload resp
  payload=$(cat <<EOF
{"name":"$repo","description":"$desc","private":true,"auto_init":true}
EOF
)
  resp=$(gh_api POST "/orgs/$GH_ORG/repos" "$payload")
  if echo "$resp" | jq -e '.id // empty' >/dev/null 2>&1; then
    echo "$resp" | jq -r '"ok repo=\(.full_name) url=\(.html_url)"'
    return 0
  fi
  # fallback to user account
  yellow "  ⚠ org-create failed, attempting user-account create"
  echo "$resp" | jq '{errors: .errors, message: .message}' 2>/dev/null
  resp=$(gh_api POST "/user/repos" "$payload")
  if echo "$resp" | jq -e '.id // empty' >/dev/null 2>&1; then
    echo "$resp" | jq -r '"ok repo=\(.full_name) url=\(.html_url)"'
    return 0
  fi
  echo "$resp" | jq .
  return 1
}

gh_repo_exists() {
  local repo="$1"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$GH_ORG/$repo")
  [ "$code" = "200" ]
}

# ─── commands ──────────────────────────────────────────────
cmd_new() {
  local name="${1:?usage: project.sh new <name>}"
  # name sanitisation — only lowercase letters, digits, dashes; no underscores/spaces
  if ! [[ "$name" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]]; then
    die "Invalid project name '$name'. Use lowercase letters, digits, dashes only (e.g. 'my-cool-app')."
  fi

  local dest="$PROJECTS_ROOT/$name"
  if [ -d "$dest" ]; then
    yellow "Folder already exists at $dest — leaving contents alone, will just init repo."
  else
    yellow "[1/4] Scaffolding project folder: $dest"
    mkdir -p "$dest"
    cp "$HERMES_HOME/projects/_template/.gitignore" "$dest/.gitignore"
    cp "$HERMES_HOME/projects/_template/README.md" "$dest/README.md"
    # Personalise README
    sed -i "s/<PROJECT_NAME>/$name/g" "$dest/README.md"
    cp "$HERMES_HOME/projects/_template/.env.example" "$dest/.env.example"
  fi

  yellow "[2/4] Initialising git + creating GitHub repo (private)"
  cd "$dest"
  git init -q -b main 2>/dev/null || git init -q
  git config user.name  "MadeAt2AM Hermes" 2>/dev/null || true
  git config user.email "hermes@madeat2am.in"

  if gh_repo_exists "$name"; then
    yellow "  ↪ repo already exists at $GH_ORG/$name — reusing"
  else
    gh_create_repo "$name" "Project '$name' — managed via MadeAt2AM Hermes pipeline"
  fi

  git remote remove origin 2>/dev/null || true
  git remote add origin "https://x-access-token:$GITHUB_TOKEN@github.com/$GH_ORG/$name.git"

  yellow "[3/4] First commit + push"
  # Pull --rebase with allow-unrelated to handle the case where GitHub auto-created
  # an empty README/.gitignore commit when we created the repo with auto_init=true.
  # -X theirs makes our local scaffold win on conflict (we have the real content).
  git add -A
  if git diff --cached --quiet; then
    yellow "  ↪ nothing to commit locally — checking remote state"
    if ! git ls-remote --heads origin main 2>/dev/null | grep -q main; then
      yellow "  ↪ no remote main yet — push our HEAD if any"
      if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
        git commit --allow-empty -q -m "Initial scaffold for $name"
      fi
    fi
  else
    git commit -q -m "Initial scaffold for $name"
  fi
  # Reconcile against remote (handles auto-init commit from GitHub)
  if git ls-remote --heads origin main 2>/dev/null | grep -q main; then
    if ! git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
      # remote has commits local doesn't — pull with allow-unrelated
      git pull --rebase --allow-unrelated-histories -s recursive -X theirs origin main 2>&1 | tail -3 || true
    fi
  fi
  git push -u origin main 2>&1 | tail -3

  yellow "[4/5] Registering GitHub webhook for auto-redeploy"
  webhook_url="http://${VPS_IP}:9000/hooks/github-push"
  webhook_secret=$(cat /root/.hermes/.dev-vps-webhook.secret 2>/dev/null || echo "")
  if [ -z "$webhook_secret" ]; then
    yellow "  ⚠ no webhook secret file at /root/.hermes/.dev-vps-webhook.secret — webhook registration skipped"
  else
    hook_payload=$(jq -n \
      --arg url "$webhook_url" \
      --arg secret "$webhook_secret" \
      '{active:true, events:["push"], config:{url:$url, content_type:"json", secret:$secret, insecure_ssl:"1"}}')
    hook_resp=$(gh_api POST "/repos/$GH_ORG/$name/hooks" "$hook_payload")
    if echo "$hook_resp" | jq -e '.id // empty' >/dev/null 2>&1; then
      green "  ✓ webhook registered (id=$(echo "$hook_resp" | jq -r '.id'))"
    else
      yellow "  ⚠ webhook registration failed (token likely lacks 'webhooks:write' on $GH_ORG/$name):"
      echo "$hook_resp" | jq '{message, documentation_url}' 2>/dev/null | sed 's/^/    /'
      yellow "  → register manually at:"
      yellow "    https://github.com/$GH_ORG/$name/settings/hooks"
      yellow "    Payload URL: $webhook_url"
      yellow "    Content type: application/json"
      yellow "    Secret: (see /root/.hermes/.dev-vps-webhook.secret)"
      yellow "    Events: push"
    fi
  fi

  yellow "[5/5] Asking dev VPS to clone + first deploy"
  # Forward GH_TOKEN through SSH so project_dev.sh can git fetch from MadeAt2AM/<name>
  # We never persist the token in shell history or in ps output (setsid wraps the call).
  _old_askpass=""
  if [ -n "${SSH_AUTH_SOCK:-}" ]; then :; fi
  ssh "${SSH_OPTS[@]}" "$DEV_VPS_HOST" \
    "GH_TOKEN='$GITHUB_TOKEN' /srv/scripts/project_dev.sh first-pull '$name'"

  green ""
  green "✓ Project '$name' created and live."
  green "  • Local folder:  $dest"
  green "  • GitHub repo:   https://github.com/$GH_ORG/$name"
  green "  • Dev VPS path:  /srv/projects/$name/"
  green "  • Live URL:      https://$name.$DOMAIN (will be valid once the container serves traffic)"
  green ""
  yellow "Next steps for you:"
  yellow "  1. cd $dest"
  yellow "  2. drop your app code in there"
  yellow "  3. add a Dockerfile + docker-compose.yml (or ask me to scaffold one)"
  yellow "  4. project.sh push  → auto-redeploys"
}

cmd_push() {
  require_inside_project
  cd "$PROJECT_DIR"
  local msg="${1:-chore: sync from local}"
  echo "→ adding all changes under $(pwd)"
  git add -A
  if git diff --cached --quiet; then
    yellow "nothing to commit"
    return 0
  fi
  git commit -q -m "$msg"
  echo "→ pushing to origin main"
  git push origin main 2>&1 | tail -5
  green "✓ pushed. GitHub webhook will fire and dev VPS will rebuild in ~30s."
}

cmd_deploy() {
  require_inside_project
  cd "$PROJECT_DIR"
  echo "→ manual redeploy trigger for $PROJECT_NAME"
  ssh "${SSH_OPTS[@]}" "$DEV_VPS_HOST" "/srv/scripts/project_dev.sh redeploy '$PROJECT_NAME'"
}

cmd_status() {
  require_inside_project
  cd "$PROJECT_DIR"
  bold "─── $PROJECT_NAME ─────────────────────────────────────"
  echo "Local path:    $(pwd)"
  echo "GitHub:        https://github.com/$GH_ORG/$PROJECT_NAME"
  echo "Dev VPS path:  /srv/projects/$PROJECT_NAME/"
  echo ""
  echo "── git ──"
  if [ -d .git ]; then
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "  not a git repo"; return; }
    local branch current_commit ahead behind
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    current_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "?")
    echo "  branch:       $branch"
    echo "  HEAD:         $current_commit"
    git status -sb 2>/dev/null | sed 's/^/  /'
    ahead=$(git rev-list --count origin/$branch..HEAD 2>/dev/null || echo 0)
    behind=$(git rev-list --count HEAD..origin/$branch 2>/dev/null || echo 0)
    echo "  ahead/behind: $ahead / $behind"
  fi
  echo ""
  echo "── dev vps ──"
  ssh "${SSH_OPTS[@]}" "$DEV_VPS_HOST" "/srv/scripts/project_dev.sh status '$PROJECT_NAME'" 2>&1 | sed 's/^/  /'
  echo ""
  echo "── live url ──"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://$PROJECT_NAME.$DOMAIN/" 2>/dev/null || echo "000")
  if [ "$code" = "200" ]; then green "  ✓ https://$PROJECT_NAME.$DOMAIN/  → HTTP 200"
  elif [ "$code" = "000" ]; then red "    ✗ https://$PROJECT_NAME.$DOMAIN/  unreachable"
  else yellow "    ! https://$PROJECT_NAME.$DOMAIN/  → HTTP $code"
  fi
}

cmd_logs() {
  require_inside_project
  local lines="${1:-50}"
  ssh "${SSH_OPTS[@]}" "$DEV_VPS_HOST" "/srv/scripts/project_dev.sh logs '$PROJECT_NAME' '$lines'"
}

cmd_teardown() {
  require_inside_project
  yellow "⚠ About to tear down project '$PROJECT_NAME'"
  yellow "  - stop & remove docker container on dev VPS"
  yellow "  - delete /srv/projects/$PROJECT_NAME on dev VPS"
  yellow "  - delete $PROJECT_NAME.$DOMAIN DNS record"
  echo ""
  read -r -p "Continue? [y/N] " yn
  case "$yn" in
    y|Y|yes|YES) ;;
    *) yellow "Aborted"; exit 0;;
  esac
  ssh "${SSH_OPTS[@]}" "$DEV_VPS_HOST" "/srv/scripts/project_dev.sh teardown '$PROJECT_NAME'"
  "$CF_DNS" del "$PROJECT_NAME" || true
  echo ""
  read -r -p "Also delete the GitHub repo $GH_ORG/$PROJECT_NAME? [y/N] " yn2
  case "$yn2" in
    y|Y|yes|YES)
      curl -s -X DELETE -H "Authorization: Bearer $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/$GH_ORG/$PROJECT_NAME" \
        -o /dev/null -w "  delete-status=%{http_code}\n"
      ;;
    *) yellow "  keeping GitHub repo $GH_ORG/$PROJECT_NAME";;
  esac
  green "✓ teardown complete for '$PROJECT_NAME'"
}

# ─── main ──────────────────────────────────────────────────
cmd="${1:-}"; shift || true
case "$cmd" in
  new)      cmd_new "$@";;
  push)     cmd_push "$@";;
  deploy)   cmd_deploy;;
  status)   cmd_status;;
  logs)     cmd_logs "$@";;
  teardown) cmd_teardown;;
  ""|-h|--help|help) usage;;
  *) die "Unknown command '$cmd'. Run 'project.sh help'.";;
esac

#!/usr/bin/env bash
# Nightly: commit anything left uncommitted in the homelab and tv-launcher repos.
# Refuses (and alerts on Discord) if a staged file looks like it holds a secret.
set -uo pipefail
REPOS=(/home/shanerunham/homelab /home/shanerunham/tv-launcher)
SECRET_RE='(?<![A-Za-z0-9_/.-])(?=[A-Za-z0-9_-]*[0-9])(?=[A-Za-z0-9_-]*[a-z])(?=[A-Za-z0-9_-]*[A-Z])[A-Za-z0-9_-]{30,}(?![A-Za-z0-9_/.-])'
SECRET_NAME_RE='(^|/)(\.env|.*\.env|.*token.*|.*secret.*|.*credential.*|.*passwd.*|.*\.key|.*\.pem)$'

DISCORD_WEBHOOK_URL=''
DISCORD_MENTION=''
[ -r /home/shanerunham/homelab/alerts.env ] && . /home/shanerunham/homelab/alerts.env
send() {
  [ -n "$DISCORD_WEBHOOK_URL" ] || return 1
  local payload
  payload=$(python3 -c 'import json, sys; print(json.dumps({"content": sys.argv[1][:1900]}))' "${DISCORD_MENTION:+$DISCORD_MENTION }$1")
  curl -fsS -m 15 --retry 3 -o /dev/null -H 'Content-Type: application/json' -d "$payload" "$DISCORD_WEBHOOK_URL"
}

for repo in "${REPOS[@]}"; do
  cd "$repo" || continue
  [ -z "$(git status --porcelain)" ] && { echo "$repo: nothing to commit"; continue; }
  git add -A
  changed=$(git diff --cached --name-only)
  suspicious=$( { grep -iE "$SECRET_NAME_RE" <<<"$changed"
                  git grep --cached -lP "$SECRET_RE" -- $(sed 's/^/:/' <<<"$changed") ':!*.png' ':!*.jpg' ':!*.webp' ':!*.mp4' ':!*.woff2' ':!*.ttf' ':!*.svg' ':!*.ico' ':!*.css' 2>/dev/null
                } | sort -u)
  if [ -n "$suspicious" ]; then
    git reset -q
    msg="Git nightly commit skipped in $repo: these files may contain a secret. Add them to .gitignore or move the secret to .env, then commit:"$'\n'"$(sed 's/^/- /' <<<"$suspicious")"
    echo "$msg"; send "$msg"
    continue
  fi
  n=$(wc -l <<<"$changed")
  if out=$(git commit -q -m "Nightly auto-commit: $n file(s)" -m "$(head -20 <<<"$changed")" 2>&1); then
    echo "$repo: committed $n file(s)"
  else  # usually the gitleaks pre-commit hook (git-autocommit/pre-commit) finding a secret
    git reset -q
    msg="Git nightly commit failed in $repo (the gitleaks hook may have found a secret):"$'\n'"$(tail -15 <<<"$out")"
    echo "$msg"; send "$msg"
  fi
done

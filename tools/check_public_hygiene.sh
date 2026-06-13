#!/usr/bin/env bash
# Public-hygiene gate — fails if the public repo contains internal infra traces,
# secret-like content, or real-data/enterprise paths. Run by CI and by the
# pre-commit hook. Keep the PUBLIC core clean (see OPEN-CORE.md).
set -uo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root" || exit 2
self="tools/check_public_hygiene.sh"
fail=0

# 1) internal infra traces (this checker is excluded; it names the tokens itself)
if grep -rInIiE \
    --include='*.py' --include='*.md' --include='*.json' --include='*.jsonl' --include='*.toml' \
    --exclude-dir='.git' --exclude-dir='runs' --exclude-dir='__pycache__' \
    '\btalki|teacher:8010|\blitellm\b|\boctominer\b|\bfossod\b|\bdgx\b|idle-dgx|diffusiongemma|code-nvfp4|emma-eval|:9397|\b100\.1[0-9]{1,2}\.[0-9]|\b192\.168\.' \
    . ; then
  echo "FAIL(1): internal infra trace found"; fail=1
fi

# 2) secret-like content
if grep -rInIE \
    --exclude-dir='.git' --exclude-dir='runs' --exclude-dir='__pycache__' --exclude="$(basename "$self")" \
    'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ANTHROPIC_API_KEY=.' \
    . ; then
  echo "FAIL(2): secret-like content found"; fail=1
fi

# 3) real-data / enterprise directories must never be tracked
for d in corpora data datasets enterprise private; do
  if [ -d "$d" ] && [ -n "$(ls -A "$d" 2>/dev/null)" ]; then
    echo "FAIL(3): forbidden directory present and non-empty: $d/"; fail=1
  fi
done

# 4) every shipped data sample must be synthetic
for f in harness/sources/samples/*; do
  [ -e "$f" ] || continue
  if ! grep -q "_synthetic" "$f"; then
    echo "FAIL(4): sample not marked _synthetic: $f"; fail=1
  fi
done

[ "$fail" = 0 ] && echo "public-hygiene: OK"
exit "$fail"

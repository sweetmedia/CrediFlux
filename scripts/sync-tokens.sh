#!/usr/bin/env bash
# sync-tokens.sh — copy branding/ tokens and fonts into each app that consumes them.
#
# Source of truth: /opt/crediflux/branding/
# Destinations:
#   - /opt/crediflux/apps/landing/src/branding/    (Vite + Tailwind 4)
#   - /opt/crediflux/frontend/app/branding/         (Next.js + Tailwind 3)
#
# The apps import `branding/tokens.css` and resolve `@font-face` URLs relative
# to the copied `fonts/` subfolder. Both apps `.gitignore` their local copies
# because this script regenerates them on every build.
#
# Called by:
#   - Dev: `npm run dev` in both apps has a `predev` hook (added in F0 part 6).
#   - CI: Dockerfile.* runs this as the first RUN step before `npm ci`.
#   - Manual: `bash /opt/crediflux/scripts/sync-tokens.sh`
#
# Exit codes:
#   0 — success
#   1 — branding source directory missing
#   2 — one of the destination apps is missing
#   3 — rsync or cp failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SRC="${REPO_ROOT}/branding"

# Destinations — one per consuming app.
LANDING_DEST="${REPO_ROOT}/apps/landing/src/branding"
# Next.js App Router treats folders under app/ as route segments unless they
# start with `_`. Using `_branding` opts the folder out of routing so
# /branding is not accidentally served as a page.
DASHBOARD_DEST="${REPO_ROOT}/frontend/app/_branding"

# ------------------------------------------------------------------------------
# Pre-flight
# ------------------------------------------------------------------------------

if [[ ! -d "${SRC}" ]]; then
  echo "error: branding source directory not found at ${SRC}" >&2
  exit 1
fi

if [[ ! -f "${SRC}/tokens.css" ]]; then
  echo "error: ${SRC}/tokens.css is missing — run F0 setup first" >&2
  exit 1
fi

if [[ ! -d "${SRC}/fonts" ]]; then
  echo "error: ${SRC}/fonts/ is missing — run F0 setup first" >&2
  exit 1
fi

# At least one destination app must exist. If only one of the two is present
# (e.g., running from a fresh clone before apps/landing submodule is pulled),
# sync just that one and skip the other with a warning.
if [[ ! -d "${REPO_ROOT}/apps/landing" && ! -d "${REPO_ROOT}/frontend" ]]; then
  echo "error: neither apps/landing nor frontend/ exists under ${REPO_ROOT}" >&2
  exit 2
fi

# ------------------------------------------------------------------------------
# Sync helpers
# ------------------------------------------------------------------------------

sync_one() {
  local label="$1"
  local dest="$2"
  local parent
  parent="$(dirname "${dest}")"

  if [[ ! -d "${parent}" ]]; then
    echo "warn:  ${label} — parent directory ${parent} not found, skipping"
    return 0
  fi

  echo "==> ${label}"
  echo "    source: ${SRC}"
  echo "    dest:   ${dest}"

  mkdir -p "${dest}/fonts/display" "${dest}/fonts/mono"

  # tokens.css — single file, overwrite every run
  cp "${SRC}/tokens.css" "${dest}/tokens.css"

  # Fonts — only the .woff2 files that are actually needed.
  # Using explicit list instead of rsync so an accidental .otf in the source
  # never leaks into an app build.
  local display_fonts=(
    "ABCWhyte-Regular-Trial.woff2"
    "ABCWhyte-Medium-Trial.woff2"
    "ABCWhyte-Bold-Trial.woff2"
    "ABCWhyte-Black-Trial.woff2"
  )
  local mono_fonts=(
    "ABCWhyteMonoInktrapVariable-Trial.woff2"
  )

  for f in "${display_fonts[@]}"; do
    if [[ -f "${SRC}/fonts/display/${f}" ]]; then
      cp "${SRC}/fonts/display/${f}" "${dest}/fonts/display/${f}"
    else
      echo "warn:  ${label} — source font missing: ${f}"
    fi
  done

  for f in "${mono_fonts[@]}"; do
    if [[ -f "${SRC}/fonts/mono/${f}" ]]; then
      cp "${SRC}/fonts/mono/${f}" "${dest}/fonts/mono/${f}"
    else
      echo "warn:  ${label} — source font missing: ${f}"
    fi
  done

  # LICENSE.md — copy into fonts/ so the trial/commercial status travels with
  # the files themselves.
  if [[ -f "${SRC}/fonts/LICENSE.md" ]]; then
    cp "${SRC}/fonts/LICENSE.md" "${dest}/fonts/LICENSE.md"
  fi

  # Small README in each dest so humans who wander in know this is generated.
  cat > "${dest}/README.md" <<EOF
# Generated — do not edit

This directory is synchronized from \`/opt/crediflux/branding/\` by
\`scripts/sync-tokens.sh\`. Any change made here will be overwritten on the
next build or dev startup.

To change tokens, fonts, or the design system contract, edit the source at
\`/opt/crediflux/branding/\` and re-run \`bash scripts/sync-tokens.sh\` (or
let the \`predev\` npm hook do it automatically).

Font licensing: see \`fonts/LICENSE.md\`.
EOF

  echo "    ok"
}

# ------------------------------------------------------------------------------
# Run
# ------------------------------------------------------------------------------

echo "sync-tokens.sh — syncing CrediFlux branding to app consumers"
echo

if [[ -d "${REPO_ROOT}/apps/landing" ]]; then
  sync_one "landing (Vite + Tailwind 4)" "${LANDING_DEST}"
else
  echo "skip: apps/landing not found"
fi

if [[ -d "${REPO_ROOT}/frontend" ]]; then
  sync_one "dashboard (Next.js + Tailwind 3)" "${DASHBOARD_DEST}"
else
  echo "skip: frontend/ not found"
fi

echo
echo "done."

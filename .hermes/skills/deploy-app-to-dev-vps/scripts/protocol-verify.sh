#!/usr/bin/env bash
# protocol-verify.sh — verify a non-JSON endpoint's wire protocol against
# expectations. Built for calendar feeds (.ics), RSS, webhooks, CSV exports,
# or any endpoint that returns structured text/binary instead of JSON.
#
# The default validate_app.sh handles JSON endpoints (assert 2xx + jq field
# checks). This script handles everything else: response headers must match
# specific MIME types, body must contain specific markers (BEGIN/END blocks,
# XML envelope, binary magic bytes), revocation/lifecycle must work, etc.
#
# Usage:
#   ./scripts/protocol-verify.sh \
#     --url "https://app.example.com/api/feed.ics?token=$TOKEN" \
#     --expect-content-type "text/calendar" \
#     --expect-disposition-prefix "inline" \
#     --expect-body-starts-with "BEGIN:" \
#     --expect-body-ends-with "END:" \
#     --expect-crlf \
#     --revoke-url "https://app.example.com/api/feed.ics?token=$TOKEN" \
#     --revoke-expected-status 401 \
#     --label "calendar feed"
#
# Returns 0 on full PASS, non-zero on FAIL. Output is colored for terminal.

set -uo pipefail

LABEL="protocol endpoint"
URL=""
EXPECT_CT=""
EXPECT_DISP_PREFIX=""
EXPECT_BODY_STARTS=""
EXPECT_BODY_ENDS=""
EXPECT_CRLF=0
REVOKE_URL=""
REVOKE_EXPECT_STATUS=""
REVOKE_BODY_EXPECT=""
REQUIRE_CALLOUT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --url)                    URL="$2"; shift 2 ;;
    --expect-content-type)    EXPECT_CT="$2"; shift 2 ;;
    --expect-disposition-prefix) EXPECT_DISP_PREFIX="$2"; shift 2 ;;
    --expect-body-starts-with) EXPECT_BODY_STARTS="$2"; shift 2 ;;
    --expect-body-ends-with)  EXPECT_BODY_ENDS="$2"; shift 2 ;;
    --expect-crlf)            EXPECT_CRLF=1; shift ;;
    --revoke-url)             REVOKE_URL="$2"; shift 2 ;;
    --revoke-expected-status) REVOKE_EXPECT_STATUS="$2"; shift 2 ;;
    --revoke-body-expect)     REVOKE_BODY_EXPECT="$2"; shift 2 ;;
    --label)                  LABEL="$2"; shift 2 ;;
    --require-callout)        REQUIRE_CALLOUT="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$URL" ]; then
  echo "usage: $0 --url <URL> [options]" >&2
  exit 2
fi

PASS=0
FAIL=0

red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[1;33m%s\033[0m\n' "$*"; }
blue()   { printf '\033[0;34m%s\033[0m\n' "$*"; }

ok()   { green "  ✓ $*"; PASS=$((PASS+1)); }
fail() { red   "  ✗ $*"; FAIL=$((FAIL+1)); }

# ─── Fetch + capture headers + body ─────────────────────────────
TMP_BODY=$(mktemp)
trap "rm -f $TMP_BODY" EXIT

blue "── $LABEL ─────────────────────────────────────────────"

HDR_FILE=$(mktemp)
trap "rm -f $TMP_BODY $HDR_FILE" EXIT

HTTP_CODE=$(curl -sS -o "$TMP_BODY" -D "$HDR_FILE" -w '%{http_code}' \
  --max-time 15 "$URL" || echo "000")

# ─── Status code ───────────────────────────────────────────────
case "$HTTP_CODE" in
  2*) ok "status -> $HTTP_CODE" ;;
  *)  fail "status -> $HTTP_CODE (expected 2xx)" ;;
esac

# ─── Content-Type ───────────────────────────────────────────────
if [ -n "$EXPECT_CT" ]; then
  ACTUAL_CT=$(grep -i '^content-type:' "$HDR_FILE" | head -1 | tr -d '\r' | sed 's/^[Cc]ontent-[Tt]ype:[[:space:]]*//')
  case "$ACTUAL_CT" in
    "$EXPECT_CT"*) ok "content-type -> $ACTUAL_CT" ;;
    *)            fail "content-type -> '$ACTUAL_CT' (expected '$EXPECT_CT...')" ;;
  esac
fi

# ─── Content-Disposition prefix (inline vs attachment) ─────────
if [ -n "$EXPECT_DISP_PREFIX" ]; then
  ACTUAL_DISP=$(grep -i '^content-disposition:' "$HDR_FILE" | head -1 | tr -d '\r' | sed 's/^[Cc]ontent-[Dd]isposition:[[:space:]]*//')
  case "$ACTUAL_DISP" in
    "$EXPECT_DISP_PREFIX"*) ok "content-disposition -> $ACTUAL_DISP" ;;
    *)                     fail "content-disposition -> '$ACTUAL_DISP' (expected prefix '$EXPECT_DISP_PREFIX')" ;;
  esac
fi

# ─── Body markers (BEGIN/END blocks, XML envelope, etc.) ───────
if [ -n "$EXPECT_BODY_STARTS" ]; then
  FIRST_LINE=$(head -1 "$TMP_BODY" | tr -d '\r')
  case "$FIRST_LINE" in
    "$EXPECT_BODY_STARTS"*) ok "body starts with -> $FIRST_LINE" ;;
    *)                      fail "body starts with -> '$FIRST_LINE' (expected '$EXPECT_BODY_STARTS')" ;;
  esac
fi

if [ -n "$EXPECT_BODY_ENDS" ]; then
  LAST_LINE=$(tail -1 "$TMP_BODY" | tr -d '\r')
  case "$LAST_LINE" in
    "$EXPECT_BODY_ENDS"*) ok "body ends with -> $LAST_LINE" ;;
    *)                    fail "body ends with -> '$LAST_LINE' (expected '$EXPECT_BODY_ENDS')" ;;
  esac
fi

# ─── CRLF line endings (RFC 5545, MIME, HTTP/1.1 line-based protocols) ──
if [ "$EXPECT_CRLF" = "1" ]; then
  if grep -q $'\r' "$TMP_BODY"; then
    ok "CRLF line endings present"
  else
    fail "expected CRLF line endings (\\r\\n) — body uses LF only"
  fi
fi

# ─── Required substrings (e.g. specific fields, must-have values) ─
if [ -n "$REQUIRE_CALLOUT" ]; then
  IFS=',' read -ra NEEDLES <<< "$REQUIRE_CALLOUT"
  for needle in "${NEEDLES[@]}"; do
    if grep -qF "$needle" "$TMP_BODY"; then
      ok "body contains -> $needle"
    else
      fail "body missing -> $needle"
    fi
  done
fi

# ─── Revocation / lifecycle test ────────────────────────────────
if [ -n "$REVOKE_URL" ] && [ -n "$REVOKE_EXPECT_STATUS" ]; then
  blue "  ── revocation test ──"
  REV_CODE=$(curl -sS -o /dev/null -w '%{http_code}' \
    --max-time 15 "$REVOKE_URL" || echo "000")
  if [ "$REV_CODE" = "$REVOKE_EXPECT_STATUS" ]; then
    ok "post-revoke status -> $REV_CODE"
  else
    fail "post-revoke status -> $REV_CODE (expected $REVOKE_EXPECT_STATUS)"
  fi
  if [ -n "$REVOKE_BODY_EXPECT" ]; then
    REV_BODY=$(curl -sS --max-time 15 "$REVOKE_URL" || echo '')
    if echo "$REV_BODY" | grep -qF "$REVOKE_BODY_EXPECT"; then
      ok "post-revoke body contains -> $REVOKE_BODY_EXPECT"
    else
      fail "post-revoke body missing -> $REVOKE_BODY_EXPECT"
    fi
  fi
fi

echo
green "PASS: $PASS"
if [ "$FAIL" -gt 0 ]; then red "FAIL: $FAIL"; else echo "FAIL: 0"; fi
echo
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
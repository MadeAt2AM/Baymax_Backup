#!/usr/bin/env bash
# cf-dns.sh — Cloudflare DNS manager for terrybot.top
#
# Usage:
#   cf-dns.sh add <subdomain> [ip]    Create A record (defaults to VPS IP)
#   cf-dns.sh del <subdomain>          Delete A record
#   cf-dns.sh list                     List all A/CNAME records for the zone
#   cf-dns.sh get <subdomain>          Get specific record
#
# Credentials: read from ~/.hermes/.env
#   CF_API_TOKEN, CF_ZONE_ID, CF_DOMAIN

set -euo pipefail

ENV_FILE="${HERMES_HOME:-$HOME/.hermes}/.env"
[ -f "$ENV_FILE" ] || { echo "ERR: $ENV_FILE not found"; exit 1; }

# shellcheck disable=SC1090
source "$ENV_FILE"

: "${CF_API_TOKEN:?CF_API_TOKEN required}"
: "${CF_ZONE_ID:?CF_ZONE_ID required}"
: "${CF_DOMAIN:?CF_DOMAIN required}"

API="https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records"
DEFAULT_IP="147.79.18.32"

cf_curl() {
    local method="$1" path="$2" data="${3:-}"
    if [ -n "$data" ]; then
        curl -sS -X "$method" "${API}${path}" \
            -H "Authorization: Bearer ${CF_API_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -sS -X "$method" "${API}${path}" \
            -H "Authorization: Bearer ${CF_API_TOKEN}" \
            -H "Content-Type: application/json"
    fi
}

usage() {
    cat <<EOF
cf-dns.sh — manage A records for ${CF_DOMAIN}

  add <sub> [ip]    Create A record (defaults to ${DEFAULT_IP})
  del <sub>         Delete A record
  list              List all A records in zone
  get <sub>         Show record for a specific subdomain
EOF
    exit 1
}

cmd="${1:-}"; shift || true
sub="${1:-}"

case "$cmd" in
    add)
        [ -z "$sub" ] && usage
        ip="${2:-$DEFAULT_IP}"
        full="${sub}.${CF_DOMAIN}"
        resp=$(cf_curl GET "/?type=A&name=${full}")
        existing=$(echo "$resp" | jq -r '.result[0].id // empty')
        if [ -n "$existing" ]; then
            echo "EXISTS: $full already has record id $existing → $ip"
            echo "$resp" | jq -r '.result[] | "\(.name)\t\(.content)"'
            exit 0
        fi
        resp=$(cf_curl POST "" "{\"type\":\"A\",\"name\":\"${full}\",\"content\":\"${ip}\",\"ttl\":60,\"proxied\":false}")
        ok=$(echo "$resp" | jq -r '.success')
        if [ "$ok" = "true" ]; then
            echo "OK: created $full → $ip"
            echo "$resp" | jq -r '"id=\(.result.id) name=\(.result.name) content=\(.result.content)"'
        else
            echo "FAIL:"
            echo "$resp" | jq .
            exit 1
        fi
        ;;
    del)
        [ -z "$sub" ] && usage
        full="${sub}.${CF_DOMAIN}"
        resp=$(cf_curl GET "/?type=A&name=${full}")
        rid=$(echo "$resp" | jq -r '.result[0].id // empty')
        if [ -z "$rid" ]; then
            echo "NOT_FOUND: no A record for $full"
            exit 0
        fi
        resp=$(cf_curl DELETE "/${rid}" "")
        ok=$(echo "$resp" | jq -r '.success')
        if [ "$ok" = "true" ]; then
            echo "OK: deleted $full"
        else
            echo "FAIL:"
            echo "$resp" | jq .
            exit 1
        fi
        ;;
    list)
        cf_curl GET "?type=A" "" | jq -r '.result[] | "\(.name)\t\(.content)\tproxied=\(.proxied)"'
        ;;
    get)
        [ -z "$sub" ] && usage
        full="${sub}.${CF_DOMAIN}"
        cf_curl GET "/?type=A&name=${full}" "" | jq .
        ;;
    *)
        usage
        ;;
esac
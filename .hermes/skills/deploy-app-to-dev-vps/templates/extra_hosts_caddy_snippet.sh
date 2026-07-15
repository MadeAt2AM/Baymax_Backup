#!/usr/bin/env bash
# write_extra_caddy() — drop-in for <name>_dev.sh
#
# Materialise a separate Caddy site file for verified custom-domain hostnames.
# Sourced from /srv/secrets/<name>-custom-domains (one hostname per line,
# `#`-prefixed lines are comments). Each host becomes a site block that
# reverse-proxies to the same <name>-web container, so all the same security
# headers from the platform host apply and Let's Encrypt issues a per-host
# cert automatically.
#
# Why a separate file (vs. putting the hostnames in the platform-host site
# block label):
#   * Listed separately in /srv/caddy/sites/ — easier for an operator to
#     see which custom domains are in scope vs. the platform's own host.
#   * Editable in-place without a redeploy — touch
#     /srv/secrets/<name>-custom-domains, re-run this snippet, Caddy reload
#     picks it up.
#
# Usage in <name>_dev.sh:
#   write_caddy
#   write_extra_caddy       # ← add this line
#   ensure_dns
#   docker exec caddy caddy reload --config /etc/caddy/Caddyfile
#
# Also add to the `teardown` case:
#   rm -f "$Caddy_FILE" "/srv/caddy/sites/${PROJ_NAME}-extra-hosts.caddy"

write_extra_caddy() {
  local EXTRA_HOSTS_FILE="/srv/secrets/${PROJ_NAME}-custom-domains"
  local EXTRA_SITE_FILE="/srv/caddy/sites/${PROJ_NAME}-extra-hosts.caddy"

  # Seed an empty sidecar on first deploy so the operator knows where to add hosts.
  if [ ! -f "$EXTRA_HOSTS_FILE" ]; then
    yellow "  → seeding empty $EXTRA_HOSTS_FILE (one hostname per line for verified custom domains)"
    cat > "$EXTRA_HOSTS_FILE" <<'SEED'
# Verified custom-domain hostnames this deployment serves.
# One hostname per line; lines beginning with # are comments.
# Example:
#   login.acme.com
SEED
    chmod 644 "$EXTRA_HOSTS_FILE"
  fi

  # Build the per-host site blocks. Skip blank and comment lines.
  yellow "  → materialising extra-hosts site file from $EXTRA_HOSTS_FILE"
  : > "$EXTRA_SITE_FILE"
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"        # strip inline comments
    line="$(echo "$line" | xargs)"  # trim whitespace
    [ -z "$line" ] && continue
    cat >> "$EXTRA_SITE_FILE" <<EOF
${line} {
    reverse_proxy ${PROJ_NAME}-web:80

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
        Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=()"
        Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        Cross-Origin-Opener-Policy "same-origin"
        -X-Powered-By
        -Server
    }
}
EOF
  done < "$EXTRA_HOSTS_FILE"
  chmod 644 "$EXTRA_SITE_FILE"
}
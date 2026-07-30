# OpenReply-Specific Deployment Lessons

## SMTP Authentication
- The SMTP password for `support@madeat2am.in` must include the trailing period: `Cris0037.`
- SMTP host: `mail.cyberslide.net`, port: `587`, STARTTLS
- Always verify SMTP auth with a real `sendMail` test from inside the container using nodemailer with `logger:true`

## Webhook Signature Verification
- Meta/Instagram webhooks are signed with either:
  - Facebook App Secret (`FACEBOOK_APP_SECRET`) 
  - Instagram App Secret (`INSTAGRAM_APP_SECRET`)
  - NOT the webhook verify token (`WEBHOOK_VERIFY_TOKEN`)
- The verification logic must try both secrets and accept if either matches
- Signature format: `sha256=<hex_digest>` in `X-Hub-Signature-256` header

## Follow-Gate Logic (Require Follow)
- In DM worker, the follow status check must be: `sendFollowPrompt = alreadyFollows === false;`
- NOT: `sendFollowPrompt = alreadyFollows !== true;` (inverted logic)
- The follow-check endpoint properly handles three states:
  - `true` (follows) → deliver link/reward
  - `false` (doesn't follow) → show follow prompt  
  - `null` (unknown) → fail-open: deliver link (don't trap real followers)

## Database &bullMQ migration step when setting run: in the project or First run --rm migrate`

## Environment Variables
- Critical secrets must be set in both:
  - `/srv/secrets/openreply.env` (source of truth)
  - `/srv/projects/openreply/.env` (copied on first deploy, manual edits survive)
- Missing SMTP_PASSWORD will cause silent auth failures
- All Meta/Facebook secrets must be present for webhook verification to work

## Verification Steps
1. Check webhook endpoint responds to Meta's challenge:
   ```bash
   curl -sS "https://openreply.terrybot.top/api/webhook?hub.mode=subscribe&hub.verify_token=WXdSaVdY8UC5wdHY-vyK49pLH-_Z3Ewx&hub.challenge=12345"
   ```
   Should return `12345`

2. Verify webhook signature validation works by sending a test payload with correct HMAC-SHA256 signature using Facebook or Instagram app secret

3. Check worker logs for DM processing:
   ```bash
   docker logs --since 5m openreply-worker-1 | grep -iE 'dmLog|SENT|processComment'
   ```

4. Validate that automations have `requireFollow` set correctly in the database:
   ```sql
   SELECT id, name, require_follow FROM automations WHERE is_active = true;
   ```
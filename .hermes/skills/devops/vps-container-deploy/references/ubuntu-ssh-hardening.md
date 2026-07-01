# Hardening SSH on Ubuntu 24.04 cloud images

Cloud images ship with a config that re-enables password auth via a drop-in, even when you edit the main `sshd_config`. Here's the full procedure, including the gotcha that bit us during this session.

## The trap

Default Ubuntu 24.04 cloud image has these files in `/etc/ssh/`:

```
sshd_config                          # main config, passwordauth=no in our case
sshd_config.ucf-dist                 # dpkg backup, ignore
sshd_config.d/
├── 50-cloud-init.conf               # contains: PasswordAuthentication yes  ← THE TRAP
└── 60-cloudimg-settings.conf        # contains: PasswordAuthentication no   ← what we want
```

The main config has:
```
Include /etc/ssh/sshd_config.d/*.conf
```

Drop-ins are loaded in alphabetical order. **`50-*` beats `60-*`**. The cloud-init settings win on every boot.

So even if you `sed -i` the main config correctly:
```bash
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
```
…you get this from `sshd -T` (the live config):
```
passwordauthentication yes
```

## Steps to actually lock down SSH on a cloud image

1. **Identify the drop-ins:**
   ```bash
   ls /etc/ssh/sshd_config.d/
   for f in /etc/ssh/sshd_config.d/*.conf; do echo "[$f]"; cat "$f"; done
   ```

2. **Pick a policy and apply it to every drop-in:**
   ```bash
   # Option A: nuke the cloud-init drop-in entirely
   rm -f /etc/ssh/sshd_config.d/50-cloud-init.conf

   # Option B: rewrite it to match your policy
   sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' \
     /etc/ssh/sshd_config.d/*.conf
   ```

3. **Edit main config too (belt and braces):**
   ```bash
   sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
   sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
   ```

4. **Validate before reloading:**
   ```bash
   /usr/sbin/sshd -t && echo "syntax OK"
   ```

5. **Reload with the CORRECT service name.** Ubuntu uses `ssh.service`, not `sshd.service`. Use whichever matches the actual systemd unit:
   ```bash
   systemctl list-unit-files | grep -i ssh
   # output: ssh.service  (so use this:)
   systemctl reload ssh.service
   ```

6. **If reload didn't take effect (socket-activated services):**
   ```bash
   systemctl restart ssh.socket
   ```

7. **Verify with `sshd -T`, NOT file contents:**
   ```bash
   sshd -T | grep -E "^(passwordauthentication|permitrootlogin|pubkeyauthentication|kbdinteractive)"
   ```
   This reads the live config the running daemon is using. File contents can lie.

   **Expected hardened output:**
   ```
   passwordauthentication no
   permitrootlogin prohibit-password
   pubkeyauthentication yes
   kbdinteractiveauthentication no
   ```

## We did everything above — except step 1 and 2 first time around

Sequence was:
1. Generate SSH key on control VPS
2. Install pubkey on dev VPS
3. Test login — works
4. `sed` main config — looks correct
5. `systemctl reload sshd` — fails (wrong service name)
6. `sshd -T` reports `passwordauthentication yes` — wait what?
7. Check drop-ins, find `50-cloud-init.conf` — that's the override

Moral: **always check `/etc/ssh/sshd_config.d/` on cloud images before assuming lockdown took effect.**

## Why cloud images set `PasswordAuthentication yes`

Cloud-init's whole point is to allow first-boot access via password that's printed in the provider's console or sent via metadata service. After first-boot, you can disable it — but you have to know to look for the drop-in.

If you do NOT remove the drop-in before the provider rotates or revokes the password (common with rotating root passwords), you lose the ability to log in via password even with the right creds.

## Other hardening to consider while you're in there

- `PermitRootLogin prohibit-password` — allows root login with key, blocks password
- `PasswordAuthentication no` — already done
- `ChallengeResponseAuthentication no` — disables keyboard-interactive (often a back door via PAM)
- `KbdInteractiveAuthentication no` — alias for the above on newer OpenSSH
- `MaxAuthTries 3`
- `LoginGraceTime 30`
- `ClientAliveInterval 300`
- `ClientAliveCountMax 2`

Add these to a single drop-in like `99-hardening.conf` rather than scattering across the main config:

```bash
cat > /etc/ssh/sshd_config.d/99-hardening.conf <<EOF
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
MaxAuthTries 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
EOF
systemctl reload ssh.service
sshd -T | grep -E "maxauthtries|logingrace|clientalive"
```

## Disabling cloud-init's password rotation

Some providers run cloud-init on every boot, which re-runs the drop-in. To make `PasswordAuthentication no` survive reboots:

```bash
touch /etc/cloud/cloud-init.disabled
# or
cat > /etc/cloud/cloud.cfg.d/99-disable.cfg <<EOF
# Disable cloud-init runtime after first boot
cloud_init_modules: []
EOF
```

For our setup we don't need this — passwords never get set on the dev VPS, so nothing to rotate.

## The session-specific symptoms we hit

| What user pasted | What it actually meant |
|---|---|
| `Failed to reload sshd.service: Unit sshd.service not found.` | Service name is `ssh.service` on Ubuntu 24.04 |
| `permitrootlogin without-password` (from `sshd -T`) | This IS the same as `prohibit-password` in the file — different syntax between config file syntax and runtime output |
| `passwordauthentication yes` (from `sshd -T`) | Drop-in override still active — check `sshd_config.d/` |
| `who` showing only one session | Working as expected — we have one root session + ephemeral my-spawned SSH sessions |

## Recovery: how to get back in if you lock yourself out

The cleanest path is the provider's console/serial — it presents a virtual TTY that bypasses sshd entirely. From there you can fix any config and reboot.

If you don't have console access:

1. Provider's "snapshot before boot" recovery mode (some have this)
2. Reinstall OS (lose state)
3. Mount the disk from another VPS in the same datacenter (advanced)

This is also why we wrote the script to **test the lockdown worked before signing off** — the order matters:
1. Install key first
2. Verify key auth works
3. THEN disable password auth
4. THEN reload
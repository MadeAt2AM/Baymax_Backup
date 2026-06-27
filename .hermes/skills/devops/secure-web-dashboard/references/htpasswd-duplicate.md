# htpasswd Duplicate Entry — Silent Auth Failures

## Symptoms

- `curl -u user:pass https://domain/api/status` returns 401 intermittently
- `htpasswd -nb user pass` shows a DIFFERENT hash than what's in `/etc/nginx/.htpasswd`
- Multiple htpasswd entries for the same user:
  ```
  chrisspeaks:$apr1$YTJoaS3Y$NLMLYFRPO.Abb7/FYoBem/
  chrisspeaks:$apr1$I2O58.wT$v4QM7uKCIe.ciQ.aUWwug.   ← wrong password hash
  ```
- Nginx error log shows: `user "chrisspeaks": password mismatch`
- Browser Basic Auth popup appears on some requests but not others (race between correct and wrong entry)

## Root Cause

Running `htpasswd` without `-c` (create new file) but with a wrong initial run (or re-running create after an existing file had data) can append a second line instead of replacing. Also, running `htpasswd -c` on an existing file may not atomically replace it — there's a race condition where the old file isn't fully removed before the new one is written.

## Fix

Completely regenerate the htpasswd file with the correct credentials:
```bash
sudo htpasswd -c -b /etc/nginx/.htpasswd chrisspeaks Cris0037
```

Verify only one entry exists:
```bash
sudo cat /etc/nginx/.htpasswd
# Should show exactly one line: username:$apr1$...
```

Verify hash matches what you expect:
```bash
sudo htpasswd -nb chrisspeaks Cris0037
# Should match the hash in the file
```

## Prevention

Never run `htpasswd -c` on a non-empty file. Always check the file after creation:
```bash
sudo htpasswd -c -b /etc/nginx/.htpasswd user password
wc -l /etc/nginx/.htpasswd  # should be 1
```

To change an existing user's password (without recreating the file):
```bash
sudo htpasswd -b /etc/nginx/.htpasswd chrisspeaks NewPassword
```
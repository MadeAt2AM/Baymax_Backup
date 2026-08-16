import re

with open('/root/.hermes/config.yaml') as f:
    txt = f.read()
m = re.search(r'^model:\s*\n\s+default:\s*(\S+)', txt, re.M)
p = re.search(r'^model:\s*\n\s+provider:\s*(\S+)', txt, re.M)
b = re.search(r'^model:\s*\s*\n\s+base_url:\s*(\S+)', txt, re.M)
fb = len(re.findall(r'^  fallback_providers', txt))
ts = re.findall(r'^\s+-\s*(\S+)', txt)
ts = [t for t in ts if t not in ['fallback_providers', 'providers']]
sk = re.search(r'external_dirs:\s*\n(.*?)(?=\n\s+\w|\n\w|\n---)', txt, re.DOTALL)
print('  Default model:', m.group(1) if m else 'N/A')
print('  Provider:', p.group(1) if p else 'N/A')
print('  Base URL:', b.group(1) if b else 'N/A')
print('  Fallback providers:', fb)
print('  Toolsets count:', len(ts))
sk_dirs = [l.strip().strip('-').strip() for l in sk.group(1).split('\n') if l.strip()] if sk else []
print('  Skills external_dirs:', sk_dirs if sk_dirs else '[]')

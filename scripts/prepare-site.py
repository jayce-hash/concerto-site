"""Netlify build: pick up committed screenshots and regenerate public pages."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
for script in ('refresh-product-captures.py', 'rebuild-consumer-site.py',
               'prepare-app-utilities.py', 'apply-public-chrome.py'):
    subprocess.run([sys.executable, str(root/'scripts'/script)], cwd=root, check=True)
# The sitemap is built from the venue, tour, and setlist pages that exist, and those
# pages are generated above, during this build. Rebuild it here so every generated
# page is listed (the committed copy only knew about the pages committed to git).
subprocess.run([sys.executable, str(root/'build_sitemap.py')], cwd=root, check=True)

for script in ('validate-brand-system.js', 'validate-release.js', 'validate-deploy.js',
               'validate-seo.js', 'validate-links.js'):
    subprocess.run(['node', str(root/'scripts'/script)], cwd=root, check=True)
print('Public website and committed screenshots are ready to publish.')

"""Netlify build: pick up committed screenshots and regenerate public pages."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
for script in ('rebuild-consumer-site.py',
               'prepare-app-utilities.py', 'apply-public-chrome.py'):
    subprocess.run([sys.executable, str(root/'scripts'/script)], cwd=root, check=True)
for script in ('validate-brand-system.js', 'validate-release.js', 'validate-deploy.js',
               'validate-seo.js', 'validate-links.js'):
    subprocess.run(['node', str(root/'scripts'/script)], cwd=root, check=True)
print('Public website is ready to publish.')

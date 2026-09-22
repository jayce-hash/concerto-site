"""Encode supplied captures without repainting, cropping, or deleting assets."""
import hashlib
import io
import json
from pathlib import Path
try:
    from PIL import Image
except ImportError:
    Image = None

root = Path(__file__).resolve().parent.parent
output = root / 'img/product/screens'
manifest_path = output / 'manifest.json'
manifest = json.loads(manifest_path.read_text())
output.mkdir(parents=True, exist_ok=True)
for source in sorted((root / 'img/product/source').glob('*.png')):
    if Image:
        with Image.open(source) as original:
            buffer = io.BytesIO()
            original.convert('RGB').save(buffer, 'WEBP', quality=90, method=6)
            data = buffer.getvalue()
        ext = 'webp'
    else:
        # Standard-library-only deploys still pick up new captures. Keep PNG
        # pixels intact when WebP encoding is unavailable; never leave stale UI.
        data = source.read_bytes()
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError(f'{source.name} is not a PNG image')
        ext = 'png'
    filename = f'{source.stem}.{hashlib.sha256(data).hexdigest()[:12]}.{ext}'
    (output / filename).write_bytes(data)
    manifest[source.stem] = filename
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
print('Updated supplied captures; existing keys and previous images preserved.')

"""Builds the website's Help Center body from the app's Help screen (app/help.tsx), so the
two always say the same thing. Run: python3 scripts/sync_help_from_app.py /path/to/concerto-native
Then run site_v8.py as usual (it keeps help.html's body as written)."""
import re, sys, html, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
src = Path(sys.argv[1], 'app/help.tsx').read_text()

def js_str(m):
    raw = m
    return json.loads('"' + raw.replace('\\\'', "'").replace('"', '\\"') + '"') if raw is not None else ''

def strings(block, key):
    out = []
    for m in re.finditer(key + r":\s*(['\"])((?:\\.|(?!\1).)*)\1", block):
        out.append(js_str(m.group(2)))
    return out

journey_block = src[src.index('export const JOURNEY'):src.index('const SECTIONS')]
journey = list(zip(strings(journey_block, 'title'), strings(journey_block, 'body')))
start_key = 'const ALL_SECTIONS' if 'const ALL_SECTIONS' in src else 'const SECTIONS'
end_key = '// Partners and Perks stay out' if '// Partners and Perks stay out' in src else 'export default function Help'
sec_block = src[src.index(start_key):src.index(end_key)]
features = Path(sys.argv[1], 'src/lib/features.ts')
partners_visible = features.exists() and 'PARTNERS_VISIBLE = true' in features.read_text()
sections = []
for part in re.split(r"\n  \{\n    title:", sec_block)[1:]:
    title = js_str(re.match(r"\s*(['\"])((?:\\.|(?!\1).)*)\1", part).group(2))
    qs, as_ = strings(part, 'q'), strings(part, 'a')
    if title == 'Partners and Perks' and not partners_visible: continue
    sections.append((title, list(zip(qs, as_))))

e = lambda t: html.escape(t, quote=False).replace("'", '&#8217;')
aside = '<aside><p>Browse topics</p><a href="#how">How Concerto Works</a>' + ''.join(f'<a href="#help-{i}">{e(t)}</a>' for i, (t, _) in enumerate(sections)) + '<a href="mailto:support@concertocity.com?subject=Concerto%20Support">Email support →</a></aside>'
how = '<section id="how"><p>Start here</p><h2>How Concerto Works</h2><ol class="c-journey">' + ''.join(f'<li><b>{e(t)}</b><span>{e(b)}</span></li>' for t, b in journey) + '</ol></section>'
secs = ''.join(f'<section id="help-{i}"><p>{e(t)}</p><h2>{e(t)}</h2>' + ''.join(f'<details><summary>{e(q)}<span>+</span></summary><div><p>{e(a)}</p></div></details>' for q, a in items) + '</section>' for i, (t, items) in enumerate(sections))
tail = '<section><p>Still stuck?</p><h2>Talk to a real person.</h2><p>Tell us what you were doing, what you expected to happen, and what you saw instead.</p><a href="mailto:support@concertocity.com?subject=Concerto%20Support">support@concertocity.com</a></section>'
body = f'<section><div>{aside}<div>{how}{secs}{tail}</div></div></section>'

p = ROOT / 'help.html'
h = p.read_text()
start = h.index('<div class="c-wrap c-doc">') + len('<div class="c-wrap c-doc">')
end = h.rindex('</div></section></main>')
h = h[:start] + body + h[end:]
h = h.replace('<p class="c-lead">How Concerto works, from saving your first show to Your Night, Concerto+, and account controls.</p>',
              '<p class="c-lead">How Concerto works, in the order you&#8217;ll use it: find a show, save it, use Your Night, keep the night, and Concerto+ when you want more.</p>')
p.write_text(h)
print(f'help.html: {len(journey)} steps, {len(sections)} sections, {sum(len(x) for _, x in sections)} answers')

const assert = require('node:assert/strict');
const { livePerks } = require('../netlify/functions/lib/perk-rules');
const today = '2026-09-21';
const perk = { id: 'test', offer: 'Coffee with dinner', details: 'Show this offer with a paid dinner.', starts_on: today, ends_on: today, url: 'https://example.com/book' };
assert.equal(livePerks([perk], today).length, 1);
for (const change of [{ offer: '' }, { details: ' ' }, { starts_on: '2026-09-22' }, { ends_on: '2026-09-20' }, { starts_on: '2026-02-30' }, { ends_on: 'bad' }]) assert.equal(livePerks([{ ...perk, ...change }], today).length, 0);
assert.equal(livePerks([{ ...perk, url: 'javascript:alert(1)' }], today)[0].url, null);
assert.equal(livePerks([{ ...perk, url: 'https://user:pass@example.com' }], today)[0].url, null);

// Exercise all endpoint paths against a fake database, with no account/network access.
const Module = require('module'), original = Module._load;
let fail = false;
const current = new Date().toISOString().slice(0, 10);
const db = { from(table) {
  const q = { then(resolve) { return Promise.resolve(resolve(fail ? { error: new Error('unavailable') } : { data: table === 'perks' ? [{ ...perk, starts_on: current, ends_on: current }, { ...perk, starts_on: '2099-01-01' }, { ...perk, ends_on: '2000-01-01' }] : table === 'partner_orgs' ? [] : [] })); } };
  for (const method of ['select', 'eq', 'contains', 'gte', 'order', 'limit', 'in', 'maybeSingle']) q[method] = () => q;
  return q;
} };
Module._load = function (name, ...args) { return name === '@supabase/supabase-js' ? { createClient: () => db } : original.call(this, name, ...args); };
const { handler } = require('../netlify/functions/partner-content'); Module._load = original;
(async () => {
  for (const query of [{ all: '1' }, { venue: 'example' }, { tour: 'example' }]) {
    const response = await handler({ queryStringParameters: query });
    assert.equal(response.statusCode, 200); assert.equal(JSON.parse(response.body).perks.length, 1);
  }
  fail = true;
  const response = await handler({ queryStringParameters: { all: '1' } });
  assert.equal(response.statusCode, 503); assert.equal(response.headers['Cache-Control'], 'no-store');
  console.log('PASS: Perks API | all/venue/tour date filtering, real benefits, safe links, unavailable state');
})().catch(error => { console.error(error); process.exitCode = 1; });

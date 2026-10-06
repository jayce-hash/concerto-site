// Perk redemption: short-lived signed codes the fan's app shows, checked by the partner's staff
// with any phone camera. Codes are signed with a server-only secret, expire fast, and a fan can
// redeem a Perk once per day. Screenshots fail because the code expires within seconds.
const crypto = require('crypto');
const SCAN_MS = 45 * 1000;          // a code on screen is good for 45 seconds
const CLAIM_MS = 5 * 60 * 1000;     // after scanning, staff have 5 minutes to enter the 4-digit code
const key = () => crypto.createHash('sha256').update('perk-codes:' + String(process.env.SUPABASE_SERVICE_ROLE_KEY || 'x')).digest();
const b64 = (s) => Buffer.from(s).toString('base64url');
function sign(payload) {
  const body = b64(JSON.stringify(payload));
  return body + '.' + crypto.createHmac('sha256', key()).update(body).digest('base64url');
}
function verify(token) {
  const [body, sig] = String(token || '').split('.');
  if (!body || !sig) return null;
  const want = crypto.createHmac('sha256', key()).update(body).digest('base64url');
  if (want.length !== sig.length || !crypto.timingSafeEqual(Buffer.from(want), Buffer.from(sig))) return null;
  try { return JSON.parse(Buffer.from(body, 'base64url').toString()); } catch { return null; }
}
const scanToken = (perkId, fan) => sign({ k: 'scan', p: perkId, f: fan, e: Date.now() + SCAN_MS, n: crypto.randomBytes(6).toString('hex') });
const claimToken = (scan) => sign({ k: 'claim', p: scan.p, f: scan.f, e: Date.now() + CLAIM_MS, n: scan.n });
const hashCode = (orgId, code) => crypto.createHash('sha256').update(String(orgId) + ':' + String(code)).digest('hex');
const today = () => new Date().toISOString().slice(0, 10);
module.exports = { scanToken, claimToken, verify, hashCode, today, SCAN_MS };

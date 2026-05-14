// ─────────────────────────────────────────
// CONCERTO AUTH LIBRARY
// Include on every page: <script src="auth.js"></script>
// Replace the two config values below with your own.
// ─────────────────────────────────────────

const CONCERTO_CONFIG = {
  supabaseUrl:  'YOUR_SUPABASE_URL',   // e.g. https://xxxx.supabase.co
  supabaseKey:  'YOUR_SUPABASE_ANON_KEY',
  stripeMonthlyUrl: 'YOUR_STRIPE_MONTHLY_CHECKOUT_URL',
  stripeAnnualUrl:  'YOUR_STRIPE_ANNUAL_CHECKOUT_URL',
};

// Load Supabase client from CDN (included via script tag on each page)
function getSupabase() {
  if (window._supabaseClient) return window._supabaseClient;
  window._supabaseClient = supabase.createClient(
    CONCERTO_CONFIG.supabaseUrl,
    CONCERTO_CONFIG.supabaseKey
  );
  return window._supabaseClient;
}

// ─── Auth helpers ───────────────────────

async function getCurrentUser() {
  const { data: { user } } = await getSupabase().auth.getUser();
  return user;
}

async function getProfile() {
  const user = await getCurrentUser();
  if (!user) return null;
  const { data } = await getSupabase()
    .from('profiles')
    .select('*')
    .eq('id', user.id)
    .single();
  return data;
}

async function signUp(email, password, displayName) {
  const { data, error } = await getSupabase().auth.signUp({
    email, password,
    options: { data: { display_name: displayName } }
  });
  if (!error && data.user) {
    await getSupabase().from('profiles').update({ display_name: displayName }).eq('id', data.user.id);
  }
  return { data, error };
}

async function signIn(email, password) {
  return await getSupabase().auth.signInWithPassword({ email, password });
}

async function signInWithGoogle() {
  return await getSupabase().auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin + '/account.html' }
  });
}

async function signInWithApple() {
  return await getSupabase().auth.signInWithOAuth({
    provider: 'apple',
    options: { redirectTo: window.location.origin + '/account.html' }
  });
}

async function signOut() {
  await getSupabase().auth.signOut();
  window.location.href = 'index.html';
}

async function resetPassword(email) {
  return await getSupabase().auth.resetPasswordForEmail(email, {
    redirectTo: window.location.origin + '/account.html?reset=true'
  });
}

// ─── Profile updates ─────────────────────

async function updateProfile(updates) {
  const user = await getCurrentUser();
  if (!user) return;
  return await getSupabase().from('profiles').update(updates).eq('id', user.id);
}

async function toggleFavorite(field, value) {
  // field: 'favorite_artists' | 'favorite_venues' | 'favorite_tours' | 'saved_cities'
  const profile = await getProfile();
  if (!profile) return;
  const current = profile[field] || [];
  const updated = current.includes(value)
    ? current.filter(v => v !== value)
    : [...current, value];
  await updateProfile({ [field]: updated });
  return updated;
}

async function isFavorite(field, value) {
  const profile = await getProfile();
  if (!profile) return false;
  return (profile[field] || []).includes(value);
}

// ─── Premium checkout ─────────────────────

async function startCheckout(tier) {
  const user = await getCurrentUser();
  if (!user) { window.location.href = 'login.html?next=premium'; return; }
  // Pass user ID to Stripe via URL param (your checkout link should include client_reference_id)
  const base = tier === 'annual' ? CONCERTO_CONFIG.stripeAnnualUrl : CONCERTO_CONFIG.stripeMonthlyUrl;
  window.location.href = `${base}?client_reference_id=${user.id}&prefilled_email=${encodeURIComponent(user.email)}`;
}

// ─── Nav update (call on every page) ─────

async function updateNavForAuth() {
  const user = await getCurrentUser();
  const ctaEl = document.querySelector('.nav-cta');
  if (!ctaEl) return;
  if (user) {
    const profile = await getProfile();
    const name = profile?.display_name || user.email.split('@')[0];
    const isPremium = profile?.is_premium;
    ctaEl.innerHTML = `
      <a href="account.html" class="nav-account-btn">
        <span class="nav-account-avatar">${name.charAt(0).toUpperCase()}</span>
        <span class="nav-account-name">${name}</span>
        ${isPremium ? '<span class="nav-premium-badge">Premium</span>' : ''}
      </a>`;
  }
  // If not logged in, keep "Download the App" button as-is
}

// Auto-run nav update
document.addEventListener('DOMContentLoaded', updateNavForAuth);

// ─── Auth guard (redirect if not logged in) ─────

async function requireAuth(redirectTo) {
  const user = await getCurrentUser();
  if (!user) {
    window.location.href = `login.html?next=${encodeURIComponent(redirectTo || window.location.pathname)}`;
  }
  return user;
}

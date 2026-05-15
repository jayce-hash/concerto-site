// ─────────────────────────────────────────
// CONCERTO AUTH LIBRARY
// Include on every page: <script src="auth.js"></script>
// Replace the two config values below with your own.
// ─────────────────────────────────────────

const CONCERTO_CONFIG = {
  supabaseUrl:  'https://qgvukssbtfkbvahaiejm.supabase.co',
  supabaseKey:  'sb_publishable_xuc86SqqrndgPMj5ToBuvw_EHDkRwYY',
  stripeMonthlyUrl: 'https://buy.stripe.com/14A7sL39K4xA63x3NraAw00',
  stripeAnnualUrl:  'https://buy.stripe.com/7sY28reSsaVYeA3es5aAw01',
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
    options: {
      data: { display_name: displayName },
      emailRedirectTo: window.location.origin + '/login.html'
    }
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
  if (!user) {
    // Not logged in — send to login, then return to premium page with tier remembered
    window.location.href = `login.html?next=${encodeURIComponent('premium.html?checkout=' + tier)}`;
    return;
  }
  const base = tier === 'annual' ? CONCERTO_CONFIG.stripeAnnualUrl : CONCERTO_CONFIG.stripeMonthlyUrl;
  window.location.href = `${base}?client_reference_id=${user.id}&prefilled_email=${encodeURIComponent(user.email)}`;
}

// ─── Nav update (call on every page) ─────

async function updateNavForAuth() {
  const user = await getCurrentUser();
  if (!user) return;

  const profile = await getProfile();
  const name = profile?.display_name || user.email.split('@')[0];
  const isPremium = profile?.is_premium;
  const initial = name.charAt(0).toUpperCase();

  // Update desktop Sign In link → styled avatar
  const authLink = document.getElementById('navAuthLink');
  if (authLink) {
    authLink.textContent = '';
    authLink.href = 'account.html';
    authLink.setAttribute('aria-label', 'My Account');
    authLink.style.cssText = [
      'display:inline-flex',
      'align-items:center',
      'justify-content:center',
      'width:36px',
      'height:36px',
      'border-radius:50%',
      'font-family:var(--body)',
      'font-size:0.75rem',
      'font-weight:700',
      'text-decoration:none',
      'transition:all 0.2s',
      isPremium
        ? 'background:rgba(201,168,76,0.1);border:2px solid #C9A84C;color:#C9A84C;'
        : 'background:rgba(18,30,54,0.06);border:2px solid #121E36;color:#121E36;'
    ].join(';');
    authLink.textContent = initial;
  }

  // Update mobile auth link
  const mobileAuth = document.getElementById('navMobileAuthLink');
  if (mobileAuth) {
    mobileAuth.textContent = 'My Account';
    mobileAuth.href = 'account.html';
  }

  // Update profile icon (mobile)
  const profileIcon = document.getElementById('navProfileIcon');
  if (profileIcon) {
    profileIcon.href = 'account.html';
    profileIcon.setAttribute('aria-label', 'My Account');
    if (isPremium) {
      profileIcon.style.borderColor = '#C9A84C';
      profileIcon.style.color = '#C9A84C';
    } else {
      profileIcon.style.borderColor = '#121E36';
      profileIcon.style.color = '#121E36';
    }
  }
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

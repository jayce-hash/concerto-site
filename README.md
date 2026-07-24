# Site additions for the native app

netlify/functions/delete-account.js: drop into the site repo and
deploy. Powers in-app account deletion (required for App Store
review). Uses the same SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY env
vars the other functions already have. Until deployed, the app falls
back to a support email flow.

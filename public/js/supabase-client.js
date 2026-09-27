// Initializes the shared Supabase client. Loaded after config.js and the
// Supabase JS CDN script on every page.
(function () {
  var cfg = window.PHALANX_CONFIG || {};
  if (!cfg.SUPABASE_URL || cfg.SUPABASE_URL.indexOf("YOUR-PROJECT-REF") !== -1) {
    console.warn("Phalanx League: Supabase is not configured yet. Edit public/js/config.js.");
  }
  window.sb = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
})();

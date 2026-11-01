// Only server-created Paddle transactions may open checkout.
(function () {
  var txn = new URLSearchParams(window.location.search).get('_ptxn');
  if (!txn) return;
  var errorBox = document.getElementById('checkout-error');
  function fail() { if (errorBox) errorBox.hidden = false; }
  if (!/^txn_[a-z0-9]{26}$/.test(txn)) { fail(); return; }
  try {
    var cfgEl = document.getElementById('paddle-config');
    var cfg = cfgEl && JSON.parse(cfgEl.textContent);
    if (!cfg || !cfg.client_token || !window.Paddle) { fail(); return; }
    if (cfg.env === 'sandbox') window.Paddle.Environment.set('sandbox');
    // Paddle.js automatically opens the transaction identified by _ptxn.
    window.Paddle.Initialize({ token: cfg.client_token });
  } catch (e) { fail(); }
})();

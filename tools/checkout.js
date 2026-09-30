// BidBell plan page (/subscribe/): highlights the plan named in ?plan=monthly|yearly and opens Paddle's overlay
// checkout. The settings (Paddle environment, client-side token, price ids) come from tools/paddle.json, which the
// build writes into the page. Without those settings the page has no checkout buttons and this only highlights.
(function () {
  var params = new URLSearchParams(window.location.search);
  var plan = (params.get('plan') || '').toLowerCase() === 'yearly' ? 'yearly' : 'monthly';

  document.querySelectorAll('[data-plan]').forEach(function (card) {
    var on = card.getAttribute('data-plan') === plan;
    card.classList.toggle('best', on);
    var btn = card.querySelector('[data-checkout]');
    if (btn) btn.classList.toggle('ghost', !on);
  });

  var cfgEl = document.getElementById('paddle-config');
  if (!cfgEl) return;
  var cfg = JSON.parse(cfgEl.textContent);
  var errorBox = document.getElementById('checkout-error');
  var errorHTML = errorBox.innerHTML;
  var c = params.get('c') || '';
  var ready = false;
  var busy = false;

  // Setting the text again (not only un-hiding the box) makes screen readers announce it.
  function showError(scroll) {
    errorBox.innerHTML = '';
    errorBox.hidden = false;
    errorBox.innerHTML = errorHTML;
    if (scroll) {
      var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      errorBox.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' });
    }
  }

  try {
    if (window.Paddle) {
      if (cfg.env === 'sandbox') window.Paddle.Environment.set('sandbox');
      window.Paddle.Initialize({ token: cfg.client_token });
      ready = true;
    }
  } catch (e) { ready = false; }
  // Paddle.js is loaded (deferred) before this file, so if it is missing now it did not load: say so straight away
  // instead of waiting for a click.
  if (!ready) showError(false);

  document.querySelectorAll('[data-checkout]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (busy) return;   // a double click opens one checkout, not two
      var priceId = cfg.prices[btn.getAttribute('data-checkout')];
      if (!ready || !priceId) { showError(true); return; }
      errorBox.hidden = true;
      var options = { items: [{ priceId: priceId, quantity: 1 }] };
      // Only a well-formed BidBell customer id is passed on to Paddle.
      if (/^[a-z0-9-]{1,60}$/.test(c)) options.customData = { subscriber_id: c };
      options.settings = { displayMode: 'overlay', successUrl: cfg.success_url };
      // For two seconds the button says what is happening and ignores more clicks (Paddle's window takes a moment).
      var label = btn.textContent;
      busy = true;
      btn.setAttribute('aria-busy', 'true');
      btn.textContent = 'Opening secure checkout…';
      var done = function () { busy = false; btn.removeAttribute('aria-busy'); btn.textContent = label; };
      setTimeout(done, 2000);
      try { window.Paddle.Checkout.open(options); } catch (e) { done(); showError(true); }
    });
  });
})();

// BidBell plan page (/subscribe/): highlights the plan named in ?plan=monthly|yearly and opens Paddle's overlay
// checkout. The settings (Paddle environment, client-side token, price ids) come from tools/paddle.json, which the
// build writes into the page. Without those settings the page has no checkout buttons and this only highlights.
(function () {
  var params = new URLSearchParams(window.location.search);
  var plan = params.get('plan') === 'yearly' ? 'yearly' : 'monthly';

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
  var c = params.get('c') || '';
  var ready = false;

  try {
    if (window.Paddle) {
      if (cfg.env === 'sandbox') window.Paddle.Environment.set('sandbox');
      window.Paddle.Initialize({ token: cfg.client_token });
      ready = true;
    }
  } catch (e) { ready = false; }

  document.querySelectorAll('[data-checkout]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      errorBox.hidden = true;
      var priceId = cfg.prices[btn.getAttribute('data-checkout')];
      if (!ready || !priceId) {
        errorBox.hidden = false;
        errorBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      var options = { items: [{ priceId: priceId, quantity: 1 }] };
      // Only a well-formed BidBell customer id is passed on to Paddle.
      if (/^[a-z0-9-]{1,60}$/.test(c)) options.customData = { subscriber_id: c };
      options.settings = { displayMode: 'overlay', successUrl: cfg.success_url };
      window.Paddle.Checkout.open(options);
    });
  });
})();

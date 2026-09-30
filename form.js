// BidBell sign-up form: checks the answers, sends them to BidBell's Google Form in the background,
// then shows the thank-you page on getbidbell.com. Without JavaScript the form still posts normally.
(function () {
  var form = document.getElementById('signup');
  if (!form) return;
  var box = document.getElementById('form-error');

  function problem(msg, focusEl) {
    box.textContent = msg;
    box.hidden = false;
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (focusEl) focusEl.focus({ preventScroll: true });
  }

  // "Nationwide" and individual states: picking Nationwide clears the states, and the other way round.
  var states = form.querySelectorAll('.state-box input');
  var all = form.querySelector('.state-box .all input');
  states.forEach(function (cb) {
    cb.addEventListener('change', function () {
      if (!cb.checked) return;
      if (cb === all) states.forEach(function (o) { if (o !== all) o.checked = false; });
      else if (all) all.checked = false;
    });
  });

  form.addEventListener('submit', function (ev) {
    box.hidden = true;
    var groups = form.querySelectorAll('fieldset[data-need]');
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i];
      var picked = g.querySelectorAll('input[type=checkbox]:checked').length;
      if (picked < 1) { ev.preventDefault(); problem('Please choose ' + g.dataset.label + '.', g.querySelector('input')); return; }
      if (g.dataset.max && picked > +g.dataset.max) { ev.preventDefault(); problem('Please choose up to ' + g.dataset.max + ' states, or Nationwide.', g.querySelector('input')); return; }
    }
    if (!window.fetch || !window.URLSearchParams) return;   // old browser: normal post to Google
    ev.preventDefault();
    var btn = form.querySelector('button[type=submit]');
    btn.disabled = true;
    btn.textContent = 'Sending…';
    var body = new URLSearchParams(new FormData(form));
    fetch(form.action, { method: 'POST', mode: 'no-cors', body: body })
      .then(function () { window.location.href = form.dataset.thanks; })
      .catch(function () { form.submit(); });   // network hiccup: fall back to a normal post
  });
})();

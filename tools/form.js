// BidBell sign-up form: checks the answers, sends them to BidBell's Google Form in the background,
// then shows the thank-you page on getbidbell.com. Without JavaScript the form still posts normally.
(function () {
  var form = document.getElementById('signup');
  if (!form) return;
  var box = document.getElementById('form-error');
  var btn = form.querySelector('button[type=submit]');
  var btnHTML = btn.innerHTML;

  // Shows the message next to the question it is about (or at the top of the form), scrolls that question
  // into view and puts the keyboard focus on its first choice.
  function problem(msg, group) {
    var where = (group && group.querySelector('.field-error')) || box;
    where.textContent = msg;
    where.hidden = false;
    if (group) {
      group.classList.add('invalid');
      group.setAttribute('aria-describedby', (group.getAttribute('aria-describedby') || '').replace(where.id, '').trim() + ' ' + where.id);
    }
    var target = group || where;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    target.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    var first = group && group.querySelector('input');
    if (first) first.focus({ preventScroll: true });
  }

  function clearProblem(group) {
    var e = group.querySelector('.field-error');
    if (e && !e.hidden) { e.hidden = true; e.textContent = ''; }
    group.classList.remove('invalid');
  }

  // "Nationwide" and individual states: picking Nationwide clears the states, and the other way round.
  // A live line under the list says how many states are chosen.
  var states = form.querySelectorAll('.state-box input');
  var all = form.querySelector('.state-box .all input');
  var count = document.getElementById('state-count');
  var stateGroup = form.querySelector('fieldset[data-max]');
  var max = stateGroup ? +stateGroup.dataset.max : 10;
  function showCount() {
    if (!count) return;
    var n = 0;
    states.forEach(function (o) { if (o !== all && o.checked) n++; });
    count.classList.toggle('over', n > max);
    count.textContent = all && all.checked ? 'Nationwide: every state is included.'
      : n === 0 ? 'No states chosen yet.'
      : n > max ? n + ' states chosen. Please remove ' + (n - max) + ' (up to ' + max + '), or choose Nationwide.'
      : n + ' of ' + max + ' states chosen.';
  }
  states.forEach(function (cb) {
    cb.addEventListener('change', function () {
      if (cb.checked) {
        if (cb === all) states.forEach(function (o) { if (o !== all) o.checked = false; });
        else if (all) all.checked = false;
      }
      showCount();
    });
  });
  showCount();

  // A group's error goes away as soon as a choice is made in it.
  form.querySelectorAll('fieldset[data-need]').forEach(function (g) {
    g.addEventListener('change', function () {
      var picked = g.querySelectorAll('input[type=checkbox]:checked').length;
      if (picked >= 1 && (!g.dataset.max || picked <= +g.dataset.max)) clearProblem(g);
    });
  });

  // Coming back to this page with the Back button: make the button usable again.
  window.addEventListener('pageshow', function () { btn.disabled = false; btn.innerHTML = btnHTML; });

  form.addEventListener('submit', function (ev) {
    box.hidden = true;
    var groups = form.querySelectorAll('fieldset[data-need]');
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i];
      var picked = g.querySelectorAll('input[type=checkbox]:checked').length;
      if (picked < 1) { ev.preventDefault(); problem('Please choose ' + g.dataset.label + '.', g); return; }
      if (g.dataset.max && picked > +g.dataset.max) { ev.preventDefault(); problem('Please choose up to ' + g.dataset.max + ' states, or Nationwide.', g); return; }
      clearProblem(g);
    }
    if (!window.fetch || !window.URLSearchParams) return;   // old browser: normal post to Google
    ev.preventDefault();
    if (btn.disabled) return;
    btn.disabled = true;
    btn.textContent = 'Sending…';
    var body = new URLSearchParams(new FormData(form));
    fetch(form.action, { method: 'POST', mode: 'no-cors', body: body })
      .then(function () { window.location.href = form.dataset.thanks; })
      .catch(function () { form.submit(); });   // network hiccup: fall back to a normal post
  });
})();

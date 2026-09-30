// BidBell phone menu (the ☰ button in the header on small screens). It works without this file; this only closes it
// after a link is tapped, on Escape, or on a tap outside it.
(function () {
  var menu = document.querySelector('.site-head .menu');
  if (!menu) return;
  menu.addEventListener('click', function (e) { if (e.target.closest('a')) menu.open = false; });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && menu.open) { menu.open = false; menu.querySelector('summary').focus(); }
  });
  document.addEventListener('click', function (e) { if (menu.open && !menu.contains(e.target)) menu.open = false; });
})();

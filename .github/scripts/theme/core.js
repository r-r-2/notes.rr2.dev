/* Every page: theme toggle, "New" tags, back-to-top button. */
(function () {
  var root = document.documentElement;

  var toggle = document.getElementById('nr-toggle');
  if (toggle) toggle.addEventListener('click', function () {
    var dark = root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    root.dataset.theme = dark ? 'light' : 'dark';
    try { localStorage.setItem('nr-theme', root.dataset.theme); } catch (e) {}
  });

  // Notes from the last 3 days get a "New" tag, worked out in the visitor's
  // own calendar so the tag never goes stale between pushes.
  var today = new Date(); today.setHours(0, 0, 0, 0);
  document.querySelectorAll('[data-fresh]').forEach(function (el) {
    var age = Math.round((today - new Date(el.getAttribute('data-fresh') + 'T00:00:00')) / 864e5);
    if (age >= 0 && age <= 3) el.classList.add('is-new');
  });

  var top = document.getElementById('nr-toplink');
  if (top) {
    var onScroll = function () { top.classList.toggle('on', scrollY > 700); };
    addEventListener('scroll', onScroll, { passive: true }); onScroll();
  }
})();

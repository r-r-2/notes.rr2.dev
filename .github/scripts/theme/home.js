/* Homepage: section chips that filter the archive, and the Recent posts carousel. */
(function () {
  // ---- Section chips ----
  var chips = document.querySelectorAll('.nr-chips [data-f]');
  function filter(f) {
    if (!f || !document.querySelector('.nr-chips [data-f="' + f + '"]')) f = 'all';
    chips.forEach(function (c) { c.toggleAttribute('aria-current', c.dataset.f === f); });
    document.querySelectorAll('.nr-month li[data-sec]').forEach(function (li) { li.hidden = f !== 'all' && li.dataset.sec !== f; });
    document.querySelectorAll('.nr-month').forEach(function (m) {
      var shown = m.querySelectorAll('li:not([hidden])').length;
      m.hidden = !shown;
      var n = m.querySelector('h3 span'); if (n) n.textContent = shown + (shown === 1 ? ' note' : ' notes');
    });
  }
  chips.forEach(function (c) { c.addEventListener('click', function (e) { e.preventDefault(); filter(c.dataset.f); }); });
  window.nrFilter = filter;
  filter(location.hash.slice(1));

  // ---- Recent posts carousel ----
  var r = document.getElementById('nr-recent'); if (!r) return;
  var s = r.querySelectorAll('.nr-track > .nr-card'), dots = r.querySelectorAll('.nr-dots button'),
      cnt = document.getElementById('nr-count'), bar = r.querySelector('.nr-bar i');
  var i = 0, n = s.length, DWELL = 6000, t = null, stopped = false, held = true,
      still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!n) return;

  function show(k, dir) {
    dir = dir || 1; k = (k + n) % n;
    r.classList.toggle('back', dir < 0);
    if (k !== i) {
      var old = s[i]; old.classList.remove('on'); old.classList.add('out');
      setTimeout(function () { old.classList.remove('out'); }, 500);
    }
    s[k].classList.remove('out'); i = k; s[i].classList.add('on');
    s.forEach(function (x, j) { x.setAttribute('aria-hidden', j !== i); x.querySelector('a').tabIndex = j === i ? 0 : -1; });
    dots.forEach(function (d, j) { d.toggleAttribute('aria-current', j === i); });
    cnt.textContent = (i + 1) + ' / ' + n;
    restart();
  }
  // The guide gets a moment to lean over and push before the post slides away.
  function change(k, dir) {
    if (window.nrLead && window.nrLead(dir || 1)) setTimeout(function () { show(k, dir); }, 300);
    else show(k, dir);
  }
  function restart() {
    clearTimeout(t); bar.style.animation = 'none'; void bar.offsetWidth; bar.style.animation = '';
    var auto = !stopped && !still && !held;
    r.classList.toggle('playing', auto);
    if (auto) t = setTimeout(function () { change(i + 1, 1); }, DWELL);
  }
  function pause(p) {
    r.classList.toggle('paused', p);
    if (p) clearTimeout(t);
    else if (!stopped && !still && !held) {
      var done = bar.offsetWidth / bar.parentNode.offsetWidth;
      t = setTimeout(function () { change(i + 1, 1); }, DWELL * (1 - done));
    }
  }
  function user(k, dir) { stopped = true; change(k, dir); }   // once steered by hand, it stops rotating

  document.getElementById('nr-prev').onclick = function () { user(i - 1, -1); };
  document.getElementById('nr-next').onclick = function () { user(i + 1, 1); };
  dots.forEach(function (d, j) { d.onclick = function () { user(j, j < i ? -1 : 1); }; });
  r.addEventListener('mouseenter', function () { pause(true); });
  r.addEventListener('mouseleave', function () { pause(false); });
  r.addEventListener('focusin', function () { pause(true); });
  r.addEventListener('focusout', function () { pause(false); });
  r.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight') user(i + 1, 1);
    if (e.key === 'ArrowLeft') user(i - 1, -1);
  });
  var x0 = null;
  r.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
  r.addEventListener('touchend', function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 40) user(dx < 0 ? i + 1 : i - 1, dx < 0 ? 1 : -1);
  });
  document.addEventListener('visibilitychange', function () { if (document.hidden) clearTimeout(t); else restart(); });

  s[0].classList.add('on'); show(0, 1); r.classList.add('ready');
  // The guide starts the rotation once its intro is done (or straight away if it is hidden).
  window.nrCarousel = { next: function () { change(i + 1, 1); }, start: function () { if (held) { held = false; restart(); } } };
  if (!document.getElementById('nr-layer')) window.nrCarousel.start();
})();

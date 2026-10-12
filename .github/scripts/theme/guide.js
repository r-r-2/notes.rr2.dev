/* The guide: a stick figure that lives on every page.
   Homepage: stands by the heading and says hi, zip-lines down to the Recent
   posts card, pushes each post away as the card changes, offers help, then
   slides down a rope beside the archive as you scroll.
   Other pages: sits on the line under the title and helps when tapped. */
(function () {
  var L = document.getElementById('nr-layer'); if (!L) return;
  var root = document.documentElement, M = L.parentNode,
      W = document.getElementById('nr-gw'), B = document.getElementById('nr-buddy'),
      bub = document.getElementById('nr-bubble'), txt = bub.querySelector('p'), acts = bub.querySelector('.nr-acts'),
      rope = document.getElementById('nr-rope'), zip = document.getElementById('nr-zip'),
      R = document.getElementById('nr-recent'), P = document.getElementById('nr-perch'),
      onBtn = document.getElementById('nr-guide-on'),
      still = matchMedia('(prefers-reduced-motion: reduce)').matches, ht = null;

  function store(k, v) {
    try { if (v === undefined) return localStorage.getItem(k); if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {}
  }
  function seen(set) {
    try { if (set) sessionStorage.setItem('nr-met', '1'); else return !!sessionStorage.getItem('nr-met'); } catch (e) {}
  }

  // ---- Talking ----
  function hide() { bub.classList.remove('show'); }
  function room() { return innerWidth - (M.getBoundingClientRect().left + parseFloat(W.style.left || 0)) - 76; }
  function fit() {
    var beside = bub.classList.contains('side') || W.classList.contains('stand') ||
                 (W.classList.contains('hang') && !root.classList.contains('rope-in'));
    bub.style.maxWidth = beside ? Math.max(150, Math.min(272, room())) + 'px' : '';
    var r = bub.getBoundingClientRect(), shift = 0;
    if (r.left < 12) shift = 12 - r.left; else if (r.right > innerWidth - 12) shift = innerWidth - 12 - r.right;
    bub.style.setProperty('--bs', shift + 'px');
  }
  // acts: [label, onClick] for a button, or [label, null, href] for a link
  function say(text, list, ms) {
    txt.textContent = text; acts.textContent = '';
    (list || []).forEach(function (a) {
      var el = document.createElement(a[2] ? 'a' : 'button');
      if (a[2]) el.href = a[2]; else el.type = 'button';
      el.textContent = a[0];
      if (a[1]) el.onclick = function (e) { e.stopPropagation(); a[1](); };
      acts.appendChild(el);
    });
    bub.classList.toggle('has-acts', !!(list && list.length));
    bub.style.setProperty('--bs', '0px'); bub.classList.add('show'); fit();
    clearTimeout(ht); if (ms) ht = setTimeout(hide, ms);
  }
  function play(c) { B.classList.remove(c); void B.offsetWidth; B.classList.add(c); setTimeout(function () { B.classList.remove(c); }, 1400); }
  function pose(p) { W.classList.remove('stand', 'hang', 'zipping'); if (p) W.classList.add(p); }
  function toTop() { scrollTo({ top: 0, behavior: still ? 'auto' : 'smooth' }); hide(); }
  function copyLink() {
    var fail = function () { say("Couldn't copy. The link is in your address bar.", [], 2600); };
    try { navigator.clipboard.writeText(location.href).then(function () { say('Link copied.', [], 1800); }, fail); } catch (e) { fail(); }
  }
  function hideGuide() { hide(); store('nr-guide-off', '1'); L.hidden = true; if (onBtn) onBtn.parentNode.hidden = false; }

  if (onBtn) onBtn.addEventListener('click', function () { store('nr-guide-off', null); location.reload(); });
  if (store('nr-guide-off')) {
    L.hidden = true; if (onBtn) onBtn.parentNode.hidden = false;
    if (window.nrCarousel) window.nrCarousel.start();
    return;
  }

  if (R) home(); else page();

  // ================================================================ homepage
  function home() {
    var H1 = document.querySelector('.nr-intro h1'), mode = 'stand', sx = 0, hx = 0, x0 = 0, y0 = 0, ymax = 0,
        cur = 0, tgt = 0, raf = 0, hanging = false, landed = false, saidHang = false, intro = true, T = [], lastY = scrollY;

    function place(x, y) { W.style.left = x + 'px'; W.style.transform = 'translateY(' + y + 'px)'; }
    function textWidth(el) { var g = document.createRange(); g.selectNodeContents(el); return g.getBoundingClientRect().width; }
    function measure() {
      var mr = M.getBoundingClientRect(), rr = R.getBoundingClientRect(), hr = H1.getBoundingClientRect(),
          months = M.querySelectorAll('.nr-month:not([hidden])'), last = (months[months.length - 1] || R).getBoundingClientRect();
      L.style.top = (rr.top - mr.top) + 'px';
      var narrow = innerWidth - rr.right < 96; root.classList.toggle('rope-in', narrow);
      sx = rr.right - mr.left - (innerWidth < 600 ? 36 : 90) - 60;        // seat on the card's top edge
      hx = narrow ? rr.right - mr.left - 50 : rr.right - mr.left + 22;   // rope: in the margin, or the card's edge on phones
      x0 = hr.left - mr.left + textWidth(H1) + 12; y0 = hr.bottom - rr.top - 22;   // standing by the heading
      ymax = Math.max(0, last.bottom - rr.top - 30);
      rope.style.left = (hx + 30) + 'px';
      if (mode === 'stand') place(x0, y0); else if (mode === 'live') { W.style.left = (hanging ? hx : sx) + 'px'; tick(); }
    }
    // Zip line from the hands where it stands to the hands where it will sit.
    function zipDown() {
      var ax = x0 + 30, ay = y0 - 57, bx = sx + 30, by = -83, dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy);
      zip.style.left = (ax - 14 * dx / len) + 'px'; zip.style.top = (ay - 14 * dy / len) + 'px';
      zip.style.width = (len + 28) + 'px'; zip.style.transform = 'rotate(' + Math.atan2(dy, dx) + 'rad)';
      zip.classList.add('on'); pose('hang'); W.classList.add('zipping');
      setTimeout(function () { place(sx, -26); }, 60);
      setTimeout(function () { zip.classList.remove('on'); pose(null); mode = 'live'; place(sx, 0); cur = 0; play('land'); }, 1700);
    }
    function aim() {
      if (still) return 0;
      var y = innerHeight * .42 - R.getBoundingClientRect().top; if (y < 90) return 0;
      var left = root.scrollHeight - innerHeight - scrollY;     // near the bottom, catch up with the last month
      if (left < 320) y += (ymax - y) * Math.max(0, 1 - left / 320);
      return Math.min(Math.max(y, 0), ymax);
    }
    function tick() {
      if (mode !== 'live') return;
      if (scrollY < lastY - 4 && hanging) hide(); lastY = scrollY;
      tgt = aim(); var h = tgt > 0;
      if (h !== hanging) {
        hanging = h; pose(h ? 'hang' : null); W.style.left = (h ? hx : sx) + 'px'; hide();
        if (h && !saidHang && !root.classList.contains('rope-in') && room() >= 170) { saidHang = true; say("Hold on, I'll come down with you.", [], 2200); }
      }
      if (!raf) raf = requestAnimationFrame(step);
    }
    function step() {
      raf = 0; cur += (tgt - cur) * .16; if (Math.abs(tgt - cur) < .5) cur = tgt;
      W.style.transform = 'translateY(' + cur + 'px)';
      rope.style.height = Math.max(0, cur - 56) + 'px'; rope.classList.toggle('on', cur > 4);
      if (hanging && ymax > 0 && cur >= ymax - 2 && !landed) {   // once per visit
        landed = true; say("That's every note. Want to go back up?", [['Back to top', toTop]], 4500);
      }
      if (cur !== tgt) raf = requestAnimationFrame(step);
    }
    function goTo(f, line) {
      if (window.nrFilter) window.nrFilter(f); measure(); say(line, [], 2600);
      var c = document.querySelector('.nr-chips'); if (c) c.scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'start' });
    }
    function offer() {
      var list = [["What's new", function () { window.nrCarousel.next(); say('Fresh off the press.', [], 2200); }]];
      document.querySelectorAll('.nr-chips [data-sec]').forEach(function (c) {
        var f = c.dataset.f, name = c.firstChild.textContent.trim();
        list.push([name, function () { goTo(f, name + ', newest first.'); }]);
      });
      list.push(["I'm good", function () { say('Okay! Tap me any time.', [], 2000); }]);
      say('Want a hand finding something?', list, 0);
    }
    // If the visitor gets going before the intro ends, jump straight to the seat.
    function skip() {
      if (!intro) return; intro = false; T.forEach(clearTimeout); hide();
      zip.classList.remove('on'); W.classList.remove('zipping');
      if (mode !== 'live') { pose(null); mode = 'live'; place(sx, 0); cur = 0; }
      window.nrCarousel.start(); tick();
    }
    window.nrLead = function (dir) {
      if (mode !== 'live' || hanging || still) return false;
      B.classList.toggle('left', dir < 0); play('push');
      setTimeout(function () { B.classList.remove('left'); }, 1100); return true;
    };
    B.addEventListener('click', function () {
      skip(); play('wave');
      if (bub.classList.contains('show') && bub.classList.contains('has-acts')) hide(); else offer();
    });

    seen(true); pose('stand');
    [[500, function () { play('wave'); say("Hi! I'm Rahul. Well, a stick version of him.", [], 0); }],
     [3300, function () { say('This is where my AI agents keep notes on what we build.', [], 0); }],
     [6300, function () { if (still) { pose(null); mode = 'live'; place(sx, 0); return; } say('Wheee!', [], 1300); zipDown(); }],
     [8600, function () { window.nrCarousel.next(); say("Out with the old. Here's another fresh one.", [], 0); }],
     [11200, function () { intro = false; window.nrCarousel.start(); offer(); }]
    ].forEach(function (x) { T.push(setTimeout(x[1], x[0])); });

    addEventListener('scroll', function () { if (intro && scrollY > 120) skip(); tick(); }, { passive: true });
    addEventListener('resize', measure);
    R.addEventListener('click', function (e) { if (intro && e.target.closest('button')) skip(); }, true);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
    if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { B.classList.toggle('off', !es[0].isIntersecting); }).observe(B);
    measure();
  }

  // ================================================================ other pages
  function page() {
    if (!P) { L.hidden = true; return; }
    function measure() {
      var mr = M.getBoundingClientRect(), pr = P.getBoundingClientRect();
      L.style.top = (pr.top - mr.top) + 'px';
      W.style.left = (pr.right - mr.left - 58) + 'px';   // at the right end of the line, beside the header's text
    }
    var tapped = false;
    B.addEventListener('click', function () {
      tapped = true; play('wave');
      if (bub.classList.contains('show') && bub.classList.contains('has-acts')) { hide(); return; }
      bub.classList.remove('side');
      say('Need anything?', [['Copy link', copyLink], ['All notes', null, '/'], ['Hide guide', hideGuide]], 0);
    });
    addEventListener('resize', measure);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
    measure();

    // Say hi once per visit, and only where the margin can hold the bubble.
    var hello = P.getAttribute('data-hello');
    if (hello && !seen()) {
      seen(true);
      setTimeout(function () {
        if (tapped) return;   // a tap already opened the menu; don't talk over it
        play('wave');
        if (innerWidth - W.getBoundingClientRect().right - 16 < 190) return;
        bub.classList.add('side'); say(hello, [], 3200);
        setTimeout(function () { bub.classList.remove('side'); }, 3600);
      }, 700);
    }
  }
})();

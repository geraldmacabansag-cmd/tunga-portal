/* Home page banner slider (templates/portal/home.html, styles in
   static/css/homepage.css, "Banner slider"). Moves to the next slide by itself
   every data-interval milliseconds (set on the <section>, 6000 = 6 seconds).
   After data-loops rounds through all the slides it stops on the first
   (welcome) slide (0 = never stops; Super Admin -> Homepage -> Banner Slider).
   It waits while the mouse is over the banner, while someone moves through it
   with the Tab key, and while the browser tab is hidden.
   Every element with data-slide-to="N" (the dots) shows slide N when clicked.
   Arrows / swipe / Left-Right keys also move it. */
(function () {
  var root = document.querySelector('.hero-carousel');
  if (!root) return;
  var slides = Array.prototype.slice.call(root.querySelectorAll('.hero-slide'));
  if (slides.length < 2) return;

  var pickers = Array.prototype.slice.call(root.querySelectorAll('[data-slide-to]'));
  var list = root.querySelector('.hc__list');
  var counter = root.querySelector('.js-hc-now');
  var mainBar = root.querySelector('.hero-carousel__progress span');
  var interval = parseInt(root.getAttribute('data-interval'), 10) || 6000;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var loops = parseInt(root.getAttribute('data-loops'), 10);
  if (isNaN(loops) || loops < 0) loops = 2;
  var current = 0, timer = null, started = 0, left = interval, paused = false;
  var loopsDone = 0, stopped = false;

  // timer bars: the one at the bottom of the picture + the one in the
  // selected "Highlights" item
  function bars() {
    var b = [];
    if (mainBar) b.push(mainBar);
    var item = list && list.querySelector('.hc__item.is-active .hc__bar span');
    if (item) b.push(item);
    return b;
  }
  function resetBars() {
    root.querySelectorAll('.hc__bar span').forEach(function (s) { s.style.transition = 'none'; s.style.width = '0'; });
  }

  // keep the selected item visible inside the list (scrolls only the list,
  // never the page)
  function revealItem(item) {
    if (!list || !item) return;
    var top = item.offsetTop, bottom = top + item.offsetHeight;   // the list is position: relative
    if (top < list.scrollTop) list.scrollTop = top - 6;
    else if (bottom > list.scrollTop + list.clientHeight) list.scrollTop = bottom - list.clientHeight + 6;
  }

  function show(i) {
    current = (i + slides.length) % slides.length;
    slides.forEach(function (s, n) {
      var on = n === current;
      s.classList.toggle('is-active', on);
      s.setAttribute('aria-hidden', on ? 'false' : 'true');
      // only the visible slide's links can be reached with Tab
      s.querySelectorAll('a, button').forEach(function (el) { el.tabIndex = on ? 0 : -1; });
    });
    pickers.forEach(function (p) {
      var on = parseInt(p.getAttribute('data-slide-to'), 10) === current;
      p.classList.toggle('is-active', on);
      if (p.hasAttribute('aria-selected')) p.setAttribute('aria-selected', on ? 'true' : 'false');
      if (p.classList.contains('hc__item')) {
        if (on) { p.setAttribute('aria-current', 'true'); revealItem(p); } else p.removeAttribute('aria-current');
      }
    });
    if (counter) counter.textContent = current + 1;
    resetBars();
    restart();
  }

  function runBar(ms) {
    if (reduceMotion) return;
    bars().forEach(function (bar) {
      bar.style.transition = 'none';
      bar.style.width = ((interval - ms) / interval * 100) + '%';
      void bar.offsetWidth;                     // apply the start width first
      bar.style.transition = 'width ' + ms + 'ms linear';
      bar.style.width = '100%';
    });
  }
  function freezeBar() {
    bars().forEach(function (bar) {
      bar.style.transition = 'none';
      bar.style.width = ((interval - left) / interval * 100) + '%';
    });
  }

  function schedule(ms) {
    clearTimeout(timer);
    started = Date.now(); left = ms;
    timer = setTimeout(autoNext, ms);
    runBar(ms);
  }
  // the timer moved it on: count the rounds, and stop on the welcome slide
  // when the set number of loops is done
  function autoNext() {
    if (current === slides.length - 1) {
      loopsDone++;
      if (loops > 0 && loopsDone >= loops) stopped = true;
    }
    show(current + 1);
  }
  function restart() {
    left = interval;
    if (stopped) { clearTimeout(timer); return; }
    if (!paused) schedule(interval); else freezeBar();
  }
  function pause() {
    if (paused) return;
    paused = true;
    clearTimeout(timer);
    left = Math.max(0, left - (Date.now() - started));
    freezeBar();
  }
  function resume() {
    if (!paused) return;
    paused = false;
    if (stopped) return;
    schedule(left || interval);
  }

  var prev = root.querySelector('.hero-carousel__nav--prev');
  var next = root.querySelector('.hero-carousel__nav--next');
  if (prev) prev.addEventListener('click', function () { show(current - 1); });
  if (next) next.addEventListener('click', function () { show(current + 1); });
  pickers.forEach(function (p) {
    p.addEventListener('click', function () { show(parseInt(p.getAttribute('data-slide-to'), 10) || 0); });
  });

  // wait while a mouse is over it (not on touch screens, where a tap would
  // otherwise stop it for good)
  root.addEventListener('pointerenter', function (e) { if (e.pointerType === 'mouse') pause(); });
  root.addEventListener('pointerleave', function (e) { if (e.pointerType === 'mouse') resume(); });
  // wait while someone moves through it with the Tab key
  root.addEventListener('focusin', function (e) {
    var kb = true;
    try { kb = e.target.matches(':focus-visible'); } catch (err) {}
    if (kb) pause();
  });
  root.addEventListener('focusout', function (e) { if (!root.contains(e.relatedTarget) && !root.matches(':hover')) resume(); });
  document.addEventListener('visibilitychange', function () { document.hidden ? pause() : resume(); });

  root.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') { e.preventDefault(); show(current - 1); }
    if (e.key === 'ArrowRight') { e.preventDefault(); show(current + 1); }
  });

  // swipe on phones
  var x0 = null, y0 = null;
  root.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
  root.addEventListener('touchend', function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) show(current + (dx < 0 ? 1 : -1));
    x0 = null;
  }, { passive: true });

  show(0);
})();
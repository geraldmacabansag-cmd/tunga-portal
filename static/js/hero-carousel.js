/* Home page banner carousel (templates/portal/home.html, styles in
   static/css/homepage.css). Moves to the next slide by itself every
   data-interval milliseconds (set on the <section>, 6000 = 6 seconds).
   It waits while the mouse is over the banner, while a button in it has the
   keyboard focus, and while the browser tab is hidden.
   Arrows / dots / swipe / Left-Right keys move it by hand. */
(function () {
  var root = document.querySelector('.hero-carousel');
  if (!root) return;
  var slides = Array.prototype.slice.call(root.querySelectorAll('.hero-slide'));
  if (slides.length < 2) return;

  var dots = Array.prototype.slice.call(root.querySelectorAll('.hero-carousel__dot'));
  var bar = root.querySelector('.hero-carousel__progress span');
  var interval = parseInt(root.getAttribute('data-interval'), 10) || 6000;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var current = 0, timer = null, started = 0, left = interval, paused = false;

  function show(i) {
    current = (i + slides.length) % slides.length;
    slides.forEach(function (s, n) {
      var on = n === current;
      s.classList.toggle('is-active', on);
      s.setAttribute('aria-hidden', on ? 'false' : 'true');
      // only the visible slide's links can be reached with Tab
      s.querySelectorAll('a, button').forEach(function (el) { el.tabIndex = on ? 0 : -1; });
    });
    dots.forEach(function (d, n) {
      d.classList.toggle('is-active', n === current);
      d.setAttribute('aria-selected', n === current ? 'true' : 'false');
    });
    restart();
  }

  function runBar(ms) {
    if (!bar || reduceMotion) return;
    bar.style.transition = 'none';
    bar.style.width = ((interval - ms) / interval * 100) + '%';
    void bar.offsetWidth;                       // apply the start width first
    bar.style.transition = 'width ' + ms + 'ms linear';
    bar.style.width = '100%';
  }
  function freezeBar() {
    if (!bar) return;
    bar.style.transition = 'none';
    bar.style.width = ((interval - left) / interval * 100) + '%';
  }

  function schedule(ms) {
    clearTimeout(timer);
    started = Date.now(); left = ms;
    timer = setTimeout(function () { show(current + 1); }, ms);
    runBar(ms);
  }
  function restart() { left = interval; if (!paused) schedule(interval); else freezeBar(); }
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
    schedule(left || interval);
  }

  root.querySelector('.hero-carousel__nav--prev').addEventListener('click', function () { show(current - 1); });
  root.querySelector('.hero-carousel__nav--next').addEventListener('click', function () { show(current + 1); });
  dots.forEach(function (d, n) { d.addEventListener('click', function () { show(n); }); });

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
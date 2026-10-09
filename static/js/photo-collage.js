/* Photo slider for the collages (templates/portal/_photo_collage.html).
   Click any photo of a collage → a full-screen slider opens on top of the
   details window: ← / → buttons, arrow keys, swipe on phones, a row of small
   photos to jump to, "3 / 17" counter. Esc or ✕ closes it (back to the details).
   Works for collages added later too (the details windows are filled when
   they open), because it listens on the whole page. */
(function () {
  if (window.PhotoSlider) return;
  var lb, img, countEl, titleEl, thumbs, prevBtn, nextBtn, list = [], at = 0;

  function build() {
    lb = document.createElement('dialog');
    lb.className = 'pc-lb';
    lb.setAttribute('aria-label', 'Photos');
    lb.innerHTML =
      '<div class="pc-lb__top"><div class="pc-lb__title"></div><span class="pc-lb__count"></span>' +
      '<button type="button" class="pc-lb__close" aria-label="Close">×</button></div>' +
      '<div class="pc-lb__stage">' +
      '<button type="button" class="pc-lb__nav pc-lb__prev" aria-label="Previous photo">&#10094;</button>' +
      '<img class="pc-lb__img" alt="">' +
      '<button type="button" class="pc-lb__nav pc-lb__next" aria-label="Next photo">&#10095;</button>' +
      '</div><div class="pc-lb__thumbs"></div>';
    document.body.appendChild(lb);
    img = lb.querySelector('.pc-lb__img');
    countEl = lb.querySelector('.pc-lb__count');
    titleEl = lb.querySelector('.pc-lb__title');
    thumbs = lb.querySelector('.pc-lb__thumbs');
    prevBtn = lb.querySelector('.pc-lb__prev');
    nextBtn = lb.querySelector('.pc-lb__next');

    prevBtn.addEventListener('click', function () { go(at - 1); });
    nextBtn.addEventListener('click', function () { go(at + 1); });
    lb.querySelector('.pc-lb__close').addEventListener('click', close);
    thumbs.addEventListener('click', function (e) {
      var t = e.target.closest('[data-i]');
      if (t) go(+t.getAttribute('data-i'));
    });
    lb.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { e.preventDefault(); go(at - 1); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); go(at + 1); }
    });
    // clicking the dark area around the photo closes it
    lb.querySelector('.pc-lb__stage').addEventListener('click', function (e) {
      if (e.target === e.currentTarget) close();
    });
    // stop Esc from also closing the details window underneath
    lb.addEventListener('cancel', function (e) { e.preventDefault(); close(); });

    // swipe left / right on phones
    var sx = null, sy = null;
    var stage = lb.querySelector('.pc-lb__stage');
    stage.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
    stage.addEventListener('touchend', function (e) {
      if (sx === null) return;
      var dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
      if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) go(at + (dx < 0 ? 1 : -1));
      sx = sy = null;
    });
  }

  function go(i) {
    if (!list.length) return;
    at = (i + list.length) % list.length;          // wraps around: after the last comes the first
    img.classList.add('is-loading');
    img.onload = function () { img.classList.remove('is-loading'); };
    img.src = list[at];
    countEl.textContent = (at + 1) + ' / ' + list.length;
    Array.prototype.forEach.call(thumbs.children, function (t, k) { t.classList.toggle('is-current', k === at); });
    var cur = thumbs.children[at];
    if (cur && cur.scrollIntoView) cur.scrollIntoView({ block: 'nearest', inline: 'center' });
    // load the next photo early so sliding feels instant
    if (list.length > 1) { var pre = new Image(); pre.src = list[(at + 1) % list.length]; }
  }

  function open(urls, start, title) {
    if (!lb) build();
    list = urls.slice();
    titleEl.textContent = title || '';
    lb.classList.toggle('pc-lb--single', list.length < 2);
    thumbs.innerHTML = list.map(function (u, k) {
      return '<button type="button" class="pc-lb__thumb" data-i="' + k + '" aria-label="Photo ' + (k + 1) + '"><img src="' + u.replace(/"/g, '&quot;') + '" alt="" loading="lazy"></button>';
    }).join('');
    if (!lb.open) {
      if (lb.showModal) lb.showModal(); else lb.setAttribute('open', '');
    }
    go(start || 0);
    nextBtn.focus({ preventScroll: true });
  }

  function close() {
    if (lb && lb.open) { if (lb.close) lb.close(); else lb.removeAttribute('open'); }
  }

  // A photo of a collage (in a details window, or on a card / list row) was
  // clicked: open the slider. Listens in the capture phase so a card's own
  // "open details" click doesn't also fire.
  function fromTile(tile, e) {
    var box = tile.closest('[data-pc-photos]');
    if (!box) return;
    var urls = [];
    try { urls = JSON.parse(box.getAttribute('data-pc-photos') || '[]'); } catch (err) {}
    if (!urls.length) return;
    e.preventDefault();
    e.stopPropagation();
    open(urls, +tile.getAttribute('data-pc-index') || 0, box.getAttribute('data-pc-title'));
  }
  document.addEventListener('click', function (e) {
    var tile = e.target.closest && e.target.closest('.pc-tile');
    if (tile) fromTile(tile, e);
  }, true);
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var tile = e.target.closest && e.target.closest('.pc-tile');
    if (tile) fromTile(tile, e);
  }, true);

  window.PhotoSlider = { open: open, close: close };
})();
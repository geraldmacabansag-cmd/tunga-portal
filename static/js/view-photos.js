/* Photo viewer for the "View" windows and review pages (Office
   Representative + Super Admin): the main image (cover) first, then every
   extra photo. With more than one photo it shows ‹ › arrows, a "2 / 5"
   counter and a row of thumbnails; click the big photo to open it full size.

   Server-drawn:  templates/includes/_view_photos.html  (data-vp-urls='[…]')
   Filled by JS:  a View button with data-gallery='["url", …]' and
                  data-gallery-target="<id of the image box in the window>". */
(function () {
  if (window.ViewPhotos) return;   // load once, even if included many times

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  function show(box, i) {
    var urls = box._vpUrls || [];
    if (!urls.length) return;
    i = (i + urls.length) % urls.length;
    box._vpI = i;
    var main = box.querySelector('.vp-main');
    if (main) main.src = urls[i];
    var count = box.querySelector('.vp-count');
    if (count) count.textContent = (i + 1) + ' / ' + urls.length;
    box.querySelectorAll('.vp-thumb').forEach(function (t, k) {
      t.classList.toggle('is-active', k === i);
      if (k === i && t.scrollIntoView) t.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    });
  }

  function fill(box, urls) {
    if (!box) return;
    urls = (urls || []).filter(Boolean);
    box.classList.add('vp');
    var main = box.querySelector('img');
    if (!main) { main = document.createElement('img'); main.alt = ''; box.appendChild(main); }
    main.classList.add('vp-main');
    main.title = 'Open full size';
    // the big photo sits in a "stage" so the arrows are centred on it
    var stage = box.querySelector('.vp-stage');
    if (!stage) {
      stage = document.createElement('div');
      stage.className = 'vp-stage';
      main.parentNode.insertBefore(stage, main);
      stage.appendChild(main);
    }
    box.querySelectorAll('.vp-prev, .vp-next, .vp-count, .vp-strip').forEach(function (el) { el.remove(); });
    box._vpUrls = urls;
    if (!urls.length) return;

    if (urls.length > 1) {
      stage.insertAdjacentHTML('beforeend',
        '<button type="button" class="vp-prev" aria-label="Previous photo"><i class="fa-solid fa-chevron-left"></i></button>' +
        '<button type="button" class="vp-next" aria-label="Next photo"><i class="fa-solid fa-chevron-right"></i></button>' +
        '<span class="vp-count"></span>');
      box.insertAdjacentHTML('beforeend', '<div class="vp-strip">' + urls.map(function (u, k) {
        return '<button type="button" class="vp-thumb" data-vp-i="' + k + '" aria-label="Photo ' + (k + 1) + '"><img src="' + esc(u) + '" alt="" loading="lazy"></button>';
      }).join('') + '</div>');
    }
    show(box, 0);
  }

  document.addEventListener('click', function (e) {
    var t = e.target;
    var box = t.closest && t.closest('.vp');
    if (box) {
      if (t.closest('.vp-prev')) { e.preventDefault(); show(box, (box._vpI || 0) - 1); return; }
      if (t.closest('.vp-next')) { e.preventDefault(); show(box, (box._vpI || 0) + 1); return; }
      var th = t.closest('.vp-thumb');
      if (th) { e.preventDefault(); show(box, +th.getAttribute('data-vp-i')); return; }
      if (t.classList.contains('vp-main') && t.src) { window.open(t.src, '_blank', 'noopener'); return; }
    }
  });

  // Super Admin "View" buttons: their own code fills the window and shows the
  // cover (and stops the click there), so this listens in the capture phase
  // and adds the rest of the photos right after.
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('[data-gallery][data-gallery-target]');
    if (!btn) return;
    var target = document.getElementById(btn.getAttribute('data-gallery-target'));
    var urls = [];
    try { urls = JSON.parse(btn.getAttribute('data-gallery') || '[]'); } catch (err) { urls = []; }
    if (!target) return;
    setTimeout(function () {
      if (urls.length) target.style.display = '';
      fill(target, urls);
    }, 0);
  }, true);

  // ← → keys move through the photos of the window that is open
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    if (/input|textarea|select/i.test((document.activeElement || {}).tagName || '')) return;
    var open = document.querySelector('.modal-backdrop.open .vp') || (document.querySelectorAll('.vp').length === 1 ? document.querySelector('.vp') : null);
    if (!open || !(open._vpUrls || []).length) return;
    show(open, (open._vpI || 0) + (e.key === 'ArrowRight' ? 1 : -1));
  });

  function init() {
    document.querySelectorAll('[data-vp-urls]').forEach(function (box) {
      var urls = [];
      try { urls = JSON.parse(box.getAttribute('data-vp-urls') || '[]'); } catch (err) { urls = []; }
      fill(box, urls);
    });
  }
  window.ViewPhotos = { fill: fill, show: show };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
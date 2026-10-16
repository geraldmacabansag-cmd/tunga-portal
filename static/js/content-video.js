/* YouTube videos of announcements, news posts and events.
   (static/css/content-video.css · office_dashboard/video.py)

   1. Player: <div class="cv" data-cv-id="VIDEO_ID"> (templates/portal/_video_embed.html)
      shows the thumbnail; tapping it loads the YouTube player
      (youtube-nocookie.com). Works inside pop-ups that copy their content
      from a <template>, because the clicks are handled here for the page.
      Closing a pop-up stops the video. While the video plays, the
      "Open on YouTube" link is hidden and shows only when the mouse is over
      the video (YouTube hides its own buttons the same way).
   2. Form box: <input class="cv-input" name="video_url"> shows a small
      preview of the video, or a message when it isn't a YouTube link.
   3. Super Admin pages: an Edit / Add button with data-photos-form="<form id>"
      and data-video="<link>" fills the form's video box; a View button with
      data-video-id="<id>" data-video-target="<box id>" shows the player in
      the view window. */
(function () {
  if (window.ContentVideo) return;
  window.ContentVideo = true;

  function youtubeId(url) {
    url = (url || '').trim();
    if (!url) return '';
    if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
    var a;
    try { a = new URL(url); } catch (e) { return ''; }
    var host = a.hostname.toLowerCase(), parts = a.pathname.split('/').filter(Boolean), id = '';
    if (host === 'youtu.be' || host === 'www.youtu.be') id = parts[0] || '';
    else if (/(^|\.)youtube(-nocookie)?\.com$/.test(host)) {
      if (a.pathname === '/watch') id = a.searchParams.get('v') || '';
      else if (parts.length >= 2 && ['shorts', 'live', 'embed', 'v'].indexOf(parts[0]) !== -1) id = parts[1];
    }
    return /^[A-Za-z0-9_-]{11}$/.test(id) ? id : '';
  }
  window.youtubeIdFromUrl = youtubeId;

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  function facadeHtml(id, title) {
    return '<div class="cv-frame"><button type="button" class="cv-play" aria-label="Play video' + (title ? ': ' + esc(title) : '') + '">'
      + '<img src="https://i.ytimg.com/vi/' + id + '/hqdefault.jpg" alt="" loading="lazy">'
      + '<span class="cv-btn" aria-hidden="true"></span><span class="cv-label">Watch video</span></button></div>'
      + '<div class="cv-meta"><a href="https://www.youtube.com/watch?v=' + id + '" target="_blank" rel="noopener">Open on YouTube</a></div>';
  }
  function build(box) {           // (re)draw a player box with its thumbnail
    var id = box.getAttribute('data-cv-id');
    if (!/^[A-Za-z0-9_-]{11}$/.test(id || '')) { box.innerHTML = ''; box.hidden = true; return; }
    box.hidden = false;
    box.classList.remove('is-playing');
    box.innerHTML = facadeHtml(id, box.getAttribute('data-cv-title') || '');
  }
  function play(box) {
    var id = box.getAttribute('data-cv-id'), frame = box.querySelector('.cv-frame');
    if (!frame) return;
    box.classList.add('is-playing');
    frame.innerHTML = '<iframe src="https://www.youtube-nocookie.com/embed/' + id + '?rel=0&autoplay=1&playsinline=1&controls=1&iv_load_policy=3&modestbranding=1"'
      + ' title="' + esc(box.getAttribute('data-cv-title') || 'YouTube video') + '" loading="lazy"'
      + ' allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"'
      + ' referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>';
  }
  function stopIn(root) {         // put playing videos back to their thumbnail
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll('.cv').forEach(function (box) { if (box.querySelector('iframe')) build(box); });
  }

  document.addEventListener('click', function (e) {
    var t = e.target;
    // 1. tap the thumbnail -> load the player
    var btn = t.closest && t.closest('.cv-play');
    if (btn) { e.preventDefault(); e.stopPropagation(); play(btn.closest('.cv')); return; }

    // 3a. Super Admin Add / Edit: fill the form's video box
    var edit = t.closest && t.closest('[data-photos-form]');
    if (edit) {
      var form = document.getElementById(edit.getAttribute('data-photos-form'));
      var input = form && form.querySelector('.cv-input');
      if (input) { input.value = edit.getAttribute('data-video') || ''; preview(input); }
    }
    // 3b. Super Admin View: show the player in the view window
    var view = t.closest && t.closest('[data-video-target]');
    if (view) {
      var slot = document.getElementById(view.getAttribute('data-video-target'));
      if (slot) {
        slot.setAttribute('data-cv-id', view.getAttribute('data-video-id') || '');
        slot.setAttribute('data-cv-title', view.getAttribute('data-title') || '');
        build(slot);
      }
    }
  }, true);

  // stop the video when a pop-up closes
  document.addEventListener('close', function (e) { stopIn(e.target); }, true);       // <dialog>
  new MutationObserver(function (list) {                                             // dashboard pop-ups (.open)
    list.forEach(function (m) {
      var el = m.target;
      if (el.classList && !el.classList.contains('open') && /modal|backdrop|dialog|lightbox/.test(el.className)) stopIn(el);
    });
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'open', 'hidden'], subtree: true });

  // 2. form box preview
  function preview(input) {
    var field = input.closest('.cv-field'), out = field && field.querySelector('.cv-preview');
    if (!out) return;
    var v = input.value.trim(), id = youtubeId(v);
    input.setCustomValidity(v && !id ? 'Please paste a YouTube link.' : '');
    if (!v) { out.innerHTML = ''; return; }
    out.innerHTML = id
      ? '<img src="https://i.ytimg.com/vi/' + id + '/mqdefault.jpg" alt=""><span class="cv-ok">✓ YouTube video found</span>'
      : '<span class="cv-bad">This is not a YouTube link. Use a link like https://www.youtube.com/watch?v=… or https://youtu.be/…</span>';
  }
  document.addEventListener('input', function (e) { if (e.target.classList && e.target.classList.contains('cv-input')) preview(e.target); });
  function init() {
    document.querySelectorAll('.cv[data-cv-id]').forEach(function (box) { if (!box.querySelector('.cv-frame')) build(box); });
    document.querySelectorAll('.cv-input').forEach(preview);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
  // players copied into pop-ups later (from <template>) are drawn when added
  new MutationObserver(function (list) {
    list.forEach(function (m) {
      m.addedNodes.forEach(function (n) {
        if (n.nodeType !== 1) return;
        var boxes = n.matches && n.matches('.cv[data-cv-id]') ? [n] : (n.querySelectorAll ? n.querySelectorAll('.cv[data-cv-id]') : []);
        Array.prototype.forEach.call(boxes, function (box) { if (!box.querySelector('.cv-frame')) build(box); });
      });
    });
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
/* "More photos" field (templates/office_dashboard/_more_photos_field.html).
   - Choosing photos adds them to the list (pick again to add more); each new
     photo can be dropped with its ✕ before saving.
   - Existing photos: click ✕ to mark for removal (click again to keep).
   - Super Admin pages share one form for Add and Edit: a button with
     data-photos='[{"id":1,"url":"…"}]' and data-photos-form="<form id>" fills
     that form's list of current photos when clicked ("[]" = new item). */
(function () {
  if (window.ContentPhotos) return;               // loaded once, even if included many times

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  // the files chosen in each field (kept here so several picks add up)
  var picked = new WeakMap();
  function filesOf(input) { if (!picked.has(input)) picked.set(input, []); return picked.get(input); }
  function sync(input) {
    try {
      var dt = new DataTransfer();
      filesOf(input).forEach(function (f) { dt.items.add(f); });
      input.files = dt.files;
    } catch (e) { /* very old browsers: the last pick is sent as-is */ }
  }
  function renderNew(field) {
    var input = field.querySelector('.cp-input'), box = field.querySelector('[data-cp-new]');
    if (!input || !box) return;
    box.innerHTML = '';
    filesOf(input).forEach(function (f, i) {
      var tile = document.createElement('div');
      tile.className = 'cp-thumb is-new';
      tile.innerHTML = '<img alt=""><button type="button" class="cp-x" title="Don\'t add this photo" data-cp-drop="' + i + '">×</button>';
      tile.querySelector('img').src = URL.createObjectURL(f);
      box.appendChild(tile);
    });
  }
  function clearNew(field) {
    var input = field.querySelector('.cp-input');
    if (!input) return;
    picked.set(input, []);
    sync(input);
    renderNew(field);
  }
  function setExisting(field, photos) {
    var box = field.querySelector('[data-cp-existing]');
    if (!box) return;
    box.innerHTML = (photos || []).map(function (p) {
      return '<label class="cp-thumb" title="Click to remove this photo when you save">'
        + '<img src="' + esc(p.url) + '" alt="">'
        + '<input type="checkbox" name="remove_photos" value="' + esc(p.id) + '">'
        + '<span class="cp-x" aria-hidden="true">×</span><span class="cp-gone">Will be removed</span></label>';
    }).join('');
  }

  document.addEventListener('change', function (e) {
    var input = e.target;
    if (!input.classList || !input.classList.contains('cp-input')) return;
    var list = filesOf(input);
    Array.prototype.forEach.call(input.files || [], function (f) {
      if (/^image\//.test(f.type)) list.push(f);
    });
    sync(input);
    renderNew(input.closest('[data-cp]'));
  });

  document.addEventListener('click', function (e) {
    // drop a newly chosen photo
    var drop = e.target.closest && e.target.closest('[data-cp-drop]');
    if (drop) {
      e.preventDefault();
      var field = drop.closest('[data-cp]'), input = field.querySelector('.cp-input');
      filesOf(input).splice(+drop.getAttribute('data-cp-drop'), 1);
      sync(input); renderNew(field);
      return;
    }
    // Super Admin Add / Edit buttons: show that item's current photos in the shared form
    var btn = e.target.closest && e.target.closest('[data-photos][data-photos-form]');
    if (btn) {
      var form = document.getElementById(btn.getAttribute('data-photos-form'));
      var f = form && form.querySelector('[data-cp]');
      if (f) {
        var list = [];
        try { list = JSON.parse(btn.getAttribute('data-photos') || '[]'); } catch (err) {}
        setExisting(f, list);
        clearNew(f);
      }
    }
  }, true);   // capture: these buttons stop the click from going further

  // a form being cleared (e.g. "Create") also clears its chosen photos
  document.addEventListener('reset', function (e) {
    var fields = e.target.querySelectorAll ? e.target.querySelectorAll('[data-cp]') : [];
    setTimeout(function () { Array.prototype.forEach.call(fields, clearNew); }, 0);
  }, true);

  // drag & drop onto the "Choose photos" box
  ['dragover', 'dragleave', 'drop'].forEach(function (type) {
    document.addEventListener(type, function (e) {
      var zone = e.target.closest && e.target.closest('.cp-drop');
      if (!zone) return;
      e.preventDefault();
      zone.classList.toggle('is-over', type === 'dragover');
      if (type === 'drop' && e.dataTransfer) {
        var input = zone.querySelector('.cp-input'), list = filesOf(input);
        Array.prototype.forEach.call(e.dataTransfer.files, function (f) { if (/^image\//.test(f.type)) list.push(f); });
        sync(input); renderNew(zone.closest('[data-cp]'));
      }
    });
  });

  window.ContentPhotos = { setExisting: setExisting, clearNew: clearNew };
})();
/* "Make Fillable" form builder — shared by the Office Representative and
 * Super Admin dashboards. The page sets window.FORM_BUILDER first:
 *   { pdfUrl, saveUrl, csrf }
 * and has a <script type="application/json" id="fields-data"> with the
 * saved fields.
 *
 * Click the PDF to add a field, drag to move, drag the dot to resize.
 * Click a field to edit it in the side panel (double-click it in the list
 * to hide the panel). Zoom buttons fit the page to any screen size. label, type, required,
 * left / center / right, top / middle / bottom, font size, bold, ALL CAPS,
 * color and hint text. Arrow keys nudge the selected field (Shift = bigger
 * steps), Delete removes it.
 */
(function () {
  var CFG = window.FORM_BUILDER;
  var MAX_FIT = 1.4;                    // never draw bigger than this when fitting
  var zoom = 1, renderScale = 1.4;     // zoom 1 = page fits the screen width
  var DEFAULTS = { text_align: 'left', v_align: 'bottom', font_size: 0, bold: false,
                   text_color: '#000000', uppercase: false, placeholder: '' };
  var SAMPLE = { text: 'Juan Dela Cruz', date: 'Oct 7, 2026', number: '12345' };

  var $ = function (id) { return document.getElementById(id); };
  var canvas = $('pdf-canvas'), ctx = canvas.getContext('2d');
  var stage = $('pdf-stage'), layer = $('field-layer');

  var pdfDoc = null, currentPage = 1, totalPages = 1;
  var fields = JSON.parse($('fields-data').textContent).map(prep);
  var selectedKey = null, nextTemp = 1, dirty = false, showSample = false;
  var suppressClick = false;
  var lastRowClick = { key: null, time: 0 };

  function prep(f) {
    for (var k in DEFAULTS) if (f[k] === undefined || f[k] === null) f[k] = DEFAULTS[k];
    f._key = f._key || (f.id ? 'f' + f.id : 'new' + (nextTemp++));
    return f;
  }
  function selected() { return fields.filter(function (f) { return f._key === selectedKey; })[0] || null; }
  function markDirty() { dirty = true; setStatus('Unsaved changes', '#b45309'); }
  function setStatus(text, color) { var s = $('save-status'); s.textContent = text; s.style.color = color || '#555'; }
  function esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;'); }

  /* ---------------- PDF ---------------- */
  function loadPage(num) {
    pdfDoc.getPage(num).then(function (page) {
      var wrap = stage.parentNode;
      var fit = Math.min(MAX_FIT, Math.max(0.3, (wrap.clientWidth - 4) / page.getViewport({ scale: 1 }).width));
      renderScale = fit * zoom;
      var vp = page.getViewport({ scale: renderScale });
      canvas.width = vp.width; canvas.height = vp.height;
      stage.style.width = vp.width + 'px'; stage.style.height = vp.height + 'px';
      page.render({ canvasContext: ctx, viewport: vp }).promise.then(renderBoxes);
    });
    $('pageIndicator').textContent = 'Page ' + num + ' of ' + totalPages;
    $('zoomLevel').textContent = Math.round(zoom * 100) + '%';
  }

  // Zoom buttons (field positions are stored as % of the page, so they stay put).
  function setZoom(z) { zoom = Math.max(0.5, Math.min(3, z)); if (pdfDoc) loadPage(currentPage); }
  $('zoomInBtn').onclick = function () { setZoom(zoom + 0.25); };
  $('zoomOutBtn').onclick = function () { setZoom(zoom - 0.25); };
  $('zoomFitBtn').onclick = function () { setZoom(1); };
  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () { if (pdfDoc) loadPage(currentPage); }, 200);
  });
  TungaPdf.open(CFG.pdfUrl).then(function (doc) {
    pdfDoc = doc; totalPages = doc.numPages; loadPage(currentPage);
  }).catch(function (err) {
    stage.innerHTML = '<p style="padding:20px;color:#c0392b;">Could not load the PDF for preview: ' + esc(err.message) + '</p>';
  });
  $('prevPageBtn').onclick = function () { if (currentPage > 1) { currentPage--; loadPage(currentPage); } };
  $('nextPageBtn').onclick = function () { if (currentPage < totalPages) { currentPage++; loadPage(currentPage); } };

  /* ---------------- Field boxes on the PDF ---------------- */
  // Same rules as the public fill-out page and the downloaded PDF, so what
  // the office sees here is what citizens get.
  function fontPx(f) {
    var boxH = f.height * canvas.height;
    return f.font_size ? f.font_size * renderScale : Math.min(14 * renderScale, boxH * 0.72);
  }

  function styleBox(box, f) {
    box.style.left = (f.x * 100) + '%';
    box.style.top = (f.y * 100) + '%';
    box.style.width = (f.width * 100) + '%';
    box.style.height = (f.height * 100) + '%';
    box.classList.toggle('is-selected', f._key === selectedKey);
    box.style.justifyContent = { left: 'flex-start', center: 'center', right: 'flex-end' }[f.text_align];
    box.style.alignItems = { top: 'flex-start', middle: 'center', bottom: 'flex-end' }[f.v_align];

    var txt = box.querySelector('.fb-text');
    if (f.field_type === 'checkbox') {
      box.style.justifyContent = 'center'; box.style.alignItems = 'center';
      txt.textContent = showSample ? '✕' : '☐';
      txt.style.cssText = 'font-size:' + Math.max(8, f.height * canvas.height * 0.8) + 'px;color:#2f5bea;';
      return;
    }
    var text = showSample ? SAMPLE[f.field_type] : (f.label || '(unlabeled)');
    txt.textContent = text;
    txt.style.cssText = [
      'font-size:' + fontPx(f).toFixed(1) + 'px',
      'font-weight:' + (f.bold ? '700' : '400'),
      'color:' + f.text_color,   // chosen color shows right away
      'text-transform:' + (f.uppercase ? 'uppercase' : 'none'),
      'text-align:' + f.text_align,
    ].join(';');
  }

  function renderBoxes() {
    layer.innerHTML = '';
    fields.filter(function (f) { return f.page_number === currentPage; }).forEach(function (f) {
      var box = document.createElement('div');
      box.className = 'fb-box';
      box.dataset.key = f._key;
      box.innerHTML = '<span class="fb-text"></span><span class="fb-handle" title="Drag to resize"></span>';
      styleBox(box, f);
      // Works with mouse, finger (phones/tablets) or pen; left button only.
      box.addEventListener('pointerdown', function (e) {
        if (e.button !== 0) return;
        startDrag(e, f, box, e.target.classList.contains('fb-handle'));
      });
      layer.appendChild(box);
    });
  }

  function refreshBox(f) {
    var box = layer.querySelector('[data-key="' + f._key + '"]');
    if (box) styleBox(box, f);
  }

  function startDrag(e, f, box, resizing) {
    e.preventDefault(); e.stopPropagation();
    select(f._key);
    var rect = stage.getBoundingClientRect();
    var startX = e.clientX, startY = e.clientY;
    var orig = { x: f.x, y: f.y, w: f.width, h: f.height };
    var moved = false;
    function onMove(ev) {
      var dx = (ev.clientX - startX) / rect.width, dy = (ev.clientY - startY) / rect.height;
      if (Math.abs(dx) + Math.abs(dy) > 0.001) moved = true;
      if (resizing) {
        f.width = Math.max(0.02, Math.min(1 - f.x, orig.w + dx));
        f.height = Math.max(0.012, Math.min(1 - f.y, orig.h + dy));
      } else {
        f.x = Math.max(0, Math.min(1 - f.width, orig.x + dx));
        f.y = Math.max(0, Math.min(1 - f.height, orig.y + dy));
      }
      styleBox(box, f);
    }
    function onUp() {
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerup', onUp);
      document.removeEventListener('pointercancel', onUp);
      if (moved) { suppressClick = true; markDirty(); }
    }
    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp);
    document.addEventListener('pointercancel', onUp);
  }

  // Click on empty space = add a new text field there.
  stage.addEventListener('click', function (e) {
    if (suppressClick) { suppressClick = false; return; }
    if (e.target !== canvas && e.target !== layer) return;
    var rect = stage.getBoundingClientRect();
    var w = 0.22, h = 0.03;
    var last = selected() || {};
    var f = prep({
      label: '', field_type: 'text', required: true, page_number: currentPage,
      x: Math.max(0, Math.min(1 - w, (e.clientX - rect.left) / rect.width - w / 2)),
      y: Math.max(0, Math.min(1 - h, (e.clientY - rect.top) / rect.height - h / 2)),
      width: w, height: h,
      // A new field copies the look of the field you were just editing.
      text_align: last.text_align, v_align: last.v_align, font_size: last.font_size,
      bold: last.bold, text_color: last.text_color, uppercase: last.uppercase,
    });
    fields.push(f);
    markDirty();
    renderBoxes();
    select(f._key);
    var lbl = $('fe-label'); if (lbl) lbl.focus();
  });

  /* ---------------- Side panel ---------------- */
  function select(key) {
    selectedKey = key;
    layer.querySelectorAll('.fb-box').forEach(function (b) { b.classList.toggle('is-selected', b.dataset.key === key); });
    renderList();
    renderEditor();
  }

  function renderList() {
    var list = $('field-list');
    $('empty-hint').style.display = fields.length ? 'none' : 'block';
    list.innerHTML = '';
    fields.forEach(function (f, i) {
      var row = document.createElement('button');
      row.type = 'button';
      row.className = 'fb-row' + (f._key === selectedKey ? ' is-selected' : '');
      row.innerHTML = '<span class="fb-row__num">' + (i + 1) + '</span>' +
        '<span class="fb-row__label">' + esc(f.label || '(unlabeled)') + '</span>' +
        '<span class="fb-row__page">p.' + f.page_number + '</span>';
      row.onclick = function () {
        // Double-click (two clicks on the same row) = hide the editor.
        // Done by timing because the list is redrawn after the first click.
        var now = Date.now();
        if (lastRowClick.key === f._key && now - lastRowClick.time < 450) {
          lastRowClick = { key: null, time: 0 };
          return select(null);
        }
        lastRowClick = { key: f._key, time: now };
        if (f.page_number !== currentPage) { currentPage = f.page_number; selectedKey = f._key; loadPage(currentPage); }
        select(f._key);
      };
      list.appendChild(row);
    });
  }

  function seg(name, value, options) {
    return '<div class="fb-seg" data-prop="' + name + '">' + options.map(function (o) {
      return '<button type="button" data-val="' + o[0] + '" title="' + o[2] + '" class="' + (value === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
    }).join('') + '</div>';
  }

  function renderEditor() {
    var box = $('field-editor'), f = selected();
    if (!f) { box.innerHTML = '<p class="fb-muted">Click a field to edit it. Double-click it in the list to hide this panel.</p>'; return; }
    var isText = f.field_type !== 'checkbox';
    var sizes = [0, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24];

    box.innerHTML =
      '<div class="fb-ed-head"><strong>Edit field</strong><span class="fb-muted">Page ' + f.page_number + '</span></div>' +
      '<label class="fb-lbl">Label</label>' +
      '<input id="fe-label" class="form-input fb-in" placeholder="e.g. Full Name" value="' + esc(f.label) + '">' +
      '<div class="fb-two">' +
        '<div><label class="fb-lbl">Type</label><select id="fe-type" class="form-input fb-in">' +
          [['text', 'Short Text'], ['date', 'Date'], ['number', 'Number'], ['checkbox', 'Checkbox']].map(function (o) {
            return '<option value="' + o[0] + '"' + (f.field_type === o[0] ? ' selected' : '') + '>' + o[1] + '</option>';
          }).join('') + '</select></div>' +
        '<label class="fb-check"><input type="checkbox" id="fe-required"' + (f.required ? ' checked' : '') + '> Required</label>' +
      '</div>' +
      (isText ?
        '<label class="fb-lbl">Text position (left / right)</label>' +
        seg('text_align', f.text_align, [['left', '<i class="fa-solid fa-align-left"></i> Left', 'Left'], ['center', '<i class="fa-solid fa-align-center"></i> Center', 'Center'], ['right', '<i class="fa-solid fa-align-right"></i> Right', 'Right']]) +
        '<label class="fb-lbl">Text position (up / down)</label>' +
        seg('v_align', f.v_align, [['top', 'Top', 'Top of the box'], ['middle', 'Middle', 'Middle of the box'], ['bottom', 'Bottom', 'Bottom of the box (sits on the line)']]) +
        '<div class="fb-two">' +
          '<div><label class="fb-lbl">Font size</label><select id="fe-size" class="form-input fb-in">' +
            sizes.map(function (s) { return '<option value="' + s + '"' + (f.font_size === s ? ' selected' : '') + '>' + (s ? s + ' pt' : 'Auto (fit box)') + '</option>'; }).join('') +
          '</select></div>' +
          '<div><label class="fb-lbl">Color</label><div class="fb-colors">' +
            ['#000000', '#1d3fa6', '#b91c1c'].map(function (c) {
              return '<button type="button" class="fb-swatch' + (f.text_color.toLowerCase() === c ? ' on' : '') + '" data-color="' + c + '" style="background:' + c + '" title="' + c + '"></button>';
            }).join('') +
            '<input type="color" id="fe-color" value="' + f.text_color + '" title="Other color">' +
          '</div></div>' +
        '</div>' +
        '<div class="fb-seg fb-toggles">' +
          '<button type="button" id="fe-bold" class="' + (f.bold ? 'on' : '') + '"><b>B</b> Bold</button>' +
          '<button type="button" id="fe-caps" class="' + (f.uppercase ? 'on' : '') + '">AA ALL CAPS</button>' +
        '</div>' +
        '<label class="fb-lbl">Hint text inside the box (optional)</label>' +
        '<input id="fe-placeholder" class="form-input fb-in" placeholder="e.g. Last name, First name" value="' + esc(f.placeholder) + '">' +
        '<button type="button" class="btn btn-secondary fb-wide" id="fe-apply-all"><i class="fa-solid fa-paintbrush"></i> Use this text style for all fields</button>'
      : '<p class="fb-muted">Checkboxes are marked with an ✕ when ticked.</p>') +
      '<div class="fb-two fb-actions">' +
        '<button type="button" class="btn btn-secondary" id="fe-dup"><i class="fa-regular fa-copy"></i> Duplicate</button>' +
        '<button type="button" class="btn btn-secondary fb-danger" id="fe-del"><i class="fa-solid fa-trash-can"></i> Delete</button>' +
      '</div>' +
      '<p class="fb-muted fb-tip">Tip: arrow keys move the field, Shift + arrow moves faster, Delete removes it.</p>';

    function change(prop, val) { f[prop] = val; markDirty(); refreshBox(f); }

    $('fe-label').oninput = function () { f.label = this.value; markDirty(); refreshBox(f); renderList(); };
    $('fe-type').onchange = function () { change('field_type', this.value); renderEditor(); };
    $('fe-required').onchange = function () { change('required', this.checked); };
    box.querySelectorAll('.fb-seg[data-prop] button').forEach(function (b) {
      b.onclick = function () { change(b.parentNode.dataset.prop, b.dataset.val); renderEditor(); };
    });
    if (isText) {
      $('fe-size').onchange = function () { change('font_size', parseInt(this.value, 10)); };
      $('fe-color').oninput = function () { change('text_color', this.value); };
      $('fe-color').onchange = function () { renderEditor(); };
      box.querySelectorAll('.fb-swatch').forEach(function (s) {
        s.onclick = function () { change('text_color', s.dataset.color); renderEditor(); };
      });
      $('fe-bold').onclick = function () { change('bold', !f.bold); renderEditor(); };
      $('fe-caps').onclick = function () { change('uppercase', !f.uppercase); renderEditor(); };
      $('fe-placeholder').oninput = function () { f.placeholder = this.value; markDirty(); };
      $('fe-apply-all').onclick = function () {
        fields.forEach(function (o) {
          ['text_align', 'v_align', 'font_size', 'bold', 'text_color', 'uppercase'].forEach(function (k) { o[k] = f[k]; });
        });
        markDirty(); renderBoxes();
        setStatus('Style copied to all fields — remember to save.', '#b45309');
      };
    }
    $('fe-dup').onclick = function () {
      var copy = prep(JSON.parse(JSON.stringify(f)));
      delete copy.id; copy._key = 'new' + (nextTemp++);
      copy.y = Math.min(1 - copy.height, f.y + f.height + 0.01);
      fields.push(copy); markDirty(); renderBoxes(); select(copy._key);
    };
    $('fe-del').onclick = removeSelected;
  }

  function removeSelected() {
    var f = selected(); if (!f) return;
    fields = fields.filter(function (x) { return x !== f; });
    selectedKey = null; markDirty(); renderBoxes(); renderList(); renderEditor();
  }

  // Keyboard: nudge / delete the selected field (not while typing in a box).
  document.addEventListener('keydown', function (e) {
    var f = selected();
    if (!f || /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName)) return;
    var step = e.shiftKey ? 0.01 : 0.001;
    var moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    if (moves[e.key]) {
      e.preventDefault();
      f.x = Math.max(0, Math.min(1 - f.width, f.x + moves[e.key][0]));
      f.y = Math.max(0, Math.min(1 - f.height, f.y + moves[e.key][1]));
      markDirty(); refreshBox(f);
    } else if (e.key === 'Delete' || e.key === 'Backspace') {
      e.preventDefault(); removeSelected();
    } else if (e.key === 'Escape') {
      select(null);
    }
  });

  $('sampleToggle').addEventListener('change', function () { showSample = this.checked; renderBoxes(); });

  /* ---------------- Save ---------------- */
  $('saveFieldsBtn').addEventListener('click', function () {
    var unlabeled = fields.filter(function (f) { return !String(f.label).trim(); })[0];
    if (unlabeled) {
      setStatus('Every field needs a label before saving.', '#c0392b');
      if (unlabeled.page_number !== currentPage) { currentPage = unlabeled.page_number; loadPage(currentPage); }
      select(unlabeled._key);
      return;
    }
    setStatus('Saving…');
    fetch(CFG.saveUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CFG.csrf },
      body: JSON.stringify({ fields: fields }),
    }).then(function (r) { return r.json(); }).then(function (data) {
      if (!data.success) throw new Error(data.error || 'Could not save.');
      // Take the saved list back (new fields now have real ids).
      var sel = selected();
      fields = data.fields.map(prep);
      var again = sel && fields.filter(function (f) {
        return f.page_number === sel.page_number && Math.abs(f.x - sel.x) < 1e-6 && Math.abs(f.y - sel.y) < 1e-6;
      })[0];
      selectedKey = again ? again._key : null;
      dirty = false;
      renderBoxes(); renderList(); renderEditor();
      setStatus('Saved! Citizens will see these fields when they fill out the form.', '#1a7f37');
    }).catch(function (err) {
      setStatus((err && err.message) || 'Something went wrong. Please try again.', '#c0392b');
    });
  });

  window.addEventListener('beforeunload', function (e) {
    if (dirty) { e.preventDefault(); e.returnValue = ''; }
  });

  renderList();
  renderEditor();
})();
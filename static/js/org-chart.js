/* ==========================================================================
   Organizational Chart — places the boxes and draws the lines.
   Used by the Office Representative's builder and by the public office page,
   so the chart looks the same in both.

   How a box's spot is decided:
   - Every box has a "slot" in a tidy tree layout. Slots use the box's normal
     size, so making one box bigger or smaller never moves the other boxes.
   - A box the rep dragged keeps that spot (data-x / data-y).
   - Any other box follows the box above it, keeping its place in the tree.
   ========================================================================== */
(function () {
  var PAD = 30, GAP_X = 24, GAP_Y = 56;
  var HEX = /^#[0-9a-fA-F]{6}$/;
  var DASH = { dashed: '7 5', dotted: '1 5' };

  // A box's width from the corner handle (0 / empty = normal size)
  function setWidth(el, w) {
    if (w) { el.style.setProperty('--w', w + 'px'); el.classList.add('has-w'); }
    else { el.style.removeProperty('--w'); el.classList.remove('has-w'); }
  }

  function setup(board, svg, canvas) {
    var api = { nodes: [], byId: {}, roots: [], shiftX: 0, shiftY: 0 };

    board.querySelectorAll('.org-box').forEach(function (el) {
      // the box's chosen colors and width (empty = default look)
      [['border', '--b'], ['fill', '--bg'], ['text', '--fg']].forEach(function (c) {
        var v = el.dataset[c[0]];
        if (HEX.test(v || '')) el.style.setProperty(c[1], v);
      });
      if (/^\d+$/.test(el.dataset.w || '')) setWidth(el, +el.dataset.w);
      var n = { el: el, id: el.dataset.id, parent: el.dataset.parent, kids: [],
                sx: el.dataset.x === '' || el.dataset.x == null ? null : +el.dataset.x,
                sy: el.dataset.y === '' || el.dataset.y == null ? null : +el.dataset.y };
      api.nodes.push(n); api.byId[n.id] = n;
    });
    api.nodes.forEach(function (n) {
      var p = api.byId[n.parent];
      if (p) p.kids.push(n); else n.parent = null;
    });
    api.roots = api.nodes.filter(function (n) { return !n.parent; });

    // Normal size (the slot) and real size (with the corner-handle width)
    function measure(n) {
      var resized = n.el.classList.contains('has-w');
      if (resized) n.el.classList.remove('has-w');
      n.slotW = n.el.offsetWidth; n.slotH = n.el.offsetHeight;
      if (resized) n.el.classList.add('has-w');
      n.w = n.el.offsetWidth; n.h = n.el.offsetHeight;
      var kidsW = 0;
      n.kids.forEach(function (k, i) { kidsW += measure(k) + (i ? GAP_X : 0); });
      n.kidsW = kidsW;
      return (n.sw = Math.max(n.slotW, kidsW));
    }
    function autoPlace(n, left, top) {        // slot: centred above its row of boxes
      n.ax = left + (n.sw - n.slotW) / 2; n.ay = top;
      var x = left + (n.sw - n.kidsW) / 2;
      n.kids.forEach(function (k) { autoPlace(k, x, top + n.slotH + GAP_Y); x += k.sw + GAP_X; });
    }
    function resolve(n, p) {
      if (n.sx !== null) {                    // dragged by the rep
        n.x = n.sx; n.y = n.sy;
        n.bx = n.sx + (n.w - n.slotW) / 2; n.by = n.sy;
      } else {                                // follows the box above it
        if (p) { n.bx = p.bx + (n.ax - p.ax); n.by = p.by + (n.ay - p.ay); }
        else { n.bx = n.ax; n.by = n.ay; }
        n.x = n.bx + (n.slotW - n.w) / 2; n.y = n.by;   // a resized box stays centred on its slot
      }
      n.kids.forEach(function (k) { resolve(k, n); });
    }
    function drawLines() {
      // solid lines first, so a dashed / dotted line still shows where it's on its own
      var solid = '', other = '', sx = api.shiftX, sy = api.shiftY;
      api.nodes.forEach(function (n) {
        var p = n.parent && api.byId[n.parent];
        if (!p) return;
        var x1 = p.x + p.w / 2 + sx, y1 = p.y + p.h + sy;
        var x2 = n.x + n.w / 2 + sx, y2 = n.y + sy;
        var mid = y1 + Math.max(14, (y2 - y1) / 2);
        if (y2 < y1) mid = (y1 + y2) / 2;
        var color = HEX.test(n.el.dataset.line || '') ? n.el.dataset.line : '';
        var ls = n.el.dataset.lineStyle;
        var path = '<path d="M' + x1 + ',' + y1 + 'V' + mid + 'H' + x2 + 'V' + y2 + '"'
                 + (color ? ' style="stroke:' + color + '"' : '')
                 + (DASH[ls] ? ' stroke-dasharray="' + DASH[ls] + '" class="is-' + ls + '"' : '') + '/>';
        if (DASH[ls]) other += path; else solid += path;
      });
      svg.innerHTML = solid + other;
    }

    // resize = true: also fit the board around the boxes (can shift everything)
    api.paint = function (resize) {
      api.roots.forEach(function (r) { resolve(r, null); });
      if (resize) {
        var minX = Infinity, minY = Infinity, maxX = 0, maxY = 0;
        api.nodes.forEach(function (n) { minX = Math.min(minX, n.x); minY = Math.min(minY, n.y); });
        api.shiftX = PAD - minX; api.shiftY = PAD - minY;
        api.nodes.forEach(function (n) {
          maxX = Math.max(maxX, n.x + n.w + api.shiftX); maxY = Math.max(maxY, n.y + n.h + api.shiftY);
        });
        board.style.width = (maxX + PAD) + 'px'; board.style.height = (maxY + PAD) + 'px';
        svg.setAttribute('width', maxX + PAD); svg.setAttribute('height', maxY + PAD);
      }
      api.nodes.forEach(function (n) {
        n.el.style.left = (n.x + api.shiftX) + 'px';
        n.el.style.top = (n.y + api.shiftY) + 'px';
      });
      drawLines();
    };
    // Measure everything again (sizes are read at 100% zoom). keepBoard = true
    // while something is being dragged/resized, so the board doesn't jump.
    api.layout = function (keepBoard) {
      if (!api.nodes.length) return;
      var before = canvas.style.zoom; canvas.style.zoom = 1;
      var x = 0;
      api.roots.forEach(function (r) { measure(r); autoPlace(r, x, 0); x += r.sw + GAP_X * 2; });
      api.paint(!keepBoard);
      canvas.style.zoom = before;
    };
    return api;
  }

  // Zoom buttons + "fit": 100% = the whole chart fits the width of its frame
  function zoomer(viewport, canvas, label, minFit) {
    var z = { zoom: 1, fit: 1 };
    z.apply = function () {
      canvas.style.zoom = (z.fit * z.zoom).toFixed(3);
      if (label) label.textContent = Math.round(z.zoom * 100) + '%';
    };
    z.computeFit = function () {
      canvas.style.zoom = 1;
      z.fit = Math.max(minFit || 0, Math.min(1, (viewport.clientWidth - 2) / canvas.scrollWidth));
      z.apply();
    };
    z.zoomIn = function () { z.zoom = Math.min(3, z.zoom + 0.25); z.apply(); };
    z.zoomOut = function () { z.zoom = Math.max(0.25, z.zoom - 0.25); z.apply(); };
    z.reset = function () { z.zoom = 1; z.computeFit(); };
    z.current = function () { return parseFloat(canvas.style.zoom) || 1; };
    return z;
  }

  // Full screen: the panel covers the whole screen (handy on phones)
  function fullscreen(panel, button, onChange) {
    function set(on) {
      panel.classList.toggle('org-is-fullscreen', on);
      document.body.classList.toggle('org-fs-open', on);
      if (button) {
        button.setAttribute('aria-pressed', on ? 'true' : 'false');
        var icon = button.querySelector('i'), text = button.querySelector('.org-fs-label');
        if (icon) icon.className = on ? 'fa-solid fa-compress' : 'fa-solid fa-expand';
        if (text) text.textContent = on ? 'Exit full screen' : 'Full screen';
      }
      if (onChange) onChange(on);
    }
    if (button) button.addEventListener('click', function () { set(!panel.classList.contains('org-is-fullscreen')); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && panel.classList.contains('org-is-fullscreen')) set(false);
    });
    return { set: set, isOn: function () { return panel.classList.contains('org-is-fullscreen'); } };
  }

  window.TungaOrgChart = { setup: setup, setWidth: setWidth, zoomer: zoomer, fullscreen: fullscreen };
})();
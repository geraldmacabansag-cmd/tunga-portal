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
  // Every box is placed so its CENTRE sits on a 10px grid line, and the bends
  // of the lines are on grid lines too — so two boxes on the same grid line are
  // joined by a perfectly straight line, whatever their sizes.
  var GRID = 10;
  function snap(v) { return Math.round(v / GRID) * GRID; }
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
      // centre on the grid (the box's own spot / slot stays as it is)
      n.x = snap(n.x + n.w / 2) - n.w / 2;
      n.y = snap(n.y + n.h / 2) - n.h / 2;
      n.kids.forEach(function (k) { resolve(k, n); });
    }
    // The line between a box (n) and the box above it (p) joins the sides that
    // face each other, wherever the rep placed them:
    //   n lower than p  -> bottom of p  to top of n      (the usual tree line)
    //   n higher than p -> top of p     to bottom of n
    //   side by side    -> right/left side of p to the facing side of n
    function connector(p, n, sx, sy) {
      var GAP = 6;
      var pL = p.x + sx, pR = pL + p.w, pT = p.y + sy, pB = pT + p.h, pCx = pL + p.w / 2, pCy = pT + p.h / 2;
      var nL = n.x + sx, nR = nL + n.w, nT = n.y + sy, nB = nT + n.h, nCx = nL + n.w / 2, nCy = nT + n.h / 2;
      var mid;
      // bends on grid lines too (the board is shifted by sx / sy)
      function gy(v, lo, hi) { var s = snap(v - sy) + sy; return (s > lo && s < hi) ? s : v; }
      function gx(v, lo, hi) { var s = snap(v - sx) + sx; return (s > lo && s < hi) ? s : v; }
      if (nT >= pB + GAP) {                       // below
        mid = pB + Math.max(14, (nT - pB) / 2);
        if (mid > nT) mid = (pB + nT) / 2;
        mid = gy(mid, pB, nT);
        return 'M' + pCx + ',' + pB + 'V' + mid + 'H' + nCx + 'V' + nT;
      }
      if (nB <= pT - GAP) {                       // above
        mid = pT - Math.max(14, (pT - nB) / 2);
        if (mid < nB) mid = (pT + nB) / 2;
        mid = gy(mid, nB, pT);
        return 'M' + pCx + ',' + pT + 'V' + mid + 'H' + nCx + 'V' + nB;
      }
      if (nL >= pR + GAP) {                       // to the right
        mid = gx((pR + nL) / 2, pR, nL);
        return 'M' + pR + ',' + pCy + 'H' + mid + 'V' + nCy + 'H' + nL;
      }
      if (nR <= pL - GAP) {                       // to the left
        mid = gx((pL + nR) / 2, nR, pL);
        return 'M' + pL + ',' + pCy + 'H' + mid + 'V' + nCy + 'H' + nR;
      }
      return '';                                  // the boxes overlap: no line until they're apart
    }

    function drawLines() {
      // solid lines first, so a dashed / dotted line still shows where it's on its own
      var solid = '', other = '', sx = api.shiftX, sy = api.shiftY;
      api.nodes.forEach(function (n) {
        var p = n.parent && api.byId[n.parent];
        if (!p) return;
        var d = connector(p, n, sx, sy);
        if (!d) return;
        var color = HEX.test(n.el.dataset.line || '') ? n.el.dataset.line : '';
        var ls = n.el.dataset.lineStyle;
        var path = '<path d="' + d + '"'
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
        api.shiftX = Math.round(PAD - minX); api.shiftY = Math.round(PAD - minY);
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

  // Zoom buttons + "fit": 100% = the whole chart fits the width of its frame.
  // minFit: never smaller than this (wider charts scroll sideways instead);
  // maxFit: how much a small chart may grow to fill the frame (1 = never grow).
  function zoomer(viewport, canvas, label, minFit, maxFit) {
    var z = { zoom: 1, fit: 1 };
    z.apply = function () {
      canvas.style.zoom = (z.fit * z.zoom).toFixed(3);
      if (label) label.textContent = Math.round(z.zoom * 100) + '%';
    };
    z.computeFit = function () {
      canvas.style.zoom = 1;
      // the chart's own width (the frame itself is always at least as wide as the panel)
      var board = canvas.querySelector('.org-board'), cs = getComputedStyle(canvas);
      var natural = (board ? board.offsetWidth : canvas.scrollWidth)
                  + parseFloat(cs.paddingLeft || 0) + parseFloat(cs.paddingRight || 0);
      var ratio = Math.min(maxFit || 1, (viewport.clientWidth - 2) / natural);
      z.fits = ratio >= (minFit || 0);          // false = it's wider than the frame even at the smallest size
      z.fit = Math.max(minFit || 0, ratio);
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
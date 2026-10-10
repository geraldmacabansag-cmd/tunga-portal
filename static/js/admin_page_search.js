/* Super Admin top-bar search: finds a keyword anywhere on the page that is
   open (text, table rows, form fields — even inside hidden tabs) and lists
   the matches. Clicking a match opens its tab if needed, scrolls to it and
   highlights it for a moment. Enter = first match, ↑ ↓ to move, Esc to close. */
(function () {
  var input = document.getElementById('topbarSearchInput');
  var box = document.getElementById('pageSearchResults');
  if (!input || !box) return;

  var MAX_RESULTS = 30;
  var SKIP = 'script, style, noscript, template, svg, select, option, .sidebar, .topbar, .breadcrumbs, ' +
             '.modal-backdrop, .dropdown-panel, #pageSearchResults, #server-messages, .toast, .toast-wrap';
  var BLOCK = 'tr, li, p, h1, h2, h3, h4, h5, h6, label, .list-row, .log-row, .notif-row, .approval-row, ' +
              '.stat-card, .card, .form-group, .gallery-item, .directory-card, td, div';
  var results = [], active = -1, timer = null;

  function esc(s) {
    return s.replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
  }

  function isShown(el) {
    return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  }

  // A hidden element inside a tab (e.g. Website Settings → Appearance):
  // returns the tab button that shows it, or null.
  function tabFor(el) {
    var node = el;
    while (node && node !== document.body) {
      if (node.id && getComputedStyle(node).display === 'none') {
        var id = node.id, short = id.replace(/^(section|tab|panel)-/, '');
        var btn = document.querySelector(
          '[data-section="' + short + '"], [data-tab="' + id + '"], [data-tab="' + short + '"], ' +
          '[aria-controls="' + id + '"], [data-target="#' + id + '"], a[href="#' + id + '"]');
        if (btn && isShown(btn)) return btn;
        return null;
      }
      node = node.parentElement;
    }
    return null;
  }

  // Heading of the panel/section the match is in, shown above the snippet.
  function contextOf(el) {
    var node = el;
    while (node && node !== document.body) {
      if (node.matches('.panel, .settings-section, section, .card, .modal-box, .stat-card, form')) {
        var h = node.querySelector('.panel-header h2, h2, h3, .stat-label');
        if (h && h.textContent.trim()) return h.textContent.trim();
      }
      node = node.parentElement;
    }
    var title = document.querySelector('.page-heading h1');
    return title ? title.textContent.trim() : 'This page';
  }

  function labelForField(field) {
    var lab = field.id && document.querySelector('label[for="' + field.id + '"]');
    if (!lab) {
      var group = field.closest('.form-group, .field-row, label, div');
      lab = group && group.querySelector('label, .form-label, .fl-label');
    }
    var t = lab ? lab.textContent.trim() : (field.getAttribute('placeholder') || field.name || 'Field');
    return t.length > 40 ? t.slice(0, 40) + '…' : t;
  }

  function snippet(text, q) {
    text = text.replace(/\s+/g, ' ').trim();
    var i = text.toLowerCase().indexOf(q);
    var start = Math.max(0, i - 40), end = Math.min(text.length, i + q.length + 60);
    var before = (start > 0 ? '…' : '') + text.slice(start, i);
    var after = text.slice(i + q.length, end) + (end < text.length ? '…' : '');
    return esc(before) + '<mark>' + esc(text.slice(i, i + q.length)) + '</mark>' + esc(after);
  }

  function addResult(el, text, q, seen, prefix) {
    if (seen.indexOf(el) !== -1) return;
    var tab = null;
    if (!isShown(el)) {
      tab = tabFor(el);
      if (!tab) return; // hidden for another reason (filtered row, closed menu…)
    }
    seen.push(el);
    results.push({
      el: el,
      tab: tab,
      where: contextOf(el) + (tab ? ' · ' + tab.textContent.trim() + ' tab' : ''),
      html: (prefix ? '<b>' + esc(prefix) + ':</b> ' : '') + snippet(text, q)
    });
  }

  function search(raw) {
    var q = raw.trim().toLowerCase();
    results = [];
    if (q.length < 2) return;
    var root = document.querySelector('main.content') || document.body;
    var seen = [];

    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue || n.nodeValue.toLowerCase().indexOf(q) === -1) return NodeFilter.FILTER_REJECT;
        return n.parentElement.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      }
    });
    var n;
    while ((n = walker.nextNode()) && results.length < MAX_RESULTS) {
      var block = n.parentElement.closest('tr') || n.parentElement.closest(BLOCK) || n.parentElement;
      var text = (isShown(block) && block.innerText) || block.textContent;
      if (text.toLowerCase().indexOf(q) === -1) text = block.textContent;
      addResult(block, text, q, seen);
    }

    // Values typed in form fields (site name, links, descriptions…).
    root.querySelectorAll('input[type=text], input[type=email], input[type=url], input[type=tel], input:not([type]), textarea')
      .forEach(function (f) {
        if (results.length >= MAX_RESULTS || f.closest(SKIP)) return;
        if ((f.value || '').toLowerCase().indexOf(q) === -1) return;
        addResult(f, f.value, q, seen, labelForField(f));
      });
  }

  function render(raw) {
    var q = raw.trim();
    if (q.length < 2) { close(); return; }
    active = results.length ? 0 : -1;
    var html = '<div class="psr-head">' + (results.length
      ? results.length + (results.length >= MAX_RESULTS ? '+' : '') + ' match' + (results.length === 1 ? '' : 'es') + ' on this page'
      : 'No matches for “' + esc(q) + '” on this page') + '</div>';
    results.forEach(function (r, i) {
      html += '<button type="button" class="psr-item' + (i === 0 ? ' is-active' : '') + '" data-i="' + i + '">' +
              '<span class="psr-where">' + esc(r.where) + '</span>' +
              '<span class="psr-text">' + r.html + '</span></button>';
    });
    box.innerHTML = html;
    position();
    box.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }

  function position() {
    var r = input.closest('.field').getBoundingClientRect();
    var width = Math.max(r.width, Math.min(380, window.innerWidth - 24));
    var left = Math.min(r.left, window.innerWidth - width - 12);
    box.style.top = (r.bottom + 8) + 'px';
    box.style.left = Math.max(12, left) + 'px';
    box.style.width = width + 'px';
  }

  function close() {
    box.hidden = true;
    box.innerHTML = '';
    active = -1;
    input.setAttribute('aria-expanded', 'false');
  }

  function setActive(i) {
    var items = box.querySelectorAll('.psr-item');
    if (!items.length) return;
    active = (i + items.length) % items.length;
    items.forEach(function (el, k) { el.classList.toggle('is-active', k === active); });
    items[active].scrollIntoView({ block: 'nearest' });
  }

  function go(i) {
    var r = results[i];
    if (!r) return;
    close();
    var topbar = document.querySelector('.topbar.search-active');
    if (topbar) { var b = document.getElementById('mobileSearchBtn'); if (b) b.click(); }
    if (r.tab) r.tab.click();
    setTimeout(function () {
      var el = r.el;
      // A collapsed sidebar-style section or <details> may still hide it.
      var det = el.closest('details');
      if (det) det.open = true;
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.remove('page-search-flash');
      void el.offsetWidth; // restart the animation if clicked twice
      el.classList.add('page-search-flash');
      if (el.matches('input, textarea')) el.focus({ preventScroll: true });
      setTimeout(function () { el.classList.remove('page-search-flash'); }, 2600);
    }, r.tab ? 80 : 0);
  }

  input.setAttribute('autocomplete', 'off');
  input.setAttribute('aria-expanded', 'false');

  input.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () { search(input.value); render(input.value); }, 150);
  });
  input.addEventListener('focus', function () {
    if (input.value.trim().length >= 2) { search(input.value); render(input.value); }
  });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(active + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(active - 1); }
    else if (e.key === 'Enter') { e.preventDefault(); search(input.value); if (results.length) go(active < 0 ? 0 : active); else render(input.value); }
    else if (e.key === 'Escape') { close(); input.blur(); }
  });

  box.addEventListener('mousedown', function (e) { e.preventDefault(); }); // keep focus in the input
  box.addEventListener('click', function (e) {
    var item = e.target.closest('.psr-item');
    if (item) { e.stopPropagation(); go(parseInt(item.dataset.i, 10)); }
  });

  document.addEventListener('click', function (e) {
    if (box.hidden) return;
    if (e.target.closest('#pageSearchResults') || e.target.closest('#topbarSearchField')) return;
    close();
  });
  window.addEventListener('resize', function () { if (!box.hidden) position(); });
  window.addEventListener('scroll', function () { if (!box.hidden) position(); }, true);

  // Ctrl+K or "/" jumps to the search box.
  document.addEventListener('keydown', function (e) {
    var typing = /input|textarea|select/i.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
    if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) {
      e.preventDefault();
      var mb = document.getElementById('mobileSearchBtn');
      if (mb && getComputedStyle(mb).display !== 'none' && !document.querySelector('.topbar.search-active')) mb.click();
      input.focus();
      input.select();
    }
  });
})();
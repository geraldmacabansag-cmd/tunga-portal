/* ==========================================================================
   Municipality of Tunga — Admin Panel
   Shared interactivity: modals, toasts, dropdowns, and working buttons
   ========================================================================== */
(function () {
  'use strict';

  /* ------------------------------------------------------------------ */
  /* Small helpers                                                       */
  /* ------------------------------------------------------------------ */
  var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };

  /* ------------------------------------------------------------------ */
  /* Static create-modals                                                */
  /* The form markup (labels + inputs) lives in the page HTML. JS only  */
  /* opens/closes the modal (CSS handles the fade/scale transition) and */
  /* wires the submit handler that inserts the new row into the page.   */
  /* ------------------------------------------------------------------ */
  function openStaticModal(modal) {
    if (!modal) return;
    modal.classList.add('open');
    document.body.classList.add('modal-open');
    var first = modal.querySelector('.form-input, .form-textarea, select');
    if (first) setTimeout(function () { first.focus(); }, 180);
  }
  function closeStaticModal(modal) {
    if (!modal) return;
    modal.classList.remove('open');
    document.body.classList.remove('modal-open');
    var form = modal.querySelector('form');
    if (form) setTimeout(function () { form.reset(); }, 200);
  }
  function wireStaticModalChrome(modal) {
    if (!modal || modal.dataset.chromeWired) return;
    modal.dataset.chromeWired = '1';
    var xBtn = modal.querySelector('.modal-x');
    var cancelBtn = modal.querySelector('[data-act="cancel"]');
    if (xBtn) xBtn.addEventListener('click', function () { closeStaticModal(modal); });
    if (cancelBtn) cancelBtn.addEventListener('click', function () { closeStaticModal(modal); });
    modal.addEventListener('click', function (e) { if (e.target === modal) closeStaticModal(modal); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && modal.classList.contains('open')) closeStaticModal(modal);
    });
  }
  // Wires a trigger button + its static modal's <form> together. onSubmit
  // receives the form's FormData and the form element itself.
  function wireCreateModal(triggerEl, modal, onSubmit) {
    if (!triggerEl || !modal) return;
    wireStaticModalChrome(modal);
    triggerEl.addEventListener('click', function () { openStaticModal(modal); });
    var form = modal.querySelector('form');
    if (form) form.addEventListener('submit', function (e) {
      e.preventDefault();
      onSubmit(new FormData(form), form);
    });
  }
  var todayStr = function () {
    return new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  };
  var nowTime = function () {
    return new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  };
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };

  /* ------------------------------------------------------------------ */
  /* Toasts                                                              */
  /* ------------------------------------------------------------------ */
  function ensureToastHost() {
    var host = document.getElementById('toast-host');
    if (!host) {
      host = document.createElement('div');
      host.id = 'toast-host';
      host.className = 'toast-host';
      document.body.appendChild(host);
    }
    return host;
  }
  function toast(msg, type) {
    var host = ensureToastHost();
    var el = document.createElement('div');
    el.className = 'toast' + (type === 'error' ? ' toast-error' : ' toast-success');
    el.innerHTML = '<i class="fa-solid ' + (type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-check') + '"></i><span></span>';
    el.querySelector('span').textContent = msg;
    host.appendChild(el);
    requestAnimationFrame(function () { el.classList.add('show'); });
    setTimeout(function () {
      el.classList.remove('show');
      setTimeout(function () { el.remove(); }, 250);
    }, 2800);
  }

  /* ------------------------------------------------------------------ */
  /* Modal                                                                */
  /* ------------------------------------------------------------------ */
  function ensureModalHost() {
    var host = document.getElementById('modal-host');
    if (!host) {
      host = document.createElement('div');
      host.id = 'modal-host';
      host.className = 'modal-backdrop';
      host.innerHTML = '<div class="modal-box"></div>';
      document.body.appendChild(host);
      host.addEventListener('click', function (e) { if (e.target === host) closeModal(); });
    }
    return host;
  }
  function openModal(titleText, bodyHtml, opts) {
    opts = opts || {};
    var host = ensureModalHost();
    var box = host.querySelector('.modal-box');
    box.className = 'modal-box' + (opts.wide ? ' modal-wide' : '');
    box.innerHTML =
      '<div class="modal-head"><h3></h3><button type="button" class="modal-x" aria-label="Close"><i class="fa-solid fa-xmark"></i></button></div>' +
      '<div class="modal-body">' + bodyHtml + '</div>';
    box.querySelector('h3').textContent = titleText;
    host.classList.add('open');
    document.body.classList.add('modal-open');
    box.querySelector('.modal-x').addEventListener('click', closeModal);
    if (opts.onOpen) opts.onOpen(box);
    return box;
  }
  function closeModal() {
    var host = document.getElementById('modal-host');
    if (host) host.classList.remove('open');
    document.body.classList.remove('modal-open');
  }
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeModal(); });

  function confirmAction(message, onYes, opts) {
    opts = opts || {};
    var body =
      '<p class="confirm-msg"></p>' +
      '<div class="modal-actions">' +
      '<button type="button" class="btn btn-secondary" data-act="cancel">Cancel</button>' +
      '<button type="button" class="btn ' + (opts.danger ? 'btn-danger' : 'btn-primary') + '" data-act="ok"></button>' +
      '</div>';
    var box = openModal(opts.title || 'Please Confirm', body);
    box.querySelector('.confirm-msg').textContent = message;
    box.querySelector('[data-act="ok"]').textContent = opts.okText || 'Confirm';
    box.querySelector('[data-act="cancel"]').addEventListener('click', closeModal);
    box.querySelector('[data-act="ok"]').addEventListener('click', function () {
      closeModal();
      if (onYes) onYes();
    });
  }

  /* ------------------------------------------------------------------ */
  /* Field-set form builder (used by "create" modals)                    */
  /* ------------------------------------------------------------------ */
  function buildFields(fields) {
    return fields.map(function (f) {
      var label = '<label class="form-label">' + esc(f.label) + (f.required ? ' <span class="req">*</span>' : '') + '</label>';
      var input;
      if (f.type === 'select') {
        input = '<select class="form-input" data-field="' + f.name + '">' +
          f.options.map(function (o) { return '<option' + (o === f.value ? ' selected' : '') + '>' + esc(o) + '</option>'; }).join('') +
          '</select>';
      } else if (f.type === 'textarea') {
        input = '<textarea class="form-textarea" data-field="' + f.name + '" placeholder="' + esc(f.placeholder || '') + '">' + esc(f.value || '') + '</textarea>';
      } else if (f.type === 'file') {
        input = '<input class="form-input" type="file" accept="image/*" data-field="' + f.name + '">';
      } else {
        input = '<input class="form-input" type="' + (f.type || 'text') + '" data-field="' + f.name + '" placeholder="' + esc(f.placeholder || '') + '" value="' + esc(f.value || '') + '">';
      }
      return '<div class="form-group">' + label + input + '</div>';
    }).join('');
  }
  function readFields(box) {
    var out = {};
    $$('[data-field]', box).forEach(function (el) {
      if (el.type === 'file') { out[el.dataset.field] = el.files && el.files[0]; }
      else { out[el.dataset.field] = el.value.trim(); }
    });
    return out;
  }

  /* ------------------------------------------------------------------ */
  /* Row helpers (label extraction, delete/view/edit, count updates)     */
  /* ------------------------------------------------------------------ */
  var ROW_SELECTOR = 'tr, .list-row, .gallery-item, .directory-card, .attachment, .step-row';

  function getRowLabel(row) {
    var sel = ['.cell-primary', '.list-title', '.gi-title', '.dc-name', '.an', '.step-title', '.mc-title'];
    for (var i = 0; i < sel.length; i++) {
      var el = row.querySelector(sel[i]);
      if (el) return el.textContent.trim();
    }
    return 'this item';
  }

  function getRowBadge(row) {
    return row.querySelector('.badge');
  }

  function statusOptionsFor(panel) {
    var select = panel.querySelector('.filters-row select');
    if (!select) return ['Published', 'Pending Approval', 'Draft'];
    var opts = $$('option', select).map(function (o) { return o.textContent.trim(); }).filter(function (t) {
      return !/^all\s/i.test(t);
    });
    return opts.length ? opts : ['Published', 'Pending Approval', 'Draft'];
  }
  function badgeClassFor(text) {
    var t = text.toLowerCase();
    if (/(published|active|approved|online)/.test(t)) return 'badge-green';
    if (/(pending)/.test(t)) return 'badge-amber';
    if (/(returned|rejected|inactive|reject)/.test(t)) return 'badge-red';
    return 'badge-gray';
  }

  function bumpPaginationCount(panel, delta) {
    var span = panel.querySelector('.pagination span');
    if (!span) return;
    var m = span.textContent.match(/of\s+(\d+)/i);
    if (!m) return;
    var total = Math.max(0, parseInt(m[1], 10) + delta);
    span.textContent = span.textContent.replace(/of\s+\d+/i, 'of ' + total);
  }
  function bumpStat(labelMatch, delta) {
    $$('.stat-card').forEach(function (card) {
      var lbl = card.querySelector('.stat-label');
      if (lbl && labelMatch.test(lbl.textContent)) {
        var val = card.querySelector('.stat-value');
        if (val) val.textContent = Math.max(0, (parseInt(val.textContent, 10) || 0) + delta);
      }
    });
  }

  function removeRow(row, panel) {
    row.classList.add('row-removing');
    setTimeout(function () { row.remove(); }, 200);
    if (panel) bumpPaginationCount(panel, -1);
  }

  function openViewModal(row) {
    var table = row.closest ? row.closest('table') : null;
    var rows = [];
    if (row.tagName === 'TR' && table) {
      var heads = $$('thead th', table).map(function (th) { return th.textContent.trim(); });
      $$('td', row).forEach(function (td, i) {
        if (!heads[i] || /actions/i.test(heads[i])) return;
        rows.push({ k: heads[i], v: td.textContent.replace(/\s+/g, ' ').trim() });
      });
    } else {
      rows.push({ k: 'Title', v: getRowLabel(row) });
      var meta = row.querySelector('.list-meta, .m-preview, .as, .step-desc, .cell-sub');
      if (meta) rows.push({ k: 'Details', v: meta.textContent.trim() });
      var badge = getRowBadge(row);
      if (badge) rows.push({ k: 'Status', v: badge.textContent.trim() });
    }
    var img = row.querySelector('img');
    var body =
      (img ? '<img class="modal-preview-img" src="' + img.src + '" alt="">' : '') +
      rows.map(function (r) {
        return '<div class="modal-view-row"><span class="k"></span><span class="v"></span></div>';
      }).join('');
    var box = openModal('View Details', body);
    var viewRows = $$('.modal-view-row', box);
    viewRows.forEach(function (el, i) {
      el.querySelector('.k').textContent = rows[i].k;
      el.querySelector('.v').textContent = rows[i].v;
    });
  }

  function openEditModal(row, panel) {
    var titleEl = row.querySelector('.cell-primary, .list-title, .gi-title, .dc-name, .an, .step-title');
    var subEl = row.querySelector('.cell-sub, .list-meta, .step-desc');
    var badge = getRowBadge(row);
    var fields = [{ name: 'title', label: 'Title', value: titleEl ? titleEl.textContent.trim() : '', required: true }];
    if (subEl) fields.push({ name: 'sub', label: 'Details', type: 'textarea', value: subEl.textContent.trim() });
    if (badge && panel) fields.push({ name: 'status', label: 'Status', type: 'select', options: statusOptionsFor(panel), value: badge.textContent.trim() });

    var box = openModal('Edit ' + (titleEl ? titleEl.textContent.trim() : 'Item'), buildFields(fields) +
      '<div class="modal-actions"><button type="button" class="btn btn-secondary" data-act="cancel">Cancel</button><button type="button" class="btn btn-primary" data-act="save">Save Changes</button></div>');
    box.querySelector('[data-act="cancel"]').addEventListener('click', closeModal);
    box.querySelector('[data-act="save"]').addEventListener('click', function () {
      var v = readFields(box);
      if (!v.title) { toast('Title is required.', 'error'); return; }
      if (titleEl) titleEl.textContent = v.title;
      if (subEl && v.sub !== undefined) subEl.textContent = v.sub;
      if (badge && v.status) {
        badge.textContent = v.status;
        badge.className = 'badge ' + badgeClassFor(v.status) + (badge.classList.contains('gi-badge') ? ' gi-badge' : '');
      }
      closeModal();
      toast('Changes saved.');
    });
  }

  function openRowMenu(anchorIc, row, panel) {
    closeAllDropdowns();
    var wrap = document.createElement('span');
    wrap.className = 'row-menu';
    anchorIc.parentNode.insertBefore(wrap, anchorIc);
    wrap.appendChild(anchorIc);
    var badge = getRowBadge(row);
    var panelHtml = '<div class="dropdown-panel open">' +
      '<div class="dd-item" data-act="view"><i class="fa-regular fa-eye"></i> View Details</div>' +
      (badge ? '<div class="dd-item" data-act="approve"><i class="fa-solid fa-check"></i> Approve</div>' +
        '<div class="dd-item" data-act="return"><i class="fa-solid fa-rotate-left"></i> Return for Revision</div>' : '') +
      '<div class="dd-item danger" data-act="delete"><i class="fa-regular fa-trash-can"></i> Delete</div>' +
      '</div>';
    wrap.insertAdjacentHTML('beforeend', panelHtml);
    var dd = wrap.querySelector('.dropdown-panel');
    dd.addEventListener('click', function (e) {
      var item = e.target.closest('.dd-item');
      if (!item) return;
      var act = item.dataset.act;
      if (act === 'view') openViewModal(row);
      else if (act === 'delete') {
        confirmAction('Delete "' + getRowLabel(row) + '"? This cannot be undone.', function () {
          removeRow(row, panel);
          toast(getRowLabel(row) + ' deleted.');
        }, { danger: true, okText: 'Delete' });
      } else if (act === 'approve' && badge) {
        badge.textContent = 'Active'; badge.className = 'badge badge-green';
        toast('Marked as active.');
      } else if (act === 'return' && badge) {
        badge.textContent = 'Pending Approval'; badge.className = 'badge badge-amber';
        toast('Returned for revision.');
      }
      dd.classList.remove('open');
      setTimeout(function () { wrap.remove(); anchorIc.remove(); }, 0);
    });
    setTimeout(function () {
      document.addEventListener('click', function onDoc(e) {
        if (!wrap.contains(e.target)) { dd.classList.remove('open'); document.removeEventListener('click', onDoc); }
      });
    }, 0);
  }

  /* ------------------------------------------------------------------ */
  /* Generic delegated click handling for row action icons                */
  /* ------------------------------------------------------------------ */
  document.addEventListener('click', function (e) {
    var ic = e.target.closest('.ic, .dl');
    if (!ic) return;
    var icon = ic.querySelector('i');
    var cls = icon ? icon.className : '';
    var row = ic.closest(ROW_SELECTOR);
    if (!row) return;
    var panel = ic.closest('.panel');

    if (/fa-trash-can/.test(cls)) {
      if (['announcements','news-updates','events','gallery'].indexOf(document.body.dataset.page) !== -1) return;
      e.preventDefault();
      var label = getRowLabel(row);
      confirmAction('Delete "' + label + '"? This cannot be undone.', function () {
        removeRow(row, panel);
        toast(label + ' deleted.');
      }, { danger: true, okText: 'Delete' });

    } else if (/fa-pen-to-square/.test(cls)) {
      if (['announcements','news-updates','events','gallery'].indexOf(document.body.dataset.page) !== -1) return;
      e.preventDefault();
      openEditModal(row, panel);

    } else if (/fa-eye/.test(cls)) {
      if (['announcements','news-updates','events','gallery'].indexOf(document.body.dataset.page) !== -1) return;
      e.preventDefault();
      // On the approval center, "view" opens the dedicated details page.
      if (document.body.dataset.page === 'approval-center') {
        window.location.href = 'super-admin-approval-details.html';
        return;
      }
      openViewModal(row);
    } else if (/fa-download/.test(cls)) {
      e.preventDefault();
      toast('Downloading ' + getRowLabel(row) + '…');
    } else if (/fa-ellipsis-vertical/.test(cls)) {
      e.preventDefault();
      openRowMenu(ic, row, panel);
    }
  });

  /* ------------------------------------------------------------------ */
  /* Search + filter + sort for tables / lists / grids                   */
  /* ------------------------------------------------------------------ */
  function wireFilters() {
    $$('.filters-row').forEach(function (bar) {
      var panel = bar.closest('.panel');
      if (!panel) return;
      var itemsHost = panel.querySelector('.data-table tbody') || panel.querySelector('.gallery-grid') ||
        (panel.querySelector('.list-row') ? panel : null) || panel.querySelector('.directory-grid');
      if (!itemsHost) return;
      var getItems = function () {
        if (itemsHost.tagName === 'TBODY') return $$('tr', itemsHost);
        if (itemsHost.classList.contains('gallery-grid')) return $$('.gallery-item', itemsHost);
        if (itemsHost.classList.contains('directory-grid')) return $$('.directory-card', itemsHost);
        return $$('.list-row', itemsHost);
      };
      var searchInput = bar.querySelector('.field.search input');
      var selects = $$('.field select', bar);
      var statusSelect = selects[0];

      function applyFilters() {
        var q = searchInput ? searchInput.value.trim().toLowerCase() : '';
        var statusVal = statusSelect ? statusSelect.value : '';
        var items = getItems();
        var shown = 0;
        items.forEach(function (item) {
          var text = item.textContent.toLowerCase();
          var matchesSearch = !q || text.indexOf(q) !== -1;
          var matchesStatus = true;
          if (statusSelect && !/^all\s/i.test(statusVal)) {
            var badge = item.querySelector('.badge');
            matchesStatus = badge ? badge.textContent.trim().toLowerCase() === statusVal.toLowerCase() : true;
          }
          var show = matchesSearch && matchesStatus;
          item.style.display = show ? '' : 'none';
          if (show) shown++;
        });
        var noRow = itemsHost.querySelector('.no-results-row');
        if (shown === 0) {
          if (!noRow) {
            if (itemsHost.tagName === 'TBODY') {
              var colCount = ($('table', panel).querySelectorAll('thead th') || []).length || 1;
              itemsHost.insertAdjacentHTML('beforeend', '<tr class="no-results-row"><td colspan="' + colCount + '">No matching results.</td></tr>');
            } else {
              itemsHost.insertAdjacentHTML('beforeend', '<div class="no-results-row" style="padding:24px;color:var(--gray-400);font-size:13px;">No matching results.</div>');
            }
          }
        } else if (noRow) {
          noRow.remove();
        }
      }
      if (searchInput) searchInput.addEventListener('input', applyFilters);
      if (statusSelect) statusSelect.addEventListener('change', applyFilters);
    });
  }

  /* ------------------------------------------------------------------ */
  /* Pagination (cosmetic paging over the same fake dataset)             */
  /* ------------------------------------------------------------------ */
  function wirePagination() {
    $$('.pagination .page-nums').forEach(function (nums) {
      nums.addEventListener('click', function (e) {
        var btn = e.target.closest('.page-btn');
        if (!btn) return;
        var buttons = $$('.page-btn', nums);
        var numeric = buttons.filter(function (b) { return /^\d+$/.test(b.textContent.trim()); });
        if (/^\d+$/.test(btn.textContent.trim())) {
          numeric.forEach(function (b) { b.classList.remove('active'); });
          btn.classList.add('active');
          toast('Showing page ' + btn.textContent.trim() + '.');
        } else {
          var current = numeric.findIndex(function (b) { return b.classList.contains('active'); });
          var isNext = !!btn.querySelector('.fa-chevron-right');
          var target = isNext ? Math.min(numeric.length - 1, current + 1) : Math.max(0, current - 1);
          numeric.forEach(function (b) { b.classList.remove('active'); });
          if (numeric[target]) { numeric[target].classList.add('active'); toast('Showing page ' + numeric[target].textContent.trim() + '.'); }
        }
      });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Topbar: notification bell + user chip dropdowns                     */
  /* ------------------------------------------------------------------ */
  function closeAllDropdowns() {
    $$('.dropdown-panel.open').forEach(function (p) { p.classList.remove('open'); });
  }
  function toggleDropdown(anchor, html) {
    var existing = anchor.querySelector('.dropdown-panel');
    if (existing) {
      var willOpen = !existing.classList.contains('open');
      closeAllDropdowns();
      if (willOpen) existing.classList.add('open');
      return;
    }
    closeAllDropdowns();
    anchor.classList.add('dropdown-anchor');
    anchor.insertAdjacentHTML('beforeend', html);
    requestAnimationFrame(function () {
      var panel = anchor.querySelector('.dropdown-panel');
      if (panel) panel.classList.add('open');
    });
  }
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.dropdown-anchor') && !e.target.closest('.icon-button') && !e.target.closest('.user-chip') && !e.target.closest('.office-switcher')) {
      closeAllDropdowns();
    }
  });

  function wireTopbar() {
    // Notification bell dropdown and user-chip dropdown are now static HTML
    // in representative_dashboard_base.html; each is wired up below.
    var officeSwitcher = $('.office-switcher');
    if (officeSwitcher) {
      officeSwitcher.addEventListener('click', function (e) {
        e.stopPropagation();
        officeSwitcher.classList.toggle('open');
        var label = officeSwitcher.querySelector('.label');
        toast('You are currently managing: ' + (label ? label.textContent.trim() : 'this office') + '.');
      });
    }
  }

function wireLogout() {
  var modal = document.getElementById('logout-confirm-modal');
  if (!modal) return;
  wireStaticModalChrome(modal); // reuses the existing X / Cancel / backdrop / Escape handling
  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('.sidebar-logout, [data-act="logout"]');
    if (!trigger) return;
    e.preventDefault();
    openStaticModal(modal);
  });
}

  /* ------------------------------------------------------------------ */
  /* Dashboard quick "create" shortcuts (bottom of dashboard panels)      */
  /* ------------------------------------------------------------------ */
  function wireDashboardQuickCreateLinks() {
    $$('.btn-secondary.btn-block').forEach(function (btn) {
      var text = btn.textContent.trim();
      var map = {
        'Create Announcement': 'announcements.html',
        'Add News': 'news-updates.html',
        'Add Event': 'events.html'
      };
      if (map[text]) btn.addEventListener('click', function () { window.location.href = map[text]; });
    });
  }

  // Shared row-insertion for the plain "table + create modal" pages
  // (Announcements, News & Updates). The form itself is static HTML;
  // this just builds the new <tr> from the submitted values.
  function insertContentRow(panel, cfg, v) {
    var tbody = panel.querySelector('tbody');
    var status = v.status || 'Published';
    var thumbHtml = cfg.useImage
      ? '<img src="https://images.unsplash.com/photo-1622547748225-3fc4abd2cca0?q=80&w=200&auto=format&fit=crop" style="width:44px;height:44px;border-radius:9px;object-fit:cover;">'
      : '<span class="row-thumb" style="background:' + cfg.thumbBg + ';color:' + cfg.thumbColor + ';"><i class="fa-solid ' + cfg.icon + '"></i></span>';
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td class="row-icon-name">' + thumbHtml + '<div><div class="cell-primary"></div><div class="cell-sub"></div></div></td>' +
      '<td>' + todayStr() + '<br><span class="cell-sub">' + nowTime() + '</span></td>' +
      '<td>0</td>' +
      '<td><span class="badge ' + badgeClassFor(status) + '"></span></td>' +
      '<td><div class="action-icons"><span class="ic"><i class="fa-regular fa-eye"></i></span><span class="ic"><i class="fa-regular fa-pen-to-square"></i></span><span class="ic"><i class="fa-regular fa-trash-can"></i></span></div></td>';
    tr.querySelector('.cell-primary').textContent = v.title;
    tr.querySelector('.cell-sub').textContent = v.sub || '';
    tr.querySelector('.badge').textContent = status;
    tbody.insertBefore(tr, tbody.firstChild);
    bumpPaginationCount(panel, 1);
    if (cfg.statLabel) bumpStat(cfg.statLabel, 1);
  }

  function wireAnnouncementsCreate() {
    if (document.body.dataset.page !== 'announcements') return;
    var trigger = document.getElementById('open-create-announcement');
    var modal = document.getElementById('create-announcement-modal');
    if (!trigger || !modal) return;
    wireStaticModalChrome(modal);
    trigger.addEventListener('click', function () { openStaticModal(modal); });
    // no submit listener here — the <form> now posts to Django normally
  }

  function wireAnnouncementViewModals() {
    if (document.body.dataset.page !== 'announcements') return;
    document.querySelectorAll('[data-view-target]').forEach(function (trigger) {
      var modal = document.getElementById(trigger.dataset.viewTarget);
      if (!modal) return;
      wireStaticModalChrome(modal);
      trigger.addEventListener('click', function () { openStaticModal(modal); });
    });
  }

  function wireAnnouncementEditModals() {
    if (document.body.dataset.page !== 'announcements') return;
    document.querySelectorAll('[data-edit-target]').forEach(function (trigger) {
      var modal = document.getElementById(trigger.dataset.editTarget);
      if (!modal) return;
      wireStaticModalChrome(modal);
      trigger.addEventListener('click', function () { openStaticModal(modal); });
    });
  }

  function wireAnnouncementDeleteModals() {
    if (document.body.dataset.page !== 'announcements') return;
    document.querySelectorAll('[data-delete-target]').forEach(function (trigger) {
      var modal = document.getElementById(trigger.dataset.deleteTarget);
      if (!modal) return;
      wireStaticModalChrome(modal);
      trigger.addEventListener('click', function () { openStaticModal(modal); });
    });
  }

  function wireNewsCreate() {
    if (document.body.dataset.page !== 'news-updates') return;
    var trigger = document.getElementById('open-add-news');
    var modal = document.getElementById('add-news-modal');
    if (!trigger || !modal) return;
    wireStaticModalChrome(modal);
    trigger.addEventListener('click', function () { openStaticModal(modal); });
    // no submit listener here — the <form> now posts to Django normally
  }

  function wireNewsViewModals() {
    if (document.body.dataset.page !== 'news-updates') return;
    document.querySelectorAll('[data-view-target]').forEach(function (trigger) {
      var modal = document.getElementById(trigger.dataset.viewTarget);
      if (!modal) return;
      wireStaticModalChrome(modal);
      trigger.addEventListener('click', function () { openStaticModal(modal); });
    });
  }

  function wireNewsEditModals() {
    if (document.body.dataset.page !== 'news-updates') return;
    document.querySelectorAll('[data-edit-target]').forEach(function (trigger) {
      var modal = document.getElementById(trigger.dataset.editTarget);
      if (!modal) return;
      wireStaticModalChrome(modal);
      trigger.addEventListener('click', function () { openStaticModal(modal); });
    });
  }

  function wireNewsDeleteModals() {
    if (document.body.dataset.page !== 'news-updates') return;
    document.querySelectorAll('[data-delete-target]').forEach(function (trigger) {
      var modal = document.getElementById(trigger.dataset.deleteTarget);
      if (!modal) return;
      wireStaticModalChrome(modal);
      trigger.addEventListener('click', function () { openStaticModal(modal); });
    });
  }

  function wireEventsCreate() {
    if (document.body.dataset.page !== 'events') return;
    var trigger = document.getElementById('open-add-event');
    var modal = document.getElementById('add-event-modal');
    if (!trigger || !modal) return;
    wireStaticModalChrome(modal);
    trigger.addEventListener('click', function () { openStaticModal(modal); });
    // no submit listener here — the <form> now posts to Django normally
  }

  function wireEventViewModals() {
    if (document.body.dataset.page !== 'events') return;
    document.querySelectorAll('[data-view-target]').forEach(function (trigger) {
      var modal = document.getElementById(trigger.dataset.viewTarget);
      if (!modal) return;
      wireStaticModalChrome(modal);
      trigger.addEventListener('click', function () { openStaticModal(modal); });
    });
  }

  function wireEventEditModals() {
    if (document.body.dataset.page !== 'events') return;
    document.querySelectorAll('[data-edit-target]').forEach(function (trigger) {
      var modal = document.getElementById(trigger.dataset.editTarget);
      if (!modal) return;
      wireStaticModalChrome(modal);
      trigger.addEventListener('click', function () { openStaticModal(modal); });
    });
  }

  function wireEventDeleteModals() {
    if (document.body.dataset.page !== 'events') return;
    document.querySelectorAll('[data-delete-target]').forEach(function (trigger) {
      var modal = document.getElementById(trigger.dataset.deleteTarget);
      if (!modal) return;
      wireStaticModalChrome(modal);
      trigger.addEventListener('click', function () { openStaticModal(modal); });
    });
  }

  function wireDownloadableFormsCreate() {
    if (document.body.dataset.page !== 'downloadable-forms') return;
    var trigger = document.getElementById('open-add-form');
    var modal = document.getElementById('add-form-modal');
    var panel = trigger ? trigger.closest('.panel') : null;
    wireCreateModal(trigger, modal, function (fd) {
      var title = (fd.get('title') || '').toString().trim();
      if (!title) { toast('Form name is required.', 'error'); return; }
      var tbody = panel.querySelector('tbody');
      var status = fd.get('status') || 'Published';
      var size = (fd.get('size') || '').toString().trim() || '200 KB';
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td class="row-icon-name"><span class="row-thumb" style="background:var(--red-50);color:var(--red-600);"><i class="fa-solid fa-file-pdf"></i></span><span class="cell-primary"></span></td>' +
        '<td><span class="tag"></span></td>' +
        '<td>PDF · ' + esc(size) + '</td>' +
        '<td>0</td>' +
        '<td><span class="badge ' + badgeClassFor(status) + '"></span></td>' +
        '<td><div class="action-icons"><span class="ic"><i class="fa-solid fa-download"></i></span><span class="ic"><i class="fa-regular fa-pen-to-square"></i></span><span class="ic"><i class="fa-regular fa-trash-can"></i></span></div></td>';
      tr.querySelector('.cell-primary').textContent = title;
      tr.querySelector('.tag').textContent = fd.get('category') || 'Permits';
      tr.querySelector('.badge').textContent = status;
      tbody.insertBefore(tr, tbody.firstChild);
      bumpPaginationCount(panel, 1);
      bumpStat(/Downloadable Forms/, 1);
      closeStaticModal(modal);
      toast(title + ' added.');
    });
  }

  function wireGalleryCreate() {
    if (document.body.dataset.page !== 'gallery') return;
    var trigger = document.getElementById('open-upload-photo');
    var modal = document.getElementById('upload-photo-modal');
    if (!trigger || !modal) return;
    wireStaticModalChrome(modal);
    trigger.addEventListener('click', function () { openStaticModal(modal); });
    // no submit listener here — the <form> now posts to Django normally
  }

  function wireAccountToggle() {
    if (document.body.dataset.page !== 'my-account') return;
    var editBtn = document.getElementById('edit-account-btn');
    var cancelBtn = document.getElementById('cancel-edit-account');
    var viewMode = document.getElementById('account-view-mode');
    var editMode = document.getElementById('account-edit-mode');
    if (!editBtn || !viewMode || !editMode) return;

    editBtn.addEventListener('click', function () {
      viewMode.style.display = 'none';
      editMode.style.display = 'block';
    });
    if (cancelBtn) {
      cancelBtn.addEventListener('click', function () {
        editMode.style.display = 'none';
        viewMode.style.display = 'block';
      });
    }
  }
  

function wireGalleryViewModals() {
  if (document.body.dataset.page !== 'gallery') return;
  document.querySelectorAll('[data-view-target]').forEach(function (item) {
    var modal = document.getElementById(item.dataset.viewTarget);
    if (!modal) return;
    wireStaticModalChrome(modal);
    item.addEventListener('click', function (e) {
      if (e.target.closest('.gi-actions')) return; // let edit/delete icons handle their own click
      openStaticModal(modal);
    });
  });
}

function wireGalleryDeleteModals() {
  if (document.body.dataset.page !== 'gallery') return;
  document.querySelectorAll('[data-delete-target]').forEach(function (trigger) {
    var modal = document.getElementById(trigger.dataset.deleteTarget);
    if (!modal) return;
    wireStaticModalChrome(modal);
    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      openStaticModal(modal);
    });
  });
}

function wireGalleryLightboxDelete() {
  if (document.body.dataset.page !== 'gallery') return;
  document.querySelectorAll('[data-open-delete]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var lightbox = btn.closest('.modal-backdrop');
      var confirmModal = document.getElementById(btn.dataset.openDelete);
      if (lightbox) closeStaticModal(lightbox);
      if (confirmModal) openStaticModal(confirmModal);
    });
  });
}

function wireOfficeProfileToggle() {
  if (document.body.dataset.page !== 'office-profile') return;
  var editBtn = document.getElementById('edit-office-profile-btn');
  var cancelBtn = document.getElementById('cancel-edit-office-profile');
  var viewMode = document.getElementById('profile-view-mode');
  var editMode = document.getElementById('profile-edit-mode');
  if (!editBtn || !viewMode || !editMode) return;

  editBtn.addEventListener('click', function () {
    viewMode.style.display = 'none';
    editMode.style.display = 'block';
  });
  if (cancelBtn) {
    cancelBtn.addEventListener('click', function () {
      editMode.style.display = 'none';
      viewMode.style.display = 'block';
    });
  }
}

  function wireOfficeOverviewCreate() {
    if (document.body.dataset.page !== 'office-overview') return;
    var trigger = document.getElementById('open-add-office');
    var modal = document.getElementById('add-office-modal');
    var panel = trigger ? trigger.closest('.panel') : null;
    wireCreateModal(trigger, modal, function (fd) {
      var title = (fd.get('title') || '').toString().trim();
      if (!title) { toast('Office name is required.', 'error'); return; }
      var tbody = panel.querySelector('tbody');
      var status = fd.get('status') || 'Active';
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td class="row-icon-name"><span class="row-thumb" style="background:var(--gray-100);color:var(--gray-600);"><i class="fa-solid fa-building"></i></span><span class="cell-primary"></span></td>' +
        '<td class="rep"></td>' +
        '<td><span class="badge"></span></td>' +
        '<td>Today, ' + nowTime() + '</td>' +
        '<td>0</td>' +
        '<td><div class="action-icons"><span class="ic"><i class="fa-regular fa-eye"></i></span><span class="ic"><i class="fa-regular fa-pen-to-square"></i></span><span class="ic"><i class="fa-solid fa-ellipsis-vertical"></i></span></div></td>';
      tr.querySelector('.cell-primary').textContent = title;
      tr.querySelector('.rep').textContent = fd.get('rep') || '—';
      tr.querySelector('.badge').className = 'badge ' + badgeClassFor(status);
      tr.querySelector('.badge').textContent = status;
      tbody.insertBefore(tr, tbody.firstChild);
      bumpPaginationCount(panel, 1);
      bumpStat(/Total Offices/, 1);
      if (/active/i.test(status)) bumpStat(/^Active Offices$/, 1); else bumpStat(/Pending Approval/, 1);
      closeStaticModal(modal);
      toast(title + ' added.');
    });
  }

  function wireAddServiceCreate() {
    if (document.body.dataset.page !== 'office-profile') return;
    var trigger = document.getElementById('open-add-service');
    var modal = document.getElementById('add-service-modal');
    var panel = trigger ? trigger.closest('.panel') : null;
    wireCreateModal(trigger, modal, function (fd) {
      var name = (fd.get('name') || '').toString().trim();
      if (!name) { toast('Service name is required.', 'error'); return; }
      var body = panel.querySelector('.panel-body');
      var row = document.createElement('div');
      row.className = 'info-row';
      row.innerHTML = '<span class="k"><i class="fa-solid fa-star" style="color:var(--blue-600);margin-right:8px;"></i><span class="nm"></span></span>';
      row.querySelector('.nm').textContent = name;
      body.appendChild(row);
      closeStaticModal(modal);
      toast(name + ' added to services.');
    });
  }

  /* ------------------------------------------------------------------ */
  /* Page: office-rep-dashboard                                          */
  /* ------------------------------------------------------------------ */
  function wireDashboard() {
    if (document.body.dataset.page !== 'dashboard') return;
    var pageMap = {
      'Announcements': 'announcements.html',
      'News & Updates': 'news-updates.html',
      'Upcoming Events': 'events.html',
      'Downloadable Forms': 'downloadable-forms.html',
      'Gallery Photos': 'gallery.html',
      'Recent Announcements': 'announcements.html',
      'Recent News & Updates': 'news-updates.html'
    };
    $$('.stat-card').forEach(function (card) {
      var label = card.querySelector('.stat-label');
      var link = card.querySelector('.stat-sub');
      if (label && link && pageMap[label.textContent.trim()]) {
        link.setAttribute('href', pageMap[label.textContent.trim()]);
      }
    });
    $$('.panel-header .link').forEach(function (link) {
      var h2 = link.closest('.panel-header').querySelector('h2');
      var key = h2 ? h2.textContent.trim() : '';
      if (pageMap[key]) link.setAttribute('href', pageMap[key]);
    });
    var quickMap = {
      'Create Announcement': 'announcements.html',
      'Add News': 'news-updates.html',
      'Add Event': 'events.html',
      'Upload Form': 'downloadable-forms.html',
      'Upload Photo': 'gallery.html',
      'Edit Office Profile': 'office-profile.html'
    };
    $$('.quick-action').forEach(function (qa) {
      var text = qa.textContent.trim();
      if (quickMap[text]) {
        qa.style.cursor = 'pointer';
        qa.addEventListener('click', function () { window.location.href = quickMap[text]; });
      }
    });
    var monthSelect = $('.panel-header select');
    if (monthSelect) monthSelect.addEventListener('change', function () {
      toast('Showing overview for ' + monthSelect.value + '.');
    });
  }
  /* Page: office-rep-dashboard                                          */
  function wirePasswordToggles() {
    document.querySelectorAll('.toggle-password').forEach(function (icon) {
      icon.addEventListener('click', function () {
        var input = document.getElementById(icon.dataset.target);
        if (!input) return;
        var showing = input.type === 'text';
        input.type = showing ? 'password' : 'text';
        icon.classList.toggle('fa-eye', showing);
        icon.classList.toggle('fa-eye-slash', !showing);
      });
    });
  }
  /* ==========================message for the change pass page============================ */
  function wirePasswordMessageAutoHide() {
    var msg = document.getElementById('pw-message');
    if (!msg) return;
    setTimeout(function () {
      msg.style.transition = 'opacity 0.4s ease';
      msg.style.opacity = '0';
      setTimeout(function () { msg.remove(); }, 400);
    }, 4000);
  }

  /* ------------------------------------------------------------------ */
  /* Page: my-account / change-password / office-profile / office-location */
  /* ------------------------------------------------------------------ */
  function wireSimpleForms() {
    var page = document.body.dataset.page;

    // Avatar / logo upload buttons
    $$('.avatar-upload .btn').forEach(function (btn) {
      var wrap = btn.closest('.avatar-upload');
      if (wrap.querySelector('input[type="file"]')) return;   // ADD THIS LINE — a real, named upload input already exists here, don't hijack it
      var img = wrap.querySelector('img');
      var input = document.createElement('input');
      input.type = 'file'; input.accept = 'image/*'; input.style.display = 'none';
      btn.parentNode.appendChild(input);
      btn.addEventListener('click', function () { input.click(); });
      input.addEventListener('change', function () {
        if (!input.files[0]) return;
        var reader = new FileReader();
        reader.onload = function (e) {
          img.src = e.target.result;
          var chipImg = $('.user-chip img');
          if (chipImg && /change photo/i.test(btn.textContent)) chipImg.src = e.target.result;
          toast('Photo updated.');
        };
        reader.readAsDataURL(input.files[0]);
      });
    });

    if (page === 'my-account') {
      var saveBtn = $$('.btn-primary').find(function (b) { return /save changes/i.test(b.textContent); });
      var discardBtn = $$('.btn-secondary').find(function (b) { return /discard/i.test(b.textContent); });
      var inputs = $$('.form-input');
      var defaults = inputs.map(function (i) { return i.value; });
      if (saveBtn) saveBtn.addEventListener('click', function () {
        var nameInput = inputs[0];
        if (nameInput) {
          var chipName = $('.user-chip .name');
          if (chipName) chipName.textContent = nameInput.value;
        }
        toast('Profile updated successfully.');
      });
      if (discardBtn) discardBtn.addEventListener('click', function () {
        inputs.forEach(function (i, idx) { i.value = defaults[idx]; });
        toast('Changes discarded.');
      });
    }

    if (page === 'office-profile') {
      var opSave = $$('.btn-primary').find(function (b) { return /save changes/i.test(b.textContent); });
      var opDiscard = $$('.btn-secondary').find(function (b) { return /discard/i.test(b.textContent); });
      var opInputs = $$('.form-input, .form-textarea');
      var opDefaults = opInputs.map(function (i) { return i.value; });
      if (opSave) opSave.addEventListener('click', function () { toast('Office profile updated successfully.'); });
      if (opDiscard) opDiscard.addEventListener('click', function () {
        opInputs.forEach(function (i, idx) { i.value = opDefaults[idx]; });
        toast('Changes discarded.');
      });
    }

    if (page === 'office-location') {
      var saveLoc = $$('.btn-primary').find(function (b) { return /save location/i.test(b.textContent); });
      if (saveLoc) saveLoc.addEventListener('click', function () {
        var inputsLoc = $$('.form-input');
        var addr = inputsLoc.map(function (i) { return i.value; }).filter(Boolean).join(', ');
        var mcAddr = $('.mc-addr');
        if (mcAddr && inputsLoc[0] && inputsLoc[2]) mcAddr.innerHTML = esc(inputsLoc[0].value) + '<br>' + esc(inputsLoc[2].value);
        toast('Office location updated.');
      });
    }
  }

  /* preview function when selecting photo in my account page */

  function wireAccountPhotoPreview() {
    if (document.body.dataset.page !== 'my-account') return;
    var input = document.getElementById('account-photo-input');
    var preview = document.getElementById('account-photo-preview');
    var chipImg = document.querySelector('.user-chip img');
    var cancelBtn = document.getElementById('cancel-edit-account');
    if (!input) return;

    var originalPreviewSrc = preview ? preview.src : null;
    var originalChipSrc = chipImg ? chipImg.src : null;

    input.addEventListener('change', function () {
      var file = input.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        if (preview) preview.src = e.target.result;
        if (chipImg) chipImg.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });

    if (cancelBtn) {
      cancelBtn.addEventListener('click', function () {
        input.value = '';
        if (preview) preview.src = originalPreviewSrc;
        if (chipImg) chipImg.src = originalChipSrc;
      });
    }
  }

  /* ------------------------------------------------------------------ */
  /* Page: messages                                                       */
  /* ------------------------------------------------------------------ */
  function wireMessages() {
    if (document.body.dataset.page !== 'messages') return;
    $$('.message-item').forEach(function (item) {
      item.addEventListener('click', function () {
        $$('.message-item').forEach(function (i) { i.classList.remove('active'); });
        item.classList.add('active');
        item.classList.remove('unread');
        var dot = item.querySelector('.m-dot');
        if (dot) dot.remove();
        var name = item.querySelector('.m-name');
        var subject = item.querySelector('.m-subject');
        var headName = $('.thread-head .thread-head, .thread-head div div');
        var headEl = $('.thread-head > div:last-child > div:first-child');
        var headSub = $('.thread-head > div:last-child > div:last-child');
        var threadImg = $('.thread-head img');
        if (headEl && name) headEl.textContent = name.textContent.trim();
        if (headSub && subject) headSub.textContent = subject.textContent.trim();
        if (threadImg) threadImg.src = item.querySelector('img').src;
      });
    });
    var input = $('.thread-input input');
    var sendBtn = $('.thread-input button');
    var body = $('.thread-body');
    function send() {
      if (!input || !input.value.trim() || !body) return;
      var bubble = document.createElement('div');
      bubble.className = 'thread-bubble out';
      bubble.textContent = input.value.trim();
      var time = document.createElement('div');
      time.className = 'thread-time out';
      time.textContent = nowTime();
      body.appendChild(bubble);
      body.appendChild(time);
      body.scrollTop = body.scrollHeight;
      input.value = '';
    }
    if (sendBtn) sendBtn.addEventListener('click', send);
    if (input) input.addEventListener('keydown', function (e) { if (e.key === 'Enter') send(); });
  }

  /* ------------------------------------------------------------------ */
  /* Page: office-rep-service-details                                    */
  /* ------------------------------------------------------------------ */
  function wireServiceDetails() {
    if (document.body.dataset.page !== 'service-details') return;
    $$('.subtab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        $$('.subtab').forEach(function (t) { t.classList.remove('active'); });
        tab.classList.add('active');
        toast('Viewing: ' + tab.textContent.trim());
      });
    });
    var previewBtn = $$('.btn-secondary').find(function (b) { return /preview/i.test(b.textContent); });
    if (previewBtn) previewBtn.addEventListener('click', function () { toast('Opening public preview…'); });
    var topSaveBtn = $$('.panel .btn-primary').find(function (b) { return /save changes/i.test(b.textContent); });
    if (topSaveBtn) topSaveBtn.addEventListener('click', function () { toast('Changes saved as draft.'); });

    var editReminders = $$('.btn-secondary.btn-sm').find(function (b) { return /edit reminders/i.test(b.textContent); });
    if (editReminders) editReminders.addEventListener('click', function () {
      var list = $('.reminder-list');
      var items = $$('li', list).map(function (li) { return li.textContent.trim(); }).join('\n');
      var box = openModal('Edit Important Reminders', buildFields([{ name: 'items', label: 'One reminder per line', type: 'textarea', value: items }]) +
        '<div class="modal-actions"><button type="button" class="btn btn-secondary" data-act="cancel">Cancel</button><button type="button" class="btn btn-primary" data-act="save">Save</button></div>', { wide: true });
      box.querySelector('[data-act="cancel"]').addEventListener('click', closeModal);
      box.querySelector('[data-act="save"]').addEventListener('click', function () {
        var v = readFields(box);
        var lines = v.items.split('\n').map(function (l) { return l.trim(); }).filter(Boolean);
        list.innerHTML = lines.map(function (l) { return '<li></li>'; }).join('');
        $$('li', list).forEach(function (li, i) { li.textContent = lines[i]; });
        closeModal();
        toast('Reminders updated.');
      });
    });

    var addStepBtn = $$('.btn-secondary.btn-sm').find(function (b) { return /add step/i.test(b.textContent); });
    var addStepModal = document.getElementById('add-step-modal');
    if (addStepBtn && addStepModal) {
      var stepsHost = addStepBtn.closest('.panel').querySelector('.panel-body');
      wireCreateModal(addStepBtn, addStepModal, function (fd) {
        var title = (fd.get('title') || '').toString().trim();
        if (!title) { toast('Step title is required.', 'error'); return; }
        var num = $$('.step-row', stepsHost).length + 1;
        var row = document.createElement('div');
        row.className = 'step-row';
        row.innerHTML = '<span class="step-num"></span><div style="flex:1;"><div class="step-title"></div><div class="step-desc"></div></div>' +
          '<div class="step-actions"><span class="ic" style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;color:var(--gray-400);"><i class="fa-regular fa-pen-to-square"></i></span><span class="ic" style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;color:var(--gray-400);"><i class="fa-regular fa-trash-can"></i></span></div>';
        row.querySelector('.step-num').textContent = num;
        row.querySelector('.step-title').textContent = title;
        row.querySelector('.step-desc').textContent = fd.get('desc') || '';
        stepsHost.appendChild(row);
        closeStaticModal(addStepModal);
        toast('Step added.');
      });
    }

    var addFormBtn = $$('.panel-header .btn-primary.btn-sm').find(function (b) { return /add form/i.test(b.textContent); });
    var addFormModal = document.getElementById('add-service-form-modal');
    if (addFormBtn && addFormModal) {
      var formsHost = addFormBtn.closest('.panel').querySelector('.panel-body');
      wireCreateModal(addFormBtn, addFormModal, function (fd) {
        var title = (fd.get('title') || '').toString().trim();
        if (!title) { toast('Form name is required.', 'error'); return; }
        var status = fd.get('status') || 'Published';
        var size = (fd.get('size') || '').toString().trim() || '200 KB';
        var row = document.createElement('div');
        row.className = 'attachment';
        row.innerHTML =
          '<span class="af"><i class="fa-solid fa-file-pdf"></i></span>' +
          '<div><div class="an"></div><div class="as">PDF · ' + esc(size) + '</div></div>' +
          '<span class="badge ' + badgeClassFor(status) + '" style="margin-left:auto;"></span>';
        row.querySelector('.an').textContent = title;
        row.querySelector('.badge').textContent = status;
        var link = formsHost.querySelector('a.link');
        if (link) formsHost.insertBefore(row, link); else formsHost.appendChild(row);
        closeStaticModal(addFormModal);
        toast(title + ' added.');
      });
    }

    $$('.panel-header .btn-secondary.btn-sm').forEach(function (btn) {
      if (!/^edit$/i.test(btn.textContent.trim())) return;
      btn.addEventListener('click', function () {
        var body = btn.closest('.panel').querySelector('.panel-body');
        var rows = $$('.info-row', body);
        var fields = rows.map(function (r, i) {
          var k = r.querySelector('.k').textContent.trim();
          var vEl = r.querySelector('.v');
          return { name: 'f' + i, label: k, value: vEl ? vEl.textContent.trim() : '' };
        });
        var box = openModal('Edit ' + btn.closest('.panel').querySelector('h2').textContent.trim(), buildFields(fields) +
          '<div class="modal-actions"><button type="button" class="btn btn-secondary" data-act="cancel">Cancel</button><button type="button" class="btn btn-primary" data-act="save">Save</button></div>');
        box.querySelector('[data-act="cancel"]').addEventListener('click', closeModal);
        box.querySelector('[data-act="save"]').addEventListener('click', function () {
          var v = readFields(box);
          rows.forEach(function (r, i) {
            var vEl = r.querySelector('.v');
            if (!vEl) return;
            var badge = vEl.querySelector('.badge');
            if (badge) { badge.textContent = v['f' + i]; badge.className = 'badge ' + badgeClassFor(v['f' + i]); }
            else vEl.textContent = v['f' + i];
          });
          closeModal();
          toast('Updated.');
        });
      });
    });
  }
  /* ------------------------------------------------------------------ */
  /* Page: super-admin-approval-center                                   */
  /* ------------------------------------------------------------------ */
  function wireApprovalCenter() {
    if (document.body.dataset.page !== 'approval-center') return;
    var tabs = $$('.tab');
    var rows = $$('tbody tr');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        tabs.forEach(function (t) { t.classList.remove('active'); });
        tab.classList.add('active');
        var label = tab.childNodes[0].textContent.trim();
        rows.forEach(function (row) {
          if (/^all$/i.test(label)) { row.style.display = ''; return; }
          var tag = row.querySelector('.tag');
          var typeText = tag ? tag.textContent.trim() : '';
          var singular = label.replace(/s$/, '');
          var match = new RegExp(singular, 'i').test(typeText) || new RegExp(label, 'i').test(typeText);
          row.style.display = match ? '' : 'none';
        });
      });
    });
  }

  /* ------------------------------------------------------------------ */
  /* Page: super-admin-approval-details                                  */
  /* ------------------------------------------------------------------ */
  function wireApprovalDetails() {
    if (document.body.dataset.page !== 'approval-details') return;
    var actions = $$('.review-action');
    actions.forEach(function (a) {
      a.addEventListener('click', function () {
        actions.forEach(function (x) { x.classList.remove('selected'); });
        a.classList.add('selected');
      });
    });
    var textarea = $('.note-input');
    var count = $('.char-count');
    if (textarea) {
      textarea.setAttribute('maxlength', '500');
      textarea.addEventListener('input', function () {
        if (count) count.textContent = textarea.value.length + ' / 500';
      });
    }
    var cancelBtn = $$('.btn-secondary').find(function (b) { return /cancel/i.test(b.textContent); });
    if (cancelBtn) cancelBtn.addEventListener('click', function () { window.location.href = 'super-admin-approval-center.html'; });
    var submitBtn = $$('.btn-primary').find(function (b) { return /submit review/i.test(b.textContent); });
    if (submitBtn) submitBtn.addEventListener('click', function () {
      var selected = $('.review-action.selected');
      var kind = selected ? selected.classList.contains('approve') ? 'approve' : selected.classList.contains('revise') ? 'revise' : 'reject' : 'approve';
      var msg = { approve: 'Content approved and published.', revise: 'Returned to sender for revision.', reject: 'Content rejected.' }[kind];
      toast(msg);
      setTimeout(function () { window.location.href = 'super-admin-approval-center.html'; }, 900);
    });
  }

  /* ------------------------------------------------------------------ */
  /* Page: super-admin-office-overview                                   */
  /* ------------------------------------------------------------------ */
  function wireOfficeOverview() {
    if (document.body.dataset.page !== 'office-overview') return;
    // status select filtering already handled by wireFilters(); nothing else special.
  }

  // User chip dropdown — plain JavaScript only (no framework/jQuery).
  (function () {
    var chip = document.querySelector('.user-chip');
    var dropdown = document.getElementById('userDropdown');
    if (!chip || !dropdown) return;

    function positionDropdown() {
      var rect = chip.getBoundingClientRect();
      dropdown.style.top = (rect.bottom + 10) + 'px';
      dropdown.style.right = (window.innerWidth - rect.right) + 'px';
    }

    function openDropdown() {
      // Close any other open dropdown-panels (notifications, etc.) first.
      document.querySelectorAll('.dropdown-panel.open').forEach(function (p) {
        if (p !== dropdown) p.classList.remove('open');
      });
      positionDropdown();
      dropdown.classList.add('open');
      dropdown.setAttribute('aria-hidden', 'false');
    }

    function closeDropdown() {
      dropdown.classList.remove('open');
      dropdown.setAttribute('aria-hidden', 'true');
    }

    function isOpen() {
      return dropdown.classList.contains('open');
    }

    chip.addEventListener('click', function (e) {
      e.stopPropagation();
      isOpen() ? closeDropdown() : openDropdown();
    });

    document.addEventListener('click', function (e) {
      if (isOpen() && !e.target.closest('#userDropdown') && !e.target.closest('.user-chip')) {
        closeDropdown();
      }
    });

    window.addEventListener('resize', function () { if (isOpen()) positionDropdown(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && isOpen()) closeDropdown(); });
  })();

  // Notification bell dropdown — plain JavaScript only (no framework/jQuery).
  (function () {
    var bell = document.getElementById('notifBellBtn');
    var dropdown = document.getElementById('notifDropdown');
    if (!bell || !dropdown) return;

    function positionDropdown() {
      var rect = bell.getBoundingClientRect();
      dropdown.style.top = (rect.bottom + 10) + 'px';
      dropdown.style.right = (window.innerWidth - rect.right) + 'px';
    }

    function openDropdown() {
      // Close any other open dropdown-panels (user chip, etc.) first.
      document.querySelectorAll('.dropdown-panel.open').forEach(function (p) {
        if (p !== dropdown) p.classList.remove('open');
      });
      positionDropdown();
      dropdown.classList.add('open');
      dropdown.setAttribute('aria-hidden', 'false');
      bell.setAttribute('aria-expanded', 'true');
      var dot = bell.querySelector('.dot');
      if (dot) dot.remove();
    }

    function closeDropdown() {
      dropdown.classList.remove('open');
      dropdown.setAttribute('aria-hidden', 'true');
      bell.setAttribute('aria-expanded', 'false');
    }

    function isOpen() {
      return dropdown.classList.contains('open');
    }

    bell.addEventListener('click', function (e) {
      e.stopPropagation();
      isOpen() ? closeDropdown() : openDropdown();
    });

    document.addEventListener('click', function (e) {
      if (isOpen() && !dropdown.contains(e.target) && e.target !== bell && !bell.contains(e.target)) {
        closeDropdown();
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen()) closeDropdown();
    });

    window.addEventListener('resize', function () {
      if (isOpen()) positionDropdown();
    });
    window.addEventListener('scroll', function () {
      if (isOpen()) positionDropdown();
    }, true);
  })();

  /* ------------------------------------------------------------------ */
  /* Init                                                                 */
  /* ------------------------------------------------------------------ */
  document.addEventListener('DOMContentLoaded', function () {
    wireTopbar();
    wireLogout();
    wireFilters();
    wirePagination();
    wireDashboardQuickCreateLinks();
    
    wireAnnouncementsCreate();
    wireAnnouncementEditModals();
    wireAnnouncementViewModals();
    wireAnnouncementDeleteModals();

    wireNewsCreate();
    wireNewsViewModals();
    wireNewsEditModals();
    wireNewsDeleteModals();

    wireEventsCreate();
    wireEventViewModals();
    wireEventEditModals();
    wireEventDeleteModals();
    
    wireDownloadableFormsCreate();
    wireGalleryCreate();
    wireGalleryViewModals();
    wireGalleryDeleteModals();
    wireGalleryLightboxDelete();

    wireOfficeProfileToggle();

    wireOfficeOverviewCreate();
    wireAddServiceCreate();
    
    wireAccountToggle();
    wireAccountPhotoPreview();

    wirePasswordToggles();
    wirePasswordMessageAutoHide();

    wireDashboard();
    wireSimpleForms();
    wireMessages();
    wireServiceDetails();
    wireApprovalCenter();
    wireApprovalDetails();
    wireOfficeOverview();
  });
})();

/* Messages (chat) — shared by the Office Representative and Super Admin pages.
 *
 * The page provides <div id="chat"> with data attributes:
 *   data-mine        "rep" or "admin"  (which side is "me")
 *   data-data-url    JSON endpoint: messages newer than ?after=<id>, and
 *                    messages changed since ?since=<time> (edited, unsent, seen…)
 *   data-send-url    POST endpoint (body, reply_to, and rep for the Super Admin)
 *   data-action-url  POST endpoint for the "⋮" menu, with 0 in place of the
 *                    message id (action = edit / unsend / delete, body)
 *   data-rep         representative id (Super Admin only)
 * and a {% csrf_token %} input inside it. Server side: office_dashboard/chat.py.
 *
 * Every message has a "⋮" button (shown when the mouse is over it, always on
 * touch screens) with: Reply, Copy, Edit (own, first minutes only), Unsend
 * (own), Delete for me, and the sent / seen time.
 * Message text is always inserted with textContent, never as HTML.
 */
(function () {
  var root = document.getElementById('chat');
  if (!root) return;

  var mine = root.getAttribute('data-mine');
  var dataUrl = root.getAttribute('data-data-url');
  var sendUrl = root.getAttribute('data-send-url');
  var actionUrl = root.getAttribute('data-action-url') || '';
  var repId = root.getAttribute('data-rep') || '';
  var tokenInput = root.querySelector('input[name="csrfmiddlewaretoken"]');
  var token = tokenInput ? tokenInput.value : '';

  var body = document.getElementById('chatBody');
  var form = document.getElementById('chatForm');
  var input = document.getElementById('chatInput');
  var sendBtn = document.getElementById('chatSend');
  var errEl = document.getElementById('chatError');
  var emptyEl = document.getElementById('chatEmpty');
  var sendLabel = sendBtn.innerHTML;

  var lastId = 0;
  var since = '';
  var msgs = {};          // id -> {data, el}
  var mode = null;        // null | {type: 'reply'|'edit', id}
  var POLL_MS = 5000;
  var OTHER = mine === 'rep' ? 'Super Admin' : 'Office';

  function nearBottom() { return body.scrollHeight - body.scrollTop - body.clientHeight < 120; }
  function scrollToEnd() { body.scrollTop = body.scrollHeight; }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function who(sender) { return sender === mine ? 'You' : (mine === 'rep' ? 'Super Admin' : (root.getAttribute('data-other') || 'Office')); }

  // ---------- drawing one message ----------
  function fill(rec) {
    var m = rec.data, wrap = rec.el;
    wrap.className = 'chat-msg' + (m.sender === mine ? ' chat-msg--mine' : '') + (m.unsent ? ' is-unsent' : '');
    wrap.innerHTML = '';
    var row = el('div', 'chat-msg__row');
    var col = el('div', 'chat-msg__col');
    if (m.reply && !m.unsent) {
      var q = el('button', 'chat-msg__quote');
      q.type = 'button';
      q.appendChild(el('span', 'chat-msg__quote-who', 'Replying to ' + (m.reply.sender === mine ? 'yourself' : who(m.reply.sender))));
      q.appendChild(el('span', 'chat-msg__quote-text', m.reply.unsent ? 'Message unsent' : m.reply.body));
      q.addEventListener('click', function () { jumpTo(m.reply.id); });
      col.appendChild(q);
    }
    var bubble = el('div', 'chat-msg__bubble');
    if (m.unsent) {
      bubble.appendChild(el('i', 'fa-solid fa-ban'));
      bubble.appendChild(document.createTextNode(' ' + (m.sender === mine ? 'You unsent a message' : 'Message unsent')));
    } else {
      bubble.textContent = m.body;
    }
    col.appendChild(bubble);
    var meta = m.time;
    if (m.edited) meta += ' · Edited';
    if (m.sender === mine && !m.unsent) meta += m.read ? ' · Seen' : ' · Sent';
    col.appendChild(el('div', 'chat-msg__time', meta));
    row.appendChild(col);

    var more = el('button', 'chat-msg__more');
    more.type = 'button';
    more.setAttribute('aria-label', 'Message options');
    more.setAttribute('aria-haspopup', 'menu');
    more.innerHTML = '<i class="fa-solid fa-ellipsis-vertical"></i>';
    more.addEventListener('click', function (e) { e.stopPropagation(); openMenu(rec, more); });
    row.appendChild(more);
    wrap.appendChild(row);
  }

  function upsert(m) {
    if (m.hidden) { remove(m.id); return; }
    var rec = msgs[m.id];
    if (!rec) {
      if (emptyEl) { emptyEl.remove(); emptyEl = null; }
      rec = msgs[m.id] = { data: m, el: el('div') };
      rec.el.setAttribute('data-id', m.id);
      // keep the order by id
      var after = null;
      Object.keys(msgs).forEach(function (k) {
        var id = +k;
        if (id > m.id && (after === null || id < after)) after = id;
      });
      if (after !== null && msgs[after] && msgs[after].el.parentNode) body.insertBefore(rec.el, msgs[after].el);
      else body.appendChild(rec.el);
    }
    rec.data = m;
    if (m.id > lastId) lastId = m.id;
    fill(rec);
    // quotes of this message in other messages follow it (edited / unsent)
    Object.keys(msgs).forEach(function (k) {
      var r = msgs[k];
      if (r.data.reply && r.data.reply.id === m.id) {
        r.data.reply.body = m.unsent ? '' : m.body.slice(0, 160);
        r.data.reply.unsent = m.unsent;
        fill(r);
      }
    });
  }

  function remove(id) {
    var rec = msgs[id];
    if (!rec) return;
    rec.el.remove();
    delete msgs[id];
    if (mode && mode.id === id) setMode(null);
  }

  function jumpTo(id) {
    var rec = msgs[id];
    if (!rec) return;
    rec.el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    rec.el.classList.add('is-flash');
    setTimeout(function () { rec.el.classList.remove('is-flash'); }, 1300);
  }

  // ---------- the "⋮" menu ----------
  var menu = el('div', 'chat-menu');
  menu.setAttribute('role', 'menu');
  menu.hidden = true;
  document.body.appendChild(menu);
  var menuFor = null;

  function item(icon, label, fn, danger) {
    var b = el('button', 'chat-menu__item' + (danger ? ' is-danger' : ''));
    b.type = 'button';
    b.setAttribute('role', 'menuitem');
    b.innerHTML = '<i class="' + icon + '"></i>';
    b.appendChild(el('span', '', label));
    b.addEventListener('click', function (e) { e.stopPropagation(); fn(b); });
    menu.appendChild(b);
    return b;
  }
  // a risky action asks once more inside the menu ("Tap again to …")
  function confirmItem(icon, label, ask, fn) {
    item(icon, label, function (b) {
      if (b.classList.contains('is-asking')) { closeMenu(); fn(); return; }
      b.classList.add('is-asking');
      b.querySelector('span').textContent = ask;
    }, true);
  }

  function openMenu(rec, anchor) {
    var m = rec.data;
    menu.innerHTML = '';
    menuFor = rec;
    var info = el('div', 'chat-menu__info');
    info.appendChild(el('span', '', 'Sent ' + m.time));
    if (m.sender === mine && m.read_time && !m.unsent) info.appendChild(el('span', '', 'Seen ' + m.read_time));
    menu.appendChild(info);
    if (!m.unsent) {
      item('fa-solid fa-reply', 'Reply', function () { closeMenu(); setMode({ type: 'reply', id: m.id }); });
      item('fa-regular fa-copy', 'Copy text', function (b) { copy(m.body, b); });
      if (m.sender === mine && m.can_edit) {
        item('fa-regular fa-pen-to-square', 'Edit', function () { closeMenu(); setMode({ type: 'edit', id: m.id }); });
      }
      if (m.sender === mine) {
        confirmItem('fa-solid fa-rotate-left', 'Unsend for everyone', 'Tap again to unsend', function () { doAction(m.id, 'unsend'); });
      }
    }
    confirmItem('fa-regular fa-trash-can', 'Delete for me', 'Tap again to delete for you', function () { doAction(m.id, 'delete'); });

    menu.hidden = false;
    rec.el.classList.add('is-menu');
    // place it next to the button, inside the screen
    var r = anchor.getBoundingClientRect();
    var w = menu.offsetWidth, h = menu.offsetHeight;
    var left = m.sender === mine ? r.right - w : r.left;
    left = Math.max(8, Math.min(left, window.innerWidth - w - 8));
    var top = r.bottom + 6;
    if (top + h > window.innerHeight - 8) top = Math.max(8, r.top - h - 6);
    menu.style.left = left + 'px';
    menu.style.top = top + 'px';
    var first = menu.querySelector('.chat-menu__item');
    if (first) first.focus();
  }
  function closeMenu() {
    if (menu.hidden) return;
    menu.hidden = true;
    if (menuFor) menuFor.el.classList.remove('is-menu');
    menuFor = null;
  }
  document.addEventListener('click', function (e) { if (!menu.contains(e.target)) closeMenu(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { closeMenu(); if (mode) setMode(null); } });
  body.addEventListener('scroll', closeMenu, { passive: true });
  window.addEventListener('resize', closeMenu);

  function copy(text, b) {
    function done() { b.querySelector('span').textContent = 'Copied'; setTimeout(closeMenu, 600); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(); });
    } else fallback();
    function fallback() {
      var t = el('textarea'); t.value = text; t.style.position = 'fixed'; t.style.opacity = '0';
      document.body.appendChild(t); t.select();
      try { document.execCommand('copy'); } catch (err) { /* ignore */ }
      t.remove(); done();
    }
  }

  // ---------- reply / edit bar above the box ----------
  var bar = el('div', 'chat-compose-bar');
  bar.hidden = true;
  form.parentNode.insertBefore(bar, form);

  function setMode(next) {
    var leavingEdit = mode && mode.type === 'edit';
    mode = next;
    if (!mode) {
      bar.hidden = true;
      sendBtn.innerHTML = sendLabel;
      if (leavingEdit) { input.value = ''; autoGrow(); }
      return;
    }
    var m = msgs[mode.id] && msgs[mode.id].data;
    if (!m) { mode = null; bar.hidden = true; return; }
    bar.innerHTML = '';
    var icon = el('i', mode.type === 'edit' ? 'fa-regular fa-pen-to-square' : 'fa-solid fa-reply');
    var txt = el('div', 'chat-compose-bar__text');
    txt.appendChild(el('b', '', mode.type === 'edit' ? 'Editing your message' : 'Replying to ' + (m.sender === mine ? 'yourself' : who(m.sender))));
    txt.appendChild(el('span', '', m.body));
    var x = el('button', 'chat-compose-bar__x');
    x.type = 'button';
    x.setAttribute('aria-label', 'Cancel');
    x.innerHTML = '<i class="fa-solid fa-xmark"></i>';
    x.addEventListener('click', function () { setMode(null); input.focus(); });
    bar.appendChild(icon); bar.appendChild(txt); bar.appendChild(x);
    bar.hidden = false;
    if (mode.type === 'edit') {
      input.value = m.body;
      sendBtn.innerHTML = '<i class="fa-solid fa-check"></i> Save';
    } else {
      if (leavingEdit) input.value = '';
      sendBtn.innerHTML = sendLabel;
    }
    autoGrow();
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  }

  // ---------- talking to the server ----------
  function post(url, fields) {
    var fd = new FormData();
    Object.keys(fields).forEach(function (k) { if (fields[k] !== '' && fields[k] != null) fd.append(k, fields[k]); });
    if (repId) fd.append('rep', repId);
    return fetch(url, {
      method: 'POST', body: fd, credentials: 'same-origin',
      headers: { 'X-CSRFToken': token, 'X-Requested-With': 'XMLHttpRequest' }
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, json: j }; }); });
  }

  function doAction(id, action, text) {
    showError('');
    return post(actionUrl.replace(/\/0\//, '/' + id + '/'), { action: action, body: text || '' })
      .then(function (res) {
        if (!res.ok || !res.json.success) { showError((res.json && res.json.error) || 'That did not work. Please try again.'); return false; }
        upsert(res.json.message);
        return true;
      })
      .catch(function () { showError('Could not reach the server. Check your connection and try again.'); return false; });
  }

  function updateUnread(map) {
    if (!map) return;
    document.querySelectorAll('[data-conv-unread]').forEach(function (b) {
      var n = parseInt(map[b.getAttribute('data-conv-unread')] || 0, 10);
      b.textContent = n;
      b.hidden = !n;
    });
  }
  // The red number next to "Messages" in the sidebar.
  function updateSidebarBadge(total) {
    if (typeof total !== 'number') return;
    document.querySelectorAll('[data-unread-badge="messages"]').forEach(function (b) {
      b.textContent = total;
      b.hidden = !total;
    });
  }

  function load(initial) {
    var url = dataUrl + (dataUrl.indexOf('?') === -1 ? '?' : '&') + 'after=' + lastId;
    if (since) url += '&since=' + encodeURIComponent(since);
    if (repId) url += '&rep=' + encodeURIComponent(repId);
    fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        var stick = initial || nearBottom();
        (data.messages || []).forEach(upsert);
        (data.changed || []).forEach(function (m) { if (msgs[m.id] || m.hidden) upsert(m); });
        if (data.now) since = data.now;
        if (stick && (data.messages || []).length) scrollToEnd();
        updateUnread(data.unread);
        updateSidebarBadge(data.unread_total);
      })
      .catch(function () { /* offline / server hiccup: try again on the next tick */ });
  }

  function showError(msg) {
    if (!errEl) return;
    errEl.textContent = msg || '';
    errEl.hidden = !msg;
  }

  function autoGrow() {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 140) + 'px';
  }

  function send() {
    var text = input.value.trim();
    if (!text) return;
    showError('');
    sendBtn.disabled = true;
    var done = function () { sendBtn.disabled = false; input.focus(); };

    if (mode && mode.type === 'edit') {
      doAction(mode.id, 'edit', text).then(function (ok) { if (ok) setMode(null); done(); });
      return;
    }
    post(sendUrl, { body: text, reply_to: mode && mode.type === 'reply' ? mode.id : '' })
      .then(function (res) {
        if (!res.ok || !res.json.success) {
          showError((res.json && res.json.error) || 'Could not send your message.');
          return;
        }
        input.value = '';
        autoGrow();
        setMode(null);
        upsert(res.json.message);
        scrollToEnd();
      })
      .catch(function () { showError('Could not send your message. Check your connection and try again.'); })
      .then(done);
  }

  form.addEventListener('submit', function (e) { e.preventDefault(); send(); });
  input.addEventListener('input', autoGrow);
  input.addEventListener('keydown', function (e) {
    // Enter sends; Shift+Enter makes a new line.
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });

  load(true);
  setInterval(function () { if (!document.hidden) load(false); }, POLL_MS);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) load(false); });
})();

/* Super Admin: filter the conversation list as you type. */
(function () {
  var search = document.getElementById('chatListSearch');
  if (!search) return;
  search.addEventListener('input', function () {
    var q = search.value.trim().toLowerCase();
    var any = false;
    document.querySelectorAll('.chat-conv').forEach(function (c) {
      var show = !q || (c.getAttribute('data-search') || '').indexOf(q) !== -1;
      c.style.display = show ? '' : 'none';
      if (show) any = true;
    });
    var none = document.getElementById('chatListNone');
    if (none) none.hidden = any;
  });
})();
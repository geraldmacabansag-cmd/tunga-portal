/* Messages (chat) — shared by the Office Representative and Super Admin pages.
 *
 * The page provides <div id="chat"> with data attributes:
 *   data-mine      "rep" or "admin"  (which side is "me")
 *   data-data-url  JSON endpoint that returns {messages: [...]} newer than ?after=
 *   data-send-url  POST endpoint (body, and rep for the Super Admin)
 *   data-rep       representative id (Super Admin only)
 * and a {% csrf_token %} input inside it.
 * Message text is always inserted with textContent, never as HTML.
 */
(function () {
  var root = document.getElementById('chat');
  if (!root) return;

  var mine = root.getAttribute('data-mine');
  var dataUrl = root.getAttribute('data-data-url');
  var sendUrl = root.getAttribute('data-send-url');
  var repId = root.getAttribute('data-rep') || '';
  var tokenInput = root.querySelector('input[name="csrfmiddlewaretoken"]');
  var token = tokenInput ? tokenInput.value : '';

  var body = document.getElementById('chatBody');
  var form = document.getElementById('chatForm');
  var input = document.getElementById('chatInput');
  var sendBtn = document.getElementById('chatSend');
  var errEl = document.getElementById('chatError');
  var emptyEl = document.getElementById('chatEmpty');

  var lastId = 0;
  var seen = {};
  var POLL_MS = 5000;

  function nearBottom() {
    return body.scrollHeight - body.scrollTop - body.clientHeight < 120;
  }

  function render(m) {
    if (seen[m.id]) return;
    seen[m.id] = true;
    if (m.id > lastId) lastId = m.id;
    if (emptyEl) { emptyEl.remove(); emptyEl = null; }

    var wrap = document.createElement('div');
    wrap.className = 'chat-msg' + (m.sender === mine ? ' chat-msg--mine' : '');
    var bubble = document.createElement('div');
    bubble.className = 'chat-msg__bubble';
    bubble.textContent = m.body;
    var time = document.createElement('div');
    time.className = 'chat-msg__time';
    time.textContent = m.time;
    wrap.appendChild(bubble);
    wrap.appendChild(time);
    body.appendChild(wrap);
  }

  function scrollToEnd() { body.scrollTop = body.scrollHeight; }

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
    if (repId) url += '&rep=' + encodeURIComponent(repId);
    fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        var stick = initial || nearBottom();
        (data.messages || []).forEach(render);
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

    var fd = new FormData();
    fd.append('body', text);
    if (repId) fd.append('rep', repId);

    fetch(sendUrl, {
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': token, 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, json: j }; }); })
      .then(function (res) {
        if (!res.ok || !res.json.success) {
          showError((res.json && res.json.error) || 'Could not send your message.');
          return;
        }
        input.value = '';
        autoGrow();
        render(res.json.message);
        scrollToEnd();
      })
      .catch(function () { showError('Could not send your message. Check your connection and try again.'); })
      .then(function () { sendBtn.disabled = false; input.focus(); });
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
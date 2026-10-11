/* Ticks the password requirements (templates/includes/_password_rules.html)
   as the person types. The server checks the same rules again. */
(function () {
  if (window.__pwRulesWired) return;
  window.__pwRulesWired = true;

  var RULES = {
    length:  function (p) { return p.length >= 8; },
    upper:   function (p) { return /[A-Z]/.test(p); },
    lower:   function (p) { return /[a-z]/.test(p); },
    number:  function (p) { return /[0-9]/.test(p); },
    special: function (p) { return /[^A-Za-z0-9]/.test(p); }
  };

  function wire(list) {
    var pw = document.getElementById(list.dataset.pwFor);
    var confirm = list.dataset.pwConfirm ? document.getElementById(list.dataset.pwConfirm) : null;
    if (!pw) return;
    function check() {
      var p = pw.value;
      list.querySelectorAll('li').forEach(function (li) {
        var rule = li.dataset.rule;
        var ok = rule === 'match' ? (p.length > 0 && confirm && p === confirm.value) : RULES[rule](p);
        li.classList.toggle('ok', !!ok);
        li.querySelector('i').className = ok ? 'fa-solid fa-circle-check' : 'fa-regular fa-circle';
      });
    }
    pw.addEventListener('input', check);
    if (confirm) confirm.addEventListener('input', check);
    check();
  }

  function init() { document.querySelectorAll('.pw-rules-live').forEach(wire); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
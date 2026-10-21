/* Wide ("landscape") windows on laptops / desktops (1100px wide or more),
   normal one-column ("portrait") windows on smaller screens.
   Styles: static/css/content-form-modal.css. Used by every window with
   class "cf-modal":
     - Add / Edit of Announcements, News & Updates, Events (both dashboards)
     - the Office Representative dashboard's Quick Actions windows
     - Add / Edit Service (both dashboards)
     - View windows ("cf-modal cf-view") of announcements, news and events
   On a wide screen the window's fields are put in two groups:
     .cf-main  (left)  the text
     .cf-side  (right) pictures, video, icon, and some extra details
   On a small screen they go back to their original order. Nothing else
   changes: the same fields are sent, only where they show on screen. */
(function () {
  var mq = window.matchMedia('(min-width: 1100px)');
  var KEEP = 'input[type="hidden"], link, script, style, template, .modal-actions, .toast-static';

  // pictures / video / icon -> right column
  var MEDIA = '.cp-field, .cv-field, .svc-icon-field, .cv, .vp, [id$="-video-wrap"], [id$="-image-wrap"], [id$="-gallery"]';
  function isMedia(el) {
    return el.matches(MEDIA) || !!el.querySelector('input[type="file"]') || !!el.querySelector('.vp, .cv');
  }
  // extra details that may also go right, from the bottom up, while the left
  // column is longer (so both columns end at about the same height)
  var SIDE_FIELDS = ['author', 'source', 'tags', 'contact_person', 'contact_info',
                     'priority', 'expiration_date', 'is_featured', 'service_scope'];
  function isExtra(el, isForm) {
    if (!isForm) return false;
    return SIDE_FIELDS.some(function (n) { return !!el.querySelector('[name="' + n + '"]'); });
  }

  function containers() {
    var list = [];
    document.querySelectorAll('.cf-modal').forEach(function (modal) {
      if (modal.classList.contains('cf-view')) {
        var body = modal.querySelector('.modal-body');
        if (body) list.push(body);
      } else {
        modal.querySelectorAll('.modal-body form').forEach(function (f) { list.push(f); });
      }
    });
    return list;
  }

  function wrap(box) {
    if (box._cf) return;
    var kids = Array.prototype.filter.call(box.children, function (el) { return !el.matches(KEEP); });
    if (!kids.length) return;
    var main = document.createElement('div'); main.className = 'cf-main';
    var side = document.createElement('div'); side.className = 'cf-side';
    kids[0].parentNode.insertBefore(main, kids[0]);
    main.parentNode.insertBefore(side, main.nextSibling);
    var slots = kids.map(function (el) {
      var mark = document.createComment('cf');
      el.parentNode.insertBefore(mark, el);        // remember where it was
      (isMedia(el) ? side : main).appendChild(el);
      return [mark, el];
    });
    box._cf = { main: main, side: side, slots: slots };
    box.classList.add('cf-landscape');
    balance(box);
  }

  function hasVisible(el) {
    return Array.prototype.some.call(el.children, function (c) { return c.offsetHeight > 0; });
  }

  function balance(box) {
    var s = box._cf;
    if (!s || !s.main.offsetHeight) return;          // window not visible yet
    var isForm = box.tagName === 'FORM';
    var extras = Array.prototype.filter.call(s.main.children, function (el) { return isExtra(el, isForm); }).reverse();
    var before = null;
    extras.forEach(function (el) {
      var tallest = Math.max(s.main.offsetHeight, s.side.offsetHeight);
      var mark = document.createComment('cf-try');
      el.parentNode.insertBefore(mark, el);
      s.side.insertBefore(el, before);                // keeps their original order
      if (Math.max(s.main.offsetHeight, s.side.offsetHeight) < tallest) {
        before = el;                                  // the window got shorter: keep it there
      } else {
        mark.parentNode.insertBefore(el, mark);       // no better: put it back
      }
      mark.remove();
    });
    // nothing to show on the right (e.g. a post without pictures): one column
    var modal = box.closest('.cf-modal');
    var empty = !hasVisible(s.side);
    box.classList.toggle('cf-single', empty);
    if (modal) modal.classList.toggle('cf-narrow', empty);
  }

  function unwrap(box) {
    var s = box._cf;
    if (!s) return;
    s.slots.forEach(function (p) { p[0].parentNode.replaceChild(p[1], p[0]); });
    s.main.remove(); s.side.remove();
    box._cf = null;
    box.classList.remove('cf-landscape', 'cf-single');
    var modal = box.closest('.cf-modal');
    if (modal) modal.classList.remove('cf-narrow');
  }

  function apply() {
    containers().forEach(function (box) { if (mq.matches) wrap(box); else unwrap(box); });
  }

  // each time a window opens: lay it out again now that it is visible (its
  // pictures may have been filled in just before)
  function relayout(modal) {
    if (!mq.matches) return;
    var boxes = modal.classList.contains('cf-view')
      ? [modal.querySelector('.modal-body')]
      : Array.prototype.slice.call(modal.querySelectorAll('.modal-body form'));
    boxes.forEach(function (box) { if (box) { unwrap(box); wrap(box); } });
  }
  function watchOpen() {
    document.querySelectorAll('.cf-modal').forEach(function (modal) {
      var wasOpen = modal.classList.contains('open');
      new MutationObserver(function () {
        var isOpen = modal.classList.contains('open');
        if (isOpen && !wasOpen) {
          requestAnimationFrame(function () {
            relayout(modal);
            // View windows: once the pictures have loaded, check the columns again
            if (modal.classList.contains('cf-view')) setTimeout(function () { relayout(modal); }, 400);
          });
        }
        wasOpen = isOpen;
      }).observe(modal, { attributes: true, attributeFilter: ['class'] });
    });
  }

  function start() { apply(); watchOpen(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
  if (mq.addEventListener) mq.addEventListener('change', apply); else mq.addListener(apply);
})();
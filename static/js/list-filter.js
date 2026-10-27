/* Filters a list on the page WITHOUT reloading it (so the page doesn't jump
   to the top): tabs, the status / category dropdowns, the search box, the
   sort dropdown and the page numbers all work in the browser.

   Used by the list pages of the Office Representative and the Super Admin:
   Announcements, News & Updates, Events, Services, Downloadable Forms and
   Gallery.

   Markup (add data-lf-strict when the "" tab is its own tab, not "All"):
     <div data-lf data-lf-param="status" data-lf-size="5" data-lf-noun="announcements">
       <a data-lf-tab="">All</a> <a data-lf-tab="expired">Expired</a> …   tabs (value = row's data-tab)
       <select data-lf-tabselect> … </select>                             same as the tabs (optional)
       <input data-lf-q>  <select data-lf-sort> (newest / oldest / most_viewed / downloads / az)
       <select data-lf-filter="when"> …                                    any other filter: a row matches
                                                                           when its data-when has the value
       (<select data-lf-category> = <select data-lf-filter="category">)
       <tr data-lf-row data-tab="published" data-title="…" data-category="…" data-date="20261027101500" data-views="3">
       (rows can also be cards: any element with data-lf-row)
       <tr data-lf-empty> (shown when nothing matches)
       <div data-lf-pager></div> <span data-lf-info></span>               page numbers (when data-lf-size > 0)
     </div>
   The address bar is updated (no reload), so a refresh or a shared link
   opens the same tab. */
(function () {
  "use strict";

  function init(root) {
    var param = root.getAttribute("data-lf-param") || "status";
    var size = parseInt(root.getAttribute("data-lf-size"), 10) || 0;
    var noun = root.getAttribute("data-lf-noun") || "items";
    // data-lf-strict: the "" tab is a real tab (rows with data-tab=""), not "show all"
    var strict = root.hasAttribute("data-lf-strict");
    // data-lf-default-tab: the tab shown when the address has none (default "")
    // data-lf-all: the tab value that means "show everything" (e.g. "all")
    var defaultTab = root.getAttribute("data-lf-default-tab") || "";
    var allValue = root.getAttribute("data-lf-all");
    var rows = Array.prototype.slice.call(root.querySelectorAll("[data-lf-row]"));
    if (!rows.length) {
      // nothing to filter: still keep the controls from reloading the page
      root.querySelectorAll("[data-lf-q]").forEach(function (q) { if (q.form) q.form.addEventListener("submit", function (e) { e.preventDefault(); }); });
      return;
    }
    var body = rows[0].parentNode;
    var empty = root.querySelector("[data-lf-empty]");
    var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-lf-tab]"));
    var tabSelect = root.querySelector("[data-lf-tabselect]");
    var qInput = root.querySelector("[data-lf-q]");
    var filterEls = Array.prototype.slice.call(root.querySelectorAll("[data-lf-filter], [data-lf-category]"));
    var sortSelect = root.querySelector("[data-lf-sort]");
    var pager = root.querySelector("[data-lf-pager]");
    var info = root.querySelector("[data-lf-info]");
    rows.forEach(function (r, i) { r._lfIndex = i; });
    var rendered = false;

    var url = new URLSearchParams(location.search);
    var defaultSort = sortSelect ? (sortSelect.querySelector("option[selected]") || sortSelect.options[0] || {}).value || "" : "";
    var filterDefaults = {};
    filterEls.forEach(function (el) {
      var o = el.querySelector("option[data-lf-default]") || el.options[0];
      filterDefaults[fname(el)] = o ? o.value : "";
    });
    var state = {
      tab: url.has(param) ? url.get(param) : defaultTab,
      q: url.get("q") || (qInput ? qInput.value : ""),
      filters: {},
      sort: url.get("sort") || (sortSelect ? sortSelect.value : ""),
      page: parseInt(url.get("page"), 10) || 1
    };
    function fname(el) { return el.getAttribute("data-lf-filter") || "category"; }
    filterEls.forEach(function (el) {
      var n = fname(el);
      state.filters[n] = url.has(n) ? url.get(n) : el.value;
    });

    function norm(s) {
      return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }

    function matches(r) {
      if (state.tab !== allValue && (strict || state.tab) && (r.getAttribute("data-tab") || "") !== state.tab) return false;
      for (var n in state.filters) {
        var v = state.filters[n];
        if (v && (" " + (r.getAttribute("data-" + n) || "") + " ").indexOf(" " + v + " ") === -1) return false;
      }
      if (state.q) {
        var hay = norm(r.getAttribute("data-title"));
        var words = norm(state.q).split(/\s+/).filter(Boolean);
        for (var i = 0; i < words.length; i++) if (hay.indexOf(words[i]) === -1) return false;
      }
      return true;
    }

    function sorter(a, b) {
      if (!sortSelect || !state.sort) return a._lfIndex - b._lfIndex;   // the order the server gave
      if (state.sort === "az" || state.sort === "name") {
        return norm(a.getAttribute("data-title")).localeCompare(norm(b.getAttribute("data-title"))) || a._lfIndex - b._lfIndex;
      }
      if (state.sort === "most_viewed" || state.sort === "downloads" || state.sort === "photos") {
        return (+b.getAttribute("data-views") || 0) - (+a.getAttribute("data-views") || 0) || a._lfIndex - b._lfIndex;
      }
      var da = a.getAttribute("data-date") || "", db = b.getAttribute("data-date") || "";
      if (da === db) return a._lfIndex - b._lfIndex;
      return state.sort === "oldest" ? (da < db ? -1 : 1) : (da > db ? -1 : 1);
    }

    function pageLink(label, page, disabled, active) {
      var el = document.createElement(disabled || active ? "span" : "a");
      el.className = "page-btn" + (active ? " active" : "");
      el.innerHTML = label;
      if (!disabled && !active) {
        el.href = "#";
        el.addEventListener("click", function (e) { e.preventDefault(); state.page = page; render(true); });
      }
      return el;
    }

    function saveUrl() {
      var u = new URLSearchParams(location.search);
      var pairs = [[param, state.tab === defaultTab ? "" : state.tab], ["q", state.q],
       ["sort", state.sort === defaultSort ? "" : state.sort], ["page", state.page > 1 ? state.page : ""]];
      for (var n in state.filters) pairs.push([n, state.filters[n] === filterDefaults[n] ? "" : state.filters[n]]);
      pairs.forEach(function (kv) {
        if (kv[1]) u.set(kv[0], kv[1]); else u.delete(kv[0]);
      });
      var qs = u.toString();
      history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
    }

    function render(keepView) {
      // keep the page where it is: remember the scroll position, and don't
      // let the list get shorter than it was (a short tab would otherwise pull
      // the page up)
      var y = window.scrollY;
      if (rendered) root.style.minHeight = Math.max(root.offsetHeight, parseFloat(root.style.minHeight) || 0) + "px";
      var shown = rows.filter(matches).sort(sorter);
      var pages = size ? Math.max(1, Math.ceil(shown.length / size)) : 1;
      if (state.page > pages) state.page = pages;
      if (state.page < 1) state.page = 1;
      var start = size ? (state.page - 1) * size : 0;
      var end = size ? start + size : shown.length;

      rows.forEach(function (r) { r.hidden = true; });
      shown.forEach(function (r, i) {
        body.appendChild(r);                 // keeps the sorted order
        r.hidden = !(i >= start && i < end);
      });
      if (empty) { if (empty.parentNode === body) body.appendChild(empty); empty.hidden = shown.length > 0; }

      tabs.forEach(function (t) {
        var on = (t.getAttribute("data-lf-tab") || "") === state.tab;
        t.classList.toggle("active", on);
        t.setAttribute("aria-selected", on ? "true" : "false");
      });
      if (tabSelect) tabSelect.value = state.tab;
      filterEls.forEach(function (el) { el.value = state.filters[fname(el)]; });
      if (sortSelect) sortSelect.value = state.sort;
      root.querySelectorAll("[data-lf-only]").forEach(function (el) {
        el.hidden = el.getAttribute("data-lf-only") !== state.tab;
      });

      if (info) {
        info.textContent = !shown.length ? "No " + noun + " found"
          : (size ? "Showing " + (start + 1) + " to " + Math.min(end, shown.length) + " of " + shown.length + " " + noun
                  : shown.length + " " + noun);
      }
      if (pager) {
        pager.innerHTML = "";
        if (size) {
          pager.appendChild(pageLink('<i class="fa-solid fa-chevron-left"></i>', state.page - 1, state.page <= 1));
          for (var p = 1; p <= pages; p++) pager.appendChild(pageLink(String(p), p, false, p === state.page));
          pager.appendChild(pageLink('<i class="fa-solid fa-chevron-right"></i>', state.page + 1, state.page >= pages));
        }
      }
      saveUrl();
      if (rendered) window.scrollTo(0, y);
      rendered = true;
      // after a page click, keep the list in view (only if its top went off screen)
      if (keepView) {
        var top = root.getBoundingClientRect().top;
        if (top < 0) root.scrollIntoView({ block: "start" });
      }
    }

    tabs.forEach(function (t) {
      t.addEventListener("click", function (e) {
        e.preventDefault();
        state.tab = t.getAttribute("data-lf-tab") || "";
        state.page = 1;
        render();
      });
    });
    if (tabSelect) tabSelect.addEventListener("change", function () { state.tab = tabSelect.value; state.page = 1; render(); });
    filterEls.forEach(function (el) {
      el.addEventListener("change", function () { state.filters[fname(el)] = el.value; state.page = 1; render(); });
    });
    if (sortSelect) sortSelect.addEventListener("change", function () { state.sort = sortSelect.value; state.page = 1; render(); });
    if (qInput) {
      qInput.value = state.q;
      var t;
      qInput.addEventListener("input", function () {
        clearTimeout(t);
        t = setTimeout(function () { state.q = qInput.value.trim(); state.page = 1; render(); }, 200);
      });
      var form = qInput.form;
      if (form) form.addEventListener("submit", function (e) { e.preventDefault(); state.q = qInput.value.trim(); state.page = 1; render(); });
    }
    render();
  }

  // Saving / deleting / pinning still sends the form (the page reloads once):
  // remember where the page was and come back to the same spot afterwards.
  var KEY = "lf-scroll:" + location.pathname;
  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (!document.querySelector("[data-lf]") || (f.method || "").toLowerCase() !== "post") return;
    try { sessionStorage.setItem(KEY, JSON.stringify({ y: window.scrollY, t: Date.now() })); } catch (err) {}
  }, true);
  function restoreScroll() {
    try {
      var s = JSON.parse(sessionStorage.getItem(KEY) || "null");
      sessionStorage.removeItem(KEY);
      if (s && Date.now() - s.t < 60000) window.scrollTo(0, s.y);
    } catch (err) {}
  }

  function start() {
    // hidden rows / notes stay hidden even when the page's CSS gives them
    // display:flex or display:block (list rows, gallery cards, help notes)
    if (!document.getElementById("lf-hidden-style")) {
      var st = document.createElement("style");
      st.id = "lf-hidden-style";
      st.textContent = "[data-lf] [hidden]{display:none !important}";
      document.head.appendChild(st);
    }
    document.querySelectorAll("[data-lf]").forEach(init);
    restoreScroll();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
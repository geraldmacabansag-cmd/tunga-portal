/* TungaPdf.open(url) -> Promise<pdfDocument>
 *
 * One small loader used by every PDF preview on the site (form builder,
 * Fill Out Online, form viewer).
 *
 * Why it works on every browser / Chrome profile / account:
 *  1. pdf.js is served from OUR OWN /static/ folder, so no CDN can be
 *     blocked by an ad-blocker, school/office network or slow connection.
 *  2. The PDF is fetched as JSON (base64 text), not as "application/pdf".
 *     Download-manager extensions (IDM, etc.), "Download PDFs instead of
 *     opening them" in Chrome settings and some antivirus add-ons grab
 *     anything that looks like a PDF and the preview stays blank. A JSON
 *     reply is never grabbed.
 *  3. cache: 'no-store' so an old/broken copy saved in one Chrome profile
 *     is never reused.
 */
window.TungaPdf = window.TungaPdf || (function () {
  var me = document.currentScript && document.currentScript.src;
  var BASE = me ? me.replace(/js\/[^\/]*$/, 'pdfjs/') : '/static/pdfjs/';
  var libPromise = null;

  function loadLib() {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if (!libPromise) {
      libPromise = new Promise(function (resolve, reject) {
        var s = document.createElement('script');
        s.src = BASE + 'pdf.js';
        s.onload = function () {
          if (!window.pdfjsLib) return reject(new Error('PDF viewer did not start.'));
          window.pdfjsLib.GlobalWorkerOptions.workerSrc = BASE + 'pdf.worker.js';
          resolve(window.pdfjsLib);
        };
        s.onerror = function () { libPromise = null; reject(new Error('Could not load the PDF viewer.')); };
        document.head.appendChild(s);
      });
    }
    return libPromise;
  }

  function loadBytes(url) {
    var jsonUrl = url + (url.indexOf('?') === -1 ? '?' : '&') + 'as=json';
    return fetch(jsonUrl, {
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    }).then(function (res) {
      return res.json().catch(function () {
        // Got an HTML page back (usually the login page) instead of JSON.
        throw new Error('Your session has expired. Please refresh the page and log in again.');
      }).then(function (data) {
        if (!res.ok || !data.pdf) throw new Error(data.error || ('Server error ' + res.status));
        var bin = atob(data.pdf);
        var bytes = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        return bytes;
      });
    });
  }

  return {
    open: function (url) {
      return Promise.all([loadLib(), loadBytes(url)]).then(function (r) {
        return r[0].getDocument({ data: r[1] }).promise;
      });
    }
  };
})();
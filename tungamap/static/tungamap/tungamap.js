/* Tunga Map — Leaflet + OpenStreetMap front end for the Django "tungamap" app. */
(() => {
  "use strict";

  // Search area around Tunga (south, west, north, east) and starting view
  const TUNGA_CENTER = [11.25, 124.75];
  const BBOX = { s: 11.20, w: 124.70, n: 11.30, e: 124.80 };

  // Icon, colour, search words (English + Waray/Filipino) and OpenStreetMap tags per type.
  // The ids must match Place.CATEGORY_CHOICES in models.py.
  const CATEGORIES = [
    { id: "school", label: "School", icon: "fa-school", color: "#2f6fd6", words: ["school", "paaralan", "eskwelahan", "elementary", "high school", "college", "daycare", "day care"], osm: ['amenity~"school|college|university|kindergarten"'] },
    { id: "health", label: "Health", icon: "fa-house-medical", color: "#d23c4b", words: ["health", "hospital", "clinic", "rhu", "health center", "pharmacy", "botika", "doctor", "lying-in", "ospital"], osm: ['amenity~"hospital|clinic|doctors|pharmacy"', "healthcare"] },
    { id: "government", label: "Government", icon: "fa-landmark", color: "#6b4fbb", words: ["municipal", "town hall", "munisipyo", "barangay hall", "government", "office", "hall", "dswd", "post office"], osm: ['amenity~"townhall|post_office|community_centre"', "office=government"] },
    { id: "church", label: "Church", icon: "fa-church", color: "#8a5a2b", words: ["church", "simbahan", "chapel", "kapilya", "parish", "mosque"], osm: ["amenity=place_of_worship"] },
    { id: "market", label: "Market & stores", icon: "fa-store", color: "#d9822b", words: ["market", "merkado", "tiangge", "store", "tindahan", "sari-sari", "shop", "grocery", "hardware"], osm: ["amenity=marketplace", "shop"] },
    { id: "food", label: "Food", icon: "fa-utensils", color: "#c2486e", words: ["restaurant", "food", "eatery", "carinderia", "kainan", "cafe", "bakery", "panaderya"], osm: ['amenity~"restaurant|cafe|fast_food"', "shop=bakery"] },
    { id: "safety", label: "Police & fire", icon: "fa-shield-halved", color: "#1d3c6e", words: ["police", "pulis", "pnp", "fire", "bfp", "bombero", "rescue", "mdrrmo", "evacuation"], osm: ['amenity~"police|fire_station"', "emergency"] },
    { id: "finance", label: "Bank & remittance", icon: "fa-building-columns", color: "#2c8a6e", words: ["bank", "atm", "remittance", "padala", "cebuana", "palawan", "lending", "pawnshop"], osm: ['amenity~"bank|atm|money_transfer|bureau_de_change"', "shop=pawnbroker"] },
    { id: "transport", label: "Transport", icon: "fa-bus", color: "#4a5868", words: ["terminal", "bus", "jeep", "van", "tricycle", "port", "gas", "gasolinahan", "fuel"], osm: ['amenity~"bus_station|fuel|ferry_terminal"', "highway=bus_stop"] },
    { id: "infra", label: "Roads & utilities", icon: "fa-bridge-water", color: "#0d7c86", words: ["bridge", "taytay", "road", "dalan", "water", "tubig", "pump", "tower", "power", "drainage", "dam", "irrigation", "solar"], osm: ["bridge=yes][name", 'man_made~"water_tower|water_well|tower"', "power=substation"] },
    { id: "recreation", label: "Parks & sports", icon: "fa-tree", color: "#4c8c2b", words: ["park", "plaza", "court", "basketball", "gym", "covered court", "sports", "beach", "resort"], osm: ['leisure~"park|pitch|sports_centre"', 'tourism~"attraction|resort"'] },
    { id: "other", label: "Other", icon: "fa-location-dot", color: "#6b7280", words: [], osm: [] },
  ];
  const CAT = Object.fromEntries(CATEGORIES.map((c) => [c.id, c]));

  document.querySelectorAll(".tmap").forEach(init);

  function init(root) {
    const $ = (name) => root.querySelector(`[data-el="${name}"]`);
    const API = root.dataset.api;
    const CSRF = root.dataset.csrf;
    const canEdit = root.dataset.canEdit === "1";
    const BARANGAYS = (root.dataset.barangays || "").split("|").filter(Boolean);

    let places = [];
    let mode = "est";
    let activeCat = "";
    let activeQuery = "";
    let lastOsm = [];
    let pickMode = false, movingPin = false;
    let draftMarker = null, editing = null;
    let newFiles = [], keepImages = [];
    const markerById = new Map();

    // ---------------- map ----------------
    const map = L.map($("map"), { zoomControl: false, scrollWheelZoom: true }).setView(TUNGA_CENTER, 14);
    L.control.zoom({ position: "topright" }).addTo(map);
    // OpenStreetMap only serves map images to sites that say who they are, so
    // send our site address with these requests (Django hides it by default).
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      referrerPolicy: "strict-origin-when-cross-origin",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
    }).addTo(map);
    L.control.scale({ imperial: false, position: "bottomright" }).addTo(map);
    const ownLayer = L.layerGroup().addTo(map);
    const osmLayer = L.layerGroup().addTo(map);
    const locLayer = L.layerGroup().addTo(map);
    // the map may be inside a tab or hidden section — fix its size when it becomes visible
    new ResizeObserver(() => map.invalidateSize()).observe(root);

    function pinIcon(cat, { osm = false, pop = false, draft = false } = {}) {
      const c = CAT[cat] || CAT.other;
      return L.divIcon({
        className: "",
        html: `<div class="tm-pin ${osm ? "osm" : ""} ${pop ? "pop" : ""} ${draft ? "draft" : ""}" style="--c:${c.color}"><span class="head"></span><i class="fa-solid ${c.icon}"></i></div>`,
        iconSize: [34, 42], iconAnchor: [17, 40], popupAnchor: [0, -36],
      });
    }

    // ---------------- helpers ----------------
    const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
    const norm = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    let toastTimer;
    function toast(msg) {
      const t = $("toast"); t.textContent = msg; t.hidden = false;
      clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 3000);
    }
    async function api(url, opts = {}) {
      const res = await fetch(url, {
        credentials: "same-origin",
        ...opts,
        headers: { "X-CSRFToken": CSRF, "X-Requested-With": "XMLHttpRequest", ...(opts.headers || {}) },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status}). Try again.`);
      return data;
    }
    const detailUrl = (id) => `${API}${id}/`;

    function categoryFromQuery(q) {
      const n = norm(q);
      if (!n) return null;
      return CATEGORIES.find((c) => norm(c.label).includes(n) || c.words.some((w) => n.includes(norm(w)) || norm(w).startsWith(n))) || null;
    }

    // ---------------- chips ----------------
    function renderChips() {
      $("chips").innerHTML = CATEGORIES.filter((c) => c.id !== "other").map((c) =>
        `<button type="button" class="tm-chip ${activeCat === c.id ? "on" : ""}" data-cat="${c.id}" style="--c:${c.color}" aria-pressed="${activeCat === c.id}"><i class="fa-solid ${c.icon}" aria-hidden="true"></i>${esc(c.label)}</button>`
      ).join("");
    }
    $("chips").addEventListener("click", (e) => {
      const b = e.target.closest(".tm-chip"); if (!b) return;
      if (activeCat === b.dataset.cat) return clearSearch();
      setMode("est"); $("q").value = "";
      runEstablishmentSearch("", b.dataset.cat);
    });

    // ---------------- places from the database ----------------
    async function loadPlaces() {
      try { places = (await api(API)).places; }
      catch (e) { places = []; toast("Couldn't load places: " + e.message); }
      refresh();
    }

    function matches(p, q) {
      const hay = norm([p.name, p.barangay, p.description, (CAT[p.category] || CAT.other).label].join(" "));
      return norm(q).split(/\s+/).every((w) => hay.includes(w));
    }

    function popupHtml(p) {
      const c = CAT[p.category] || CAT.other;
      const imgs = p.images.map((im) => `<img src="${esc(im.url)}" alt="Photo of ${esc(p.name)}" data-photo="${esc(im.url)}" loading="lazy">`).join("");
      const edit = canEdit ? `<div class="tm-row"><button type="button" class="tm-btn tm-small" data-edit="${p.id}"><i class="fa-solid fa-pen"></i> Edit</button><button type="button" class="tm-btn tm-small tm-ghost" data-del="${p.id}"><i class="fa-solid fa-trash"></i> Delete</button></div>` : "";
      return `<div class="tm-pop">
        ${p.published ? "" : '<span class="badge" style="color:var(--tmap-warn)">HIDDEN FROM PUBLIC</span>'}
        <h4>${esc(p.name)}</h4>
        <div class="meta"><i class="fa-solid ${c.icon}" style="color:${c.color}"></i> ${esc(c.label)}${p.barangay ? " · Brgy. " + esc(p.barangay) : ""}</div>
        ${imgs ? `<div class="gallery">${imgs}</div>` : ""}
        ${p.description ? `<p>${esc(p.description)}</p>` : ""}
        ${p.contact ? `<p><i class="fa-solid fa-phone"></i> <span style="user-select:all">${esc(p.contact)}</span></p>` : ""}
        <div class="coords">${p.lat.toFixed(5)}, ${p.lng.toFixed(5)} · <a href="https://www.openstreetmap.org/directions?to=${p.lat}%2C${p.lng}" target="_blank" rel="noopener">Directions</a></div>
        ${edit}
      </div>`;
    }

    function drawOwn(list, pop) {
      ownLayer.clearLayers(); markerById.clear();
      list.forEach((p) => {
        const m = L.marker([p.lat, p.lng], { icon: pinIcon(p.category, { pop, draft: !p.published }), title: p.name, alt: p.name })
          .bindPopup(() => popupHtml(p), { maxWidth: 300, autoPanPadding: [30, 30] });
        m.addTo(ownLayer); markerById.set(String(p.id), m);
      });
    }

    // ---------------- OpenStreetMap places (Overpass API) ----------------
    let overpassCtl;
    async function searchOSM(q, cat) {
      const c = cat ? CAT[cat] : null;
      const bbox = `(${BBOX.s},${BBOX.w},${BBOX.n},${BBOX.e})`;
      let parts = [];
      if (c && c.osm.length) parts = c.osm.map((t) => `nwr[${t}]${bbox};`);
      else if (q && q.length >= 3) parts = [`nwr["name"~"${q.replace(/["\\]/g, "")}",i]${bbox};`];
      if (!parts.length) return [];
      overpassCtl?.abort(); overpassCtl = new AbortController();
      try {
        const res = await fetch("https://overpass-api.de/api/interpreter", {
          method: "POST",
          body: "data=" + encodeURIComponent(`[out:json][timeout:20];(${parts.join("")});out center 150;`),
          signal: overpassCtl.signal,
        });
        const data = await res.json();
        const own = new Set(places.map((p) => norm(p.name)));
        return data.elements.map((el) => ({
          id: "osm-" + el.type + el.id,
          osmUrl: `https://www.openstreetmap.org/${el.type}/${el.id}`,
          name: el.tags?.name || (el.tags?.amenity || el.tags?.shop || "Unnamed").replace(/_/g, " "),
          category: cat || guessCat(el.tags || {}),
          lat: el.lat ?? el.center?.lat, lng: el.lon ?? el.center?.lon,
          tags: el.tags || {}, osm: true,
        })).filter((p) => p.lat && !own.has(norm(p.name)));
      } catch (e) {
        if (e.name !== "AbortError") toast("OpenStreetMap search is busy right now. Showing municipality data only.");
        return [];
      }
    }
    function guessCat(t) {
      const a = t.amenity || "";
      if (/school|college|university|kindergarten/.test(a)) return "school";
      if (/hospital|clinic|doctors|pharmacy/.test(a) || t.healthcare) return "health";
      if (/townhall|post_office|community_centre/.test(a) || t.office === "government") return "government";
      if (a === "place_of_worship") return "church";
      if (/restaurant|cafe|fast_food/.test(a)) return "food";
      if (/police|fire_station/.test(a) || t.emergency) return "safety";
      if (/bank|atm|money_transfer/.test(a)) return "finance";
      if (/bus_station|fuel|ferry_terminal/.test(a) || t.highway === "bus_stop") return "transport";
      if (a === "marketplace" || t.shop) return "market";
      if (t.leisure || t.tourism) return "recreation";
      if (t.bridge || t.man_made || t.power) return "infra";
      return "other";
    }
    function drawOSM(list) {
      osmLayer.clearLayers(); markerById.forEach((m, k) => k.startsWith("osm-") && markerById.delete(k));
      list.forEach((p) => {
        const c = CAT[p.category] || CAT.other;
        const extra = [p.tags["addr:street"], p.tags.opening_hours && "Hours: " + p.tags.opening_hours, p.tags.phone].filter(Boolean).map(esc).join("<br>");
        const m = L.marker([p.lat, p.lng], { icon: pinIcon(p.category, { osm: true, pop: true }), title: p.name, alt: p.name })
          .bindPopup(`<div class="tm-pop"><span class="badge">FROM OPENSTREETMAP</span><h4>${esc(p.name)}</h4>
            <div class="meta"><i class="fa-solid ${c.icon}" style="color:${c.color}"></i> ${esc(c.label)}</div>
            ${extra ? `<p>${extra}</p>` : ""}
            <div class="coords">${p.lat.toFixed(5)}, ${p.lng.toFixed(5)} · <a href="${p.osmUrl}" target="_blank" rel="noopener">View on OSM</a></div>
            ${canEdit ? `<div class="tm-row"><button type="button" class="tm-btn tm-small" data-import="${p.id}"><i class="fa-solid fa-file-import"></i> Add to Tunga Map</button></div>` : ""}</div>`, { maxWidth: 300 })
          .addTo(osmLayer);
        markerById.set(p.id, m);
      });
      lastOsm = list;
    }

    // ---------------- establishment search ----------------
    async function runEstablishmentSearch(q, forcedCat) {
      const cat = forcedCat || (categoryFromQuery(q)?.id ?? "");
      // words that just name a type ("school", "paaralan") show the whole type
      const typeOnly = !!forcedCat || (!!cat && [...CAT[cat].words, CAT[cat].label].some((w) => norm(w) === norm(q) || norm(w).startsWith(norm(q))));
      activeCat = cat; activeQuery = q;
      renderChips(); locLayer.clearLayers();

      const own = places.filter((p) => (typeOnly ? p.category === cat : matches(p, q) || (cat && p.category === cat)));
      drawOwn(own, true);
      renderResults(own, [], labelFor(q, cat), true);
      fit(own);
      $("legend").hidden = false;

      if ($("osmToggle").checked) {
        const osm = await searchOSM(typeOnly ? "" : q, typeOnly ? cat : "");
        if (activeQuery !== q || activeCat !== cat) return; // a newer search started
        drawOSM(osm);
        renderResults(own, osm, labelFor(q, cat), false);
        fit([...own, ...osm]);
      } else { osmLayer.clearLayers(); lastOsm = []; }
    }
    const labelFor = (q, cat) => (cat && (!q || categoryFromQuery(q)?.id === cat) ? CAT[cat].label : q ? `Results for “${q}”` : "All infrastructure");
    function fit(list) {
      const pts = list.filter((p) => p.lat).map((p) => [p.lat, p.lng]);
      if (pts.length === 1) map.flyTo(pts[0], 17, { duration: 0.6 });
      else if (pts.length > 1) map.flyToBounds(pts, { padding: [50, 50], maxZoom: 17, duration: 0.6 });
    }

    function renderResults(own, osm, label, loading) {
      $("resultsLabel").textContent = `${label} · ${own.length + osm.length}`;
      $("clearBtn").hidden = !activeCat && !activeQuery;
      const row = (p) => {
        const c = CAT[p.category] || CAT.other;
        const sub = p.osm ? "OpenStreetMap" : [c.label, p.barangay && "Brgy. " + p.barangay].filter(Boolean).join(" · ");
        return `<li class="tm-result ${p.osm ? "osm" : ""}" tabindex="0" data-id="${p.id}" style="--c:${c.color}">
          <span class="tm-ico"><i class="fa-solid ${c.icon}" aria-hidden="true"></i></span>
          <span><b>${esc(p.name)}</b><small>${esc(sub)}${p.published === false ? ' · <span class="tm-draft">Hidden</span>' : ""}</small></span></li>`;
      };
      let html = own.map(row).join("") + osm.map(row).join("");
      if (loading && $("osmToggle").checked) html += `<li class="tm-empty"><i class="fa-solid fa-spinner fa-spin"></i> Checking OpenStreetMap…</li>`;
      else if (!own.length && !osm.length) {
        html = `<li class="tm-empty">${places.length
          ? "No matches in Tunga. Try another word, like <b>school</b>, <b>health center</b> or a barangay name."
          : "No infrastructure added yet." + (canEdit ? " Use <b>Add infrastructure</b> below to place the first one." : " Municipal staff are adding schools, health centers, halls and more.")}</li>`;
      }
      $("results").innerHTML = html;
    }

    function openResult(li) {
      if (!li) return;
      if (li.dataset.loc != null) return showLocation(lastLocations[+li.dataset.loc]);
      const marker = markerById.get(li.dataset.id);
      if (!marker) return;
      map.flyTo(marker.getLatLng(), 18, { duration: 0.6 });
      map.once("moveend", () => marker.openPopup());
      root.querySelector(".tm-panel").classList.remove("open");
    }
    $("results").addEventListener("click", (e) => openResult(e.target.closest(".tm-result")));
    $("results").addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openResult(e.target.closest(".tm-result")); } });

    // ---------------- place / street search (Nominatim) ----------------
    let lastLocations = [];
    async function runLocationSearch(q) {
      activeQuery = q; activeCat = ""; renderChips();
      osmLayer.clearLayers(); locLayer.clearLayers(); $("legend").hidden = true;
      drawOwn(places, false);
      $("resultsLabel").textContent = "Searching places…";
      $("clearBtn").hidden = false;
      $("results").innerHTML = `<li class="tm-empty"><i class="fa-solid fa-spinner fa-spin"></i> Looking up “${esc(q)}” in Tunga…</li>`;
      const base = "https://nominatim.openstreetmap.org/search?format=jsonv2&polygon_geojson=1&countrycodes=ph";
      try {
        let list = await (await fetch(`${base}&limit=15&bounded=1&viewbox=${BBOX.w},${BBOX.n},${BBOX.e},${BBOX.s}&q=${encodeURIComponent(q)}`)).json();
        if (!list.length) list = await (await fetch(`${base}&limit=8&q=${encodeURIComponent(q + ", Leyte")}`)).json();
        if (activeQuery !== q) return;
        lastLocations = list;
        $("resultsLabel").textContent = `Places for “${q}” · ${list.length}`;
        if (!list.length) {
          $("results").innerHTML = `<li class="tm-empty">No place called “${esc(q)}” found. Try a barangay (e.g. <b>San Roque</b>) or a street name.</li>`;
          return;
        }
        $("results").innerHTML = list.map((r, i) => `<li class="tm-result" tabindex="0" data-loc="${i}" style="--c:var(--tmap-warn)">
          <span class="tm-ico"><i class="fa-solid fa-map-pin" aria-hidden="true"></i></span>
          <span><b>${esc(r.name || r.display_name.split(",")[0])}</b><small>${esc(r.display_name.split(",").slice(1, 4).join(","))}</small></span></li>`).join("");
        showLocation(list[0]);
      } catch {
        $("results").innerHTML = `<li class="tm-empty">Place search is unavailable right now. Check the internet connection and try again.</li>`;
      }
    }
    function showLocation(r) {
      locLayer.clearLayers();
      if (r.geojson && r.geojson.type !== "Point") L.geoJSON(r.geojson, { style: { color: "#b4372b", weight: 3, fillOpacity: 0.08 } }).addTo(locLayer);
      const icon = L.divIcon({ className: "", html: '<i class="fa-solid fa-location-dot tm-loc-pin"></i>', iconSize: [30, 36], iconAnchor: [13, 34], popupAnchor: [0, -30] });
      L.marker([+r.lat, +r.lon], { icon }).addTo(locLayer)
        .bindPopup(`<div class="tm-pop"><h4>${esc(r.name || r.display_name.split(",")[0])}</h4><div class="meta">${esc(r.display_name)}</div><div class="coords">${(+r.lat).toFixed(5)}, ${(+r.lon).toFixed(5)}</div></div>`)
        .openPopup();
      const bb = r.boundingbox?.map(Number);
      if (bb) map.flyToBounds([[bb[0], bb[2]], [bb[1], bb[3]]], { maxZoom: 17, padding: [40, 40], duration: 0.6 });
      else map.flyTo([+r.lat, +r.lon], 17);
      root.querySelector(".tm-panel").classList.remove("open");
    }

    // ---------------- search form ----------------
    function setMode(m) {
      mode = m;
      root.querySelectorAll(".tm-mode button").forEach((b) => { b.classList.toggle("on", b.dataset.mode === m); b.setAttribute("aria-selected", b.dataset.mode === m); });
      $("q").placeholder = m === "est" ? "Search school, health center, market…" : "Search barangay, street, landmark…";
      $("osmToggleWrap").hidden = m !== "est";
      $("chips").hidden = m !== "est";
    }
    root.querySelectorAll(".tm-mode button").forEach((b) => b.addEventListener("click", () => { setMode(b.dataset.mode); $("q").focus(); }));
    $("searchForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const q = $("q").value.trim();
      if (!q) return clearSearch();
      mode === "est" ? runEstablishmentSearch(q) : runLocationSearch(q);
    });
    $("q").addEventListener("search", () => { if (!$("q").value) clearSearch(); });
    $("q").addEventListener("focus", () => root.querySelector(".tm-panel").classList.add("open"));
    $("osmToggle").addEventListener("change", () => (activeCat || activeQuery ? refresh() : osmLayer.clearLayers()));
    $("clearBtn").addEventListener("click", clearSearch);
    $("grab").addEventListener("click", () => root.querySelector(".tm-panel").classList.toggle("open"));

    function clearSearch() {
      activeCat = ""; activeQuery = ""; $("q").value = "";
      osmLayer.clearLayers(); locLayer.clearLayers(); lastOsm = []; $("legend").hidden = true;
      setMode(mode); renderChips(); refresh();
    }
    function refresh() {
      if (activeCat || activeQuery) {
        if (mode === "loc") return drawOwn(places, false);
        return runEstablishmentSearch(activeQuery, activeQuery ? "" : activeCat);
      }
      drawOwn(places, false);
      renderResults(places, [], "All infrastructure", false);
    }

    // ---------------- photo viewer (everyone) ----------------
    root.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));
    $("photoDlg").addEventListener("click", (e) => { if (e.target === $("photoDlg")) $("photoDlg").close(); });
    $("map").addEventListener("click", (e) => {
      const photo = e.target.closest("[data-photo]");
      if (photo) { $("photoImg").src = photo.dataset.photo; $("photoImg").alt = photo.alt; $("photoDlg").showModal(); }
    });

    // ---------------- editing (staff only) ----------------
    if (canEdit) setupEditing();

    function setupEditing() {
      $("pCat").innerHTML = CATEGORIES.map((c) => `<option value="${c.id}">${esc(c.label)}</option>`).join("");
      $("pBrgy").innerHTML = `<option value="">— Select barangay —</option>` + BARANGAYS.map((b) => `<option value="${esc(b)}">${esc(b)}</option>`).join("");

      const hint = (html) => { $("hint").innerHTML = html; $("hint").hidden = !html; };

      $("addBtn").addEventListener("click", () => {
        pickMode = true; map.getContainer().style.cursor = "crosshair";
        root.querySelector(".tm-panel").classList.remove("open");
        hint('<i class="fa-solid fa-location-crosshairs"></i> Tap the map where the infrastructure is. <button type="button" class="tm-link" data-act="cancelPick">Cancel</button>');
      });
      $("hint").addEventListener("click", (e) => {
        const act = e.target.closest("[data-act]")?.dataset.act;
        if (act === "cancelPick") { pickMode = false; map.getContainer().style.cursor = ""; hint(""); }
        if (act === "donePin") { movingPin = false; hint(""); $("placeDlg").showModal(); }
      });
      map.on("click", (e) => {
        if (!pickMode) return;
        pickMode = false; map.getContainer().style.cursor = ""; hint("");
        openPlaceForm(null, e.latlng);
      });

      $("movePin").addEventListener("click", () => {
        movingPin = true; $("placeDlg").close();
        map.panTo(draftMarker.getLatLng());
        hint('<i class="fa-solid fa-hand-pointer"></i> Drag the pin to the exact spot. <button type="button" class="tm-btn tm-small" data-act="donePin">Done</button>');
      });

      function openPlaceForm(place, latlng, preset = {}) {
        editing = place;
        newFiles = []; keepImages = place ? place.images.slice() : [];
        $("placeTitle").textContent = place ? "Edit infrastructure" : "Add infrastructure";
        $("pName").value = place?.name ?? preset.name ?? "";
        $("pCat").value = place?.category ?? preset.category ?? "school";
        $("pBrgy").value = place?.barangay ?? "";
        $("pDesc").value = place?.description ?? preset.description ?? "";
        $("pContact").value = place?.contact ?? preset.contact ?? "";
        $("pPublished").checked = place ? place.published : true;
        $("pImgs").value = ""; $("placeErr").hidden = true;
        draftMarker?.remove();
        draftMarker = L.marker(latlng || [place.lat, place.lng], { draggable: true, icon: pinIcon($("pCat").value), zIndexOffset: 1000 }).addTo(map);
        draftMarker.on("drag dragend", updateCoords);
        updateCoords(); renderThumbs();
        $("placeDlg").showModal();
        $("pName").focus();
      }
      function updateCoords() { const p = draftMarker.getLatLng(); $("pCoords").textContent = `${p.lat.toFixed(6)}, ${p.lng.toFixed(6)}`; }
      $("pCat").addEventListener("change", () => draftMarker?.setIcon(pinIcon($("pCat").value)));
      $("placeDlg").addEventListener("close", () => { if (movingPin) return; draftMarker?.remove(); draftMarker = null; });

      $("pImgs").addEventListener("change", () => {
        const room = 6 - keepImages.length - newFiles.length;
        const files = [...$("pImgs").files].filter((f) => f.type.startsWith("image/"));
        if (files.length > room) toast(room > 0 ? `Only ${room} more photo${room === 1 ? "" : "s"} can be added` : "This place already has 6 photos");
        newFiles.push(...files.slice(0, Math.max(0, room)));
        $("pImgs").value = ""; renderThumbs();
      });
      function renderThumbs() {
        $("pThumbs").innerHTML =
          keepImages.map((im, i) => `<div class="tm-thumb"><img src="${esc(im.url)}" alt=""><button type="button" data-rk="${i}" aria-label="Remove photo">✕</button></div>`).join("") +
          newFiles.map((f, i) => `<div class="tm-thumb"><img src="${URL.createObjectURL(f)}" alt=""><button type="button" data-rn="${i}" aria-label="Remove photo">✕</button></div>`).join("");
      }
      $("pThumbs").addEventListener("click", (e) => {
        const b = e.target.closest("button"); if (!b) return;
        if (b.dataset.rk != null) keepImages.splice(+b.dataset.rk, 1); else newFiles.splice(+b.dataset.rn, 1);
        renderThumbs();
      });

      $("placeForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const pos = draftMarker.getLatLng();
        const fd = new FormData();
        fd.append("name", $("pName").value);
        fd.append("category", $("pCat").value);
        fd.append("barangay", $("pBrgy").value);
        fd.append("description", $("pDesc").value);
        fd.append("contact", $("pContact").value);
        fd.append("published", $("pPublished").checked ? "true" : "false");
        fd.append("lat", pos.lat.toFixed(7));
        fd.append("lng", pos.lng.toFixed(7));
        newFiles.forEach((f) => fd.append("images", f));
        if (editing) fd.append("keepImages", JSON.stringify(keepImages.map((im) => im.id)));
        const btn = $("placeSave");
        btn.disabled = true; btn.textContent = "Saving…";
        try {
          const saved = await api(editing ? detailUrl(editing.id) : API, { method: "POST", body: fd });
          const wasEditing = !!editing;
          $("placeDlg").close();
          toast(wasEditing ? "Changes saved" : `Added “${saved.name}” to the map`);
          await loadPlaces();
          const m = markerById.get(String(saved.id));
          if (m) { map.flyTo(m.getLatLng(), 17, { duration: 0.5 }); map.once("moveend", () => m.openPopup()); }
        } catch (err) {
          $("placeErr").textContent = err.message; $("placeErr").hidden = false;
        } finally { btn.disabled = false; btn.textContent = "Save"; }
      });

      let toDelete = null;
      $("delDlg").addEventListener("close", async () => {
        if ($("delDlg").returnValue !== "yes" || !toDelete) return;
        try { await api(detailUrl(toDelete.id), { method: "DELETE" }); map.closePopup(); toast(`Deleted “${toDelete.name}”`); loadPlaces(); }
        catch (err) { toast(err.message); }
        toDelete = null;
      });

      $("map").addEventListener("click", (e) => {
        const ed = e.target.closest("[data-edit]");
        if (ed) { map.closePopup(); openPlaceForm(places.find((p) => String(p.id) === ed.dataset.edit)); return; }
        const del = e.target.closest("[data-del]");
        if (del) {
          toDelete = places.find((p) => String(p.id) === del.dataset.del);
          $("delName").textContent = toDelete.name; $("delDlg").returnValue = "";
          $("delDlg").showModal(); return;
        }
        const imp = e.target.closest("[data-import]");
        if (imp) {
          const p = lastOsm.find((x) => x.id === imp.dataset.import);
          map.closePopup();
          openPlaceForm(null, L.latLng(p.lat, p.lng), {
            name: p.name === "Unnamed" ? "" : p.name, category: p.category,
            contact: p.tags.phone || "", description: p.tags.opening_hours ? "Hours: " + p.tags.opening_hours : "",
          });
        }
      });
    }

    // ---------------- start ----------------
    renderChips(); setMode("est"); loadPlaces();
  }
})();
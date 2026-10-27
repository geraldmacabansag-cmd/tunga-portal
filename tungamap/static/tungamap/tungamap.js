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
    const PUBLIC = root.dataset.public === "1";     // citizens' view: published places only, no OSM extras
    const COMPACT = root.dataset.compact === "1";   // small box (Contact Us): list opens as a drawer
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
    let brgy = "";                       // barangay filter ("" = all)
    let pickPreset = {};                 // what the next map tap creates (pin or building name)
    let firstLoad = true;
    const store = {                      // remembers the viewer's map choices (if the browser allows)
      get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch { return d; } },
      set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
    };
    let showNames = store.get("tmap-names", "1") === "1";
    let boundsOn = false;
    const inBrgy = (p) => !brgy || p.barangay === brgy;

    // ---------------- map ----------------
    // Rotation comes from the leaflet-rotate plugin (loaded in _map.html). Without it
    // the map still works, just without turning.
    const CAN_ROTATE = typeof L.Map.prototype.setBearing === "function";
    const map = L.map($("map"), {
      zoomControl: false, scrollWheelZoom: !COMPACT,      // in a page section, don't hijack page scrolling
      rotate: CAN_ROTATE, bearing: 0, rotateControl: false,   // our own compass below
      touchRotate: CAN_ROTATE, shiftKeyRotate: CAN_ROTATE,     // two-finger twist / Shift + mouse wheel
    }).setView(TUNGA_CENTER, 14);
    L.control.zoom({ position: "topright" }).addTo(map);
    // OpenStreetMap only serves map images to sites that say who they are, so
    // send our site address with these requests (Django hides it by default).
    const streets = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      referrerPolicy: "strict-origin-when-cross-origin",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
    });
    // Satellite photos, so you can see the actual buildings (with road/place names on top)
    const satellite = L.layerGroup([
      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        maxZoom: 19, maxNativeZoom: 18,
        attribution: 'Imagery &copy; <a href="https://www.esri.com/" target="_blank" rel="noopener">Esri</a>, Maxar, Earthstar Geographics',
      }),
      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
        maxZoom: 19, maxNativeZoom: 18,
      }),
    ]);
    let baseLayer = store.get("tmap-base", "streets") === "satellite" ? satellite : streets;
    baseLayer.addTo(map);
    L.control.scale({ imperial: false, position: "bottomright" }).addTo(map);
    const meLayer = L.layerGroup().addTo(map);

    // Map tools (top right, under + / −): names, satellite, my location, back to Tunga
    const Tools = L.Control.extend({
      options: { position: "topright" },
      onAdd() {
        const d = L.DomUtil.create("div", "leaflet-bar tm-tools");
        d.innerHTML =
          '<a href="#" role="button" data-tool="more" class="tm-more" title="Map tools" aria-label="Show or hide the map tools" aria-expanded="false"><i class="fa-solid fa-layer-group"></i></a>' +
          '<a href="#" role="button" data-tool="names" title="Show / hide building names" aria-label="Show or hide building names"><i class="fa-solid fa-font"></i></a>' +
          '<a href="#" role="button" data-tool="base" title="Satellite view" aria-label="Switch between map and satellite view"><i class="fa-solid fa-satellite"></i></a>' +
          '<a href="#" role="button" data-tool="locate" title="Show my location" aria-label="Show my location"><i class="fa-solid fa-location-crosshairs"></i></a>' +
          '<a href="#" role="button" data-tool="bounds" title="Show barangay and municipal boundaries" aria-label="Show barangay and municipal boundaries"><i class="fa-solid fa-draw-polygon"></i></a>' +
          '<a href="#" role="button" data-tool="home" title="Back to all of Tunga" aria-label="Back to all of Tunga"><i class="fa-solid fa-house"></i></a>';
        L.DomEvent.disableClickPropagation(d);
        L.DomEvent.on(d, "click", (e) => {
          const a = e.target.closest("[data-tool]"); if (!a) return;
          L.DomEvent.preventDefault(e);
          tool(a.dataset.tool);
        });
        return d;
      },
    });
    map.addControl(new Tools());
    map.on("click", () => root.querySelector(".tm-tools")?.classList.remove("expanded"));

    // Compass (top right): the needle always points north. Click it to face north
    // again; ⟲ ⟳ turn the map. Also: two-finger twist on phones, Shift + mouse wheel.
    if (CAN_ROTATE) {
      const Compass = L.Control.extend({
        options: { position: "topright" },
        onAdd() {
          const d = L.DomUtil.create("div", "leaflet-bar tm-compass");
          d.innerHTML =
            '<a href="#" role="button" data-rot="-15" title="Turn left" aria-label="Turn the map left"><i class="fa-solid fa-rotate-left"></i></a>' +
            '<a href="#" role="button" data-rot="north" class="tm-needle-btn" title="Face north" aria-label="Face north">' +
              '<svg class="tm-needle" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l4 10h-8z" fill="#d23c4b"/><path d="M12 22l-4-10h8z" fill="#9aa5ae"/><circle cx="12" cy="12" r="1.6" fill="#fff"/></svg>' +
              '<span class="tm-n">N</span></a>' +
            '<a href="#" role="button" data-rot="15" title="Turn right" aria-label="Turn the map right"><i class="fa-solid fa-rotate-right"></i></a>';
          L.DomEvent.disableClickPropagation(d);
          L.DomEvent.on(d, "click", (e) => {
            const a = e.target.closest("[data-rot]"); if (!a) return;
            L.DomEvent.preventDefault(e);
            if (a.dataset.rot === "north") map.setBearing(0);
            else map.setBearing((map.getBearing() + Number(a.dataset.rot) + 360) % 360);
          });
          return d;
        },
      });
      map.addControl(new Compass());
      const syncCompass = () => {
        const b = map.getBearing();
        const needle = root.querySelector(".tm-needle-btn");
        if (needle) { needle.style.setProperty("--b", `${-b}deg`); needle.classList.toggle("turned", Math.round(b) % 360 !== 0); }
      };
      map.on("rotate", syncCompass); syncCompass();
    }
    function syncTools() {
      const q = (k) => root.querySelector(`.tm-tools [data-tool="${k}"]`);
      root.classList.toggle("tm-names-off", !showNames);
      q("names")?.classList.toggle("on", showNames);
      const sat = baseLayer === satellite;
      root.classList.toggle("tm-sat", sat);
      q("bounds")?.classList.toggle("on", boundsOn);
      if (q("base")) { q("base").classList.toggle("on", sat); q("base").title = sat ? "Map view" : "Satellite view"; q("base").innerHTML = `<i class="fa-solid ${sat ? "fa-map" : "fa-satellite"}"></i>`; }
    }
    function tool(name) {
      if (name === "more") {   // phones: the tools fold into one button
        const box = root.querySelector(".tm-tools"), open = box.classList.toggle("expanded");
        box.querySelector(".tm-more").setAttribute("aria-expanded", open);
        return;
      }
      if (name === "names") { showNames = !showNames; store.set("tmap-names", showNames ? "1" : "0"); toast(showNames ? "Building names shown" : "Building names hidden"); }
      if (name === "base") {
        map.removeLayer(baseLayer);
        baseLayer = baseLayer === satellite ? streets : satellite;
        baseLayer.addTo(map); store.set("tmap-base", baseLayer === satellite ? "satellite" : "streets");
      }
      if (name === "home") { map.closePopup(); if (CAN_ROTATE) map.setBearing(0); map.flyTo(TUNGA_CENTER, 14, { duration: 0.6 }); }
      if (name === "bounds") toggleBoundaries();
      if (name === "hall" && hallMarker) { closePanel(); map.flyTo(hallMarker.getLatLng(), 18, { duration: 0.6 }); map.once("moveend", () => hallMarker.openPopup()); }
      if (name === "locate") {
        if (!navigator.geolocation) return toast("This browser can't share your location.");
        toast("Finding your location…");
        map.locate({ setView: true, maxZoom: 17, enableHighAccuracy: true });
      }
      syncTools();
    }
    map.on("locationfound", (e) => {
      meLayer.clearLayers();
      L.circle(e.latlng, { radius: e.accuracy, color: "#2f6fd6", weight: 1, fillOpacity: 0.08 }).addTo(meLayer);
      L.circleMarker(e.latlng, { radius: 7, color: "#fff", weight: 3, fillColor: "#2f6fd6", fillOpacity: 1 })
        .bindPopup("You are here").addTo(meLayer);
      toast("This is your location");
    });
    map.on("locationerror", () => toast("Couldn't get your location. Allow location access in your browser and try again."));
    // names are hidden when zoomed far out, so the map doesn't get crowded
    const syncZoom = () => root.classList.toggle("tm-far", map.getZoom() < 15);
    map.on("zoomend", syncZoom);
    syncZoom(); syncTools();

    if (COMPACT) {
      map.on("click", () => map.scrollWheelZoom.enable());
      map.on("mouseout", () => map.scrollWheelZoom.disable());
      const btn = document.createElement("button");
      btn.type = "button"; btn.className = "tm-drawer-btn";
      btn.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> <span>Search &amp; places</span>';
      btn.addEventListener("click", () => {
        const open = root.classList.toggle("tm-drawer-open");
        btn.innerHTML = open ? '<i class="fa-solid fa-xmark"></i> <span>Close</span>' : '<i class="fa-solid fa-magnifying-glass"></i> <span>Search &amp; places</span>';
        if (open) setTimeout(() => $("q").focus(), 250);
      });
      root.querySelector(".tm-mapwrap").appendChild(btn);
      new MutationObserver(() => {
        if (!root.classList.contains("tm-drawer-open")) btn.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> <span>Search &amp; places</span>';
      }).observe(root, { attributes: true, attributeFilter: ["class"] });
    }

    // ---------------- the Municipal Hall (Website Settings → Map location) ----------------
    let hallMarker = null, hallPlace = null;   // hallPlace: the hall in search results
    const hEsc = (s) => String(s ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
    if (root.dataset.hallLat) {
      const hall = { lat: +root.dataset.hallLat, lng: +root.dataset.hallLng, name: root.dataset.hallName, address: root.dataset.hallAddress };
      const hallIcon = window.TungaLguPin ? TungaLguPin.icon(false)
        : L.divIcon({ className: "", html: '<i class="fa-solid fa-landmark tm-loc-pin"></i>', iconSize: [30, 36], iconAnchor: [15, 34], popupAnchor: [0, -30] });
      hallMarker = L.marker([hall.lat, hall.lng], { icon: hallIcon, title: hall.name, zIndexOffset: 1000 }).addTo(map);
      hallPlace = { id: "hall", name: hall.name, category: "government", barangay: "",
                    description: "Municipal Hall town hall munisipyo LGU " + (hall.address || ""), lat: hall.lat, lng: hall.lng };
      hallMarker.bindTooltip(hEsc(hall.name), { permanent: true, direction: "bottom", className: "tm-name", opacity: 1, offset: [0, 2] });
      hallMarker.bindPopup(`<div class="tm-pop"><span class="badge">MUNICIPAL HALL</span><h4>${hEsc(hall.name)}</h4>
        <div class="meta"><i class="fa-solid fa-location-dot"></i> ${hEsc(hall.address)}</div>
        <div class="coords">${hall.lat.toFixed(5)}, ${hall.lng.toFixed(5)}</div>
        <div class="tm-row"><a class="tm-btn tm-small" target="_blank" rel="noopener" href="https://www.google.com/maps/dir/?api=1&destination=${hall.lat},${hall.lng}"><i class="fa-solid fa-diamond-turn-right"></i> Get directions</a></div></div>`, { maxWidth: 280 });
      // a "Municipal Hall" button with the other map tools
      const tools = root.querySelector(".tm-tools");
      if (tools) {
        const a = document.createElement("a");
        a.href = "#"; a.setAttribute("role", "button"); a.dataset.tool = "hall";
        a.title = "Go to the " + hall.name; a.setAttribute("aria-label", a.title);
        a.innerHTML = '<i class="fa-solid fa-landmark"></i>';
        tools.insertBefore(a, tools.querySelector('[data-tool="home"]'));
      }
      if (root.dataset.start === "hall") { map.setView([hall.lat, hall.lng], 17); setTimeout(() => hallMarker.openPopup(), 300); }
    }

    // ---------------- barangay & municipal boundaries (from OpenStreetMap) ----------------
    // Loaded once from OpenStreetMap (Overpass) and remembered in the browser for 2 weeks.
    const boundsLayer = L.layerGroup();          // all boundaries (the polygon button)
    const highlightLayer = L.layerGroup().addTo(map); // one barangay (barangay filter)
    let boundaries = null, boundariesPromise = null;
    const BOUNDS_KEY = "tmap-boundaries-v1", BOUNDS_DAYS = 14;

    function brgyKey(s) {
      return norm(s).replace(/\bbarangay\b|\bbrgy\.?|\(pob\.?\)|poblacion/g, "")
        .replace(/\bsto\.?\s/g, "santo ").replace(/\bsta\.?\s/g, "santa ").replace(/[^a-z0-9]+/g, " ").trim();
    }
    function matchBarangay(osmName) {          // OSM name -> our barangay list ("Sto. Niño" -> "Santo Niño")
      const k = brgyKey(osmName);
      return BARANGAYS.find((b) => brgyKey(b) === k) || BARANGAYS.find((b) => k && (k.includes(brgyKey(b)) || brgyKey(b).includes(k))) || "";
    }
    function stitch(segs) {                    // join boundary pieces into closed rings
      const same = (a, b) => Math.abs(a[0] - b[0]) < 1e-9 && Math.abs(a[1] - b[1]) < 1e-9;
      segs = segs.map((s) => s.slice()); const rings = [];
      while (segs.length) {
        let ring = segs.shift(), grew = true;
        while (grew && !same(ring[0], ring[ring.length - 1])) {
          grew = false;
          for (let i = 0; i < segs.length; i++) {
            const s = segs[i], a = ring[0], z = ring[ring.length - 1];
            if (same(z, s[0])) ring = ring.concat(s.slice(1));
            else if (same(z, s[s.length - 1])) ring = ring.concat(s.slice().reverse().slice(1));
            else if (same(a, s[s.length - 1])) ring = s.concat(ring.slice(1));
            else if (same(a, s[0])) ring = s.slice().reverse().concat(ring.slice(1));
            else continue;
            segs.splice(i, 1); grew = true; break;
          }
        }
        if (ring.length > 3) rings.push(ring);
      }
      return rings;
    }
    function relToArea(rel) {
      const ways = (rel.members || []).filter((m) => m.type === "way" && m.geometry);
      const pts = (w) => w.geometry.map((g) => [+g.lat.toFixed(6), +g.lon.toFixed(6)]);
      const outer = stitch(ways.filter((w) => w.role !== "inner").map(pts));
      const inner = stitch(ways.filter((w) => w.role === "inner").map(pts));
      const label = (rel.members || []).find((m) => m.type === "node" && (m.role === "label" || m.role === "admin_centre"));
      return { name: rel.tags?.name || "", outer, inner, label: label ? [label.lat, label.lon] : null };
    }
    function inRing(pt, ring) {
      let inside = false;
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const [yi, xi] = ring[i], [yj, xj] = ring[j];
        if ((yi > pt[0]) !== (yj > pt[0]) && pt[1] < ((xj - xi) * (pt[0] - yi)) / (yj - yi) + xi) inside = !inside;
      }
      return inside;
    }
    const inArea = (pt, a) => a.outer.some((r) => inRing(pt, r)) && !a.inner.some((r) => inRing(pt, r));
    function centerOf(a) {                     // where to write the barangay name
      if (a.label) return a.label;
      const r = a.outer.slice().sort((x, y) => y.length - x.length)[0] || [];
      let A = 0, cy = 0, cx = 0;                 // centroid of the biggest ring
      for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
        const f = r[j][1] * r[i][0] - r[i][1] * r[j][0];
        A += f; cx += (r[j][1] + r[i][1]) * f; cy += (r[j][0] + r[i][0]) * f;
      }
      if (!A) return r[0] || TUNGA_CENTER;
      return [cy / (3 * A), cx / (3 * A)];
    }

    function loadBoundaries() {
      if (boundaries) return Promise.resolve(boundaries);
      if (boundariesPromise) return boundariesPromise;
      try {
        const saved = JSON.parse(store.get(BOUNDS_KEY, "null"));
        if (saved && Date.now() - saved.t < BOUNDS_DAYS * 864e5 && saved.d?.brgys?.length) return Promise.resolve(boundaries = saved.d);
      } catch { /* ignore */ }
      const q = `[out:json][timeout:40];
        rel["boundary"="administrative"]["admin_level"="6"]["name"~"^Tunga$",i](${BBOX.s - 0.1},${BBOX.w - 0.1},${BBOX.n + 0.1},${BBOX.e + 0.1})->.t;
        .t out geom;
        .t map_to_area->.a;
        rel(area.a)["boundary"="administrative"]["admin_level"="10"];
        out geom;`;
      boundariesPromise = fetch("https://overpass-api.de/api/interpreter", { method: "POST", body: "data=" + encodeURIComponent(q) })
        .then((r) => { if (!r.ok) throw new Error("busy"); return r.json(); })
        .then((data) => {
          const rels = data.elements.filter((e) => e.type === "relation");
          const townRel = rels.find((r) => r.tags?.admin_level === "6");
          const town = townRel ? relToArea(townRel) : null;
          const brgys = rels.filter((r) => r.tags?.admin_level === "10").map(relToArea)
            .filter((a) => a.outer.length)
            .map((a) => ({ ...a, center: centerOf(a), match: matchBarangay(a.name) }))
            .filter((a) => (town ? inArea(a.center, town) : !!a.match));
          if (!brgys.length && !town) throw new Error("none");
          boundaries = { town, brgys };
          store.set(BOUNDS_KEY, JSON.stringify({ t: Date.now(), d: boundaries }));
          return boundaries;
        })
        .catch((e) => { boundariesPromise = null; throw e; });
      return boundariesPromise;
    }

    // which barangay (from our list) is this spot in? -> "San Roque" or "" if unknown
    function barangayAt(latlng) {
      return loadBoundaries().then((b) => {
        const pt = [latlng.lat, latlng.lng];
        const hit = b.brgys.find((a) => inArea(pt, a));
        return hit ? (hit.match || hit.name) : "";
      }).catch(() => null);   // null = boundaries not available
    }
    root._tmapBarangayAt = barangayAt; // for the Super Admin page (Municipal Hall pin)

    // count by the Barangay saved on each place (same as the barangay filter)
    const placesInside = (a) => (a.match ? places.filter((p) => p.barangay === a.match) : places.filter((p) => inArea([p.lat, p.lng], a))).length;
    function brgyPopup(a) {
      const n = placesInside(a), name = a.match || a.name;
      return `<div class="tm-pop"><span class="badge">BARANGAY</span><h4>${esc(name)}</h4>
        <div class="meta">Municipality of Tunga, Leyte</div>
        <p>${n} place${n === 1 ? "" : "s"} on the map</p>
        ${a.match ? `<div class="tm-row"><button type="button" class="tm-btn tm-small" data-brgy-show="${esc(a.match)}"><i class="fa-solid fa-list"></i> Show places here</button></div>` : ""}</div>`;
    }
    const busyEditing = () => pickMode || movingPin || root.classList.contains("lgu-editing");
    function drawBoundaries(b) {
      boundsLayer.clearLayers();
      if (b.town) {
        L.polygon([...b.town.outer, ...b.town.inner], { color: "#15231d", weight: 3, dashArray: "8 6", fill: false })
          .on("click", (e) => {
            if (busyEditing()) return;
            L.popup({ maxWidth: 260 }).setLatLng(e.latlng).setContent(
              `<div class="tm-pop"><span class="badge">MUNICIPALITY</span><h4>Municipality of Tunga</h4>
               <div class="meta">Province of Leyte</div><p>${b.brgys.length} barangays · ${places.length} places on the map</p></div>`).openOn(map);
          }).addTo(boundsLayer);
      }
      b.brgys.forEach((a, i) => {
        const hue = (i * 47) % 360;
        const poly = L.polygon([...a.outer, ...a.inner], {
          color: `hsl(${hue} 55% 38%)`, weight: 2, fillColor: `hsl(${hue} 60% 50%)`, fillOpacity: 0.07,
        }).addTo(boundsLayer);
        poly.on("mouseover", () => poly.setStyle({ fillOpacity: 0.18 }));
        poly.on("mouseout", () => poly.setStyle({ fillOpacity: 0.07 }));
        poly.on("click", (e) => {
          if (busyEditing()) return;   // tapping to place something: let the map handle it
          L.popup({ maxWidth: 260 }).setLatLng(e.latlng).setContent(brgyPopup(a)).openOn(map);
        });
        L.marker(a.center, { interactive: false, keyboard: false,
          icon: L.divIcon({ className: "", iconSize: null, html: `<div class="tm-brgy-name">${esc(a.match || a.name)}</div>` }) }).addTo(boundsLayer);
      });
    }
    function toggleBoundaries() {
      boundsOn = !boundsOn; syncTools();
      if (!boundsOn) { map.removeLayer(boundsLayer); return; }
      toast("Loading barangay boundaries…");
      loadBoundaries().then((b) => {
        if (!boundsOn) return;
        drawBoundaries(b); boundsLayer.addTo(map);
        toast(`${b.brgys.length} barangay${b.brgys.length === 1 ? "" : "s"} shown — click one to see its name and places`);
        const all = b.town ? b.town.outer.flat() : b.brgys.flatMap((a) => a.outer.flat());
        if (all.length) map.flyToBounds(all, { padding: [30, 30], duration: 0.6 });
      }).catch(() => { boundsOn = false; syncTools(); toast("Boundaries couldn't be loaded from OpenStreetMap right now. Try again later."); });
    }
    function highlightBarangay(name) {
      highlightLayer.clearLayers();
      if (!name) return;
      loadBoundaries().then((b) => {
        const a = b.brgys.find((x) => x.match === name);
        if (!a || brgy !== name) return;
        L.polygon([...a.outer, ...a.inner], { color: "#0f6b52", weight: 3, fillColor: "#0f6b52", fillOpacity: 0.08, interactive: false }).addTo(highlightLayer);
        map.flyToBounds(a.outer.flat(), { padding: [30, 30], duration: 0.6 });
      }).catch(() => {});
    }
    const ownLayer = L.layerGroup().addTo(map);
    const osmLayer = L.layerGroup().addTo(map);
    const locLayer = L.layerGroup().addTo(map);
    // the map may be inside a tab or hidden section — fix its size when it becomes visible
    new ResizeObserver(() => map.invalidateSize()).observe(root);
    // Let the page add its own layers (e.g. the Super Admin's Municipal Hall pin).
    // Top-left corner of the map: buttons a page can add to (e.g. "Back"), plus
    // "Show list" when the left panel is hidden with its ✕ button.
    const topLeft = document.createElement("div");
    topLeft.className = "tm-tl";
    root.querySelector(".tm-mapwrap").appendChild(topLeft);
    {
      const hideBtn = document.createElement("button");
      hideBtn.type = "button"; hideBtn.className = "tm-hide-panel";
      hideBtn.title = "Hide the list"; hideBtn.setAttribute("aria-label", "Hide the list");
      hideBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
      root.querySelector(".tm-brand").appendChild(hideBtn);
      const showBtn = document.createElement("button");
      showBtn.type = "button"; showBtn.className = "tm-show-panel";
      showBtn.innerHTML = '<i class="fa-solid fa-bars"></i> <span>Show list</span>';
      topLeft.appendChild(showBtn);
      const isPhone = () => window.matchMedia("(max-width: 760px)").matches;
      const setHidden = (hide, remember = true) => {
        root.classList.toggle("tm-panel-hidden", hide);
        if (hide) root.querySelector(".tm-panel").classList.remove("open");
        // remembered on computers only; on phones the list comes back next visit
        if (remember && !isPhone() && !COMPACT) store.set("tmap-panel-hidden", hide ? "1" : "0");
        setTimeout(() => map.invalidateSize(), 30);
      };
      hideBtn.addEventListener("click", () => setHidden(true));
      showBtn.addEventListener("click", () => setHidden(false));
      if (!COMPACT && !isPhone() && store.get("tmap-panel-hidden", "0") === "1") setHidden(true, false);
    }
    root._tmap = map;
    root.dispatchEvent(new CustomEvent("tmap:ready", { detail: { map } }));

    function pinIcon(cat, { osm = false, pop = false, draft = false } = {}) {
      const c = CAT[cat] || CAT.other;
      return L.divIcon({
        className: "",
        html: `<div class="tm-pin ${osm ? "osm" : ""} ${pop ? "pop" : ""} ${draft ? "draft" : ""}" style="--c:${c.color}"><span class="head"></span><i class="fa-solid ${c.icon}"></i></div>`,
        iconSize: [34, 42], iconAnchor: [17, 40], popupAnchor: [0, -36],
      });
    }

    // the list: bottom sheet on phones, drawer in compact mode
    function closePanel() { root.querySelector(".tm-panel").classList.remove("open"); root.classList.remove("tm-drawer-open"); }

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

    // Search words. Whole words only, so "business" is not "bus" (Transport)
    // and "church" is not "rhu" (Health). Short forms are written out:
    // "Sto. Nino" = "Santo Nino", "Brgy." = "Barangay".
    const ABBR = { sto: "santo", sta: "santa", brgy: "barangay", bgy: "barangay", pob: "poblacion", natl: "national", elem: "elementary", nhs: "national high school" };
    const STOP = new Set(["of", "the", "ng", "sa", "in", "at", "and", "near", "a", "an"]);
    function words(s) {
      return norm(s).replace(/[^a-z0-9]+/g, " ").trim().split(" ").filter(Boolean)
        .flatMap((w) => (ABBR[w] || w).split(" "));
    }
    const qWords = (q) => words(q).filter((w) => !STOP.has(w));
    const hasPhrase = (text, phrase) => (" " + words(text).join(" ") + " ").includes(" " + words(phrase).join(" ") + " ");
    function categoryFromQuery(q) {
      const ws = qWords(q);
      if (!ws.length) return null;
      const one = ws.length === 1 && ws[0].length >= 3 ? ws[0] : "";
      return CATEGORIES.find((c) => c.id !== "other" && (
        hasPhrase(q, c.label) || c.words.some((w) => hasPhrase(q, w)) ||
        (one && [c.label, ...c.words].some((w) => words(w).some((x) => x.startsWith(one))))
      )) || null;
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
      try { places = (await api(API)).places; if (PUBLIC) places = places.filter((p) => p.published); }
      catch (e) { places = []; toast("Couldn't load places: " + e.message); }
      refresh();
      if (firstLoad) {          // a shared link (…#place=12) opens that place
        firstLoad = false;
        const id = (location.hash.match(/place=(\d+)/) || [])[1];
        const m = id && markerById.get(id);
        if (m) { map.setView(m.getLatLng(), 18); setTimeout(() => m.openPopup(), 200); }
        else openBarangayFromLink();
      }
    }

    // A link from the About Us page (…/tunga-map/#barangay=San%20Roque) opens
    // that barangay's hall pin. No hall pin: the barangay itself is shown.
    function openBarangayFromLink() {
      const raw = (location.hash.match(/barangay=([^&]+)/) || [])[1];
      if (!raw) return;
      let wanted = "";
      try { wanted = decodeURIComponent(raw.replace(/\+/g, " ")); } catch (e) { wanted = raw; }
      const key = brgyKey(wanted);
      if (!key) return;
      const sameBrgy = (p) => p.barangay && brgyKey(p.barangay) === key;
      const isHall = (p) => /barangay hall|brgy\.? hall/.test(norm(p.name));
      const hall = places.find((p) => sameBrgy(p) && isHall(p))
        || places.find((p) => isHall(p) && brgyKey(p.name).includes(key));
      const m = hall && markerById.get(String(hall.id));
      if (m) {
        map.setView(m.getLatLng(), 17);
        setTimeout(() => m.openPopup(), 250);
        return;
      }
      const name = matchBarangay(wanted);
      if (name) {
        toast("Barangay " + name + " has no barangay hall pin yet.");
        brgy = name;
        highlightBarangay(name);
      }
    }

    // every search word is found in the place (start of a word counts:
    // "sch" finds "School"; "schools" finds "school")
    function matches(p, q) {
      const ws = qWords(q);
      if (!ws.length) return false;
      const c = CAT[p.category] || CAT.other;
      const hay = words([p.name, p.barangay, p.barangay && "barangay", p.description, c.label].join(" "));
      return ws.every((w) => {
        const alt = w.length > 3 && w.endsWith("s") ? w.slice(0, -1) : w;
        return hay.some((h) => h.startsWith(w) || h.startsWith(alt));
      });
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
        <div class="coords">${p.lat.toFixed(5)}, ${p.lng.toFixed(5)} · <a href="https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lng}" target="_blank" rel="noopener">Directions</a> · <a href="#place=${p.id}" data-share="${p.id}">Copy link</a></div>
        ${edit}
      </div>`;
    }

    function drawOwn(list, pop) {
      ownLayer.clearLayers(); markerById.clear();
      if (hallMarker) markerById.set("hall", hallMarker);
      list.forEach((p) => {
        const c = CAT[p.category] || CAT.other;
        let m;
        if (p.labelOnly) {
          // a building name: just the text, written on the building
          m = L.marker([p.lat, p.lng], {
            icon: L.divIcon({ className: "", iconSize: null,
              html: `<div class="tm-blabel ${p.published ? "" : "draft"}">${esc(p.name)}</div>` }),
            title: p.name, alt: p.name, riseOnHover: true,
          });
        } else {
          m = L.marker([p.lat, p.lng], { icon: pinIcon(p.category, { pop, draft: !p.published }), title: p.name, alt: p.name });
          m.bindTooltip(esc(p.name), { permanent: true, direction: "bottom", className: "tm-name", opacity: 1, offset: [0, 2] });
        }
        m.bindPopup(() => popupHtml(p), { maxWidth: 300, autoPanPadding: [30, 30] });
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

      const pool = places.filter(inBrgy).concat(hallPlace && !brgy ? [hallPlace] : []);
      const own = pool.filter((p) => (typeOnly ? p.category === cat : matches(p, q) || (cat && p.category === cat)))
        .map((p, i) => [p, matches(p, q) ? 0 : 1, i]).sort((a, b) => a[1] - b[1] || a[2] - b[2]).map((x) => x[0]);  // exact matches first
      // a name typed in that isn't one of the Tunga Map's places: look it up as
      // a place / street instead (the public map has no OpenStreetMap extras)
      if (q && !own.length && !typeOnly && !$("osmToggle").checked) return runLocationSearch(q, true);
      drawOwn(own.filter((p) => p.id !== "hall"), true);
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
      $("clearBtn").hidden = !activeCat && !activeQuery && !brgy;
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
      closePanel();
    }
    $("results").addEventListener("click", (e) => openResult(e.target.closest(".tm-result")));
    $("results").addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openResult(e.target.closest(".tm-result")); } });

    // ---------------- place / street search (Nominatim) ----------------
    let lastLocations = [];
    async function runLocationSearch(q, fromEst = false) {
      activeQuery = q; activeCat = ""; renderChips();
      osmLayer.clearLayers(); locLayer.clearLayers(); $("legend").hidden = true;
      drawOwn(places.filter(inBrgy), false);
      $("resultsLabel").textContent = "Searching places…";
      $("clearBtn").hidden = false;
      $("results").innerHTML = `<li class="tm-empty"><i class="fa-solid fa-spinner fa-spin"></i> Looking up “${esc(q)}” in Tunga…</li>`;
      const base = "https://nominatim.openstreetmap.org/search?format=jsonv2&polygon_geojson=1&countrycodes=ph";
      try {
        let list = await (await fetch(`${base}&limit=15&bounded=1&viewbox=${BBOX.w},${BBOX.n},${BBOX.e},${BBOX.s}&q=${encodeURIComponent(q)}`)).json();
        if (!list.length) list = await (await fetch(`${base}&limit=8&q=${encodeURIComponent(q + ", Leyte")}`)).json();
        if (activeQuery !== q) return;
        lastLocations = list;
        $("resultsLabel").textContent = (fromEst ? `No establishment found — places for “${q}”` : `Places for “${q}”`) + ` · ${list.length}`;
        if (!list.length) {
          $("results").innerHTML = fromEst
            ? `<li class="tm-empty">Nothing called “${esc(q)}” on the map yet. Try another word, like <b>school</b>, <b>health center</b> or a barangay name.</li>`
            : `<li class="tm-empty">No place called “${esc(q)}” found. Try a barangay (e.g. <b>San Roque</b>) or a street name.</li>`;
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
      closePanel();
    }

    // ---------------- search form ----------------
    function setMode(m) {
      mode = m;
      root.querySelectorAll(".tm-mode button").forEach((b) => { b.classList.toggle("on", b.dataset.mode === m); b.setAttribute("aria-selected", b.dataset.mode === m); });
      $("q").placeholder = m === "est" ? "Search school, health center, market…" : "Search barangay, street, landmark…";
      $("osmToggleWrap").hidden = m !== "est" || PUBLIC;
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
    $("brgyFilter").addEventListener("change", () => {
      brgy = $("brgyFilter").value;
      refresh();
      if (brgy) fit(places.filter(inBrgy));
      highlightBarangay(brgy);
    });
    $("grab").addEventListener("click", () => root.querySelector(".tm-panel").classList.toggle("open"));

    function clearSearch() {
      activeCat = ""; activeQuery = ""; $("q").value = "";
      brgy = ""; $("brgyFilter").value = ""; highlightLayer.clearLayers();
      osmLayer.clearLayers(); locLayer.clearLayers(); lastOsm = []; $("legend").hidden = true;
      setMode(mode); renderChips(); refresh();
    }
    function refresh() {
      if (activeCat || activeQuery) {
        if (mode === "loc") return drawOwn(places.filter(inBrgy), false);
        return runEstablishmentSearch(activeQuery, activeQuery ? "" : activeCat);
      }
      drawOwn(places.filter(inBrgy), false);
      renderResults(places.filter(inBrgy), [], brgy ? "Brgy. " + brgy : "All infrastructure", false);
    }

    // ---------------- photo viewer (everyone) ----------------
    root.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));
    $("photoDlg").addEventListener("click", (e) => { if (e.target === $("photoDlg")) $("photoDlg").close(); });
    $("map").addEventListener("click", (e) => {
      const bshow = e.target.closest("[data-brgy-show]");
      if (bshow) {
        map.closePopup(); $("brgyFilter").value = bshow.dataset.brgyShow;
        $("brgyFilter").dispatchEvent(new Event("change"));
        root.querySelector(".tm-panel").classList.add("open");
        return;
      }
      const share = e.target.closest("[data-share]");
      if (share) {
        e.preventDefault();
        const url = location.href.split("#")[0] + "#place=" + share.dataset.share;
        if (navigator.clipboard) navigator.clipboard.writeText(url).then(() => toast("Link copied — paste it anywhere to share this place"), () => window.prompt("Copy this link:", url));
        else window.prompt("Copy this link:", url);
        return;
      }
      const photo = e.target.closest("[data-photo]");
      if (photo) { $("photoImg").src = photo.dataset.photo; $("photoImg").alt = photo.alt; $("photoDlg").showModal(); }
    });

    // ---------------- editing (staff only) ----------------
    if (canEdit) { setupEditing(); setTimeout(() => loadBoundaries().catch(() => {}), 1500); }

    function setupEditing() {
      $("pCat").innerHTML = CATEGORIES.map((c) => `<option value="${c.id}">${esc(c.label)}</option>`).join("");
      $("pBrgy").innerHTML = `<option value="">— Select barangay —</option>` + BARANGAYS.map((b) => `<option value="${esc(b)}">${esc(b)}</option>`).join("");

      const hint = (html) => { $("hint").innerHTML = html; $("hint").hidden = !html; };

      $("labelBtn")?.addEventListener("click", () => {
        pickMode = true; root.classList.add("tm-picking"); pickPreset = { labelOnly: true, category: "government" };
        map.getContainer().style.cursor = "crosshair";
        closePanel();
        hint('<i class="fa-solid fa-font"></i> Tap the building you want to name.' +
          (baseLayer === satellite ? "" : ' <button type="button" class="tm-link" data-act="sat">Use satellite view</button>') +
          ' <button type="button" class="tm-link" data-act="cancelPick">Cancel</button>');
      });
      $("exportBtn")?.addEventListener("click", exportCsv);
      function exportCsv() {
        const cell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
        const head = ["Name", "Type", "Barangay", "Latitude", "Longitude", "Contact", "Description", "Shown to public", "Name only (no pin)", "Photos"];
        const rows = places.map((p) => [p.name, (CAT[p.category] || CAT.other).label, p.barangay, p.lat.toFixed(6), p.lng.toFixed(6),
          p.contact, p.description, p.published ? "Yes" : "No", p.labelOnly ? "Yes" : "No", p.images.length]);
        const csv = "\ufeff" + [head, ...rows].map((r) => r.map(cell).join(",")).join("\r\n");
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
        a.download = `tunga-map-places-${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 2000);
        toast(`Exported ${places.length} place${places.length === 1 ? "" : "s"}`);
      }

      $("addBtn").addEventListener("click", () => {
        pickMode = true; root.classList.add("tm-picking"); pickPreset = {}; map.getContainer().style.cursor = "crosshair";
        closePanel();
        hint('<i class="fa-solid fa-location-crosshairs"></i> Tap the map where the infrastructure is. <button type="button" class="tm-link" data-act="cancelPick">Cancel</button>');
      });
      $("hint").addEventListener("click", (e) => {
        const act = e.target.closest("[data-act]")?.dataset.act;
        if (act === "cancelPick") { pickMode = false; root.classList.remove("tm-picking"); map.getContainer().style.cursor = ""; hint(""); }
        if (act === "sat") { if (baseLayer !== satellite) tool("base"); e.target.closest("[data-act]").remove(); }
        if (act === "donePin") { movingPin = false; hint(""); $("placeDlg").showModal(); }
      });
      map.on("click", (e) => {
        if (!pickMode) return;
        pickMode = false; root.classList.remove("tm-picking"); map.getContainer().style.cursor = ""; hint("");
        openPlaceForm(null, e.latlng, pickPreset);
      });

      $("movePin").addEventListener("click", () => {
        movingPin = true; $("placeDlg").close();
        map.panTo(draftMarker.getLatLng());
        hint('<i class="fa-solid fa-hand-pointer"></i> Drag the pin to the exact spot. <button type="button" class="tm-btn tm-small" data-act="donePin">Done</button>');
      });

      function openPlaceForm(place, latlng, preset = {}) {
        editing = place;
        newFiles = []; keepImages = place ? place.images.slice() : [];
        const labelOnly = place ? !!place.labelOnly : !!preset.labelOnly;
        $("placeTitle").textContent = place ? (labelOnly ? "Edit building name" : "Edit infrastructure") : (labelOnly ? "Name a building" : "Add infrastructure");
        $("pLabelOnly").checked = labelOnly;
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
        draftMarker.on("dragend", () => autoBarangay(draftMarker.getLatLng()));
        $("pBrgyNote").textContent = ""; $("pBrgyNote").className = "tm-note";
        if (!place || latlng) autoBarangay(draftMarker.getLatLng());   // new spot: fill it in
        updateCoords(); renderThumbs();
        $("placeDlg").showModal();
        $("pName").focus();
      }
      // fills in the Barangay box from where the pin is (barangay boundaries)
      let autoSeq = 0;
      function autoBarangay(latlng) {
        const seq = ++autoSeq, note = $("pBrgyNote");
        note.textContent = "Finding the barangay…"; note.className = "tm-note";
        barangayAt(latlng).then((name) => {
          if (seq !== autoSeq) return;
          if (name === null) { note.textContent = "Couldn't look up the barangay — please choose it."; return; }
          if (name && BARANGAYS.includes(name)) {
            $("pBrgy").value = name;
            note.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Filled in from the map: Brgy. ${esc(name)}`; note.className = "tm-note ok";
          } else {
            $("pBrgy").value = "";
            note.textContent = "This spot is outside Tunga's barangays — choose one if needed."; note.className = "tm-note warn";
          }
        });
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
        fd.append("labelOnly", $("pLabelOnly").checked ? "true" : "false");
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
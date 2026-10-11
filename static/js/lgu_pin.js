/* The Municipal Hall pin — one look and one way of moving it, used by both
   Website Settings → General → Map location and the Interactive Map, so
   pinning the location works (and looks) exactly the same in both places.
   Both save to the same place (Contact Us → Our Location).

   TungaLguPin.icon()                         the pin's look
   TungaLguPin.create(map, [lat, lng], name)  adds the pin to a Leaflet map
   TungaLguPin.edit(map, pin, onMove)         start moving: drag the pin or click the map
   TungaLguPin.stopEdit(map, pin)             stop moving
   TungaLguPin.inLeyte(lat, lng)              the same limit the server checks
*/
(function () {
  var COLOR = '#c0392b';
  var ZOOM = 17;

  function icon(editing) {
    return L.divIcon({
      className: '',
      html:
        '<div style="position:relative;width:38px;height:46px;' + (editing ? 'filter:drop-shadow(0 0 6px rgba(255,212,59,.95));' : '') + '">' +
          '<span style="position:absolute;left:0;top:0;width:38px;height:38px;border-radius:50% 50% 50% 4px;' +
            'transform:rotate(-45deg);background:' + COLOR + ';border:3px solid #fff;box-shadow:0 3px 9px rgba(0,0,0,.4);"></span>' +
          '<i class="fa-solid fa-landmark" style="position:absolute;left:0;top:0;width:38px;height:38px;display:grid;' +
            'place-items:center;color:#fff;font-size:15px;"></i>' +
        '</div>',
      iconSize: [38, 46], iconAnchor: [19, 44], popupAnchor: [0, -40]
    });
  }

  function create(map, pos, name) {
    var pin = L.marker(pos, { icon: icon(false), zIndexOffset: 1000, title: name || 'Municipal Hall', keyboard: true });
    return pin.addTo(map);
  }

  function edit(map, pin, onMove) {
    stopEdit(map, pin);
    pin.setIcon(icon(true));
    pin.dragging.enable();
    function moved(ll) { if (onMove) onMove(ll); }
    pin._lguDrag = function () { moved(pin.getLatLng()); };
    pin._lguClick = function (e) { pin.setLatLng(e.latlng); moved(e.latlng); };
    pin.on('dragend', pin._lguDrag);
    map.on('click', pin._lguClick);
    map.getContainer().style.cursor = 'crosshair';
  }

  function stopEdit(map, pin) {
    if (pin._lguDrag) pin.off('dragend', pin._lguDrag);
    if (pin._lguClick) map.off('click', pin._lguClick);
    pin._lguDrag = pin._lguClick = null;
    if (pin.dragging) pin.dragging.disable();
    pin.setIcon(icon(false));
    map.getContainer().style.cursor = '';
  }

  function inLeyte(lat, lng) {
    return lat >= 9.8 && lat <= 12.6 && lng >= 124.0 && lng <= 125.9;
  }

  window.TungaLguPin = { icon: icon, create: create, edit: edit, stopEdit: stopEdit, inLeyte: inLeyte, ZOOM: ZOOM, COLOR: COLOR };
})();
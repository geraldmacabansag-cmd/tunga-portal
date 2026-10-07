/* Builds the citizen's input boxes on top of the PDF on the "Fill Out
 * Online" page/popup, using the style the office chose in the builder:
 * left / center / right, top / middle / bottom, font size, bold, color,
 * ALL CAPS and hint text. The downloaded PDF (offices/pdf_stamp.py) uses
 * the same rules, so what people type is where it ends up on paper.
 *
 *   TungaFill.build(fieldsData, fieldLayer)   -> creates the inputs
 *   TungaFill.scale(fieldLayer, renderScale)  -> sizes text after each zoom
 */
window.TungaFill = window.TungaFill || (function () {
  var JUSTIFY = { top: 'flex-start', middle: 'center', bottom: 'flex-end' };

  function build(fieldsData, layer) {
    fieldsData.forEach(function (f) {
      var box = document.createElement('div');
      box.className = 'fill-field-box';
      box.dataset.page = f.page_number;
      box.style.cssText = [
        'position:absolute', 'box-sizing:border-box',
        'left:' + (f.x * 100) + '%', 'top:' + (f.y * 100) + '%',
        'width:' + (f.width * 100) + '%', 'height:' + (f.height * 100) + '%',
        'flex-direction:column',
        'justify-content:' + (JUSTIFY[f.v_align] || 'flex-end'),
      ].join(';');

      var input = document.createElement('input');
      input.name = 'field_' + f.id;
      input.dataset.fieldId = f.id;

      if (f.field_type === 'checkbox') {
        input.type = 'checkbox';
        input.checked = !!f.initial_value;
        input.style.cssText = 'display:block;width:100%;height:100%;margin:0;cursor:pointer;';
      } else {
        input.type = f.field_type === 'date' ? 'date' : (f.field_type === 'number' ? 'number' : 'text');
        input.value = f.initial_value || '';
        input.title = f.label || '';
        input.placeholder = f.placeholder || '';
        input.className = 'fill-online-input';
        input.dataset.fontSize = f.font_size || 0;
        input.dataset.boxHeight = f.height;
        input.style.cssText = [
          'display:block', 'width:100%', 'box-sizing:border-box', 'margin:0', 'outline:none',
          'border:1px solid transparent', 'background:transparent', 'border-radius:3px',
          'text-align:' + (f.text_align || 'left'),
          'font-weight:' + (f.bold ? '700' : '400'),
          'color:' + (f.text_color || '#000000'),
          'text-transform:' + (f.uppercase ? 'uppercase' : 'none'),
        ].join(';');
        if (f.uppercase) {
          input.addEventListener('input', function () {
            var pos = input.selectionStart;
            input.value = input.value.toUpperCase();
            try { input.setSelectionRange(pos, pos); } catch (e) { /* date/number inputs */ }
          });
        }
      }
      box.appendChild(input);
      layer.appendChild(box);
    });
  }

  // renderScale = pdf.js scale the page is drawn at (1 = 1 CSS px per PDF point).
  function scale(layer, renderScale) {
    var stageHeight = layer.parentNode.offsetHeight;
    layer.querySelectorAll('.fill-online-input').forEach(function (el) {
      var boxPx = parseFloat(el.dataset.boxHeight) * stageHeight;
      var size = parseInt(el.dataset.fontSize, 10);
      // Same as the downloaded PDF: chosen size, or "auto" = fit the box (max 14pt).
      var fontPx = size ? size * renderScale : Math.min(14 * renderScale, boxPx * 0.72);
      fontPx = Math.max(1, fontPx);
      el.style.fontSize = fontPx.toFixed(2) + 'px';
      el.style.lineHeight = '1.15';
      el.style.height = Math.min(boxPx, fontPx * 1.3).toFixed(2) + 'px';
      el.style.padding = '0 ' + Math.max(0, 2 * renderScale / 1.4).toFixed(2) + 'px';
    });
  }

  return { build: build, scale: scale };
})();
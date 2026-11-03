// calcula el envio en vivo segun pais/estado/entrega
(function () {
  var f = document.getElementById('co');
  if (!f) return;
  var info = document.getElementById('zone-info');
  var shipBox = f.querySelector('.ship-f');
  var go = document.getElementById('go');

  function deliv() { return f.querySelector('input[name=delivery]:checked').value; }

  function upd() {
    var d = deliv();
    shipBox.style.display = d === 'recoger' ? 'none' : '';
    var p = new URLSearchParams({ delivery: d, country: f.country.value, state: f.state.value });
    fetch('/api/envio?' + p).then(function (r) { return r.json(); }).then(function (r) {
      if (!r.ok) { info.textContent = r.msg; go.disabled = true; return; }
      go.disabled = false;
      document.getElementById('ship-v').textContent = r.ship_txt;
      document.getElementById('total-v').textContent = r.total_txt;
      info.textContent = r.zone || '';
    });
  }

  f.querySelectorAll('input[name=delivery]').forEach(function (i) { i.onchange = upd; });
  ['country', 'state'].forEach(function (n) { f[n].addEventListener('change', upd); f[n].addEventListener('input', upd); });
  upd();
})();

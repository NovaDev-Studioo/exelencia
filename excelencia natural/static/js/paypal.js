// botones de paypal: el servidor crea y captura la orden, aqui solo los conectamos
(function () {
  var box = document.getElementById('paypal-btn');
  if (!box || !window.paypal) return;
  var code = box.dataset.code;
  var csrf = document.body.dataset.csrf;
  var err = document.getElementById('pp-err');
  var h = { 'X-CSRF': csrf, 'Content-Type': 'application/json' };

  paypal.Buttons({
    style: { shape: 'pill', color: 'gold', label: 'pay' },
    createOrder: function () {
      return fetch('/paypal/crear/' + code, { method: 'POST', headers: h })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (d.error) throw new Error(d.error); return d.id; });
    },
    onApprove: function (data) {
      return fetch('/paypal/capturar/' + code, { method: 'POST', headers: h, body: JSON.stringify({ id: data.orderID }) })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.error) { err.textContent = d.error; return; }
          location = d.url;
        });
    },
    onError: function () { err.textContent = 'Ocurrió un error con PayPal. Intenta de nuevo.'; }
  }).render('#paypal-btn');
})();

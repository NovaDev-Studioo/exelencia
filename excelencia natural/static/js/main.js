// js general de la tienda y del admin
(function () {
  var csrf = document.body.dataset.csrf;
  var logged = document.body.dataset.login === '1';

  function toast(msg, cls) {
    var box = document.getElementById('toasts');
    if (!box) return;
    var d = document.createElement('div');
    d.className = 'toast ' + (cls || '');
    d.textContent = msg;
    box.appendChild(d);
    setTimeout(function () { d.classList.add('out'); setTimeout(function () { d.remove(); }, 450); }, 3200);
  }

  function post(url, data) {
    var fd = new FormData();
    for (var k in (data || {})) fd.append(k, data[k]);
    return fetch(url, { method: 'POST', body: fd, headers: { 'X-CSRF': csrf, 'X-Requested-With': 'fetch' } })
      .then(function (r) { return r.json(); });
  }

  // los mensajes flash que ya vienen del servidor se quitan solos
  document.querySelectorAll('.toasts .toast').forEach(function (t) {
    setTimeout(function () { t.classList.add('out'); }, 4200);
  });

  // menu movil
  var bg = document.getElementById('burger');
  if (bg) bg.onclick = function () { document.getElementById('nav').classList.toggle('open'); };

  // agregar al carrito sin recargar
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-add]');
    if (!b) return;
    e.preventDefault();
    var qEl = b.dataset.qtyFrom ? document.querySelector(b.dataset.qtyFrom) : null;
    post('/carrito/agregar/' + b.dataset.add, { qty: qEl ? qEl.value : 1 }).then(function (r) {
      var n = document.getElementById('cart-n');
      if (n) { n.textContent = r.count; n.classList.remove('zero'); n.classList.remove('bump'); void n.offsetWidth; n.classList.add('bump'); }
      toast(r.msg);
    }).catch(function () { toast('Error', 'warn'); });
  });

  // favoritos
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-fav]');
    if (!b) return;
    e.preventDefault();
    if (!logged) { location = document.body.dataset.loginUrl; return; }
    post('/favoritos/' + b.dataset.fav).then(function (r) { b.classList.toggle('on', r.on); });
  });

  // likes de publicaciones
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-like]');
    if (!b) return;
    if (!logged) { location = document.body.dataset.loginUrl; return; }
    post('/publicaciones/' + b.dataset.like + '/like').then(function (r) {
      b.classList.toggle('on', r.on);
      b.querySelector('span').textContent = r.n;
    });
  });

  // +/- de cantidad en la pagina de producto
  document.querySelectorAll('[data-q]').forEach(function (b) {
    b.onclick = function () {
      var i = document.getElementById('q');
      var v = (parseInt(i.value, 10) || 1) + parseInt(b.dataset.q, 10);
      i.value = Math.max(1, Math.min(v, parseInt(i.max, 10) || 99));
    };
  });

  // galeria
  var big = document.getElementById('g-main');
  document.querySelectorAll('.g-thumbs img').forEach(function (t) {
    t.onclick = function () {
      big.src = t.dataset.big;
      document.querySelectorAll('.g-thumbs img').forEach(function (x) { x.classList.remove('on'); });
      t.classList.add('on');
    };
  });

  // boton de subir
  var up = document.getElementById('to-top');
  if (up) {
    window.addEventListener('scroll', function () { up.classList.toggle('show', window.scrollY > 500); });
    up.onclick = function () { window.scrollTo({ top: 0, behavior: 'smooth' }); };
  }

  // animacion al hacer scroll
  var els = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.1 });
    els.forEach(function (el, i) { el.style.transitionDelay = (i % 4) * 70 + 'ms'; io.observe(el); });
  } else {
    els.forEach(function (el) { el.classList.add('in'); });
  }
})();

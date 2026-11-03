import os
import re
import uuid
import secrets
import smtplib
from functools import wraps
from email.message import EmailMessage

import requests
from flask import session, request, redirect, url_for, flash, abort, g

import config
from db import q, one, ex, settings
from i18n import T


# ---------- sesion / permisos ----------
def me():
    if 'me' not in g:
        uid = session.get('uid')
        g.me = one('SELECT * FROM users WHERE id = ?', (uid,)) if uid else None
    return g.me


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not me() or me()['role'] != 'cliente':
            flash('Inicia sesión para continuar.', 'warn')
            return redirect(url_for('auth.login', next=request.full_path))
        return f(*a, **k)
    return w


def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        u = me()
        if not u or u['role'] != 'admin':
            return redirect(url_for('auth.admin_login', next=request.path))
        return f(*a, **k)
    return w


# ---------- csrf ----------
def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_hex(16)
    return session['_csrf']


def check_csrf():
    tok = request.form.get('_csrf') or request.headers.get('X-CSRF')
    if not tok or tok != session.get('_csrf'):
        abort(400, 'Token inválido, recarga la página.')


# ---------- idioma / moneda ----------
def lang():
    return 'es'


def cur():
    return session.get('cur', 'MXN')


def tr(key, **kw):
    s = T.get(lang(), T['es']).get(key) or T['es'].get(key, key)
    return s.format(**kw) if kw else s


def rate():
    try:
        return float(settings().get('usd_rate') or 18)
    except ValueError:
        return 18.0


def to_cur(mxn, c=None):
    c = c or cur()
    return round(mxn / rate(), 2) if c == 'USD' else round(mxn, 2)


def money(n, c=None):
    c = c or cur()
    return ('US$ ' if c == 'USD' else '$ ') + f'{n:,.2f}' + (' USD' if c == 'USD' else ' MXN')


def pname(p):
    return (p['name_en'] if lang() == 'en' and p['name_en'] else p['name'])


def pdesc(p):
    return (p['descr_en'] if lang() == 'en' and p['descr_en'] else p['descr'])


# ---------- precios ----------
def unit_price(p, c=None):
    c = c or cur()
    if c == 'USD':
        return p['price_usd'] if p['price_usd'] else round(p['price_mxn'] / rate(), 2)
    return p['price_mxn']


def ws_price(p, c=None):
    # precio de mayoreo, o None si el producto no tiene
    c = c or cur()
    if not p['ws_min'] or p['ws_min'] < 2:
        return None
    if c == 'USD':
        v = p['ws_usd'] if p['ws_usd'] else round(p['ws_mxn'] / rate(), 2)
        return v or None
    return p['ws_mxn'] or None


def img_of(pid):
    r = one('SELECT file FROM product_images WHERE product_id = ? ORDER BY pos, id LIMIT 1', (pid,))
    return r['file'] if r else None


def _cats():
    if '_cats' not in g:
        g._cats = {c['id']: c for c in q('SELECT * FROM categories')}
    return g._cats


def cat_icon(cid):
    c = _cats().get(cid)
    return c['icon'] if c else 'leaf'


def cat_name(cid):
    c = _cats().get(cid)
    if not c:
        return ''
    return c['name_en'] if lang() == 'en' and c['name_en'] else c['name']


# ---------- carrito ----------
def cart_lines(c=None):
    c = c or cur()
    res = []
    cart = session.get('cart', {})
    for pid, n in list(cart.items()):
        p = one('SELECT * FROM products WHERE id = ? AND active = 1', (pid,))
        if not p:
            cart.pop(pid, None)
            continue
        n = max(1, min(int(n), max(p['stock'], 0))) if p['stock'] > 0 else 0
        if n == 0:
            cart.pop(pid, None)
            continue
        cart[pid] = n
        up = unit_price(p, c)
        w = ws_price(p, c)
        is_ws = bool(w and n >= p['ws_min'])
        if is_ws:
            up = w
        res.append({'p': p, 'qty': n, 'unit': up, 'ws': is_ws, 'sum': round(up * n, 2), 'img': img_of(p['id'])})
    session['cart'] = cart
    return res


def cart_count():
    return sum(int(v) for v in session.get('cart', {}).values())


# ---------- cupones ----------
def check_coupon(code, sub_mxn):
    # regresa (cupon, error)
    from datetime import date
    cp = one('SELECT * FROM coupons WHERE code = ? COLLATE NOCASE AND active = 1', (code.strip(),))
    if not cp:
        return None, 'Código no válido.'
    if cp['expires'] and cp['expires'] < date.today().isoformat():
        return None, 'Este código ya venció.'
    if cp['max_uses'] and cp['used'] >= cp['max_uses']:
        return None, 'Este código ya se agotó.'
    if sub_mxn < (cp['min_total'] or 0):
        return None, f"Compra mínima de $ {cp['min_total']:,.0f} MXN para usar este código."
    if cp['kind'] == 'free_product':
        p = one('SELECT * FROM products WHERE id = ? AND active = 1 AND stock > 0', (cp['product_id'],))
        if not p:
            return None, 'El producto de regalo ya no está disponible.'
    return cp, None


def totals(lines, c=None):
    # calcula subtotal, descuento y producto regalo segun el cupon en sesion
    c = c or cur()
    sub = round(sum(l['sum'] for l in lines), 2)
    disc, gift, cp = 0.0, None, None
    code = session.get('coupon')
    if code and lines:
        sub_mxn = sub * rate() if c == 'USD' else sub
        cp, err = check_coupon(code, sub_mxn)
        if err:
            session.pop('coupon', None)
            cp = None
        elif cp['kind'] == 'percent':
            disc = round(sub * cp['value'] / 100, 2)
        elif cp['kind'] == 'fixed':
            disc = min(sub, to_cur(cp['value'], c))
        elif cp['kind'] == 'free_product':
            gift = one('SELECT * FROM products WHERE id = ?', (cp['product_id'],))
    return {'sub': sub, 'disc': disc, 'gift': gift, 'cp': cp}


# ---------- envios ----------
def find_zone(country, state):
    zs = q('SELECT * FROM zones WHERE active = 1')
    country = (country or '').strip().lower()
    is_mx = country in ('méxico', 'mexico', 'mx', '')
    state = (state or '').strip().lower()
    if not is_mx:
        for z in zs:
            if z['country'] == 'EX':
                return z
        return None
    dflt = None
    for z in zs:
        if z['country'] != 'MX':
            continue
        st = [s.strip().lower() for s in (z['states'] or '').split(',') if s.strip()]
        if not st:
            dflt = z
        elif state in st:
            return z
    return dflt


def ship_cost(zone, sub, c=None):
    # sub viene en la moneda actual; el umbral de envio gratis esta en MXN
    c = c or cur()
    if not zone:
        return 0.0
    sub_mxn = sub * rate() if c == 'USD' else sub
    if zone['free_from'] and sub_mxn >= zone['free_from']:
        return 0.0
    if c == 'USD':
        return zone['price_usd'] if zone['price_usd'] else round(zone['price_mxn'] / rate(), 2)
    return zone['price_mxn']


# ---------- archivos ----------
def save_img(f):
    if not f or not f.filename:
        return None
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in config.ALLOWED_IMG:
        return None
    name = uuid.uuid4().hex[:14] + '.' + ext
    f.save(os.path.join(config.UPLOADS, name))
    return name


def del_img(name):
    try:
        os.remove(os.path.join(config.UPLOADS, name))
    except OSError:
        pass


# ---------- notificaciones ----------
STATUS_TXT = {
    'pendiente': 'está pendiente de pago',
    'pagado': 'fue pagado. ¡Gracias!',
    'preparando': 'se está preparando',
    'enviado': 'ya fue enviado',
    'entregado': 'fue entregado',
    'cancelado': 'fue cancelado',
}


def wa_num(tel):
    d = re.sub(r'\D', '', tel or '')
    if len(d) == 10:
        d = '52' + d
    return d


def wa_link(tel, text):
    from urllib.parse import quote
    return f'https://wa.me/{wa_num(tel)}?text={quote(text)}'


def send_wa(tel, text):
    # whatsapp cloud api, solo si hay token
    if not (config.WA_TOKEN and config.WA_PHONE_ID):
        return False
    try:
        r = requests.post(
            f'https://graph.facebook.com/v19.0/{config.WA_PHONE_ID}/messages',
            headers={'Authorization': 'Bearer ' + config.WA_TOKEN},
            json={'messaging_product': 'whatsapp', 'to': wa_num(tel), 'type': 'text', 'text': {'body': text}},
            timeout=10)
        return r.ok
    except requests.RequestException:
        return False


def send_mail(to, subj, body):
    s = config.SMTP
    if not (s['host'] and to):
        return False
    try:
        m = EmailMessage()
        m['From'], m['To'], m['Subject'] = s['user'], to, subj
        m.set_content(body)
        with smtplib.SMTP(s['host'], s['port'], timeout=10) as srv:
            srv.starttls()
            if s['user']:
                srv.login(s['user'], s['pass'])
            srv.send_message(m)
        return True
    except Exception:
        return False


def notify(o, event=None):
    # guarda el aviso en la bd y trata de mandarlo por whatsapp / correo
    st = settings()
    event = event or o['status']
    txt = f"Excelencia Natural: tu pedido {o['code']} {STATUS_TXT.get(event, event)}."
    if event == 'enviado' and o['tracking']:
        txt += f" Guía {o['carrier']}: {o['tracking']}."
    ok = send_wa(o['phone'], txt)
    ex('INSERT INTO notifications(order_id, target, kind, text, sent) VALUES(?,?,?,?,?)',
       (o['id'], o['phone'], 'cliente', txt, int(ok)))
    send_mail(o['email'], f"Pedido {o['code']}", txt)
    if event in ('pagado', 'pendiente'):
        # aviso al personal de pedido nuevo
        adm = f"Nuevo pedido {o['code']} de {o['name']} por {money(o['total'], o['currency'])} ({event})."
        ok2 = send_wa(st['admin_wa'], adm)
        ex('INSERT INTO notifications(order_id, target, kind, text, sent) VALUES(?,?,?,?,?)',
           (o['id'], st['admin_wa'], 'admin', adm, int(ok2)))
        send_mail(st['email'], f"Nuevo pedido {o['code']}", adm)

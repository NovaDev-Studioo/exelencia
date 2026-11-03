import random
import string
from flask import (Blueprint, render_template, request, session, redirect, url_for,
                   flash, jsonify, abort)

from db import q, one, ex, get_db
from i18n import FAQ
import utils as u

bp = Blueprint('shop', __name__)

ESTADOS = ['Aguascalientes', 'Baja California', 'Baja California Sur', 'Campeche', 'Chiapas', 'Chihuahua',
           'Ciudad de México', 'Coahuila', 'Colima', 'Durango', 'Estado de México', 'Guanajuato', 'Guerrero',
           'Hidalgo', 'Jalisco', 'Michoacán', 'Morelos', 'Nayarit', 'Nuevo León', 'Oaxaca', 'Puebla', 'Querétaro',
           'Quintana Roo', 'San Luis Potosí', 'Sinaloa', 'Sonora', 'Tabasco', 'Tamaulipas', 'Tlaxcala', 'Veracruz',
           'Yucatán', 'Zacatecas']


def back(default='shop.index'):
    return redirect(request.referrer or url_for(default))


def is_ajax():
    return request.headers.get('X-Requested-With') == 'fetch'


# ---------- idioma / moneda ----------
@bp.route('/moneda/<c>')
def set_cur(c):
    if c in ('MXN', 'USD'):
        session['cur'] = c
    return back()


# ---------- inicio y catalogo ----------
@bp.route('/')
def index():
    feat = q('SELECT * FROM products WHERE active = 1 AND featured = 1 ORDER BY id DESC LIMIT 8')
    posts = q('SELECT * FROM posts ORDER BY id DESC LIMIT 3')
    cats = q('''SELECT c.*, (SELECT COUNT(*) FROM products p WHERE p.cat_id = c.id AND p.active = 1) AS n
                FROM categories c ORDER BY c.name''')
    revs = q('''SELECT r.*, u.name AS uname, p.name AS pname, p.id AS pid FROM reviews r
                JOIN users u ON u.id = r.user_id JOIN products p ON p.id = r.product_id
                WHERE r.visible = 1 AND r.stars >= 4 AND r.body != '' ORDER BY r.id DESC LIMIT 3''')
    return render_template('index.html', feat=feat, posts=posts, cats=cats, revs=revs)


@bp.route('/catalogo')
def catalog():
    s = request.args.get('q', '').strip()
    cat = request.args.get('cat', type=int)
    pmin = request.args.get('min', type=float)
    pmax = request.args.get('max', type=float)
    sort = request.args.get('sort', 'new')
    ws = request.args.get('ws') == '1'
    sql, args = 'SELECT * FROM products WHERE active = 1', []
    if s:
        sql += ' AND (name LIKE ? OR name_en LIKE ? OR descr LIKE ?)'
        args += [f'%{s}%'] * 3
    if cat:
        sql += ' AND cat_id = ?'
        args.append(cat)
    # los filtros de precio vienen en la moneda activa, los pasamos a mxn
    if pmin is not None:
        sql += ' AND price_mxn >= ?'
        args.append(pmin * u.rate() if u.cur() == 'USD' else pmin)
    if pmax is not None:
        sql += ' AND price_mxn <= ?'
        args.append(pmax * u.rate() if u.cur() == 'USD' else pmax)
    if ws:
        sql += ' AND ws_min > 1 AND ws_mxn > 0'
    sql += {'low': ' ORDER BY price_mxn ASC', 'high': ' ORDER BY price_mxn DESC'}.get(sort, ' ORDER BY id DESC')
    prods = q(sql, args)
    cats = q('SELECT * FROM categories ORDER BY name')
    return render_template('catalog.html', prods=prods, cats=cats, f=dict(q=s, cat=cat, min=pmin, max=pmax, sort=sort, ws=ws))


@bp.route('/producto/<int:pid>')
def product(pid):
    p = one('SELECT * FROM products WHERE id = ? AND active = 1', (pid,))
    if not p:
        abort(404)
    imgs = q('SELECT * FROM product_images WHERE product_id = ? ORDER BY pos, id', (pid,))
    revs = q('''SELECT r.*, u.name FROM reviews r JOIN users u ON u.id = r.user_id
                WHERE r.product_id = ? AND r.visible = 1 ORDER BY r.id DESC''', (pid,))
    avg = round(sum(r['stars'] for r in revs) / len(revs), 1) if revs else 0
    cat = one('SELECT * FROM categories WHERE id = ?', (p['cat_id'],)) if p['cat_id'] else None
    fav = False
    mine = None
    if u.me():
        fav = bool(one('SELECT 1 FROM wishlist WHERE user_id = ? AND product_id = ?', (u.me()['id'], pid)))
        mine = one('SELECT * FROM reviews WHERE user_id = ? AND product_id = ?', (u.me()['id'], pid))
    rel = q('SELECT * FROM products WHERE active = 1 AND cat_id = ? AND id != ? LIMIT 4', (p['cat_id'], pid))
    return render_template('product.html', p=p, imgs=imgs, revs=revs, avg=avg, cat=cat, fav=fav, mine=mine, rel=rel)


# ---------- favoritos y resenas ----------
@bp.route('/favoritos')
@u.login_required
def wishlist():
    prods = q('''SELECT p.* FROM products p JOIN wishlist w ON w.product_id = p.id
                 WHERE w.user_id = ? AND p.active = 1''', (u.me()['id'],))
    return render_template('wishlist.html', prods=prods)


@bp.route('/favoritos/<int:pid>', methods=['POST'])
@u.login_required
def fav(pid):
    uid = u.me()['id']
    if one('SELECT 1 FROM wishlist WHERE user_id = ? AND product_id = ?', (uid, pid)):
        ex('DELETE FROM wishlist WHERE user_id = ? AND product_id = ?', (uid, pid))
        on = False
    else:
        ex('INSERT INTO wishlist VALUES(?, ?)', (uid, pid))
        on = True
    if is_ajax():
        return jsonify(on=on)
    return back()


@bp.route('/resena/<int:pid>', methods=['POST'])
@u.login_required
def review(pid):
    st = request.form.get('stars', type=int) or 0
    if not 1 <= st <= 5:
        flash('Elige de 1 a 5 estrellas.', 'warn')
        return back()
    ex('''INSERT INTO reviews(product_id, user_id, stars, body) VALUES(?,?,?,?)
          ON CONFLICT(product_id, user_id) DO UPDATE SET stars = excluded.stars, body = excluded.body, visible = 1''',
       (pid, u.me()['id'], st, request.form.get('body', '').strip()[:800]))
    flash('¡Gracias por tu reseña!', 'ok')
    return redirect(url_for('shop.product', pid=pid) + '#reseñas')


# ---------- carrito ----------
@bp.route('/carrito')
def cart():
    lines = u.cart_lines()
    tot = u.totals(lines)
    # barra de envio gratis: usamos el umbral mas bajo de las zonas activas
    goal = one('SELECT MIN(free_from) m FROM zones WHERE active = 1 AND free_from > 0')['m']
    free = None
    if goal and lines:
        g = u.to_cur(goal)
        cur_sub = tot['sub'] - tot['disc']
        free = dict(goal=g, left=max(g - cur_sub, 0), pct=min(100, int(cur_sub * 100 / g)))
    return render_template('cart.html', lines=lines, tot=tot, free=free)


@bp.route('/carrito/agregar/<int:pid>', methods=['POST'])
def cart_add(pid):
    p = one('SELECT * FROM products WHERE id = ? AND active = 1', (pid,))
    if not p or p['stock'] < 1:
        flash('Producto agotado.', 'warn')
        return back()
    n = request.form.get('qty', 1, type=int) or 1
    c = session.get('cart', {})
    c[str(pid)] = min(int(c.get(str(pid), 0)) + max(n, 1), p['stock'])
    session['cart'] = c
    if is_ajax():
        return jsonify(count=u.cart_count(), msg=u.tr('added'))
    flash(u.tr('added'), 'ok')
    return back()


@bp.route('/carrito/cantidad/<int:pid>', methods=['POST'])
def cart_qty(pid):
    n = request.form.get('qty', 1, type=int)
    c = session.get('cart', {})
    if n is None or n < 1:
        c.pop(str(pid), None)
    else:
        c[str(pid)] = n
    session['cart'] = c
    return redirect(url_for('shop.cart'))


@bp.route('/carrito/quitar/<int:pid>', methods=['POST'])
def cart_del(pid):
    c = session.get('cart', {})
    c.pop(str(pid), None)
    session['cart'] = c
    return redirect(url_for('shop.cart'))


@bp.route('/carrito/cupon', methods=['POST'])
def cart_coupon():
    code = request.form.get('code', '').strip()
    lines = u.cart_lines()
    sub = sum(l['sum'] for l in lines)
    sub_mxn = sub * u.rate() if u.cur() == 'USD' else sub
    cp, err = u.check_coupon(code, sub_mxn)
    if err:
        flash(err, 'warn')
    else:
        session['coupon'] = cp['code']
        flash('Código aplicado', 'ok')
    return redirect(url_for('shop.cart'))


@bp.route('/carrito/cupon/quitar', methods=['POST'])
def cart_coupon_del():
    session.pop('coupon', None)
    return redirect(url_for('shop.cart'))


# ---------- checkout ----------
def calc_ship(delivery, country, state, base):
    if delivery == 'recoger':
        return None, 0.0
    z = u.find_zone(country, state)
    return z, u.ship_cost(z, base)


@bp.route('/api/envio')
def api_ship():
    lines = u.cart_lines()
    t = u.totals(lines)
    z, cost = calc_ship(request.args.get('delivery', 'envio'), request.args.get('country'),
                        request.args.get('state'), t['sub'] - t['disc'])
    deliv = request.args.get('delivery', 'envio')
    if deliv == 'envio' and not z:
        return jsonify(ok=False, msg='Por ahora no enviamos a ese destino.')
    total = round(t['sub'] - t['disc'] + cost, 2)
    return jsonify(ok=True, ship=cost, ship_txt=u.money(cost) if cost else u.tr('free'),
                   total=total, total_txt=u.money(total),
                   zone=(z['name'] + ' · ' + z['carrier'] + ' · ' + z['days']) if z else '')


def new_code():
    while True:
        c = 'XM-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not one('SELECT 1 FROM orders WHERE code = ?', (c,)):
            return c


@bp.route('/checkout', methods=['GET', 'POST'])
@u.login_required
def checkout():
    lines = u.cart_lines()
    if not lines:
        return redirect(url_for('shop.cart'))
    t = u.totals(lines)
    me = u.me()
    if request.method == 'POST':
        f = request.form
        deliv = f.get('delivery', 'envio')
        d = {k: f.get(k, '').strip() for k in ('name', 'phone', 'email', 'addr', 'city', 'state', 'zip', 'country', 'notes')}
        d['country'] = d['country'] or 'México'
        miss = [k for k in ('name', 'phone', 'email') if not d[k]]
        if deliv == 'envio':
            miss += [k for k in ('addr', 'city', 'state', 'zip') if not d[k]]
        if miss or not f.get('terms'):
            flash('Completa todos los campos y acepta los términos.', 'warn')
            return render_template('checkout.html', lines=lines, tot=t, d=d, estados=ESTADOS, deliv=deliv)
        z, ship = calc_ship(deliv, d['country'], d['state'], t['sub'] - t['disc'])
        if deliv == 'envio' and not z:
            flash('Por ahora no enviamos a ese destino.', 'warn')
            return render_template('checkout.html', lines=lines, tot=t, d=d, estados=ESTADOS, deliv=deliv)
        total = round(t['sub'] - t['disc'] + ship, 2)
        code = new_code()
        oid = ex('''INSERT INTO orders(code, user_id, currency, subtotal, discount, shipping, total, coupon, delivery,
                    name, phone, email, addr, city, state, zip, country, zone, carrier, notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                 (code, me['id'], u.cur(), t['sub'], t['disc'], ship, total, (t['cp']['code'] if t['cp'] else ''), deliv,
                  d['name'], d['phone'], d['email'], d['addr'], d['city'], d['state'], d['zip'], d['country'],
                  (z['name'] if z else 'Recoger en tienda'), (z['carrier'] if z else ''), d['notes']))
        db = get_db()
        for l in lines:
            db.execute('INSERT INTO order_items(order_id, product_id, name, qty, price, ws) VALUES(?,?,?,?,?,?)',
                       (oid, l['p']['id'], l['p']['name'], l['qty'], l['unit'], int(l['ws'])))
            db.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (l['qty'], l['p']['id']))
        if t['gift']:
            g = t['gift']
            db.execute('INSERT INTO order_items(order_id, product_id, name, qty, price, free) VALUES(?,?,?,?,0,1)',
                       (oid, g['id'], g['name'] + ' (regalo)', 1, ))
            db.execute('UPDATE products SET stock = stock - 1 WHERE id = ?', (g['id'],))
        if t['cp']:
            db.execute('UPDATE coupons SET used = used + 1 WHERE id = ?', (t['cp']['id'],))
        db.commit()
        session['cart'] = {}
        session.pop('coupon', None)
        u.notify(one('SELECT * FROM orders WHERE id = ?', (oid,)), 'pendiente')
        return redirect(url_for('pay.pay_page', code=code))
    d = dict(name=me['name'], phone=me['phone'], email=me['email'], addr='', city='', state='Puebla', zip='', country='México', notes='')
    return render_template('checkout.html', lines=lines, tot=t, d=d, estados=ESTADOS, deliv='envio')


# ---------- cuenta y pedidos ----------
@bp.route('/mi-cuenta', methods=['GET', 'POST'])
@u.login_required
def account():
    me = u.me()
    if request.method == 'POST':
        ex('UPDATE users SET name = ?, phone = ? WHERE id = ?',
           (request.form.get('name', me['name']).strip() or me['name'], request.form.get('phone', '').strip(), me['id']))
        flash('Datos guardados.', 'ok')
        return redirect(url_for('shop.account'))
    orders = q('SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC', (me['id'],))
    return render_template('account.html', orders=orders)


@bp.route('/pedido/<code>')
@u.login_required
def order(code):
    o = one('SELECT * FROM orders WHERE code = ? AND user_id = ?', (code, u.me()['id']))
    if not o:
        abort(404)
    items = q('SELECT * FROM order_items WHERE order_id = ?', (o['id'],))
    return render_template('order.html', o=o, items=items)


# ---------- publicaciones (solo las crea el personal) ----------
@bp.route('/publicaciones')
def blog():
    posts = q('''SELECT p.*, (SELECT COUNT(*) FROM post_likes l WHERE l.post_id = p.id) AS likes
                 FROM posts p ORDER BY p.id DESC''')
    mine = set()
    if u.me():
        mine = {r['post_id'] for r in q('SELECT post_id FROM post_likes WHERE user_id = ?', (u.me()['id'],))}
    return render_template('blog.html', posts=posts, mine=mine)


@bp.route('/publicaciones/<int:pid>/like', methods=['POST'])
@u.login_required
def like(pid):
    uid = u.me()['id']
    if one('SELECT 1 FROM post_likes WHERE post_id = ? AND user_id = ?', (pid, uid)):
        ex('DELETE FROM post_likes WHERE post_id = ? AND user_id = ?', (pid, uid))
        on = False
    else:
        ex('INSERT INTO post_likes VALUES(?, ?)', (pid, uid))
        on = True
    n = one('SELECT COUNT(*) c FROM post_likes WHERE post_id = ?', (pid,))['c']
    if is_ajax():
        return jsonify(on=on, n=n)
    return back('shop.blog')


# ---------- paginas fijas ----------
@bp.route('/nosotros')
def about():
    return render_template('about.html')


@bp.route('/contacto', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        f = request.form
        if f.get('name') and f.get('email') and f.get('body'):
            ex('INSERT INTO messages(name, email, body) VALUES(?,?,?)',
               (f['name'].strip()[:100], f['email'].strip()[:120], f['body'].strip()[:2000]))
            flash(u.tr('sent_ok'), 'ok')
            return redirect(url_for('shop.contact'))
        flash('Completa todos los campos.', 'warn')
    return render_template('contact.html')


@bp.route('/preguntas-frecuentes')
def faq():
    return render_template('faq.html', items=FAQ[u.lang()])


@bp.route('/terminos')
def terms():
    return render_template('legal/terms.html')


@bp.route('/privacidad')
def privacy():
    return render_template('legal/privacy.html')


@bp.route('/devoluciones')
def returns():
    return render_template('legal/returns.html')

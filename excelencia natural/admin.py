from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

from db import q, one, ex, get_db, set_setting, DEFAULTS
import utils as u

bp = Blueprint('admin', __name__, url_prefix='/admin')

STATUSES = ['pendiente', 'pagado', 'preparando', 'enviado', 'entregado', 'cancelado']


@bp.before_request
def only_staff():
    # todo lo de /admin pide cuenta de personal, menos el login (que vive en auth)
    me = u.me()
    if not me or me['role'] != 'admin':
        return redirect(url_for('auth.admin_login', next=request.path))


def num(k, d=0.0, f=None):
    f = f or request.form
    try:
        return float(f.get(k, d) or d)
    except ValueError:
        return d


# ---------- panel ----------
@bp.route('/')
def dashboard():
    st = {}
    st['ventas'] = one("SELECT COALESCE(SUM(total),0) s FROM orders WHERE pay_status='pagado' AND currency='MXN'")['s']
    st['ventas_usd'] = one("SELECT COALESCE(SUM(total),0) s FROM orders WHERE pay_status='pagado' AND currency='USD'")['s']
    st['nuevos'] = one("SELECT COUNT(*) c FROM orders WHERE status='pagado'")['c']
    st['pend'] = one("SELECT COUNT(*) c FROM orders WHERE status='pendiente'")['c']
    st['msgs'] = one('SELECT COUNT(*) c FROM messages WHERE seen = 0')['c']
    st['prods'] = one('SELECT COUNT(*) c FROM products WHERE active = 1')['c']
    low = q('SELECT * FROM products WHERE active = 1 AND stock <= 5 ORDER BY stock LIMIT 8')
    last = q('SELECT * FROM orders ORDER BY id DESC LIMIT 6')
    return render_template('admin/dashboard.html', st=st, low=low, last=last)


# ---------- productos ----------
@bp.route('/productos')
def products():
    s = request.args.get('q', '').strip()
    rows = q('''SELECT p.*, c.name AS cat FROM products p LEFT JOIN categories c ON c.id = p.cat_id
                WHERE p.name LIKE ? ORDER BY p.id DESC''', (f'%{s}%',))
    return render_template('admin/products.html', rows=rows, s=s)


@bp.route('/productos/nuevo', methods=['GET', 'POST'])
@bp.route('/productos/<int:pid>', methods=['GET', 'POST'])
def product_form(pid=None):
    p = one('SELECT * FROM products WHERE id = ?', (pid,)) if pid else None
    if pid and not p:
        abort(404)
    if request.method == 'POST':
        f = request.form
        if not f.get('name', '').strip():
            flash('Ponle nombre al producto.', 'warn')
        else:
            vals = (f['name'].strip(), f.get('name_en', '').strip(), f.get('descr', '').strip(), f.get('descr_en', '').strip(),
                    f.get('cat_id', type=int) or None, num('price_mxn'), num('price_usd'), num('ws_mxn'), num('ws_usd'),
                    int(num('ws_min')), int(num('stock')), int(bool(f.get('featured'))), int(bool(f.get('active'))))
            if p:
                ex('''UPDATE products SET name=?, name_en=?, descr=?, descr_en=?, cat_id=?, price_mxn=?, price_usd=?,
                      ws_mxn=?, ws_usd=?, ws_min=?, stock=?, featured=?, active=? WHERE id=?''', vals + (pid,))
            else:
                pid = ex('''INSERT INTO products(name, name_en, descr, descr_en, cat_id, price_mxn, price_usd,
                            ws_mxn, ws_usd, ws_min, stock, featured, active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''', vals)
            pos = one('SELECT COALESCE(MAX(pos),0) m FROM product_images WHERE product_id = ?', (pid,))['m']
            for fl in request.files.getlist('imgs'):
                name = u.save_img(fl)
                if name:
                    pos += 1
                    ex('INSERT INTO product_images(product_id, file, pos) VALUES(?,?,?)', (pid, name, pos))
            flash('Producto guardado', 'ok')
            return redirect(url_for('admin.product_form', pid=pid))
    imgs = q('SELECT * FROM product_images WHERE product_id = ? ORDER BY pos, id', (pid,)) if pid else []
    cats = q('SELECT * FROM categories ORDER BY name')
    return render_template('admin/product_form.html', p=p, imgs=imgs, cats=cats)


@bp.route('/productos/<int:pid>/img/<int:iid>/borrar', methods=['POST'])
def img_del(pid, iid):
    r = one('SELECT * FROM product_images WHERE id = ? AND product_id = ?', (iid, pid))
    if r:
        u.del_img(r['file'])
        ex('DELETE FROM product_images WHERE id = ?', (iid,))
    return redirect(url_for('admin.product_form', pid=pid))


@bp.route('/productos/<int:pid>/borrar', methods=['POST'])
def product_del(pid):
    for r in q('SELECT file FROM product_images WHERE product_id = ?', (pid,)):
        u.del_img(r['file'])
    ex('DELETE FROM products WHERE id = ?', (pid,))
    flash('Producto eliminado.', 'ok')
    return redirect(url_for('admin.products'))


@bp.route('/productos/<int:pid>/activo', methods=['POST'])
def product_toggle(pid):
    ex('UPDATE products SET active = 1 - active WHERE id = ?', (pid,))
    return redirect(request.referrer or url_for('admin.products'))


# ---------- categorias ----------
@bp.route('/categorias', methods=['GET', 'POST'])
def categories():
    if request.method == 'POST':
        f = request.form
        if f.get('name', '').strip():
            ex('INSERT INTO categories(name, name_en, icon) VALUES(?,?,?)',
               (f['name'].strip(), f.get('name_en', '').strip(), f.get('icon', 'leaf').strip() or 'leaf'))
            flash('Categoría creada.', 'ok')
        return redirect(url_for('admin.categories'))
    rows = q('SELECT c.*, (SELECT COUNT(*) FROM products p WHERE p.cat_id = c.id) n FROM categories c ORDER BY name')
    return render_template('admin/categories.html', rows=rows)


@bp.route('/categorias/<int:cid>/borrar', methods=['POST'])
def category_del(cid):
    ex('DELETE FROM categories WHERE id = ?', (cid,))
    return redirect(url_for('admin.categories'))


# ---------- pedidos ----------
@bp.route('/pedidos')
def orders():
    st = request.args.get('st', '')
    rows = q('SELECT * FROM orders WHERE (? = "" OR status = ?) ORDER BY id DESC', (st, st))
    return render_template('admin/orders.html', rows=rows, st=st, statuses=STATUSES)


@bp.route('/pedidos/<int:oid>', methods=['GET', 'POST'])
def order(oid):
    o = one('SELECT * FROM orders WHERE id = ?', (oid,))
    if not o:
        abort(404)
    if request.method == 'POST':
        f = request.form
        new = f.get('status', o['status'])
        if new not in STATUSES:
            abort(400)
        ex('UPDATE orders SET status = ?, tracking = ?, carrier = ? WHERE id = ?',
           (new, f.get('tracking', '').strip(), f.get('carrier', o['carrier']).strip(), oid))
        if new == 'cancelado' and o['status'] != 'cancelado':
            # regresamos el stock
            for it in q('SELECT * FROM order_items WHERE order_id = ?', (oid,)):
                ex('UPDATE products SET stock = stock + ? WHERE id = ?', (it['qty'], it['product_id']))
        if new == 'pagado' and o['pay_status'] != 'pagado':
            ex("UPDATE orders SET pay_status = 'pagado', pay_ref = 'MANUAL' WHERE id = ?", (oid,))
        o2 = one('SELECT * FROM orders WHERE id = ?', (oid,))
        if new != o['status'] or f.get('tracking') != o['tracking']:
            u.notify(o2, new)
        flash('Pedido actualizado y cliente avisado', 'ok')
        return redirect(url_for('admin.order', oid=oid))
    items = q('SELECT * FROM order_items WHERE order_id = ?', (oid,))
    notes = q('SELECT * FROM notifications WHERE order_id = ? AND kind = "cliente" ORDER BY id DESC', (oid,))
    wa = u.wa_link(o['phone'], f"Excelencia Natural: tu pedido {o['code']} {u.STATUS_TXT.get(o['status'], '')}." +
                   (f" Guía {o['carrier']}: {o['tracking']}." if o['tracking'] else ''))
    return render_template('admin/order.html', o=o, items=items, notes=notes, statuses=STATUSES, wa=wa)


# ---------- cupones ----------
@bp.route('/cupones', methods=['GET', 'POST'])
def coupons():
    if request.method == 'POST':
        f = request.form
        code = f.get('code', '').strip().upper()
        if not code:
            flash('Escribe el código.', 'warn')
        elif one('SELECT 1 FROM coupons WHERE code = ?', (code,)):
            flash('Ese código ya existe.', 'warn')
        else:
            ex('''INSERT INTO coupons(code, kind, value, product_id, min_total, max_uses, expires)
                  VALUES(?,?,?,?,?,?,?)''',
               (code, f.get('kind', 'percent'), num('value'), f.get('product_id', type=int) or None,
                num('min_total'), int(num('max_uses')), f.get('expires', '')))
            flash('Cupón creado.', 'ok')
        return redirect(url_for('admin.coupons'))
    rows = q('''SELECT c.*, p.name AS pname FROM coupons c LEFT JOIN products p ON p.id = c.product_id ORDER BY c.id DESC''')
    prods = q('SELECT id, name FROM products ORDER BY name')
    return render_template('admin/coupons.html', rows=rows, prods=prods)


@bp.route('/cupones/<int:cid>/<act>', methods=['POST'])
def coupon_act(cid, act):
    if act == 'borrar':
        ex('DELETE FROM coupons WHERE id = ?', (cid,))
    elif act == 'activo':
        ex('UPDATE coupons SET active = 1 - active WHERE id = ?', (cid,))
    return redirect(url_for('admin.coupons'))


# ---------- zonas de envio ----------
@bp.route('/envios', methods=['GET', 'POST'])
def zones():
    if request.method == 'POST':
        f = request.form
        zid = f.get('id', type=int)
        vals = (f.get('name', '').strip(), f.get('country', 'MX'), f.get('states', '').strip(), f.get('carrier', '').strip(),
                num('price_mxn'), num('price_usd'), num('free_from'), f.get('days', '').strip(), int(bool(f.get('active'))))
        if not vals[0]:
            flash('Ponle nombre a la zona.', 'warn')
        elif zid:
            ex('''UPDATE zones SET name=?, country=?, states=?, carrier=?, price_mxn=?, price_usd=?, free_from=?, days=?, active=?
                  WHERE id=?''', vals + (zid,))
            flash('Zona guardada', 'ok')
        else:
            ex('''INSERT INTO zones(name, country, states, carrier, price_mxn, price_usd, free_from, days, active)
                  VALUES(?,?,?,?,?,?,?,?,?)''', vals)
            flash('Zona creada', 'ok')
        return redirect(url_for('admin.zones'))
    return render_template('admin/zones.html', rows=q('SELECT * FROM zones ORDER BY country DESC, id'))


@bp.route('/envios/<int:zid>/borrar', methods=['POST'])
def zone_del(zid):
    ex('DELETE FROM zones WHERE id = ?', (zid,))
    return redirect(url_for('admin.zones'))


# ---------- publicaciones ----------
@bp.route('/publicaciones', methods=['GET', 'POST'])
def posts():
    if request.method == 'POST':
        f = request.form
        if f.get('title', '').strip():
            ex('INSERT INTO posts(title, body, image, author_id) VALUES(?,?,?,?)',
               (f['title'].strip(), f.get('body', '').strip(), u.save_img(request.files.get('image')) or '', u.me()['id']))
            flash('Publicado', 'ok')
        return redirect(url_for('admin.posts'))
    return render_template('admin/posts.html', rows=q('SELECT * FROM posts ORDER BY id DESC'))


@bp.route('/publicaciones/<int:pid>/borrar', methods=['POST'])
def post_del(pid):
    r = one('SELECT image FROM posts WHERE id = ?', (pid,))
    if r and r['image']:
        u.del_img(r['image'])
    ex('DELETE FROM posts WHERE id = ?', (pid,))
    ex('DELETE FROM post_likes WHERE post_id = ?', (pid,))
    return redirect(url_for('admin.posts'))


# ---------- resenas y mensajes ----------
@bp.route('/resenas')
def reviews():
    rows = q('''SELECT r.*, p.name AS pname, u.name AS uname FROM reviews r
                JOIN products p ON p.id = r.product_id JOIN users u ON u.id = r.user_id ORDER BY r.id DESC''')
    return render_template('admin/reviews.html', rows=rows)


@bp.route('/resenas/<int:rid>/<act>', methods=['POST'])
def review_act(rid, act):
    if act == 'borrar':
        ex('DELETE FROM reviews WHERE id = ?', (rid,))
    else:
        ex('UPDATE reviews SET visible = 1 - visible WHERE id = ?', (rid,))
    return redirect(url_for('admin.reviews'))


@bp.route('/mensajes')
def messages():
    rows = q('SELECT * FROM messages ORDER BY id DESC')
    ex('UPDATE messages SET seen = 1')
    return render_template('admin/messages.html', rows=rows)


# ---------- personal, ajustes, cuenta ----------
@bp.route('/personal', methods=['GET', 'POST'])
def staff():
    if request.method == 'POST':
        f = request.form
        email, pw = f.get('email', '').strip().lower(), f.get('password', '')
        if not f.get('name', '').strip() or '@' not in email or len(pw) < 6:
            flash('Revisa los datos (contraseña de 6+ caracteres).', 'warn')
        elif one('SELECT 1 FROM users WHERE email = ?', (email,)):
            flash('Ese correo ya está registrado.', 'warn')
        else:
            ex('INSERT INTO users(name, email, pass_hash, role) VALUES(?,?,?,"admin")',
               (f['name'].strip(), email, generate_password_hash(pw)))
            flash('Persona agregada al personal', 'ok')
        return redirect(url_for('admin.staff'))
    return render_template('admin/staff.html', rows=q('SELECT * FROM users WHERE role = "admin"'))


@bp.route('/personal/<int:uid>/borrar', methods=['POST'])
def staff_del(uid):
    if uid == u.me()['id']:
        flash('No puedes borrarte a ti mismo.', 'warn')
    else:
        ex('DELETE FROM users WHERE id = ? AND role = "admin"', (uid,))
    return redirect(url_for('admin.staff'))


@bp.route('/ajustes', methods=['GET', 'POST'])
def settings_page():
    if request.method == 'POST':
        for k in DEFAULTS:
            if k in request.form:
                set_setting(k, request.form[k].strip())
        flash('Ajustes guardados', 'ok')
        return redirect(url_for('admin.settings_page'))
    return render_template('admin/settings.html')


@bp.route('/cuenta', methods=['GET', 'POST'])
def my_account():
    me = u.me()
    if request.method == 'POST':
        f = request.form
        if not check_password_hash(me['pass_hash'] or '', f.get('old', '')):
            flash('La contraseña actual no coincide.', 'warn')
        elif len(f.get('new', '')) < 6:
            flash('La nueva contraseña debe tener 6+ caracteres.', 'warn')
        else:
            ex('UPDATE users SET pass_hash = ? WHERE id = ?', (generate_password_hash(f['new']), me['id']))
            flash('Contraseña cambiada', 'ok')
        return redirect(url_for('admin.my_account'))
    return render_template('admin/account.html')


@bp.route('/ayuda')
def help():
    return render_template('admin/help.html')

import secrets
import requests
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

import config
from db import one, ex
import utils as u

bp = Blueprint('auth', __name__)


def safe_next(n):
    # solo rutas internas, nada de redirigir a otros sitios
    return n if n and n.startswith('/') and not n.startswith('//') else None


def start_session(user):
    keep = {k: session[k] for k in ('lang', 'cur', 'cart', 'coupon') if k in session}
    session.clear()
    session.update(keep)
    session['uid'] = user['id']
    session.permanent = True


@bp.route('/registro', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        f = request.form
        name, email, pw = f.get('name', '').strip(), f.get('email', '').strip().lower(), f.get('password', '')
        if not (name and '@' in email and len(pw) >= 6):
            flash('Revisa tus datos (contraseña de 6+ caracteres).', 'warn')
        elif one('SELECT 1 FROM users WHERE email = ?', (email,)):
            flash('Ese correo ya tiene cuenta, inicia sesión.', 'warn')
        else:
            uid = ex('INSERT INTO users(name, email, pass_hash, phone) VALUES(?,?,?,?)',
                     (name, email, generate_password_hash(pw), f.get('phone', '').strip()))
            start_session(one('SELECT * FROM users WHERE id = ?', (uid,)))
            flash(f'¡Bienvenido, {name}!', 'ok')
            return redirect(safe_next(request.args.get('next')) or url_for('shop.index'))
    return render_template('register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = one('SELECT * FROM users WHERE email = ?', (email,))
        if user and user['role'] == 'admin':
            flash('Esta cuenta es de personal. Entra por el acceso de administración.', 'warn')
        elif user and user['pass_hash'] and check_password_hash(user['pass_hash'], request.form.get('password', '')):
            start_session(user)
            return redirect(safe_next(request.args.get('next')) or url_for('shop.index'))
        else:
            flash('Correo o contraseña incorrectos.', 'warn')
    return render_template('login.html')


@bp.route('/salir')
def logout():
    keep = {k: session[k] for k in ('lang', 'cur') if k in session}
    session.clear()
    session.update(keep)
    return redirect(url_for('shop.index'))


# ---------- acceso del personal (separado del de clientes) ----------
@bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = one('SELECT * FROM users WHERE email = ? AND role = "admin"', (email,))
        if user and check_password_hash(user['pass_hash'] or '', request.form.get('password', '')):
            start_session(user)
            return redirect(safe_next(request.args.get('next')) or url_for('admin.dashboard'))
        flash('Datos incorrectos.', 'warn')
    return render_template('admin/login.html')


# ---------- login con Google / Facebook (clientes) ----------
@bp.route('/oauth/<prov>')
def oauth_start(prov):
    cf = config.OAUTH.get(prov)
    if not cf or not cf['id']:
        flash('Ese método de acceso aún no está configurado.', 'warn')
        return redirect(url_for('auth.login'))
    st = secrets.token_urlsafe(16)
    session['oauth_state'] = st
    cb = url_for('auth.oauth_cb', prov=prov, _external=True)
    from urllib.parse import urlencode
    qs = urlencode({'client_id': cf['id'], 'redirect_uri': cb, 'response_type': 'code', 'scope': cf['scope'], 'state': st})
    return redirect(cf['auth'] + '?' + qs)


@bp.route('/oauth/<prov>/callback')
def oauth_cb(prov):
    cf = config.OAUTH.get(prov)
    if not cf or request.args.get('state') != session.pop('oauth_state', None) or 'code' not in request.args:
        flash('No se pudo iniciar sesión.', 'warn')
        return redirect(url_for('auth.login'))
    cb = url_for('auth.oauth_cb', prov=prov, _external=True)
    try:
        tk = requests.post(cf['token'], data={
            'client_id': cf['id'], 'client_secret': cf['secret'], 'code': request.args['code'],
            'redirect_uri': cb, 'grant_type': 'authorization_code'}, timeout=10).json()
        info = requests.get(cf['info'], headers={'Authorization': 'Bearer ' + tk['access_token']}, timeout=10).json()
    except Exception:
        flash('No se pudo iniciar sesión.', 'warn')
        return redirect(url_for('auth.login'))
    email = (info.get('email') or '').lower()
    oid = f"{prov}:{info.get('sub') or info.get('id')}"
    if not email:
        flash('Tu cuenta no compartió un correo.', 'warn')
        return redirect(url_for('auth.login'))
    user = one('SELECT * FROM users WHERE email = ?', (email,))
    if user and user['role'] == 'admin':
        flash('Esta cuenta es de personal.', 'warn')
        return redirect(url_for('auth.login'))
    if not user:
        uid = ex('INSERT INTO users(name, email, oauth) VALUES(?,?,?)', (info.get('name') or email, email, oid))
        user = one('SELECT * FROM users WHERE id = ?', (uid,))
    start_session(user)
    return redirect(url_for('shop.index'))

import requests
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort

import config
from db import one, ex, q
import utils as u

bp = Blueprint('pay', __name__)


def my_order(code):
    o = one('SELECT * FROM orders WHERE code = ? AND user_id = ?', (code, u.me()['id']))
    if not o:
        abort(404)
    return o


def pp_token():
    r = requests.post(config.PAYPAL_API + '/v1/oauth2/token', data={'grant_type': 'client_credentials'},
                      auth=(config.PAYPAL_ID, config.PAYPAL_SECRET), timeout=15)
    r.raise_for_status()
    return r.json()['access_token']


def mark_paid(o, ref):
    if o['pay_status'] == 'pagado':
        return
    ex("UPDATE orders SET pay_status = 'pagado', status = 'pagado', pay_ref = ? WHERE id = ?", (ref, o['id']))
    u.notify(one('SELECT * FROM orders WHERE id = ?', (o['id'],)), 'pagado')


@bp.route('/pedido/<code>/pagar')
@u.login_required
def pay_page(code):
    o = my_order(code)
    items = q('SELECT * FROM order_items WHERE order_id = ?', (o['id'],))
    if o['pay_status'] == 'pagado':
        return redirect(url_for('shop.order', code=code))
    return render_template('pay.html', o=o, items=items,
                           pp_id=config.PAYPAL_ID if (config.PAYPAL_ID and config.PAYPAL_SECRET) else '')


@bp.route('/paypal/crear/<code>', methods=['POST'])
@u.login_required
def pp_create(code):
    o = my_order(code)
    if o['pay_status'] == 'pagado' or o['status'] == 'cancelado':
        return jsonify(error='Este pedido no se puede pagar.'), 400
    try:
        r = requests.post(config.PAYPAL_API + '/v2/checkout/orders', timeout=15,
                          headers={'Authorization': 'Bearer ' + pp_token()},
                          json={'intent': 'CAPTURE', 'purchase_units': [{
                              'reference_id': o['code'], 'custom_id': o['code'],
                              'description': 'Pedido Excelencia Natural ' + o['code'],
                              'amount': {'currency_code': o['currency'], 'value': f"{o['total']:.2f}"}}]})
        r.raise_for_status()
        return jsonify(id=r.json()['id'])
    except requests.RequestException:
        return jsonify(error='No pudimos conectar con PayPal.'), 502


@bp.route('/paypal/capturar/<code>', methods=['POST'])
@u.login_required
def pp_capture(code):
    o = my_order(code)
    oid = (request.get_json(silent=True) or {}).get('id', '')
    try:
        r = requests.post(f'{config.PAYPAL_API}/v2/checkout/orders/{oid}/capture', timeout=15,
                          headers={'Authorization': 'Bearer ' + pp_token(), 'Content-Type': 'application/json'})
        data = r.json()
    except requests.RequestException:
        return jsonify(error='No pudimos confirmar el pago.'), 502
    try:
        cap = data['purchase_units'][0]['payments']['captures'][0]
        ok = (data.get('status') == 'COMPLETED'
              and data['purchase_units'][0].get('custom_id', cap.get('custom_id')) in (o['code'], None)
              and cap['amount']['currency_code'] == o['currency']
              and abs(float(cap['amount']['value']) - o['total']) < 0.01)
    except (KeyError, IndexError, ValueError):
        ok = False
    if not ok:
        return jsonify(error='El pago no se pudo verificar.'), 400
    mark_paid(o, oid)
    return jsonify(ok=True, url=url_for('shop.order', code=code))


@bp.route('/pedido/<code>/pago-demo', methods=['POST'])
@u.login_required
def pay_demo(code):
    # solo funciona mientras PayPal no este configurado (para probar en local)
    if config.PAYPAL_ID and config.PAYPAL_SECRET:
        abort(404)
    o = my_order(code)
    mark_paid(o, 'DEMO')
    flash(u.tr('paid_ok'), 'ok')
    return redirect(url_for('shop.order', code=code))

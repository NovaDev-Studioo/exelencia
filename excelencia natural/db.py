import sqlite3
import os
from flask import g
import config


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(config.DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(e=None):
    d = g.pop('db', None)
    if d is not None:
        d.close()


def q(sql, args=()):
    return get_db().execute(sql, args).fetchall()


def one(sql, args=()):
    return get_db().execute(sql, args).fetchone()


def ex(sql, args=()):
    # ejecuta y guarda; regresa el id nuevo
    d = get_db()
    cur = d.execute(sql, args)
    d.commit()
    return cur.lastrowid


def init_db():
    d = sqlite3.connect(config.DB_PATH)
    d.executescript(open(os.path.join(config.BASE, 'schema.sql'), encoding='utf-8').read())
    d.commit()
    d.close()


# ---- ajustes de la tienda (tabla settings) ----
DEFAULTS = {
    'store_name': 'Excelencia Natural',
    'slogan': 'Lo natural, más cerca de ti',
    'email': '',
    'whatsapp': '2215937389',
    'admin_wa': '2215937389',            # a este numero llegan los avisos de pedidos nuevos
    'address': 'Av 14 Pte 717, San Pablo de los Frailes, 72000 Heroica Puebla de Zaragoza, Pue.',
    'hours': 'Lunes a sábado de 9:00 a 19:00',
    'usd_rate': '18',                    # 1 USD = X MXN
    'instagram': '', 'facebook': '', 'tiktok': '',
}


def settings():
    res = dict(DEFAULTS)
    try:
        for r in q('SELECT k, v FROM settings'):
            res[r['k']] = r['v']
    except sqlite3.Error:
        pass
    return res


def set_setting(k, v):
    ex('INSERT INTO settings(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v', (k, v))

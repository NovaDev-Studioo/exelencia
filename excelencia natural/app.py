import os
from flask import Flask, request, session, redirect, url_for

import config
import db
import utils
from i18n import T
import icons
import art


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    app.teardown_appcontext(db.close_db)
    os.makedirs(config.UPLOADS, exist_ok=True)

    # si no existe la bd la creamos sola
    if not os.path.exists(config.DB_PATH):
        db.init_db()

    from shop import bp as shop_bp
    from auth import bp as auth_bp
    from pay import bp as pay_bp
    from admin import bp as admin_bp
    for b in (shop_bp, auth_bp, pay_bp, admin_bp):
        app.register_blueprint(b)

    @app.before_request
    def guard():
        if request.method == 'POST':
            utils.check_csrf()

    @app.context_processor
    def inject():
        return dict(
            S=db.settings(), me=utils.me(), t=utils.tr, lang=utils.lang(), cur=utils.cur(),
            money=utils.money, pname=utils.pname, pdesc=utils.pdesc, unit_price=utils.unit_price,
            ws_price=utils.ws_price, img_of=utils.img_of, csrf=utils.csrf_token, cart_n=utils.cart_count(),
            to_cur=utils.to_cur, cat_icon=utils.cat_icon, cat_name=utils.cat_name, wa_link=utils.wa_link,
            oauth_on={k: bool(v['id']) for k, v in config.OAUTH.items()},
            paypal_on=bool(config.PAYPAL_ID and config.PAYPAL_SECRET),
        )

    app.jinja_env.globals.update(icon=icons.icon, cat_icons=icons.CAT_ICONS, hero_art=art.hero_art,
                                 sprig=art.sprig, product_ph=art.product_ph, divider=art.divider)

    @app.template_filter('fdate')
    def fdate(s):
        return (s or '')[:16]

    @app.errorhandler(404)
    def nf(e):
        from flask import render_template
        return render_template('404.html'), 404

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)

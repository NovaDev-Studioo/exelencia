import os

BASE = os.path.dirname(os.path.abspath(__file__))


def load_env():
    # mini lector de .env para no depender de python-dotenv
    p = os.path.join(BASE, '.env')
    if not os.path.exists(p):
        return
    for ln in open(p, encoding='utf-8'):
        ln = ln.strip()
        if not ln or ln.startswith('#') or '=' not in ln:
            continue
        k, v = ln.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())


load_env()

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-cambiala')
DB_PATH = os.path.join(BASE, 'excelencia.db')
UPLOADS = os.path.join(BASE, 'static', 'uploads')
MAX_CONTENT_LENGTH = 8 * 1024 * 1024
ALLOWED_IMG = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

PAYPAL_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET', '')
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
PAYPAL_API = 'https://api-m.paypal.com' if PAYPAL_MODE == 'live' else 'https://api-m.sandbox.paypal.com'

OAUTH = {
    'google': {
        'id': os.environ.get('GOOGLE_CLIENT_ID', ''),
        'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        'auth': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token': 'https://oauth2.googleapis.com/token',
        'info': 'https://openidconnect.googleapis.com/v1/userinfo',
        'scope': 'openid email profile',
    },
    'facebook': {
        'id': os.environ.get('FACEBOOK_CLIENT_ID', ''),
        'secret': os.environ.get('FACEBOOK_CLIENT_SECRET', ''),
        'auth': 'https://www.facebook.com/v19.0/dialog/oauth',
        'token': 'https://graph.facebook.com/v19.0/oauth/access_token',
        'info': 'https://graph.facebook.com/me?fields=id,name,email',
        'scope': 'email public_profile',
    },
}

WA_TOKEN = os.environ.get('WA_TOKEN', '')
WA_PHONE_ID = os.environ.get('WA_PHONE_ID', '')

SMTP = {
    'host': os.environ.get('SMTP_HOST', ''),
    'port': int(os.environ.get('SMTP_PORT', '587') or 587),
    'user': os.environ.get('SMTP_USER', ''),
    'pass': os.environ.get('SMTP_PASS', ''),
}

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@excelencianatural.local')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')

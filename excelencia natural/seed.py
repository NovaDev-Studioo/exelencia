"""Crea la base de datos y mete datos de ejemplo.  Uso:  python seed.py"""
from werkzeug.security import generate_password_hash
import sqlite3
import config
import db

db.init_db()
c = sqlite3.connect(config.DB_PATH)
c.execute('PRAGMA foreign_keys = ON')

# admin
if not c.execute("SELECT 1 FROM users WHERE role = 'admin'").fetchone():
    c.execute("INSERT INTO users(name, email, pass_hash, role) VALUES(?,?,?,'admin')",
              ('Personal Excelencia Natural', config.ADMIN_EMAIL, generate_password_hash(config.ADMIN_PASS)))
    print('Admin creado:', config.ADMIN_EMAIL, '/', config.ADMIN_PASS, ' (cámbiala en Mi cuenta)')

# categorias
if not c.execute('SELECT 1 FROM categories').fetchone():
    cats = [('Tés e infusiones', 'Teas & infusions', 'cup'), ('Suplementos', 'Supplements', 'pill'),
            ('Cuidado personal', 'Personal care', 'bottle'), ('Semillas y granos', 'Seeds & grains', 'wheat'),
            ('Aceites naturales', 'Natural oils', 'droplet')]
    c.executemany('INSERT INTO categories(name, name_en, icon) VALUES(?,?,?)', cats)

    # (nombre, nombre_en, descr, cat, mxn, ws_min, ws_mxn, stock, destacado)
    prods = [
        ('Té de manzanilla', 'Chamomile tea', 'Infusión de flor de manzanilla, caja con 25 sobres.', 1, 59, 6, 48, 40, 1),
        ('Té de jamaica', 'Hibiscus tea', 'Flor de jamaica seca, bolsa de 200 g.', 1, 65, 6, 52, 35, 1),
        ('Moringa en cápsulas', 'Moringa capsules', 'Suplemento alimenticio de moringa, 90 cápsulas.', 2, 189, 5, 160, 25, 1),
        ('Spirulina en polvo', 'Spirulina powder', 'Suplemento alimenticio, bote de 250 g.', 2, 249, 4, 215, 18, 0),
        ('Jabón de avena y miel', 'Oat & honey soap', 'Jabón artesanal en barra de 100 g.', 3, 55, 10, 40, 60, 1),
        ('Crema de sábila', 'Aloe vera cream', 'Crema hidratante con sábila, 120 ml.', 3, 95, 6, 78, 30, 0),
        ('Semillas de chía', 'Chia seeds', 'Semilla de chía, bolsa de 500 g.', 4, 85, 6, 70, 50, 1),
        ('Avena integral', 'Whole oats', 'Avena integral a granel, bolsa de 1 kg.', 4, 48, 10, 38, 70, 0),
        ('Aceite de coco', 'Coconut oil', 'Aceite de coco prensado en frío, 250 ml.', 5, 145, 6, 120, 22, 1),
        ('Aceite de almendras', 'Almond oil', 'Aceite de almendras dulces, 120 ml.', 5, 110, 6, 92, 3, 0),
    ]
    for n, ne, ds, cat, mxn, wm, wp, st, ft in prods:
        c.execute('''INSERT INTO products(name, name_en, descr, cat_id, price_mxn, ws_min, ws_mxn, stock, featured)
                     VALUES(?,?,?,?,?,?,?,?,?)''', (n, ne, ds, cat, mxn, wm, wp, st, ft))

# zonas de envio (valores propuestos, editables en el panel)
if not c.execute('SELECT 1 FROM zones').fetchone():
    c.executemany('INSERT INTO zones(name, country, states, carrier, price_mxn, free_from, days) VALUES(?,?,?,?,?,?,?)', [
        ('Puebla (local)', 'MX', 'Puebla', 'Mensajería local', 60, 599, '1 a 2 días hábiles'),
        ('Centro de México', 'MX', 'Ciudad de México,Estado de México,Tlaxcala,Morelos,Hidalgo,Querétaro,Veracruz', 'Estafeta', 120, 999, '2 a 4 días hábiles'),
        ('Resto de México', 'MX', '', 'Estafeta', 170, 1299, '3 a 6 días hábiles'),
        ('Internacional', 'EX', '', 'DHL', 650, 0, '7 a 15 días hábiles'),
    ])

# cupones de ejemplo
if not c.execute('SELECT 1 FROM coupons').fetchone():
    c.execute("INSERT INTO coupons(code, kind, value) VALUES('BIENVENIDA10','percent',10)")
    c.execute("INSERT INTO coupons(code, kind, value, min_total) VALUES('AHORRA50','fixed',50,500)")
    c.execute("INSERT INTO coupons(code, kind, product_id, max_uses) VALUES('REGALO','free_product',5,50)")

if not c.execute('SELECT 1 FROM posts').fetchone():
    c.execute("INSERT INTO posts(title, body) VALUES(?,?)",
              ('¡Bienvenidos a la tienda en línea de Excelencia Natural!', 'Ya puedes comprar tus productos naturistas favoritos desde casa. Usa el código BIENVENIDA10 en tu primera compra'))

c.commit()
c.close()
print('Listo. Ejecuta:  python app.py')

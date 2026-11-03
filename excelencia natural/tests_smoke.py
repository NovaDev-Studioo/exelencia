import sys, re, io, os
sys.path.insert(0, '.')
os.chdir('.')
from app import app
c = app.test_client()
fails = []
def tok(html):
    m = re.search(r'name="_csrf" value="([^"]+)"', html) or re.search(r'data-csrf="([^"]+)"', html)
    return m.group(1)
def get(u, **k):
    r = c.get(u, **k)
    if r.status_code not in (200, 302): fails.append((u, r.status_code))
    return r
def T(): return tok(c.get('/').get_data(as_text=True))
def post(u, data=None, **k):
    d = dict(data or {}); d['_csrf'] = T()
    r = c.post(u, data=d, **k)
    if r.status_code >= 400: fails.append((u, r.status_code, r.get_data(as_text=True)[:200]))
    return r

for u in ['/', '/catalogo', '/catalogo?q=té&sort=low&min=10&max=200', '/producto/1', '/nosotros', '/contacto', '/preguntas-frecuentes', '/publicaciones', '/terminos', '/privacidad', '/devoluciones', '/registro', '/login', '/admin/login', '/carrito', '/moneda/USD', '/catalogo', '/', '/producto/3', '/preguntas-frecuentes', '/moneda/MXN']:
    get(u)
# cliente no entra a admin
r = c.get('/admin/'); assert r.status_code == 302 and 'admin/login' in r.location
# registro
r = post('/registro', dict(name='Ana Prueba', email='ana@test.com', password='secreto1', phone='2221234567'))
assert r.status_code == 302
# carrito: 6 pzas de te manzanilla -> mayoreo
post('/carrito/agregar/1', dict(qty=6))
post('/carrito/agregar/5', dict(qty=1))
h = get('/carrito').get_data(as_text=True)
assert 'mayoreo' in h.lower() or 'Wholesale' in h, 'mayoreo no aplicado'
assert '48.00' in h, 'precio mayoreo'
post('/carrito/cupon', dict(code='BIENVENIDA10'))
h = get('/carrito').get_data(as_text=True); assert 'Descuento' in h
post('/carrito/cupon', dict(code='REGALO'))
h = get('/carrito').get_data(as_text=True); assert 'Regalo' in h
# envio api
j = c.get('/api/envio?delivery=envio&country=México&state=Puebla').get_json(); print(j)
j2 = c.get('/api/envio?delivery=envio&country=Canada&state=ON').get_json(); print(j2)
j3 = c.get('/api/envio?delivery=recoger').get_json(); print(j3)
get('/checkout')
# checkout con falta de datos
r = post('/checkout', dict(delivery='envio', name='Ana', phone='1', email='a@a.com'))
assert r.status_code == 200
# checkout valido
r = post('/checkout', dict(delivery='envio', name='Ana', phone='2221234567', email='ana@test.com', addr='Calle 1', city='Puebla', state='Puebla', zip='72000', country='México', terms='on'))
assert r.status_code == 302, r.status_code
loc = r.location; print(loc)
code = loc.split('/')[-2]
h = get(loc).get_data(as_text=True); assert 'Simular pago' in h
r = post(f'/pedido/{code}/pago-demo'); assert r.status_code == 302
h = get(f'/pedido/{code}').get_data(as_text=True); assert 'pagado' in h
get('/mi-cuenta')
# resena, favorito, like
post('/resena/1', dict(stars=5, body='Muy bueno')); 
r = c.post('/favoritos/1', data={'_csrf': T()}, headers={'X-Requested-With': 'fetch'}); print(r.get_json())
get('/favoritos')
r = c.post('/publicaciones/1/like', data={'_csrf': T()}, headers={'X-Requested-With': 'fetch'}); print(r.get_json())
h = get('/producto/1').get_data(as_text=True); assert 'Muy bueno' in h
# stock descontado
from db import one
import db as dbm
with app.app_context():
    print('stock te:', one('SELECT stock FROM products WHERE id=1')['stock'], 'jabon:', one('SELECT stock FROM products WHERE id=5')['stock'])
# contacto
post('/contacto', dict(name='X', email='x@x.com', body='hola'))
# csrf falla
r = c.post('/contacto', data={'name': 'x'}); assert r.status_code == 400
# cliente sale; admin
get('/salir')
r = post('/login', dict(email='admin@excelencianatural.local', password='admin123')); assert b'personal' in r.data.lower() or r.status_code == 200
r = post('/admin/login', dict(email='admin@excelencianatural.local', password='admin123')); assert r.status_code == 302
for u in ['/admin/', '/admin/productos', '/admin/productos/nuevo', '/admin/productos/1', '/admin/categorias', '/admin/pedidos', '/admin/pedidos?st=pagado', '/admin/pedidos/1', '/admin/cupones', '/admin/envios', '/admin/publicaciones', '/admin/resenas', '/admin/mensajes', '/admin/personal', '/admin/ajustes', '/admin/cuenta', '/admin/ayuda']:
    get(u)
# crear producto con imagen
from PIL import Image
b = io.BytesIO(); Image.new('RGB', (50, 50), 'green').save(b, 'PNG'); b.seek(0)
r = post('/admin/productos/nuevo', dict(name='Prod nuevo', price_mxn='100', stock='5', active='on', ws_min='3', ws_mxn='80', imgs=(b, 'a.png')), content_type='multipart/form-data')
print('nuevo prod', r.status_code, r.location)
# cambiar estado
r = post('/admin/pedidos/1', dict(status='enviado', carrier='Estafeta', tracking='ABC123')); assert r.status_code == 302
h = get('/admin/pedidos/1').get_data(as_text=True); assert 'ABC123' in h
# cancelar devuelve stock
post('/admin/pedidos/1', dict(status='cancelado', carrier='', tracking=''))
with app.app_context():
    print('stock te tras cancelar:', one('SELECT stock FROM products WHERE id=1')['stock'])
# crear cupon, zona, post, categoria, staff
post('/admin/cupones', dict(code='x1', kind='percent', value='5'))
post('/admin/envios', dict(name='Zona X', country='MX', states='Jalisco', price_mxn='99', days='3', active='on'))
post('/admin/publicaciones', dict(title='Hola', body='Texto'))
post('/admin/categorias', dict(name='Nueva', icon='leaf'))
post('/admin/personal', dict(name='Otro', email='otro@x.com', password='123456'))
post('/admin/ajustes', dict(store_name='Excelencia Natural', usd_rate='17.5'))
# vistas publicas con USD
get('/moneda/USD'); get('/'); get('/catalogo'); get('/producto/1')
print('FALLAS:', fails)

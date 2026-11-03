# Excelencia Natural · Tienda en línea de productos naturistas

Flask + SQLite + HTML/CSS/JavaScript. Funciona 100% en local.

## Arrancar
```bash
cd excelencia-natural
pip install -r requirements.txt
python seed.py        # crea la base de datos con datos de ejemplo (solo la primera vez)
python app.py         # abre http://127.0.0.1:5000
```
- Tienda: `http://127.0.0.1:5000`
- Panel del personal: `http://127.0.0.1:5000/admin/login`
  (usuario `admin@excelencianatural.local`, contraseña `admin123`; cámbiala en Mi cuenta)

Logo: `static/img/Logo.png` (recortado de tu logo de referencia, fondo transparente; el original está en `logo-original.jpg`). Si tienes una versión en alta resolución o SVG, reemplaza `Logo.png` y se actualiza en todo el sitio.

## Diseño
Paleta tomada del logo (crema, verde hoja, verde profundo y dorado), tipografías Playfair Display + Dancing Script + Nunito. Sin emojis: los íconos son SVG en código (`icons.py`) y las ilustraciones botánicas se generan en código (`art.py`), así se ven nítidos en cualquier pantalla. Si más adelante tienes fotos reales de tus productos, súbelas en el panel y reemplazan a la ilustración automáticamente.

## Lo que incluye (según tu cuestionario)
- Clientes y personal **separados**: los clientes no entran al admin y las cuentas de personal no entran como cliente.
- Catálogo con búsqueda, filtros (categoría, precio, orden), galería de fotos, reseñas, favoritos.
- **Mayoreo** por producto (piezas mínimas + precio), se aplica solo en el carrito.
- Cupones: porcentaje, monto fijo y **código de producto gratis**.
- Pesos y dólares (tipo de cambio editable) · Solo español.
- Envíos **por zona** (Puebla, Centro, Resto de México, Internacional), envío gratis desde un monto y **recoger en tienda**.
- Cuenta obligatoria para comprar; login con Google/Facebook (opcional).
- Pago con **PayPal** (MXN/USD). Sin llaves funciona en modo demostración.
- Avisos por WhatsApp y correo en cada cambio de estado del pedido.
- Publicaciones tipo red social (solo el personal publica; clientes dan ♥).
- Páginas: inicio, catálogo, producto, carrito/checkout, nosotros, contacto (formulario, mapa, WhatsApp), FAQ, publicaciones, términos, privacidad, devoluciones.
- Panel admin sencillo con manual integrado (menú "Ayuda").

## Configuración opcional (`.env`, copia `.env.example`)
| Qué | Variables |
|---|---|
| PayPal | `PAYPAL_CLIENT_ID`, `PAYPAL_SECRET`, `PAYPAL_MODE` (`sandbox`/`live`) |
| Google / Facebook | `GOOGLE_CLIENT_ID/SECRET`, `FACEBOOK_CLIENT_ID/SECRET` (redirect: `/oauth/google/callback`, `/oauth/facebook/callback`) |
| WhatsApp automático | `WA_TOKEN`, `WA_PHONE_ID` (WhatsApp Cloud API). Sin esto, cada pedido tiene un botón "Abrir en WhatsApp" |
| Correo | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` |

## Propuestas que hice (editables en el panel → Envíos / Ajustes)
- Paquetería: mensajería local (Puebla), Estafeta (nacional), DHL (internacional).
- Envío gratis desde $599 (Puebla), $999 (Centro), $1,299 (resto); internacional sin envío gratis.
- Tipografías: Playfair Display (títulos), Dancing Script (acentos) y Nunito (texto), acordes al logo.
- Devoluciones: 7 días, producto sellado. Los textos legales son **borradores**: revísalos con un asesor y cuida las leyendas de COFEPRIS (no prometer curas).

## Para publicar en internet (pendiente)
Dominio, hosting, SSL y correo propio. Al publicar: `SECRET_KEY` propio, `gunicorn app:app` detrás de HTTPS, y respaldar `excelencia.db` y `static/uploads/`.

## Estructura
`app.py` arranque · `shop.py` tienda · `auth.py` cuentas · `pay.py` PayPal · `admin.py` panel · `utils.py` precios/carrito/envíos/avisos · `db.py` + `schema.sql` base de datos · `i18n.py` textos ES/EN · `templates/` · `static/`

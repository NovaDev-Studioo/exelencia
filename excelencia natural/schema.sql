CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  pass_hash TEXT,
  role TEXT NOT NULL DEFAULT 'cliente',      -- cliente | admin (personal)
  phone TEXT DEFAULT '',
  oauth TEXT DEFAULT '',                     -- google:123 / facebook:456
  created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  name_en TEXT DEFAULT '',
  icon TEXT DEFAULT '🌿'
);

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  name_en TEXT DEFAULT '',
  descr TEXT DEFAULT '',
  descr_en TEXT DEFAULT '',
  cat_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  price_mxn REAL NOT NULL DEFAULT 0,
  price_usd REAL DEFAULT 0,                  -- 0 = se calcula con el tipo de cambio
  ws_mxn REAL DEFAULT 0,                     -- precio mayoreo (0 = sin mayoreo)
  ws_usd REAL DEFAULT 0,
  ws_min INTEGER DEFAULT 0,                  -- piezas minimas para mayoreo
  stock INTEGER DEFAULT 0,
  featured INTEGER DEFAULT 0,
  active INTEGER DEFAULT 1,
  created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  file TEXT NOT NULL,
  pos INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS wishlist (
  user_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  PRIMARY KEY (user_id, product_id)
);

CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL,
  stars INTEGER NOT NULL,
  body TEXT DEFAULT '',
  visible INTEGER DEFAULT 1,
  created TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (product_id, user_id)
);

CREATE TABLE IF NOT EXISTS coupons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL,                        -- percent | fixed | free_product
  value REAL DEFAULT 0,                      -- % o monto en MXN
  product_id INTEGER,                        -- para free_product
  min_total REAL DEFAULT 0,                  -- minimo en MXN
  max_uses INTEGER DEFAULT 0,                -- 0 = ilimitado
  used INTEGER DEFAULT 0,
  expires TEXT DEFAULT '',
  active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS zones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  country TEXT NOT NULL DEFAULT 'MX',        -- MX | EX (extranjero)
  states TEXT DEFAULT '',                    -- estados separados por coma (vacio = el resto)
  carrier TEXT DEFAULT '',
  price_mxn REAL DEFAULT 0,
  price_usd REAL DEFAULT 0,
  free_from REAL DEFAULT 0,                  -- MXN, 0 = nunca gratis
  days TEXT DEFAULT '',
  active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  status TEXT DEFAULT 'pendiente',           -- pendiente|pagado|preparando|enviado|entregado|cancelado
  pay_status TEXT DEFAULT 'pendiente',
  pay_ref TEXT DEFAULT '',
  currency TEXT DEFAULT 'MXN',
  subtotal REAL, discount REAL DEFAULT 0, shipping REAL DEFAULT 0, total REAL,
  coupon TEXT DEFAULT '',
  delivery TEXT DEFAULT 'envio',             -- envio | recoger
  name TEXT, phone TEXT, email TEXT,
  addr TEXT DEFAULT '', city TEXT DEFAULT '', state TEXT DEFAULT '', zip TEXT DEFAULT '', country TEXT DEFAULT 'México',
  zone TEXT DEFAULT '', carrier TEXT DEFAULT '', tracking TEXT DEFAULT '',
  notes TEXT DEFAULT '',
  created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id INTEGER,
  name TEXT, qty INTEGER, price REAL,
  ws INTEGER DEFAULT 0,                      -- 1 si se aplico mayoreo
  free INTEGER DEFAULT 0                     -- 1 si vino de codigo de producto gratis
);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  body TEXT DEFAULT '',
  image TEXT DEFAULT '',
  author_id INTEGER,
  created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS post_likes (
  post_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  PRIMARY KEY (post_id, user_id)
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT, email TEXT, body TEXT,
  seen INTEGER DEFAULT 0,
  created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER,
  target TEXT, kind TEXT, text TEXT,
  sent INTEGER DEFAULT 0,
  created TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
  k TEXT PRIMARY KEY,
  v TEXT
);

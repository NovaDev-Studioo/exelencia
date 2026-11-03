"""Ilustraciones botanicas en SVG generadas con codigo (inspiradas en la rama de eucalipto del logo)."""
import math
import random
from markupsafe import Markup
from icons import P

GREENS = ['#6fa83a', '#8dc34a', '#a9d35e', '#4f8a2b', '#2f6b3d']
DEEP = '#1e4a36'
GOLD = '#e7a72b'


def _bez(p, t):
    # punto y angulo de una curva bezier cubica
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p
    u = 1 - t
    x = u**3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3
    y = u**3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3
    dx = 3 * u * u * (x1 - x0) + 6 * u * t * (x2 - x1) + 3 * t * t * (x3 - x2)
    dy = 3 * u * u * (y1 - y0) + 6 * u * t * (y2 - y1) + 3 * t * t * (y3 - y2)
    return x, y, math.degrees(math.atan2(dy, dx))


def _leaf(x, y, ang, ln, wd, col, op=1):
    d = f'M0 0C{ln*.3:.1f} {-wd:.1f} {ln*.75:.1f} {-wd:.1f} {ln:.1f} 0C{ln*.75:.1f} {wd:.1f} {ln*.3:.1f} {wd:.1f} 0 0Z'
    vein = f'<path d="M0 0L{ln*.9:.1f} 0" stroke="#fff" stroke-opacity=".35" stroke-width="1" fill="none"/>'
    return (f'<g transform="translate({x:.1f} {y:.1f}) rotate({ang:.1f})" opacity="{op}">'
            f'<path d="{d}" fill="{col}"/>{vein}</g>')


def branch(pts, n=9, ln=46, wd=15, seed=1, cols=None, stem=DEEP, round_leaves=False):
    r = random.Random(seed)
    cols = cols or GREENS
    out = [f'<path d="M{pts[0][0]} {pts[0][1]}C{pts[1][0]} {pts[1][1]} {pts[2][0]} {pts[2][1]} {pts[3][0]} {pts[3][1]}" '
           f'stroke="{stem}" stroke-width="2.6" fill="none" stroke-linecap="round"/>']
    for i in range(n):
        t = .12 + .86 * i / max(n - 1, 1)
        x, y, a = _bez(pts, t)
        k = 1 - .45 * t                      # hojas mas chicas hacia la punta
        side = 1 if i % 2 == 0 else -1
        la = a + side * r.uniform(38, 62)
        w = wd * k * (1.9 if round_leaves else 1)
        out.append(_leaf(x, y, la, ln * k * r.uniform(.85, 1.1), w, r.choice(cols), .95))
    x, y, a = _bez(pts, 1)
    out.append(_leaf(x, y, a, ln * .6, wd * .6, cols[0]))
    return ''.join(out)


def flower(x, y, s=1, col=DEEP):
    # boton tipo eucalipto: cabeza redonda con rayitas
    g = [f'<g transform="translate({x} {y}) scale({s})">',
         f'<ellipse cx="0" cy="0" rx="16" ry="13" fill="#fff" fill-opacity=".6" stroke="{col}" stroke-width="1.6"/>']
    for k in range(-4, 5):
        g.append(f'<path d="M{k*3.2} -12Q{k*4} 0 {k*3.2} 12" stroke="{col}" stroke-width="1" fill="none" opacity=".8"/>')
    g.append(f'<path d="M-16 -4Q0 -26 16 -4" stroke="{col}" stroke-width="1.6" fill="none"/>')
    g.append('</g>')
    return ''.join(g)


def _wrap(w, h, body, cls='', defs=''):
    return Markup(f'<svg class="art {cls}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
                  f'role="img" aria-hidden="true" preserveAspectRatio="xMidYMid meet"><defs>{defs}</defs>{body}</svg>')


def hero_art():
    defs = (
        '<linearGradient id="hg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8dc34a"/>'
        '<stop offset=".55" stop-color="#cfe27a"/><stop offset="1" stop-color="#e7a72b"/></linearGradient>'
        '<radialGradient id="hb" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="#fffef4"/>'
        '<stop offset="1" stop-color="#f1f7d8"/></radialGradient>'
        '<clipPath id="hc"><ellipse cx="260" cy="310" rx="226" ry="286"/></clipPath>')
    b = ['<ellipse cx="260" cy="310" rx="246" ry="302" fill="url(#hg)" opacity=".9"/>',
         '<ellipse cx="260" cy="310" rx="226" ry="286" fill="url(#hb)"/>',
         '<g clip-path="url(#hc)">',
         '<circle cx="120" cy="150" r="90" fill="#cfe27a" opacity=".35"/><circle cx="400" cy="480" r="110" fill="#f6d46a" opacity=".3"/>',
         '<g class="sway s1">',
         branch([(300, 600), (210, 470), (400, 330), (330, 70)], n=11, ln=92, wd=32, seed=3),
         flower(338, 92, 1.1), flower(280, 150, .8),
         '</g><g class="sway s2">',
         branch([(110, 600), (80, 480), (190, 400), (150, 250)], n=8, ln=74, wd=26, seed=8, cols=['#a9d35e', '#8dc34a', '#6fa83a']),
         '</g><g class="sway s3">',
         branch([(420, 600), (470, 520), (430, 450), (470, 360)], n=6, ln=60, wd=20, seed=5, cols=['#4f8a2b', '#2f6b3d', '#6fa83a']),
         '</g></g>']
    return _wrap(520, 620, ''.join(b), 'hero-art-svg', defs)


def sprig(w=260, h=200, seed=2, flip=False, cols=None):
    t = ' transform="scale(-1 1) translate(-%d 0)"' % w if flip else ''
    body = f'<g{t}>' + branch([(8, h - 10), (w * .3, h * .9), (w * .6, h * .3), (w - 12, 20)], n=9, ln=48, wd=15, seed=seed, cols=cols) + '</g>'
    return _wrap(w, h, body, 'sprig')


def product_ph(icon_name='leaf'):
    """Imagen de relleno elegante para productos sin foto."""
    defs = ('<linearGradient id="pg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f4f9e1"/>'
            '<stop offset="1" stop-color="#fdf0c2"/></linearGradient>')
    ic = P.get(icon_name) or P['leaf']
    body = (
        '<rect width="400" height="400" fill="url(#pg)"/>'
        '<circle cx="320" cy="90" r="110" fill="#cfe27a" opacity=".25"/>'
        + branch([(-6, 410), (60, 330), (110, 300), (150, 210)], n=6, ln=84, wd=27, seed=4)
        + branch([(410, 410), (350, 340), (300, 310), (270, 230)], n=6, ln=80, wd=26, seed=6, cols=['#a9d35e', '#8dc34a', '#4f8a2b'])
        + '<circle cx="200" cy="190" r="62" fill="#fff" fill-opacity=".85" stroke="url(#pg)"/>'
        '<circle cx="200" cy="190" r="62" fill="none" stroke="#8dc34a" stroke-width="2" stroke-dasharray="3 6"/>'
        f'<g transform="translate(166 156) scale(2.83)" fill="none" stroke="{DEEP}" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round">{ic}</g>')
    return _wrap(400, 400, body, 'ph-svg', defs)


def divider():
    return Markup('<svg class="divider" viewBox="0 0 200 20" aria-hidden="true"><path d="M0 10h80M120 10h80" stroke="#8dc34a" '
                  'stroke-width="1.5" opacity=".6"/><path d="M100 2c6 4 8 10 0 16-8-6-6-12 0-16z" fill="#6fa83a"/>'
                  '<path d="M88 10c4-3 8-3 12 0-4 3-8 3-12 0zM100 10c4-3 8-3 12 0-4 3-8 3-12 0z" fill="#a9d35e"/></svg>')

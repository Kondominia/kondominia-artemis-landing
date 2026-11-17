#!/usr/bin/env python3
"""Blog estático de Kondominia a partir de los artículos del WordPress anterior.

Uso:
  python3 tools/blog/build.py --fetch   # descarga artículos e imágenes del WordPress (una vez)
  python3 tools/blog/build.py           # genera las páginas desde tools/blog/data/posts.json

Genera en public/:
  <slug>/index.html          un artículo por entrada, en la MISMA ruta que tenía en WordPress
  blog/index.html            índice del blog
  wp-content/uploads/...     imágenes, en las mismas rutas (conserva el SEO de imágenes)
  _redirects, sitemap.xml    reescritos (bloques generados entre marcas)

Solo biblioteca estándar. Las rutas de los artículos no cambian: no hacen falta 301.
"""
import argparse
import html
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PUBLIC = os.path.join(ROOT, "public")
DATA = os.path.join(ROOT, "tools", "blog", "data")
WP = "https://www.kondominia.com"
SITE = "https://www.kondominia.com"
GA_ID = "G-XWS9X8P621"
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]


# ─── Descarga ──────────────────────────────────────────────────────────────────

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "kondominia-blog-export"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch():
    os.makedirs(DATA, exist_ok=True)
    posts = json.loads(get(f"{WP}/wp-json/wp/v2/posts?per_page=100&_embed=1"))
    cats = json.loads(get(f"{WP}/wp-json/wp/v2/categories?per_page=100"))
    slim = []
    for p in posts:
        terms = (p.get("_embedded", {}).get("wp:term") or [[]])[0]
        slim.append({
            "id": p["id"], "slug": p["slug"], "link": p["link"],
            "date": p["date"], "modified": p["modified"],
            "title": p["title"]["rendered"], "excerpt": p["excerpt"]["rendered"],
            "content": p["content"]["rendered"],
            "featured": p.get("jetpack_featured_media_url") or "",
            "categories": [{"slug": t["slug"], "name": t["name"]} for t in terms],
        })
    with open(os.path.join(DATA, "posts.json"), "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "categories.json"), "w", encoding="utf-8") as f:
        json.dump([{"slug": c["slug"], "name": c["name"], "count": c["count"]} for c in cats], f, ensure_ascii=False, indent=1)
    print(f"{len(slim)} artículos y {len(cats)} categorías guardados en tools/blog/data/")
    images = set()
    for p in slim:
        images |= set(re.findall(r'<img[^>]+src="([^"]+)"', p["content"]))
        if p["featured"]:
            images.add(p["featured"])
    ok = 0
    for url in sorted(images):
        path = local_upload_path(url)
        if not path:
            continue
        dest = os.path.join(PUBLIC, path.lstrip("/"))
        if os.path.exists(dest):
            ok += 1
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            parts = urllib.parse.urlsplit(url.replace("http://", "https://"))
            data = get(urllib.parse.urlunsplit(parts._replace(path=urllib.parse.quote(urllib.parse.unquote(parts.path)))))
            with open(dest, "wb") as f:
                f.write(data)
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ! no se pudo descargar {url}: {e}", file=sys.stderr)
    print(f"{ok}/{len(images)} imágenes en public/wp-content/uploads/")


def local_upload_path(url):
    """Ruta local de una imagen del WordPress (/wp-content/uploads/...), o None si es externa."""
    m = re.match(r"https?://(?:www\.)?kondominia\.com(/wp-content/uploads/[^?#\"']+)", url)
    return urllib.request.unquote(m.group(1)) if m else None


# ─── Limpieza del contenido ────────────────────────────────────────────────────

def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def norm(s):
    return re.sub(r"[^a-z0-9]", "", text(s).lower())


def clean_content(raw, title):
    c = raw
    meta_desc = None
    # Algunos artículos traen pegado un documento HTML completo (<!DOCTYPE>, <head>, <body>).
    m = re.search(r'<meta name="description" content="([^"]+)"', c)
    if m:
        meta_desc = html.unescape(m.group(1))
    if re.search(r"<body", c, re.I):
        c = re.sub(r"^.*?<body[^>]*>", "", c, flags=re.S | re.I)
        c = re.sub(r"</body>.*$", "", c, flags=re.S | re.I)
        c = re.sub(r"^\s*(<br\s*/?>|</p>)+", "", c.strip(), flags=re.I)
    c = re.sub(r"<(script|style)\b.*?</\1>", "", c, flags=re.S | re.I)
    c = re.sub(r"</?(article|html|head|body)\b[^>]*>", "", c, flags=re.I)
    # El título se muestra fuera del contenido: se quita un <h1> igual y el resto baja a <h2>.
    first_h1 = re.search(r"<h1[^>]*>(.*?)</h1>", c, flags=re.S | re.I)
    if first_h1 and norm(first_h1.group(1)) == norm(title):
        c = c.replace(first_h1.group(0), "", 1)
    c = re.sub(r"<h1([^>]*)>(.*?)</h1>", r"<h2\1>\2</h2>", c, flags=re.S | re.I)

    def fix_img(mm):
        tag = mm.group(0)
        tag = re.sub(r'\s(srcset|sizes)="[^"]*"', "", tag)
        src = re.search(r'src="([^"]+)"', tag)
        if src:
            local = local_upload_path(src.group(1))
            if local:
                tag = tag.replace(src.group(1), urllib.request.quote(local))
        if "loading=" not in tag:
            tag = tag.replace("<img", '<img loading="lazy" decoding="async"', 1)
        if "alt=" not in tag:
            tag = tag.replace("<img", '<img alt=""', 1)
        return tag
    c = re.sub(r"<img\b[^>]*>", fix_img, c, flags=re.I)
    c = re.sub(r"<iframe\b", '<iframe loading="lazy"', c, flags=re.I)
    # Enlaces internos absolutos → relativos (sirven igual en la URL de prueba y en www).
    c = re.sub(r'href="https?://(?:www\.)?kondominia\.com(/[^"]*)"', r'href="\1"', c)
    c = re.sub(r"<p>(\s|&nbsp;|<br\s*/?>)*</p>", "", c, flags=re.I)
    return c.strip(), meta_desc


def summary(s, limit=158):
    s = text(s).replace(" [&hellip;]", "").replace("[…]", "").strip()
    s = re.sub(r"\s*(\[\s*…\s*\]|…)$", "", s)
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0].rstrip(",;:.")
    return cut + "…"


def fecha(iso):
    d = datetime.fromisoformat(iso)
    return f"{d.day} de {MONTHS[d.month - 1]} de {d.year}"


def esc(s):
    return html.escape(s, quote=True)


# ─── Plantillas ────────────────────────────────────────────────────────────────

HEAD_COMMON = """  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <!-- Google Analytics 4 (igual que index.html): solo en kondominia.com. -->
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag() { dataLayer.push(arguments); }
    (function () {
      var GA_ID = '%(ga)s';
      if (!/(^|\\.)kondominia\\.com$/.test(location.hostname)) return;
      var s = document.createElement('script');
      s.async = true;
      s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
      document.head.appendChild(s);
      gtag('js', new Date());
      gtag('config', GA_ID);
    })();
  </script>
  <link rel="icon" type="image/png" href="/kondominia-5-3.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Quicksand:wght@500;600;700&display=swap" rel="stylesheet" />
  <script src="https://cdn.tailwindcss.com?plugins=typography"></script>
  <script>
    tailwind.config = { theme: { extend: {
      fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'], brand: ['Quicksand', 'sans-serif'] },
      colors: {
        k: { 50: '#ecfaff', 100: '#d3f3ff', 200: '#a6e7ff', 400: '#33c8f7', 500: '#0bb4ee', 600: '#0093cc', 700: '#0274a3' },
        sun: { 50: '#fff6eb', 100: '#ffe8cc', 400: '#fbab45', 500: '#f7941d', 600: '#dd7a08' },
        ink: { 950: '#06121f', 900: '#0a1a2c', 800: '#11263d', 700: '#1b3552', 600: '#2b4a6b' },
      },
    } } }
  </script>
  <style>
    body { font-family: 'Inter', system-ui, sans-serif; }
    h1, h2, h3, .font-brand { font-family: 'Quicksand', sans-serif; }
    .prose img { border-radius: 16px; height: auto; margin-left: auto; margin-right: auto; }
    .prose iframe { width: 100%%; min-height: 420px; border: 0; border-radius: 16px; }
    .prose figure figcaption { text-align: center; }
  </style>"""

HEADER = """<header class="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-slate-100">
  <div class="max-w-6xl mx-auto px-5 sm:px-8 h-16 flex items-center justify-between gap-6">
    <a href="/" aria-label="Kondominia"><img src="/kondominia-1-2.png" alt="Kondominia" class="h-8 w-auto" /></a>
    <nav class="hidden md:flex items-center gap-7 text-[14px] font-medium text-slate-600">
      <a href="/#finanzas" class="hover:text-ink-900">Producto</a>
      <a href="/#ia" class="hover:text-ink-900">IA</a>
      <a href="/#planes" class="hover:text-ink-900">Precios</a>
      <a href="/blog/" class="text-ink-900">Blog</a>
      <a href="/#contacto" class="hover:text-ink-900">Contacto</a>
    </nav>
    <div class="flex items-center gap-3">
      <a href="https://app.kondominia.com/login" class="hidden sm:inline text-[14px] font-medium text-slate-600 hover:text-ink-900">Iniciar sesión</a>
      <a href="https://app.kondominia.com/register" class="inline-flex items-center px-4 py-2 rounded-full text-[14px] font-semibold text-ink-950 bg-sun-500 hover:bg-sun-400">Prueba gratis</a>
    </div>
  </div>
</header>"""

CTA = """<aside class="mt-14 rounded-3xl bg-ink-900 text-white p-8 sm:p-10" data-ga-area="cta-blog">
  <p class="text-[12.5px] font-semibold uppercase tracking-[0.16em] text-k-400">Kondominia</p>
  <h2 class="mt-3 text-[26px] sm:text-[30px] leading-tight font-bold">Administra el condominio sin complicaciones.</h2>
  <p class="mt-3 text-white/70 text-[15.5px] leading-relaxed">Cuotas, cobros, gastos, nómina, e-CF y reportes DGII en una sola plataforma. Prueba 30 días gratis, sin tarjeta.</p>
  <div class="mt-6 flex flex-wrap gap-3">
    <a href="https://app.kondominia.com/register" class="inline-flex px-6 py-3 rounded-full font-semibold text-ink-950 bg-sun-500 hover:bg-sun-400">Prueba 30 días gratis</a>
    <a href="/#contacto" class="inline-flex px-6 py-3 rounded-full font-semibold text-white ring-1 ring-white/25 hover:bg-white/10">Hablar con ventas</a>
  </div>
</aside>"""

FOOTER = """<footer class="bg-ink-950 text-white/60 mt-20">
  <div class="max-w-6xl mx-auto px-5 sm:px-8 py-14 grid grid-cols-2 md:grid-cols-[1.6fr_1fr_1fr_1fr] gap-10 text-[14px]">
    <div class="col-span-2 md:col-span-1">
      <img src="/kondominia-1-2.png" alt="Kondominia" class="h-8 w-auto" />
      <p class="mt-4 max-w-xs leading-relaxed">Plataforma de gestión condominial para administradoras y juntas de condóminos en República Dominicana.</p>
      <p class="mt-4 flex gap-4">
        <a href="https://www.instagram.com/kondominia/" target="_blank" rel="noopener" class="hover:text-white">Instagram</a>
        <a href="https://www.facebook.com/kondominia/" target="_blank" rel="noopener" class="hover:text-white">Facebook</a>
        <a href="https://www.linkedin.com/company/kondominia" target="_blank" rel="noopener" class="hover:text-white">LinkedIn</a>
      </p>
    </div>
    <div>
      <p class="text-white font-semibold mb-3">Producto</p>
      <ul class="space-y-2">
        <li><a href="/#finanzas" class="hover:text-white">Finanzas</a></li>
        <li><a href="/#fiscal" class="hover:text-white">Fiscal y nómina</a></li>
        <li><a href="/#ia" class="hover:text-white">IA Kondominia</a></li>
        <li><a href="/#planes" class="hover:text-white">Precios</a></li>
      </ul>
    </div>
    <div>
      <p class="text-white font-semibold mb-3">Compañía</p>
      <ul class="space-y-2">
        <li><a href="/blog/" class="hover:text-white">Blog</a></li>
        <li><a href="/#contacto" class="hover:text-white">Contacto</a></li>
        <li><a href="https://app.kondominia.com/login" class="hover:text-white">Iniciar sesión</a></li>
      </ul>
    </div>
    <div>
      <p class="text-white font-semibold mb-3">Legal</p>
      <ul class="space-y-2">
        <li><a href="https://app.kondominia.com/terminos" class="hover:text-white">Términos de uso</a></li>
        <li><a href="https://app.kondominia.com/privacidad" class="hover:text-white">Política de privacidad</a></li>
        <li><a href="/politica-de-seguridad/" class="hover:text-white">Política de seguridad</a></li>
      </ul>
    </div>
  </div>
  <div class="border-t border-white/10">
    <div class="max-w-6xl mx-auto px-5 sm:px-8 py-8 flex flex-col md:flex-row md:items-center justify-between gap-8 text-[12.5px] leading-relaxed">
      <div class="space-y-1">
        <p>© 2026 Kondominia. Todos los derechos reservados.</p>
        <p>Soluciones ART (RNC 1-31-42927-2), Federico Geraldino 84, Santo Domingo, República Dominicana.</p>
        <p>All in Software (NIT 9500083-6), Ciudad de Guatemala.</p>
      </div>
      <div class="flex flex-wrap items-center gap-4 shrink-0" aria-label="Medios de pago aceptados y autenticación segura">
        <img src="/img/pagos/visa.svg" alt="Visa" class="h-12 w-auto" />
        <img src="/img/pagos/mastercard.svg" alt="Mastercard" class="h-12 w-auto" />
        <span class="inline-flex rounded-md bg-white p-1"><img src="/img/pagos/visa-secure.png" alt="Visa Secure" class="h-12 w-auto" /></span>
        <span class="inline-flex rounded-md bg-white px-2 py-1"><img src="/img/pagos/mastercard-id-check.png" alt="Mastercard ID Check" class="h-12 w-auto" /></span>
      </div>
    </div>
  </div>
</footer>
<a data-ga-area="burbuja" href="https://wa.me/18092244502?text=Hola%2C%20me%20interesa%20conocer%20m%C3%A1s%20sobre%20Kondominia" target="_blank" rel="noopener"
   aria-label="Escríbenos por WhatsApp" class="fixed bottom-6 right-5 z-40 w-10 h-10 grid place-items-center rounded-full shadow-lg text-white hover:scale-110 transition" style="background:#25D366">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12.004 2C6.477 2 2 6.477 2 12.004c0 1.77.463 3.431 1.27 4.878L2 22l5.234-1.243A9.953 9.953 0 0 0 12.004 22C17.53 22 22 17.523 22 12.004 22 6.477 17.53 2 12.004 2zm0 18.214a8.196 8.196 0 0 1-4.188-1.148l-.3-.178-3.106.737.762-3.027-.196-.31A8.21 8.21 0 0 1 3.786 12c0-4.534 3.684-8.22 8.218-8.22 4.535 0 8.22 3.686 8.22 8.22 0 4.535-3.685 8.214-8.22 8.214z"/></svg>
</a>
<script>
  // Analytics: mismos eventos de clic que la landing.
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href');
    var box = a.closest('[data-ga-area], header, footer, article');
    var where = box ? (box.getAttribute('data-ga-area') || box.tagName.toLowerCase()) : 'otro';
    var name = null;
    if (href.indexOf('app.kondominia.com/register') !== -1) name = 'sign_up_click';
    else if (href.indexOf('app.kondominia.com/login') !== -1) name = 'login_click';
    else if (href.indexOf('wa.me/') !== -1) name = 'whatsapp_click';
    else if (href.indexOf('instagram.com') !== -1) name = 'instagram_click';
    if (name) gtag('event', name, { link_location: 'blog-' + where });
  });
</script>"""


def page(title, description, canonical, head_extra, body):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
{HEAD_COMMON % {"ga": GA_ID}}
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}" />
  <link rel="canonical" href="{canonical}" />
  <meta property="og:site_name" content="Kondominia" />
  <meta property="og:locale" content="es_DO" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(description)}" />
  <meta property="og:url" content="{canonical}" />
{head_extra}
</head>
<body class="bg-white text-ink-900 antialiased">
<!-- Generado por tools/blog/build.py: no editar a mano. -->
{HEADER}
{body}
{FOOTER}
</body>
</html>
"""


def category_of(p):
    named = [c for c in p["categories"] if c["slug"] != "uncategorized"]
    return named[0]["name"] if named else "Administración"


def image_url(p):
    local = local_upload_path(p["featured"]) if p["featured"] else None
    return urllib.request.quote(local) if local else None


def card(p):
    img = image_url(p)
    img_html = (f'<img src="{img}" alt="" loading="lazy" decoding="async" class="w-full aspect-[16/10] object-cover" />'
                if img else '<div class="w-full aspect-[16/10] bg-k-50"></div>')
    return f"""<a href="{p['path']}" class="group block rounded-2xl overflow-hidden bg-white ring-1 ring-slate-200/70 hover:ring-k-400 hover:shadow-lg transition">
      {img_html}
      <div class="p-5">
        <p class="text-[12px] font-semibold uppercase tracking-wider text-k-600">{esc(p['category'])}</p>
        <h3 class="mt-2 text-[18px] leading-snug font-bold group-hover:text-k-700">{esc(p['title_text'])}</h3>
        <p class="mt-2 text-[14px] leading-relaxed text-slate-500">{esc(summary(p['description'], 120))}</p>
        <p class="mt-3 text-[12.5px] text-slate-400">{fecha(p['date'])}</p>
      </div>
    </a>"""


def build():
    with open(os.path.join(DATA, "posts.json"), encoding="utf-8") as f:
        posts = json.load(f)
    for p in posts:
        p["title_text"] = text(p["title"])
        p["path"] = p["link"].replace(WP, "") or "/"
        p["body"], meta_desc = clean_content(p["content"], p["title"])
        desc = text(meta_desc or p["excerpt"] or p["body"])
        # Muchos extractos repiten el título al principio (a veces dos veces): se quita.
        while desc.lower().startswith(p["title_text"].lower()):
            desc = desc[len(p["title_text"]):].strip()
        p["description"] = summary(desc or p["title_text"])
        p["category"] = category_of(p)
        words = len(text(p["body"]).split())
        p["minutes"] = max(1, math.ceil(words / 200))
    posts.sort(key=lambda p: p["date"], reverse=True)

    for p in posts:
        canonical = SITE + p["path"]
        img = image_url(p)
        og_img = SITE + img if img else SITE + "/kondominia-1-2.png"
        ld = {
            "@context": "https://schema.org", "@type": "BlogPosting",
            "headline": p["title_text"], "description": p["description"],
            "datePublished": p["date"], "dateModified": p["modified"],
            "image": og_img, "mainEntityOfPage": canonical, "inLanguage": "es",
            "author": {"@type": "Organization", "name": "Kondominia", "url": SITE + "/"},
            "publisher": {"@type": "Organization", "name": "Kondominia",
                          "logo": {"@type": "ImageObject", "url": SITE + "/kondominia-5-3.png"}},
        }
        head_extra = f"""  <meta property="og:type" content="article" />
  <meta property="og:image" content="{og_img}" />
  <meta property="article:published_time" content="{p['date']}" />
  <meta property="article:modified_time" content="{p['modified']}" />
  <meta name="twitter:card" content="summary_large_image" />
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>"""
        related = [q for q in posts if q is not p and q["category"] == p["category"]][:3]
        if len(related) < 3:
            related += [q for q in posts if q is not p and q not in related][: 3 - len(related)]
        hero = f'<img src="{img}" alt="" class="mt-8 w-full rounded-3xl aspect-[16/9] object-cover" />' if img else ""
        body = f"""<main>
  <article class="max-w-3xl mx-auto px-5 sm:px-8 pt-10 sm:pt-14">
    <nav class="text-[13px] text-slate-400" aria-label="Ruta"><a href="/" class="hover:text-k-700">Inicio</a> <span class="mx-1">›</span> <a href="/blog/" class="hover:text-k-700">Blog</a></nav>
    <p class="mt-6 text-[12.5px] font-semibold uppercase tracking-[0.16em] text-k-600">{esc(p['category'])}</p>
    <h1 class="mt-3 text-[32px] sm:text-[42px] leading-[1.1] font-bold tracking-[-0.015em]">{esc(p['title_text'])}</h1>
    <p class="mt-4 text-[14px] text-slate-500"><time datetime="{p['date']}">{fecha(p['date'])}</time> · {p['minutes']} min de lectura</p>
    {hero}
    <div class="prose prose-slate prose-lg max-w-none mt-10 prose-headings:font-bold prose-a:text-k-700 prose-img:rounded-2xl">
{p['body']}
    </div>
    {CTA}
  </article>
  <section class="max-w-6xl mx-auto px-5 sm:px-8 mt-20">
    <h2 class="text-[24px] font-bold">Sigue leyendo</h2>
    <div class="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {''.join(card(q) for q in related)}
    </div>
  </section>
</main>"""
        out = os.path.join(PUBLIC, p["path"].strip("/"), "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(page(f"{p['title_text']} | Kondominia", p["description"], canonical, head_extra, body))

    # Índice del blog
    index_body = f"""<main>
  <section class="bg-slate-50 border-b border-slate-100">
    <div class="max-w-6xl mx-auto px-5 sm:px-8 py-14 sm:py-20">
      <p class="text-[12.5px] font-semibold uppercase tracking-[0.16em] text-k-600">Blog</p>
      <h1 class="mt-3 text-[34px] sm:text-[46px] leading-[1.1] font-bold tracking-[-0.015em]">Ideas para administrar mejor el condominio.</h1>
      <p class="mt-4 max-w-2xl text-[16.5px] leading-relaxed text-slate-600">Consejos sobre cobros, seguridad, mantenimiento, convivencia y gestión para administradoras y juntas de condóminos.</p>
    </div>
  </section>
  <section class="max-w-6xl mx-auto px-5 sm:px-8 mt-12">
    <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {''.join(card(q) for q in posts)}
    </div>
  </section>
</main>"""
    os.makedirs(os.path.join(PUBLIC, "blog"), exist_ok=True)
    with open(os.path.join(PUBLIC, "blog", "index.html"), "w", encoding="utf-8") as f:
        f.write(page("Blog | Kondominia", "Consejos sobre cobros, seguridad, mantenimiento, convivencia y gestión de condominios para administradoras y juntas de condóminos.",
                     SITE + "/blog/", '  <meta property="og:type" content="website" />\n  <meta property="og:image" content="' + SITE + '/kondominia-1-2.png" />', index_body))

    write_redirects(posts)
    write_sitemap(posts)
    print(f"{len(posts)} artículos + /blog/ generados en public/")


def replace_block(path, block, start, end):
    with open(path, encoding="utf-8") as f:
        s = f.read()
    new = f"{start}\n{block}\n{end}"
    if start in s:
        s = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: new, s, flags=re.S)
    else:
        s = s.rstrip() + "\n\n" + new + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)


def write_redirects(posts):
    with open(os.path.join(DATA, "categories.json"), encoding="utf-8") as f:
        cats = json.load(f)
    lines = []
    for p in posts:
        bare = p["path"].rstrip("/")
        if bare:
            lines.append(f"{bare} {p['path']} 301")
    for c in cats:
        lines.append(f"/category/{c['slug']} /blog/ 301")
        lines.append(f"/category/{c['slug']}/ /blog/ 301")
    lines += ["/feed /blog/ 301", "/feed/ /blog/ 301"]
    replace_block(os.path.join(PUBLIC, "_redirects"), "\n".join(lines),
                  "# >>> blog (generado por tools/blog/build.py)", "# <<< blog")


def write_sitemap(posts):
    today = datetime.now().strftime("%Y-%m-%d")
    urls = [("/", today), ("/blog/", today), ("/politica-de-seguridad/", "2026-11-14")]
    urls += [(p["path"], p["modified"][:10]) for p in posts]
    body = "\n".join(f"  <url>\n    <loc>{SITE}{u}</loc>\n    <lastmod>{d}</lastmod>\n  </url>" for u, d in urls)
    with open(os.path.join(PUBLIC, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n')


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="descargar artículos e imágenes del WordPress")
    args = ap.parse_args()
    if args.fetch:
        fetch()
    build()

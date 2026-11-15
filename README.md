# Kondominia — Landing Page

Landing page pública de [Kondominia](https://www.kondominia.com), plataforma de gestión condominial para administradoras y juntas de condóminos en República Dominicana.

## Stack

- HTML estático, sin paso de build
- [Tailwind CSS](https://tailwindcss.com) vía CDN
- Google Fonts (Inter para texto, Quicksand para títulos)
- JavaScript vanilla

## Estructura

```
index.html                     # Página principal (todo en un solo archivo)
politica-de-seguridad/         # Política de seguridad (requisito del procesador de pagos)
img/pagos/                     # Logos de Visa, Mastercard, Visa Secure y Mastercard ID Check
kondominia-1-2.png             # Logo horizontal
kondominia-5-3.png             # Isotipo
_redirects, _headers           # Configuración de Cloudflare Pages
robots.txt, sitemap.xml        # SEO
```

## Contenido

Los textos y precios salen del código de la app (`kondominia-artemis`, rama `main`):

- Precios: plan único por tramos, versión `PLAN_UNICO_2026_11` (`src/lib/pricing/plan-unico.ts`).
  Si se activa otra versión de precios, actualizar `PRICING` en el script de `index.html`.
- IA Kondominia: `src/content/guia-uso/13-ia-kondominia.md` y `src/lib/copilot/usage.ts`.
- Seguridad: `docs/pii-encryption-phase1.md` y `docs/deployment/`.
- No nombrar al procesador de pagos en textos públicos: puede cambiar.

## Formulario de contacto

Envía los datos a un webhook de Make (sin exponer correos). Los envíos de prueba desde
la URL `*.pages.dev` también llegan a Make.

## Publicación (Cloudflare Pages)

Sitio estático, sin paso de build. Se publica con cada push a `main`; cada rama
genera una URL de vista previa.

Configuración del proyecto en Cloudflare (Workers & Pages → Create → Pages →
Connect to Git → `Kondominia/kondominia-artemis-landing`):

- Production branch: `main`
- Framework preset: `None`
- Build command: vacío
- Build output directory: `/`

Archivos que interpreta Cloudflare Pages:

- `_redirects`: redirecciones 301 de las URLs del WordPress anterior (no se publica).
- `_headers`: marca `noindex` la URL de prueba `*.pages.dev` y sus vistas previas.
- `robots.txt` y `sitemap.xml`: se sirven tal cual.

Dominio: en el proyecto, Custom domains → `www.kondominia.com`. Si el DNS de
`kondominia.com` no está en Cloudflare, crear un CNAME `www` hacia
`<proyecto>.pages.dev`. El dominio sin `www` puede seguir en el servidor actual,
que ya redirige a `www`.

Ojo: todo lo que esté en la raíz del repositorio queda público (por ejemplo, este README).

## Funcionalidades del landing

- Hero con texto rotativo animado
- Secciones: Funcionalidades, Cuotas y Cobros, Gas, Visitas, Planes, Testimonios
- Toggle de facturación mensual/anual (−15%)
- Formulario de contacto con webhook a Make (sin exponer emails)
- Widget flotante de WhatsApp e Instagram
- Menú hamburger responsivo
- Modal "Próximamente" en botones de login/registro

## Contacto

- Instagram: [@kondominia](https://instagram.com/kondominia)
- WhatsApp: +1 809 224 4502

## Migración SEO (WordPress → esta landing)

Hoy `www.kondominia.com` es un WordPress (Apache) con ~32 artículos de blog que traen
el tráfico orgánico. Para cambiar a esta landing sin perder posicionamiento:

1. **Blog a subdominio.** Servir el mismo WordPress en `blog.kondominia.com`, con las
   mismas rutas (Ajustes → Generales: URL del sitio). Portada del blog = lista de entradas.
2. **Redirecciones 301.** `_redirects` envía cada URL antigua (entradas, categorías,
   páginas legales, `/contacto/`, `/wp-admin`, `/wp-content`) a su destino nuevo. Si se
   publica un artículo nuevo antes del cambio, añadir su ruta. `/politica-de-seguridad/`
   no se redirige: la sirve esta landing.
3. **Dominio canónico:** `https://www.kondominia.com/` (el apex redirige a `www`).
4. **Search Console:** verificar `www.kondominia.com` y `blog.kondominia.com`, enviar
   `sitemap.xml` y `blog.kondominia.com/wp-sitemap.xml`, y vigilar «Páginas» y 404
   durante 2–3 meses. No apagar el servidor WordPress.
5. **DNS** (está en DigitalOcean): cambiar solo el CNAME `www` hacia `<proyecto>.pages.dev`
   (bajar antes el TTL a 300). `kondominia.com`, `blog`, `app` y el correo no cambian.

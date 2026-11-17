# Kondominia — Landing Page

Landing page pública de [Kondominia](https://www.kondominia.com), plataforma de gestión condominial para administradoras y juntas de condóminos en República Dominicana.

## Stack

- HTML estático, sin paso de build
- [Tailwind CSS](https://tailwindcss.com) vía CDN
- Google Fonts (Inter para texto, Quicksand para títulos)
- JavaScript vanilla

## Estructura

```
public/                            # Lo que se publica (nada fuera de aquí es público)
  index.html                       # Página principal (todo en un solo archivo)
  politica-de-seguridad/           # Política de seguridad (requisito del procesador de pagos)
  blog/, <artículo>/               # Blog estático (generado, ver «Blog»)
  wp-content/uploads/              # Imágenes de los artículos, en sus rutas originales
  img/pagos/                       # Logos de Visa, Mastercard, Visa Secure y Mastercard ID Check
  kondominia-1-2.png               # Logo horizontal
  kondominia-5-3.png               # Isotipo
  _redirects                       # 301 de las URLs del WordPress anterior
  _headers                         # noindex en la URL de prueba de Cloudflare
  robots.txt, sitemap.xml          # SEO
wrangler.jsonc                     # Configuración de Cloudflare
tools/blog/                        # Generador del blog y copia de los artículos del WordPress
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
la URL de prueba de Cloudflare también llegan a Make.

## Google Analytics

GA4, propiedad «Kondominia - GA4», ID `G-XWS9X8P621` (el mismo flujo web que usaba el
WordPress, así se conserva el historial). Solo se carga en `kondominia.com`; en la URL de
prueba los eventos quedan en `dataLayer` sin enviarse. Eventos propios:

| Evento | Cuándo | Parámetros |
|---|---|---|
| `generate_lead` | Formulario de contacto enviado | `form_name`, `units_range` |
| `sign_up_click` | Clic en «Prueba gratis» | `link_location` |
| `login_click` | Clic en «Iniciar sesión» | `link_location` |
| `whatsapp_click` / `instagram_click` | Clic en WhatsApp o Instagram | `link_location` |
| `open_contact_modal` | Se abre «Hablar con ventas» | — |
| `pricing_calculator_use` | Primer uso de la calculadora | `units` |

## Publicación (Cloudflare)

Se publica en Cloudflare como Worker con archivos estáticos (la versión actual de
Cloudflare Pages). Proyecto `kondominia-landing` en la cuenta de Kondominia.

- URL de prueba: https://kondominia-landing.jfebles.workers.dev (marcada `noindex`).
- Publicar desde la raíz del repositorio: `npx wrangler deploy`
  (la primera vez, `npx wrangler login`). Solo se sube la carpeta `public/`.
- `preview_urls` está desactivado: no quedan URLs públicas de versiones anteriores.
- Gratis en el plan Workers Free (las peticiones a archivos estáticos no se cobran).

Dominio: en Cloudflare, Workers & Pages → `kondominia-landing` → Settings → Domains &
Routes → Custom domain `www.kondominia.com`. Para un dominio propio en un Worker, la zona
DNS tiene que estar en Cloudflare; hoy el DNS está en DigitalOcean (ver «Migración SEO»).

## Contacto

- Instagram: [@kondominia](https://instagram.com/kondominia)
- WhatsApp: +1 809 224 4502

## Blog

Los 32 artículos del WordPress anterior se sirven como páginas estáticas en **las mismas
rutas** (`www.kondominia.com/<artículo>/`), así que no necesitan redirecciones. Índice en `/blog/`.

- Fuente: `tools/blog/data/posts.json` (copia exportada del WordPress el 16/11/2026).
- Regenerar después de cambiar la plantilla o un artículo: `python3 tools/blog/build.py`.
  Reescribe `public/<artículo>/`, `public/blog/`, el bloque «blog» de `_redirects` y `sitemap.xml`.
- `--fetch` vuelve a descargar artículos e imágenes del WordPress (solo mientras exista).
- Artículo nuevo: añadirlo a `posts.json` (mismos campos) y regenerar.

## Migración SEO (WordPress → esta landing)

Ver `LANZAMIENTO.md` (cambio previsto el 15/12/2026). Las rutas de los artículos no cambian; las
categorías, `/feed/` y `/blog-kondominia/` redirigen a `/blog/`; las páginas legales, a la app.
Después del cambio: Search Console (enviar `sitemap.xml`, vigilar «Páginas» y 404 unos meses).

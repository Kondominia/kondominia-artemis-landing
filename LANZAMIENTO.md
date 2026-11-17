# Lanzamiento de la nueva landing — 15 de diciembre de 2026

Objetivo: `www.kondominia.com` sirve esta landing **y el blog** desde Cloudflare. Los 32 artículos
del WordPress ya están convertidos a páginas estáticas en sus mismas rutas (decisión de Joan,
16/11: opción B), así que no hace falta `blog.kondominia.com` ni redirigir artículos. El servidor
del WordPress se apaga unas semanas después del cambio.

## Estado de partida (16/11/2026)

| Nombre | Hoy | Después del lanzamiento |
|---|---|---|
| `kondominia.com` | A `162.243.229.14` (WordPress, CentOS/Apache/PHP 7.2) | Worker de la landing → 301 a `www` |
| `www` | CNAME `kondominia.com` | Worker `kondominia-landing` |
| `app` | A `45.55.123.125` | igual, **solo DNS** (Caddy emite su certificado) |
| `stg-app`, `stg-mcp` | A `167.172.138.35` | igual, solo DNS |
| `stg` | A `162.243.253.34` (no responde) | revisar si se elimina |
| MX | Google Workspace (5 registros) | igual |
| TXT | SPF Google, `google-site-verification`, DKIM `google._domainkey`, DMARC | igual |
| CNAME Mailtrap | `mt41`, `rwmt1/2._domainkey`, `mt-link` | igual, solo DNS |

DNS en DigitalOcean (`ns1-3.digitalocean.com`); registrador GoDaddy (dominio vence 14/03/2028).
**DNSSEC desactivado** (no hay que tocar nada en GoDaddy antes de cambiar los nameservers) y sin
registros CAA. La lista solo incluye lo visible desde fuera: **exportar la zona completa desde
DigitalOcean antes de mover nada.** Borrador para importar: [`dns/kondominia.com.zone`](dns/kondominia.com.zone).

Exportación de DigitalOcean (17/11): [`dns/digitalocean-export-2026-11-17.zone`](dns/digitalocean-export-2026-11-17.zone).
Además de lo de arriba trae 4 registros de **Mailtrap** (correo transaccional de la app):
`mt41`, `rwmt1._domainkey`, `rwmt2._domainkey` y `mt-link`, todos CNAME. Ya están en el borrador
y tienen que quedar en «DNS only»: si fallan, los correos de la app caen en spam.

## Calendario

### Semana 1 — 16 a 22 nov: decisiones y contenido (nada de esto afecta a la web actual)
- [x] Inventario de URLs del WordPress (17/11). Su sitemap está roto (devuelve la portada), así
      que se sacaron por la API: 32 artículos, 6 páginas, 3 categorías, 16 etiquetas, 4 autores.
      Añadidas redirecciones para `/tag/*`, `/author/*`, `/page/*`, `/blog-kondominia/page/*`,
      `/comments/feed/`, `/<artículo>/feed/`, `/favicon.ico` y `/sitemap_index.xml`; probadas en la
      URL de prueba.
- [x] Borrador de la zona para Cloudflare (`dns/kondominia.com.zone`, todo «DNS only»).
- [x] Exportar la zona DNS de DigitalOcean (17/11) y cotejarla con el borrador: 19 registros iguales.
- [ ] Cloudflare → Add a site → `kondominia.com` (Free) e importar la zona. **Sin cambiar los
      nameservers**, la zona queda «Pending» y no recibe tráfico: se puede dejar lista ya.
- [ ] Copia del servidor del WordPress (snapshot en DigitalOcean): de 128 imágenes de la
      biblioteca, 63 no se usan en ningún artículo y no se copiaron a la landing.
- [ ] Confirmar quién tiene acceso a GoDaddy (cambio de nameservers) y SSH al servidor del WordPress.
- [ ] Contenido: nombres reales de condominios (con permiso), cifras del hero
      («+20 administradoras · +3,000 unidades»), razón social del pie, MCP «Próximamente».
- [ ] Decidir si la versión en inglés entra el 15/12 o después.

### Semana 2 — 23 a 29 nov: mover el DNS a Cloudflare (sin cambio visible)
- [ ] Revisar que la zona de Cloudflare sigue idéntica a DigitalOcean y todo en **DNS only**.
- [ ] Bajar el TTL en DigitalOcean a 300 un día antes.
- [ ] Cambiar los nameservers en GoDaddy a los de Cloudflare.
- [ ] Verificar: web actual, `app`, `stg-app`, correo (enviar y recibir), correos de la app.
- [ ] Search Console: propiedad de dominio verificada por DNS.

### Semana 3 — 30 nov a 6 dic: contenido final
- [x] Blog estático en la URL de prueba (16/11): 32 artículos, `/blog/`, imágenes en sus rutas.
- [ ] Revisar los artículos y decidir si se retiran los muy antiguos o de temporada (p. ej. COVID).
- [ ] Merge del PR #1 de la landing; contenido final desplegado en la URL de prueba.

### Semana 4 — 7 a 14 dic: congelación y pruebas
- [ ] Probar `_redirects` contra la URL de prueba (16/11: 32 artículos 200, 32 variantes sin «/» 301,
      93 imágenes 200, categorías/feed/legales/wp-admin 301). Repetir tras cualquier cambio.
- [ ] Formularios → Make (con «PRUEBA» en el nombre) y escenario con los campos nuevos.
- [ ] Revisión en móvil y escritorio; Lighthouse; enlaces del pie.
- [ ] Plan de vuelta atrás ensayado (abajo).

### 15 dic — cambio
1. Worker `kondominia-landing` → Custom domains: `www.kondominia.com` y `kondominia.com`
   (Cloudflare sustituye los registros de esos nombres). Regla de redirección en la zona
   (Rules → Redirect Rules): `kondominia.com/*` → `https://www.kondominia.com/${1}`, 301.
2. Comprobar: `www` sirve la landing, el apex redirige a `www`, los artículos responden 200 en su
   ruta, categorías y `/feed/` van a `/blog/`, `app` y correo intactos, GA → Tiempo real.
3. Search Console: enviar `sitemap.xml`; vigilar «Páginas» y 404 durante 2–3 meses. Mantener
   el servidor del WordPress encendido (sin DNS) unas semanas por si hay que volver atrás.

## Vuelta atrás
Quitar los custom domains del Worker y volver a crear `kondominia.com` A `162.243.229.14` y
`www` CNAME `kondominia.com` (el WordPress sigue igual en su servidor). Con el DNS
en Cloudflare el cambio es inmediato.

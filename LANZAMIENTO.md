# Lanzamiento de la nueva landing — 15 de diciembre de 2026

Objetivo: `www.kondominia.com` sirve esta landing (Cloudflare), el WordPress pasa a
`blog.kondominia.com` con las mismas rutas, y el tráfico orgánico se conserva con 301.

## Estado de partida (16/11/2026)

| Nombre | Hoy | Después del lanzamiento |
|---|---|---|
| `kondominia.com` | A `162.243.229.14` (WordPress, CentOS/Apache/PHP 7.2) | Worker de la landing → 301 a `www` |
| `www` | CNAME `kondominia.com` | Worker `kondominia-landing` |
| `blog` | no existe | A `162.243.229.14`, proxy de Cloudflare (SSL en el borde) |
| `app` | A `45.55.123.125` | igual, **solo DNS** (Caddy emite su certificado) |
| `stg-app`, `stg-mcp` | A `167.172.138.35` | igual, solo DNS |
| `stg` | A `162.243.253.34` (no responde) | revisar si se elimina |
| MX | Google Workspace (5 registros) | igual |
| TXT | SPF Google, `google-site-verification`, DKIM `google._domainkey`, DMARC | igual |

DNS en DigitalOcean (`ns1-3.digitalocean.com`); registrador GoDaddy. La lista solo incluye lo
visible desde fuera: **exportar la zona completa desde DigitalOcean antes de mover nada.**

## Calendario

### Semana 1 — 16 a 22 nov: decisiones y contenido
- [ ] Exportar la zona DNS de DigitalOcean (Networking → Domains → kondominia.com).
- [ ] Confirmar quién tiene acceso a GoDaddy (cambio de nameservers) y SSH al servidor del WordPress.
- [ ] Contenido: nombres reales de condominios (con permiso), cifras del hero
      («+20 administradoras · +3,000 unidades»), razón social del pie, MCP «Próximamente».
- [ ] Decidir si la versión en inglés entra el 15/12 o después.

### Semana 2 — 23 a 29 nov: mover el DNS a Cloudflare (sin cambio visible)
- [ ] Cloudflare → Add a site → `kondominia.com` (plan Free). Comparar el escaneo con la exportación.
- [ ] Todos los registros en **DNS only** (nube gris), idénticos a DigitalOcean.
- [ ] Bajar el TTL en DigitalOcean a 300 un día antes.
- [ ] Cambiar los nameservers en GoDaddy a los de Cloudflare.
- [ ] Verificar: web actual, `app`, `stg-app`, correo (enviar y recibir), correos de la app.
- [ ] Search Console: propiedad de dominio verificada por DNS.

### Semana 3 — 30 nov a 6 dic: blog y vista previa
- [ ] `blog.kondominia.com` → `162.243.229.14` con proxy de Cloudflare; SSL «Full» (vale el
      certificado actual del servidor). En Apache, `ServerAlias blog.kondominia.com`.
- [ ] Probar las 32 entradas en `blog.` **antes** de cambiar la URL del sitio en WordPress
      (con un plugin o `wp-config.php` que respete el host, para no romper `www` mientras tanto).
- [ ] Merge del PR #1 de la landing; contenido final desplegado en la URL de prueba.

### Semana 4 — 7 a 14 dic: congelación y pruebas
- [ ] Probar las 94 reglas de `_redirects` contra la URL de prueba (script de comprobación).
- [ ] Formularios → Make (con «PRUEBA» en el nombre) y escenario con los campos nuevos.
- [ ] Revisión en móvil y escritorio; Lighthouse; enlaces del pie.
- [ ] Plan de vuelta atrás ensayado (abajo).

### 15 dic — cambio
1. WordPress: URL del sitio → `https://blog.kondominia.com`.
2. Worker `kondominia-landing` → Custom domains: `www.kondominia.com` y `kondominia.com`
   (Cloudflare sustituye los registros de esos nombres).
3. Comprobar: `www` sirve la landing, el apex redirige a `www`, una muestra de URLs antiguas
   devuelve 301 a `blog.`, `app` y correo intactos, GA → Tiempo real recibe visitas.
4. Search Console: enviar `sitemap.xml` y `blog.kondominia.com/wp-sitemap.xml`; vigilar
   «Páginas» y 404 durante 2–3 meses. No apagar el servidor del WordPress.

## Vuelta atrás
Quitar los custom domains del Worker y volver a crear `kondominia.com` A `162.243.229.14` y
`www` CNAME `kondominia.com`, con la URL del sitio de WordPress de nuevo en `www`. Con el DNS
en Cloudflare el cambio es inmediato.

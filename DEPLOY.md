# Despliegue de CONECTA en hosting gratis (Railway, prueba)

**Lee esto antes de crear cuentas: no es gratis para siempre.**
La información de precios cambia y las fuentes secundarias consultadas
el 2026-10-29 no coinciden en todos los detalles. Verifica la página
oficial de precios de Railway antes de crear la cuenta.

Lo que indican esas fuentes (a verificar en railway.com/pricing):
- Prueba: 5 USD de crédito por única vez, 30 días, sin tarjeta.
- Después de la prueba: plan Free de 0 USD con 1 USD de crédito al mes.
- Un bot pequeño corriendo 24/7 consume más de 1 USD al mes en
  memoria/CPU según esas mismas fuentes, así que el plan Free
  probablemente NO alcance para un mes completo siempre encendido.
- Hobby cuesta 5 USD/mes y requiere tarjeta, y Richard no puede
  pagar en línea desde Cuba. Conclusión honesta: Railway sirve
  para probar el bot en real durante la prueba, no es todavía
  una solución permanente gratis. Si el bot despega, habrá que
  buscar otra vía (un servidor de alguien de confianza, un VPS
  que se pueda pagar por otra vía, o una arquitectura webhook
  en un servicio serverless) antes de que se acabe el crédito.

Por qué no Render gratis para este bot: el servicio gratis de
Render se duerme tras 15 minutos sin tráfico web, y los workers
de fondo no tienen instancia gratis (la más barata ronda 7 USD/mes
según esas fuentes). Nuestro bot usa polling (espera mensajes
constantemente), no una web que se despierte con visitas, así
que Render gratis lo dejaría dormido justo cuando alguien le escriba.

## Qué necesitas antes de desplegar
1. El código de CONECTA en un repositorio de GitHub (ver "Subir el código").
2. Una cuenta en Railway (puede entrar con GitHub).
3. El token NUEVO del bot (el que sacaste con /revoke). NO lo pegues
   en ningún chat. Lo escribirás tú mismo en el panel de variables
   de Railway.

## Subir el código a GitHub (pendiente de decidir cómo)
Opción A (recomendada si tu sesión de GitHub sigue viva en el
navegador): autorizas a Muse a crear el repositorio `conecta-bot`
en tu GitHub y subir estos archivos. Muse no cierra ventanas.
Opción B: descargas el ZIP del proyecto, lo descomprimes y subes
los archivos a un repositorio nuevo desde la web de GitHub
(Add file > Upload files). Desde el teléfono es más lento, pero
no requiere darle acceso a Muse a tu GitHub.

Archivos que deben ir al repo (sin `.env` y sin `*.db`):
`conecta/`, `locales/`, `tests/`, `requirements.txt`,
`Procfile`, `railway.json`, `.gitignore`, `README.md`, `DEPLOY.md`.

## Pasos en Railway (una vez el código esté en GitHub)
1. Entra a railway.app y crea cuenta con GitHub.
2. New Project > Deploy from GitHub repo > elige `conecta-bot`.
3. En el servicio, abre Variables y añade:
   - `BOT_TOKEN` = tu token nuevo (lo escribes tú en ese panel)
   - `ADMIN_IDS` = tu ID de Telegram (lo ves con @userinfobot)
   - `DATABASE_PATH` = `conecta.db`
4. Start Command (si Railway lo pide): `python -m conecta.bot`
5. Deploy. En los logs debe aparecer el bot arrancando sin
   errores de token. Si dice que falta `BOT_TOKEN`, revisa el
   paso 3: el nombre de la variable debe ser exacto.
6. Prueba desde Telegram: abre @ConectaCitasBot, pulsa Start,
   elige idioma y crea un perfil de prueba.

## Límites de este MVP en hosting gratis
- Base SQLite en `conecta.db`: los datos viven en el disco del
  contenedor y se pueden perder en un redespliegue o reinicio.
  Para producción hace falta Postgres (Fase 4), no SQLite.
- El bot se reinicia si el servicio se cae; Railway lo vuelve
  a levantar según la política de reinicio de `railway.json`.
- No pongas datos reales sensibles en la prueba: usa cuentas
  de prueba y perfiles de prueba, no personas reales todavía.

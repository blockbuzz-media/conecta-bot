# CONECTA — Bot internacional de citas para Telegram

**Estado real, sin inflar:** MVP funcional de la Fase 3 (bot). No está publicado,
no está conectado a Telegram todavía y no tiene pagos. Lo que falta para
publicarlo depende de una acción del propietario (crear el bot en @BotFather),
explicada abajo en "Puesta en marcha".

## Qué hace este MVP (verificado con pruebas, ver `tests/`)
- Primera pantalla: **solo selector de idioma** (Español, English, Português,
  Italiano). Después todo sale en el idioma elegido, que queda guardado.
- Cambio de idioma en cualquier momento con `/idioma`.
- Registro guiado, una pregunta por paso: 18+, nombre visible, usuario propio
  de la plataforma, edad, género, qué busca, tipo de relación, país/ciudad
  opcionales, idiomas, intereses, bio, foto y rango de edad deseado.
- Vista previa del perfil antes de publicarlo.
- Descubrimiento por tarjetas: foto, nombre, edad, bio corta, idiomas e
  intereses. Botones: Me gusta, Pasar, Reportar, Bloquear.
- Filtros respetados en ambos sentidos: edad y género buscado. No se repiten
  perfiles descartados ni se muestran bloqueados o inactivos.
- Match solo cuando el like es mutuo. Aviso a ambos en su idioma.
- Chat **por relevo del bot con identificadores internos**: nadie ve el
  número de teléfono ni el usuario personal de Telegram del otro.
  MVP: solo texto. Las fotos en el chat todavía no están (ver "No hecho").
- Límite gratuito: 20 Me gusta al día.
- Reportar, bloquear, pausar (`/pausar`), borrar cuenta (`/eliminar`).
- Estados de perfil: borrador, activo, pausado, suspendido, eliminado.
  La revisión manual ("pendiente de revisión") es una tarea del admin en
  la Fase 4; en este MVP el perfil pasa de borrador a activo al publicarlo
  y el admin puede suspenderlo después.
- Panel admin mínimo: `/admin` (solo para los IDs en `ADMIN_IDS`) muestra
  usuarios, activos, matches, reportes y mensajes. No es el panel completo
  de la Fase 4.

## Qué NO hace todavía (para no vender humo)
- No hay Mini App visual (el MVP es bot conversacional; la Mini App es
  una mejora posterior, no un botón falso).
- No hay pagos, suscripciones Premium ni créditos. El botón Premium
  responde honestamente que aún no está disponible. Nunca se desbloquea
  nada pulsando un botón.
- No hay traducción automática de mensajes, modo viaje, impulsos,
  deshacer descarte, ni estadísticas de perfil. Son Fase 5-6.
- No hay verificación de identidad ni revisión automática de imágenes.
  La edad se declara en el registro y se exige 18+; la verificación
  razonable es trabajo de la Fase 4.
- No hay cuentas de prueba presentadas como personas reales. Los tests
  usan datos ficticios claramente de prueba, solo en la base de pruebas.

## Arquitectura
```
Telegram (usuario Android)
  └─ Bot API ──► bot.py (aiogram 3, FSM, handlers)
                    ├─ i18n.py ──► locales/*.json (es, en, pt, it)
                    ├─ db.py ────► SQLite (MVP) / PostgreSQL (producción, por env)
                    ├─ matching.py (compatibilidad edad/género, filtros)
                    └─ config.py (solo variables de entorno, nunca secretos en código)
Fotos: se guardan como file_id de Telegram, no como blobs en la base.
Chat: mensajes de texto con remitente interno; el bot los reenvía al otro
usuario del match. Si se usa Telegram para transportar mensajes, la
limitación es que Telegram conoce los Telegram IDs de ambos (es su
plataforma); CONECTA no revela entre usuarios el teléfono ni el @ personal.
```

## Requisitos verificables (checklist)
- [x] Selector de idioma primero y persistencia del idioma.
- [x] Registro guiado y validación 18+.
- [x] Vista previa antes de publicar.
- [x] Filtros de edad y género en ambos sentidos.
- [x] No repetir descartados; excluir bloqueados e inactivos.
- [x] Match solo mutuo; aviso en el idioma de cada uno.
- [x] Chat solo entre matches y no bloqueados; sin revelar contacto personal.
- [x] Límite diario de Me gusta.
- [x] Reportar, bloquear, pausar, eliminar cuenta.
- [x] Pruebas del núcleo ejecutadas (ver abajo).
- [ ] Bot creado en @BotFather y token en entorno (propietario).
- [ ] Prueba real con 2 teléfonos Android en Telegram (propietario + pruebas).
- [ ] Fase 4: moderación, apelaciones, panel completo.
- [ ] Fase 5: pagos con Telegram Stars (investigar reglas vigentes antes).
- [ ] Fase 6: Mini App, traducción de mensajes, estadísticas.

## Puesta en marcha (lo que debe hacer el propietario)
1. En Telegram, abre @BotFather → `/newbot` → elige nombre y usuario
   (por ejemplo `ConectaCitasBot`). Guarda el token que te da.
2. En el servidor o PC donde correrá el bot, copia `.env.example` a `.env`
   y pon `BOT_TOKEN=el_token_de_BotFather` y `ADMIN_IDS=tu_id_de_Telegram`
   (tu ID lo ves con @userinfobot). Nunca pegues el token en un chat.
3. Instala dependencias y arranca:
   ```
   pip install -r requirements.txt
   python -m conecta.bot
   ```
4. En Telegram busca tu bot, pulsa Start y prueba: idioma → registro →
   `/descubrir` con una segunda cuenta de prueba.
5. Sin token no hay bot en línea: el código no puede conectarse solo.

## Pruebas
Pruebas del núcleo (sin Telegram, sin token, sin red):
```
python -m unittest discover -s tests -v
```
Resultado en esta entrega: 11 pruebas, todas superadas (ver
`tests/test_core.py`). Las pruebas de red, Android real y pagos NO se han
ejecutado y no se declaran superadas.

## Presupuesto estimado (estimación, no precio garantizado)
| Concepto | MVP | Si crece |
|---|---|---|
| BotFather / Telegram Bot API | 0 USD/mes | 0 USD/mes |
| Hosting plan gratis (Railway/Render, con sus límites) | 0 USD/mes | ~5-20 USD/mes |
| Base de datos (SQLite local / Postgres plan gratis) | 0 USD | ~0-15 USD/mes |
| Fotos (file_id de Telegram, sin S3 en MVP) | 0 USD | según almacenamiento si se migra |
| Dominio | no necesario en MVP | ~10-15 USD/año si se quiere web |
| Telegram Stars / pagos | no implementado | comisión según reglas vigentes de Telegram al implementar |
**Total MVP: 0 USD/mes** en plan gratis, aceptando sus límites (el plan
gratis puede dormirse o limitar horas). Antes de pagar nada, verifica los
límites y precios vigentes del proveedor que elijas, porque cambian.

## Estructura
```
conecta/
  README.md  requirements.txt  .env.example  .gitignore
  locales/es.json  locales/en.json  locales/pt.json  locales/it.json
  conecta/config.py  conecta/db.py  conecta/i18n.py
  conecta/matching.py  conecta/bot.py
  tests/test_core.py
```

## Seguridad y privacidad (MVP)
- Sin teléfono, sin @ personal de Telegram y sin GPS exacto en perfiles.
- Orientación y preferencias íntimas: no se publican en la tarjeta; solo
  se usan para filtrar.
- El admin no lee chats desde `/admin` (solo contadores). Leer un chat
  requeriría un procedimiento documentado y justificado (Fase 4).
- Borrado: la cuenta pasa a "eliminado", se limpian bio, foto e intereses.

# YomaTV Web

**Estado del fuente:** YomaTV publicada el 25 de octubre de 2026, versión web `yomatv-20261025-2`. [Identidad, aplicaciones y publicación automática](YOMATV-2026-10-25.md).

Aplicación PHP + MySQL publicada en **https://hk-br035.gt.tc/seasonav1/**. La portada es el catálogo completo: **4.485 títulos** obtenidos del HTML público de AnimeAV1, sin su API oficial. **Temporada** conserva el horario de 64 animes como sección secundaria. Los capítulos de cada anime se consultan al abrir su ficha. La página anterior del dominio se conserva.

## Entrega 1 de 4 — 17 de octubre de 2026

La hoja de ruta completa está en **PLAN-4-ENTREGAS.md**. Las entregas 1–4 están publicadas. La entrega 4 incorpora infraestructura, seguridad y mantenimiento; su estado de verificación y publicación aparece al final de este documento.

- **Identidad MAL:** el último ID autorizado se conserva al desconectar. Conectar una cuenta distinta renueva su caché, relaciones y sincronización, y detiene los envíos de la anterior. La biblioteca web, notas, favoritos, vistos y archivos se conservan. Un editor o reproductor abierto con otra cuenta ya no puede escribir usando la conexión nueva. Al actualizar una instalación anterior, los pendientes con una cuenta identificable se atribuyen a ella; los antiguos sin propietario verificable se detienen y explican que hay que abrir el capítulo de nuevo. No se atribuyen silenciosamente a una cuenta nueva.
- **Retirar de MAL:** cancela los envíos del anime y espera si una escritura ya está en curso. Los reintentos antiguos no lo recrean. La retirada bloquea su envío automático hasta volver a añadirlo expresamente con «Guardar en MyAnimeList».
- **Progreso pendiente:** conserva el capítulo más avanzado también cuando falta conexión o vínculo. Ver el 8 y después el 2 sin conexión mantiene pendiente el 8.
- **Colas grandes:** la carga inicial incluye todos los trabajos activos y los últimos 80 terminados. Los resúmenes y contadores salen del historial completo. Al abrir un anime, su historial se recupera mediante páginas privadas de hasta 200 registros y se muestra en páginas de 36 capítulos. Al cambiar de anime se descarta historial cargado que ya no hace falta. No existe el corte anterior de 2.000 registros en la interfaz; el límite por lote de envío sigue siendo 2.000 capítulos. Los clientes anteriores que piden la respuesta completa conservan ese formato.
- **Interfaz:** la última búsqueda de MAL gana aunque las respuestas lleguen desordenadas; se conserva su foco. Cerrar, sustituir o abandonar un diálogo invalida las respuestas que podrían reabrirlo. Los borradores de ficha se conservan al cambiar favorito y están separados por usuario. Un fallo al guardar visto muestra error/reintento, no «Guardando…» indefinidamente.
- **PC:** emparejar u olvidar un equipo invalida la marca anterior de preferencias. Una respuesta del emparejamiento anterior no puede confirmar la aplicación de preferencias en el nuevo.
- **Bibliotecas grandes:** el JSON sigue siendo compatible. La web valida la copia antes de comenzar, admite archivos de hasta 128 MB y los importa en bloques ordenados de hasta 1 MiB, manteniendo el límite de 12 MiB por petición del servidor. Si se interrumpe, conserva lo ya aplicado y permite reintentar o seleccionar la copia otra vez; combinar los mismos registros no crea duplicados. Cada bloque se confirma en una transacción propia. La exportación comprueba que el JSON pueda restaurarse con este mecanismo.
- **Mantenimiento:** el error de una ficha no detiene a las siguientes. Tiene espera progresiva por anime, cinco intentos antes de apartarlo y un botón administrador para reintentar los apartados. El panel distingue la actualización del horario de la finalización de sus fichas. Las consultas periódicas de una página administradora visible retoman sus pendientes; no se añade un proceso permanente al hosting.

Pruebas nuevas: `test_reliability_http.py`, `test_reliability_ui.js`, `test_reliability_upgrade.php` y `test_maintenance_rotation.php`: **24 grupos de comprobación**, más las regresiones de cuentas, cola, MAL, progreso automático, filtros/rutas, reproductor y esquema. Casos principales: 2.001 trabajos activos, 4.000 registros de un anime, copia Unicode de más de 13 MB restaurada en 16 bloques, cambios de cuenta con pendientes y respuestas tardías. Usan SQLite, proveedores ficticios o simulaciones de JavaScript; no modifican una lista MAL real ni el ejecutable del usuario. Las comprobaciones en Brave dependen de disponer de acceso al navegador.

## Primera fase de correcciones — 14 de octubre de 2026

- Biblioteca, vistos, preferencias, preparación, exportación y confirmación usan respuestas parciales. La página combina los cambios por anime/solicitud, conserva los demás trabajos e ignora respuestas atrasadas o de otra cuenta. Los clientes anteriores sin `X-Season-Response: patch` siguen recibiendo el formato original. El estado completo queda para la carga inicial y los cambios de sesión.
- Las peticiones a AnimeAV1 desde el alojamiento requieren una cuenta administradora y POST con CSRF. Esto incluye listados y servidores, además de los botones de actualización. Las consultas GET leen datos guardados; al abrir una ficha incompleta, el cliente administrador puede actualizarla con un POST. Los demás usuarios consultan los capítulos almacenados. Hay límites por administrador, por sitio y entre peticiones.
- Los iconos PNG de 32, 180 y 192 px suman aproximadamente 32 KB. Se conserva la mascota; los iconos grandes anteriores dejaron de ser recursos de la interfaz.
- Los ejemplos de configuración usan valores ficticios. `config.local.php` y `access.local.php` son privados y están excluidos del ZIP de fuente.
- **Mi cuenta** permite cambiar contraseña, generar/renovar diez códigos de recuperación, exportar/importar la biblioteca y eliminar una cuenta normal. Cambiar o recuperar la contraseña cierra las otras sesiones. La cuenta administradora está protegida frente al borrado.
- PHP está separado en autenticación, catálogo, preferencias, biblioteca, transferencias, cola, sincronización y estado. JavaScript separa cuenta, transporte de estado, biblioteca y puente de la cola. Los módulos están formateados para lectura.

**Configura la recuperación antes de necesitarla:** la entrega 4 ofrece diez códigos al registrarte. En cuentas anteriores, abre Mi cuenta, confirma tu contraseña y genera diez códigos. Descarga el TXT o guárdalos por tu cuenta. Solo se muestran una vez; el servidor guarda sus hashes y cada código se consume al usarlo. Renovarlos invalida los anteriores. En el acceso, **Olvidé mi contraseña** pide correo, código y contraseña nueva. No envía correos.

La biblioteca JSON incluye estados, favoritos, exclusiones, puntuaciones, notas y capítulos vistos. Importar combina con la colección actual y aplica los valores del archivo a animes coincidentes. Los registros desconocidos se notifican y no se inventan capítulos ni se lanza scraping. Cada petición admite hasta 12 MiB, 5.000 animes y 50.000 capítulos vistos; la interfaz divide las copias grandes en bloques y admite archivos de hasta 128 MB. La exportación no contiene contraseñas, códigos de recuperación ni datos del puente.

Las cuentas administradoras existentes se seleccionan mediante `private/access.local.php`, siguiendo `access.example.php`. Los correos reservados no pueden obtener privilegios registrándose de nuevo. La configuración del propietario se conserva en el archivo privado del servidor y no entra al paquete compartible. El publicador nuevo no cambia administradores ni admite sobrescrituras parciales. No se crea ninguna cuenta automáticamente.

Pruebas de esta fase: `test_hardening.py`, `test_schema_upgrade.py` y `test_state_client.js`, junto con las regresiones anteriores. La prueba con 2.000 trabajos confirmó una reducción del 99,8 % al marcar un favorito. Los fixtures son bases SQLite aisladas; no se trasladan al alojamiento ni se descargan videos. Las peticiones al puente se dividen en lotes de hasta 2.000 IDs cuando el cliente acumula más trabajos.

La limpieza del 13 de octubre de 2026 retiró las bases SQLite de prueba, cachés HTML, previews anteriores y respaldos repetidos. Las pruebas, el generador del catálogo/radio y el fuente publicado se conservan. Las capturas y evidencias antiguas citadas aquí están archivadas en `../_archivo/codigo-anterior-2026-10-13.zip`. `verification/package_final.py` genera el ZIP de fuente desde los archivos actuales, sin depender de estados ni tokens de pruebas anteriores.

## Usarla

1. Abre la web y crea tu cuenta. Esa cuenta es independiente de las credenciales MySQL del alojamiento.
   Si todavía no tienes la aplicación, pulsa **Descargar .exe** en la portada, el módulo «Cómo funciona» o el diálogo de conexión: abre el [enlace de YomaTV en GitHub Releases](https://github.com/EduardoGPT4/YomaTV/releases) proporcionado por el propietario.
2. Explora **Catálogo completo**, busca un título, filtra su formato y ordena por nombre o incorporación. Pulsa **Seguir** o la estrella. En cada ficha puedes marcar capítulos vistos, guardar notas, puntuar y excluir un anime de las descargas. **Temporada** permite consultar el horario semanal.
3. Pulsa **Preparar** para añadir el último capítulo, o abre una ficha y elige capítulos/todos los disponibles. No se crean solicitudes duplicadas para el mismo capítulo e idioma.
4. Empareja una vez: en el YomaTV.exe actualizado pulsa **Conectar web**, copia el código y pégalo en **Conectar YomaTV** de la página. Permite el acceso a la red local si el navegador lo solicita. Usa la web en ese mismo equipo y mantén la aplicación en la bandeja.
5. **Preparar**, **Preparar todos** y **Preparar seleccionados** envían automáticamente esos capítulos al programa y reanudan su cola. **Enviar a la PC** transmite la cola pendiente completa del idioma elegido. Se incorporan las preferencias conservando videos, parciales y carpeta de destino. Las exclusiones tienen prioridad. Un capítulo añadido manualmente se descarga aunque no sea favorito; la selección de favoritos limita las revisiones automáticas.
6. El indicador superior muestra **App conectada**, **No detectada** o **Sin emparejar**. Mientras la página esté visible, actualiza el estado cada 3 segundos con trabajos pendientes y cada 15 segundos en reposo. Muestra cola, porcentaje, verificación, pausa, errores y capítulos descargados. Los archivos completados se confirman automáticamente mediante sus recibos verificados. Al volver a abrir la página se recuperan las confirmaciones pendientes.

**Cola para la PC** agrupa las solicitudes por anime: una fila con portada, cantidad descargada y estado. Al abrirla aparecen sus capítulos en orden numérico, con filtros por estado y páginas de 36. **Enviar pendientes de este anime** limita el envío a esa serie; **Ver ficha y preparar capítulos** abre su listado completo. Las confirmaciones se actualizan sin perder la página que estás consultando.

En la ficha, los capítulos **Descargados** aparecen en verde y su selección está bloqueada. Los capítulos ya preparados o en descarga tampoco se seleccionan otra vez; los fallidos y las solicitudes retiradas permiten reintentar. **Preparar todos** incluye únicamente los elegibles. El registro corresponde a la cuenta y al idioma elegido y no marca automáticamente los capítulos como vistos. Si borras un video del disco, el registro web conserva la confirmación de su descarga.

**Alternativa sin conexión directa:** si la app está cerrada, no está emparejada o el navegador rechaza la conexión, se descarga el JSON de esa selección. En YomaTV usa **Importar cola web**. En **Cola para la PC → Opciones de respaldo**, **Guardar cola JSON** permite elegir este método expresamente y **Importar resultados** recibe los archivos de **Exportar resultados web**; admite varios archivos. El apartado permanece plegado durante el uso automático.

El código se guarda en `datos/web-bridge.json` del PC y en el almacenamiento local de ese navegador. No se envía a PHP, MySQL o los archivos de cola. Puedes olvidar el equipo desde la web o revocar todos los códigos anteriores desde **Conectar web → Revocar conexiones** en el programa. El puente escucha únicamente en `127.0.0.1:47653`, exige el token en cada operación y el Origin exacto `https://hk-br035.gt.tc`. También valida Host, preflight, tamaño y contenido de la cola. No admite otros dominios o dispositivos de la red.

**En cola web** significa que la solicitud todavía espera envío. Los estados **Descargando**, **Verificando**, **Pausado** y **Falló** proceden del puente local, con porcentaje y motivo breve cuando están disponibles. **Descargado** requiere un recibo del registro de archivos completados y verificados por YomaTV, con tamaño y SHA-256. Las tarjetas del horario muestran el estado de su último capítulo en el idioma elegido. Retirar una solicitud de la lista web no cancela una descarga que ya se inició allí.

El registro de confirmación documenta una descarga verificada; la web no vuelve a leer el video ni lo almacena. La revisión diaria y la recuperación tras un apagado siguen ejecutándose en Windows, incluso con el navegador cerrado. La conexión directa ocurre entre el navegador y el PC; no necesita evadir el sistema de acceso por navegador de InfinityFree.

Chrome y Edge pueden pedir permiso de **acceso a la red local** además de CORS. No se desactiva la seguridad del navegador ni se instalan certificados. Si el navegador no lo permite, usa los archivos JSON. Referencias oficiales: [Chrome](https://developer.chrome.com/blog/local-network-access), [Edge](https://learn.microsoft.com/es-es/deployedge/ms-edge-local-network-access).

**Brave:** permite **Acceso a la red local** para `https://hk-br035.gt.tc` en los controles junto a la URL → Configuración del sitio. En versiones anteriores puede aparecer como **Localhost**. Recarga y vuelve a emparejar. Su permiso puede durar hasta cerrar el sitio o un período elegido; el código de YomaTV permanece válido hasta revocarlo. Referencias: [configuración del sitio](https://support.brave.app/hc/en-us/articles/360018205431-How-do-I-change-site-permissions), [implementación oficial y comprobación en Windows](https://github.com/brave/brave-browser/issues/51843). La instalación de Brave del usuario no está conectada a las herramientas de automatización de este workspace y su permiso necesita comprobarse allí.

## Funciones conectadas

- Cuentas con sesión, contraseñas hash y datos personales separados.
- Catálogo de 4.485 títulos, búsqueda, filtros de formato/temporada, orden A–Z y paginación de 24 tarjetas. El estado habitual solo incluye el horario y los animes personales, sin cargar miles de fichas en cada acción.
- Horario de lunes a domingo, búsqueda, portadas y fichas con sinopsis reales.
- Biblioteca con estados, favoritos, notas, puntuación y progreso por capítulos vistos.
- Listados de capítulos actualizables y enlaces al reproductor externo MP4Upload/Voe.
- Colas persistentes con deduplicación, retirada, exportación y confirmación idempotente.
- Preferencias de idioma, servidor, calidad, alternativas, hora, concurrencia, velocidad y temporadas.
- Historial de acciones. Diseño adaptable a escritorio y teléfono, con estados vacíos y errores visibles.

**Guardar preferencias** las aplica inmediatamente en YomaTV mediante el puente, sin preparar una cola. Si la aplicación está cerrada se conservan en la web y se sincronizan cuando vuelva a conectar. El botón permanece visible al desplazarse. La carpeta de destino y el estado de pausa se conservan. Cambiar el ritmo de una descarga activa reinicia su trabajador conservando los parciales; los capítulos ya pedidos mantienen su idioma. La primera revisión completa continúa siendo secuencial; después, **Animes a la vez (1–4)** limita la concurrencia entre animes, manteniendo los capítulos de cada uno en orden. Las versiones antiguas del EXE muestran un aviso para actualizar antes de aplicar preferencias al instante.

El puente conserva el protocolo `seasonav1.bridge/v1` y anuncia capacidades. Añade `POST /settings`, `GET /status?installation=…&ids=…` y resultados filtrados por ID, con las mismas protecciones de token, origen y tamaño. Sus referencias de trabajos se guardan en SQLite, también para colas antiguas; la consulta no expone rutas locales ni errores completos. El horario y las fichas se actualizan al solicitarlo desde la web. Las consultas tienen espera mínima entre revisiones, tamaño y tiempo limitados; un cambio del scraper conserva la información anterior y muestra un aviso.

## Reproducción, seguimiento y personalización — 14 de octubre de 2026

En cada capítulo, **Ver capítulo** abre un reproductor integrado con el mismo tema, selección de servidor/idioma y capítulo y anterior/siguiente. Se incrusta el reproductor del servidor disponible (MP4Upload o Voe); PHP no almacena ni retransmite videos. La radio se pausa al abrirlo. Cerrar el diálogo retira el iframe y detiene su reproducción. Si el proveedor no responde, se ofrece cambiar servidor o abrirlo externamente. La reproducción desde el proveedor depende de su disponibilidad; el video sintético de pruebas sí se reprodujo y actualizó el progreso.

### Detección del 80 % y sincronización automática con MAL

Cuando MAL confirma el progreso, aparece dentro del video el aviso **«Capítulo X actualizado en MyAnimeList»**, centrado abajo, con check menta y entrada/salida deslizante. Dura 4,2 segundos, se coloca sobre los controles si están visibles y respeta la preferencia de movimiento reducido. No aparece por sincronizaciones pendientes o fallidas, ni solo por abrir un capítulo marcado anteriormente. Un reintento confirmado también puede mostrarlo. El aviso se limita a una vez por apertura del reproductor; cambiar capítulo, servidor o cerrar cancela sus temporizadores. No requiere actualizar la extensión.

Para MP4Upload, instala una vez la extensión **YomaTV · Progreso de video** en Brave. El icono de ayuda del reproductor aparece si falta la extensión o necesita actualizarse a **1.1**; incluye el ZIP y las instrucciones: extraerlo, abrir `brave://extensions`, activar Modo de desarrollador y Cargar descomprimida con la carpeta que contiene `manifest.json`. Conserva esa carpeta y recarga la web. Para actualizar una instalación existente, reemplaza sus archivos por los del ZIP nuevo y pulsa Recargar en su tarjeta de `brave://extensions`. También está el código en `browser-extension/YomaTV-Brave/` y el paquete público en `htdocs/downloads/YomaTV-Brave.zip`.

La extensión conecta el elemento de video con la web. La barra inferior muestra reproducción/pausa, saltos de diez segundos, «Saltar intro» (+85 s desde la posición actual), posición, volumen, velocidad de 0,5× a 2× y pantalla completa. El progreso tiene una pista de ocho píxeles y zona de interacción de 24 px, rangos de video cargado y vista previa de tiempo al pasar el mouse (sin miniaturas). Espacio o K pausa, las flechas saltan diez segundos, F activa pantalla completa y M silencia; se respetan campos y botones. Los atajos funcionan también dentro del iframe. Picture-in-picture tiene un icono en la esquina superior derecha dentro del documento del video para recibir directamente el gesto del usuario; solo se muestra si el navegador ofrece la API y avisa si rechaza la apertura. El modal limita la altura del video y permite scroll interno en ventanas pequeñas. La marca Visto ✓ MAL está junto al título, separada de los controles. Aparece al mover el mouse, tocar o usar el teclado y se oculta mientras reproduce y deja de haber interacción. La posición llega desde el video, no desde un contador de tiempo en la página. Se marca visto cuando `currentTime / duration >= 0.8`, una vez por reproducción; adelantar directamente más allá del umbral también cuenta. Para 23 minutos, el umbral es 18:24. Los anuncios de otro origen o marcados como anuncios no cuentan.

Al llegar al umbral, la web registra el capítulo y usa el ID de MAL vinculado a esa ficha y esa cuenta. Consulta el progreso actual en MAL antes de enviar: mantiene el mayor entre lo recién visto y lo consultado, conserva la puntuación y completa la lista al alcanzar su total conocido. Las peticiones simultáneas a nuestra web se serializan por anime; otra aplicación que edite MAL entre la lectura y escritura sigue sujeta al comportamiento normal de su API. Los capítulos fraccionarios/especiales y los números superiores al total no se envían automáticamente a una ficha incorrecta.

Si falta la conexión o el vínculo, se guarda el visto en la web y se explica qué falta. Un fallo de MAL conserva el envío en una tabla propia, con espera progresiva de 30 segundos hasta 15 minutos; se reintenta mientras la web está visible o en otra visita. Conectar MAL y vincular una ficha permite retomar sus marcas pendientes. No se anuncia «confirmado en MAL» hasta recibir su respuesta. Un vínculo cambiado no recibe una marca antigua de otro ID.

La extensión tiene permiso `storage` para conexiones temporales entre pestaña, documento e iframe en `storage.session`. Solo se ejecuta en esta web y los embeds de MP4Upload; no recibe contraseñas, cookies, tokens ni datos de la cuenta de MAL. Usa mensajes internos de la extensión, validando dominio, pestaña, frame, documento y un nonce por reproducción. No acepta conexiones externas ni pide acceso a todas las páginas. Voe conserva su reproductor habitual y no admite esta detección en esta versión.

Pruebas: 11 grupos HTTP del envío automático, 14 del controlador, 7 del enlace de la extensión y 7 del adaptador del video, más las regresiones de MAL y funciones web. La prueba de navegador reprodujo un video sintético de treinta segundos y confirmó capítulo 6 en la web y en el proveedor simulado de MAL. La revisión responsive (1280×720, 390×844 y 900×420) confirmó controles sin desbordamiento, scroll interno y estado MAL junto al título. La API de PiP fue rechazada por el navegador integrado; su activación real en Brave aún no se ha podido comprobar. La instalación y reproducción de un capítulo real en Brave requieren instalar la extensión en el navegador del usuario, que no está conectado a la automatización.

El catálogo busca sin distinguir acentos ni mayúsculas y utiliza los alias de MAL de los animes vinculados. Añade año, emisión, capítulos sin ver y géneros disponibles. No inventa metadatos ausentes: hay filtros **Año sin datos** y **Estado sin datos**. Las tarjetas activas muestran una cuenta regresiva estimada a partir de la última publicación semanal; no es una fecha garantizada. **Temporada → Exportar calendario** genera un `.ics` con trece recurrencias semanales estimadas.

### Filtros personales del catálogo

La barra principal contiene búsqueda, formato, orden y **Más filtros**. El panel adicional ofrece los cinco estados de biblioteca, favoritos, seguidos o no seguidos; descargas confirmadas, en cola o sin preparar; índice A–Z y números/otros; año, temporada de estreno, emisión, horario actual, capítulos sin ver e idioma comprobado. Los filtros se combinan en SQL antes de contar y paginar: no se limitan a las 24 tarjetas visibles. **Con capítulos descargados** significa al menos un capítulo confirmado. **Sin preparar** ignora trabajos cancelados y trabajos de otras cuentas. Los filtros personales requieren sesión.

Los géneros incluidos se combinan con **todos** (AND), y los excluidos descartan cualquier coincidencia. Una ficha sin géneros conocidos no pasa ninguno de esos filtros. Los idiomas proceden de los servidores de capítulos ya consultados, indexados en `sa1_episode_languages`; no se deducen del idioma preferido ni de la cola. `Idioma sin comprobar` no significa que el anime carezca de doblaje.

Los órdenes incluyen nombre A–Z/Z–A, mi puntuación, capítulos disponibles, estreno más reciente y última actualización de ficha. Cada filtro genera un chip eliminable y **Limpiar filtros** los retira todos. Los valores y la página se guardan en el fragmento `#discover?...` de la URL, conservando parámetros del alojamiento como `?i=1`. Los enlaces compartidos restauran el filtro; los datos personales siguen perteneciendo a la cuenta que abre el enlace. Atrás/Adelante restaura filtros y página.

Las actualizaciones y búsquedas en MAL solicitan géneros, emisión, fechas, estudios y media pública. `sa1_catalog_mal` comparte únicamente metadatos públicos obtenidos de coincidencias exactas únicas, con formato/fecha compatibles; también aprovecha metadatos de API ya guardados antes de esta versión. No publica estados de biblioteca, notas, puntuaciones personales ni tokens. Dos IDs de MAL igualmente compatibles bloquean la coincidencia pública: se conserva la elección personal de cada usuario. El XML no puede publicar metadatos globales. Las fichas muestran géneros, estudios y media de MAL cuando existen; el panel informa de cuántas tienen datos. No se realizan miles de búsquedas remotas al abrir el catálogo: los huecos se completan conforme se actualiza MAL o se consulta una ficha. Los títulos todavía sin correspondencia siguen mostrando datos desconocidos.

Pruebas de esta ampliación: `test_catalog_filters.py` (33 comprobaciones HTTP), `test_catalog_route.js` (7 comprobaciones de URL, historial y respuestas tardías) y `test_catalog_metadata.php` (4 comprobaciones de coincidencias públicas conservadoras), además de las regresiones de MAL y del estado del cliente. Se usan SQLite y cuentas/proveedor ficticios; los fixtures no se publican ni se incluyen en el ZIP de fuente.

La campana cuenta capítulos nuevos de animes seguidos, favoritos o por ver, detectados durante una actualización posterior al seguimiento. No crea miles de avisos por capítulos antiguos. El panel permite leerlos; las notificaciones del navegador son optativas y solo funcionan mientras la web esté abierta. No se implementa push con el navegador cerrado. **Estadísticas** muestra progreso visto sin duplicar animes vinculados, horas estimadas, bytes confirmados por la PC y puntuación media por temporada.

**Preferencias → Apariencia** ofrece claro, oscuro o sistema y acentos menta, azul, rosa o violeta. La elección se guarda en ese navegador. La PWA se instala desde el navegador compatible o desde Preferencias. El service worker guarda únicamente recursos públicos y un índice de 4.483 títulos; sin conexión permite buscar y paginar ese catálogo. No guarda sesiones, tokens, listas personales, respuestas de API, videos ni operaciones POST. Las fichas y acciones personales requieren conexión.

### Actualizaciones y avisos del scraper

Al visitar como administrador, el cliente solicita una revisión si han transcurrido doce horas. El servidor evita revisiones concurrentes y mantiene un punto de continuación: consulta el horario y procesa de uno en uno los listados pendientes, con pausas. Se detiene cuando la pestaña se oculta y puede continuar en otra visita. Los fallos conservan los datos anteriores, tienen espera de quince minutos y aparecen en el panel de Preferencias de la cuenta administradora.

InfinityFree gratuito también bloquea las peticiones de cron externos; UptimeRobot no sustituye un cron allí. Se usa la revisión durante visitas y no se configura un servicio externo. Fuente: [anuncio oficial de InfinityFree](https://forum.infinityfree.com/t/cron-job-feature-is-now-disabled/80495).

Para migrar a un alojamiento compatible, `maintenance.php` admite POST con un token aleatorio de 256 bits en `Authorization: Bearer …`, cuyo hash se guarda en la base. Permanece desactivado por defecto. Solo habilita `external_maintenance => true` en la configuración privada de un alojamiento que permita tareas programadas. El administrador podrá generar el token confirmando su contraseña; se muestra una vez y renovarlo invalida el anterior. Un POST cada cinco minutos deja que el servidor aplique el intervalo de doce horas y termine un listado por solicitud. No se incluyen tokens en URLs, JavaScript o el ZIP.

Pruebas de esta ampliación: 14 grupos HTTP integrados, 12 comprobaciones PHP y 6 del service worker, además de las regresiones web y OAuth. La edición/remoción de MAL se verificó con un proveedor local simulado; ninguna prueba cambió listas reales de MAL. Los fixtures de prueba no se publican.

## Radio de anime

**Radio anime** contiene 42 openings/endings de otoño2026 y una versión instrumental de Their Secret (OST de The Apothecary Diaries), publicada por Umeko y CaliMelodies en 2024 y señalada como cover. Los 43 enlaces se verificaron con YouTube oEmbed. El orden de populares corresponde a las vistas registradas por [Openingpedia](https://www.openingpedia.com/en/seasons/fall-2026), con fecha visible; no pretende clasificar todo YouTube ni actualizar las vistas en tiempo real.

La radio está apagada al entrar. Activarla carga el reproductor oficial de YouTube con vídeo visible de al menos 200 px de alto, controles, volumen, anterior/siguiente y avance al terminar. Su barra inferior reserva espacio y no tapa la lista. Permanece al navegar por las secciones; los iconos alternan reproducir/pausar según el estado real. **Minimizar** compacta la barra y pausa el vídeo; **Ampliar** permite escucharlo de nuevo. También se pausa cuando la pestaña queda oculta o una ficha cubre el reproductor. Apagarla destruye el reproductor. Solo se recuerda el volumen en localStorage; no se guarda una autorización de reproducción automática.

Antes de activarla se informa de la conexión con YouTube y se enlazan su privacidad y condiciones. Los vídeos conservan controles y publicidad de YouTube. Si un vídeo no permite inserción, está restringido o el navegador bloquea YouTube, se muestra el motivo y se puede elegir Siguiente o abrir el enlace externo. No se extrae ni descarga el audio.

## Índice completo y mantenimiento

La consulta sin filtros de `/catalogo` tiene un límite de 1.000 resultados. `catalog_seed.py` recorrió 277 páginas públicas y dividió por intervalos de años, verificando que cada intervalo quede por debajo de ese límite y tenga todas sus filas. El resultado suma 4.483 títulos únicos. Se guarda en `data/catalog.json.gz` (aproximadamente 1,5 MB) y se importa por lotes en MySQL una vez por versión, conservando capítulos, biblioteca y colas. En las peticiones normales se lee únicamente el pequeño manifiesto de versión.

**Buscar novedades** consulta la primera página del directorio y agrega/actualiza sus fichas, sin borrar títulos antiguos. **Actualizar horario** mantiene las emisiones semanales y **Actualizar listado** renueva los capítulos de una ficha. Para renovar todo el índice desde el equipo de desarrollo: `python catalog_seed.py --refresh`, seguido de `python deploy.py`; sin `--refresh` se puede reanudar desde la caché local. La selección musical es una instantánea revisada: para cambiarla se prepara el JSON musical y se ejecuta `radio_seed.py`, que verifica sus enlaces antes de publicar. No se presentan como actuales selecciones de otra temporada.

Pruebas añadidas: `verification/test_catalog.py` verifica búsqueda, paginación, aislamiento y la exportación ordenada de 220 capítulos de Naruto; `verification/test_radio_client.js` verifica apagado, pausa, avance y callbacks tardíos. Se conservan las pruebas previas de cuentas y del puente con YomaTV.

`verification/test_downloads.js` verifica la agrupación de 220 capítulos, paginación, filtros, bloqueo por idioma y actualización de los controles al recibir una confirmación. `verification/test_downloads_http.py` comprueba que la ficha muestre sus confirmaciones, que preparar nuevamente los descargados no genere solicitudes y que las cuentas/idiomas permanezcan separados. Usa SQLite desechable y recibos sintéticos; no descarga videos de anime. Capturas `verification/grouped-queue-*.png` y `verification/grouped-episodes-blocked.png`.

## MySQL y alojamiento

La conexión MySQL se configura en `private/config.local.php` con los datos del alojamiento. Las tablas propias con prefijo `sa1_` se crean automáticamente: usuarios, catálogo, capítulos, seguimiento, vistos, trabajos, preferencias, historial, metadatos, límites, recuperación y conexión/lista/vínculos de MAL, notificaciones e índice de búsqueda. Las migraciones conservan las cuentas y bibliotecas existentes. No eliminan tablas ajenas ni importan datos de las cuentas de prueba locales.

`private/config.local.php` se generó únicamente en el alojamiento durante la publicación. No está en JavaScript, archivos de descarga ni el paquete de fuente. `private/.htaccess` deniega acceso y los archivos PHP también exigen el arranque interno.

InfinityFree gratuito no admite procesos de descarga prolongados ni cron. Por eso el motor sigue en la PC. Tampoco se sube el EXE de 66 MB o los videos al alojamiento. Documentación: [cron y restricciones](https://forum.infinityfree.com/t/restrictions-on-php/110456), [MySQL externo](https://forum.infinityfree.com/t/connecting-to-mysql-from-an-external-application/49339).

## Fuente y desarrollo

`htdocs/` contiene el sitio completo, sin compilación ni paquetes npm necesarios para ejecutarlo. PHP 8.0+ con PDO MySQL, cURL y mbstring; para la vista local se usa PDO SQLite. Los iconos de la mascota están en `assets/icon-32.png`, `icon-180.png` e `icon-192.png`.

```powershell
$env:SEASON_WEB_SQLITE = Join-Path (Get-Location) 'verification/preview.sqlite'
php -S 127.0.0.1:8086 -t htdocs
```

El catálogo inicial en `data/season.json` se puede regenerar con `seed.py` desde la caché del programa local. El script FTPS `deploy.py` reutiliza las herramientas de publicación y credenciales de `Expedition-7` de este workspace; no forma parte del sitio publicado. Para otro equipo, sube `htdocs/` y configura la conexión PHP protegida usando `private/config.example.php` como referencia.

## Verificación

- 48 pruebas del programa, incluidos preferencias sin cola, preservación de pausa/destino, consultas de progreso aisladas, referencias de más de 50 colas y capítulos con idioma anterior. El EXE instalado respondió a los nuevos endpoints sin cambiar su configuración: conserva los 71 capítulos y la pausa. `../YomaTV/verification/live-frozen-check.json`.
- Recorrido local con MP4 sintético verificado: preparación desde tarjeta → porcentaje en vivo → recibo automático → tarjeta **Descargado**. Preferencias sincronizadas antes de crear una cola, desconexión/reconexión, iconos de radio y vista móvil de 390 px con guardado fijo. Capturas `verification/live-*.png`. No se descargaron capítulos nuevos de Internet en esta prueba.
- 15 comprobaciones HTTP locales: sesión/CSRF, registro, acceso, cuentas aisladas, favoritos, vistos, preferencias, cola sin duplicados, exportación ordenada y limitada a la selección, trabajos ajenos rechazados, recibos válidos y repetidos y retirada de solicitudes.
- Pruebas PHP del lector de literales sobre el HTML real del horario y de una ficha, incluida decodificación Unicode.
- Recorrido web local → EXE empaquetado → web local con un capítulo real de 128.677.133 bytes ya verificado, reutilizado sin descargar de nuevo. Evidencia: `verification/roundtrip-check.json`.
- Diseño y controles probados en el navegador, en escritorio y a 390 px. No hubo desbordamiento horizontal; favoritos y vistos persistieron. Capturas en `verification/`.
- Sitio publicado por FTPS y consultado por HTTPS con su catálogo respaldado por MySQL. Se retiraron todos los diagnósticos públicos temporales.

La disponibilidad de capítulos, idiomas, calidad y servidores depende de AnimeAV1 y sus reproductores. El archivo descargado se verifica en YomaTV, con lectura de paquetes y muestras decodificadas; no se decodifican todos los fotogramas.

### Conexión con MyAnimeList

En **Mi cuenta → Conectar MyAnimeList**, el usuario autoriza desde MAL y vuelve a esta web. La dirección registrada debe ser exactamente `https://hk-br035.gt.tc/seasonav1/mal-callback.php`, sin barra final. El flujo usa OAuth 2, PKCE (`plain`, compatible con MAL), un estado aleatorio ligado a la sesión y a la cuenta, y una caducidad de diez minutos. Los callbacks no se reutilizan.

La configuración `mal` vive exclusivamente en `htdocs/private/config.local.php` del servidor: `client_id`, `client_secret`, `redirect_uri` y `encryption_key` (32 bytes aleatorios codificados en Base64). Conserva esa clave al publicar versiones: cambiarla impide descifrar los tokens ya guardados. El publicador conserva la configuración privada existente. Los ejemplos y el ZIP no incluyen credenciales reales.

Los tokens se cifran con AES-256-GCM, con autenticación ligada al usuario, en `sa1_mal_connections`. El acceso se renueva automáticamente con el refresh token. **Consultar mi lista** obtiene páginas de 50 animes con estado, nota y capítulos vistos; no sigue URLs de paginación externas. **Desvincular** borra los tokens de esta web; para retirar el permiso en MAL, usa su configuración de aplicaciones autorizadas. Eliminar la cuenta web borra también su conexión.

La portada del catálogo muestra primero **Continuar viendo**, **Viendo / Watching** y **Por ver / Plan to watch** de la cuenta, con portada y progreso. **Mi lista MAL** permite consultar los cinco estados, buscar y paginar. La lista se guarda por usuario y se actualiza en páginas de 50; al entrar se refresca si la última revisión tiene más de seis horas. También se puede actualizar manualmente. No es una sincronización permanente con el navegador cerrado.

Las coincidencias automáticas requieren un título o alias normalizado único y fechas/formato compatibles. No se vinculan automáticamente resultados ambiguos. **Vincular AnimeAV1**, **Revisar vínculo** y **Buscar en MAL** permiten comparar y confirmar el ID de la temporada correcta; cada ficha y cada ID se relacionan una sola vez por usuario. No todos los títulos tienen correspondencia exacta: secuelas, especiales, versiones de doblaje y series agrupadas pueden requerir selección manual.

**Editar en MAL → Guardar en MyAnimeList** envía el estado, puntuación y número de capítulos vistos a la lista real mediante PATCH. **Retirar de mi lista de MAL** pide confirmación expresa. Las descargas de la PC se conservan. La reproducción con la extensión actualiza automáticamente el progreso al alcanzar el 80 %; guardar en biblioteca y el botón manual de visto de una ficha mantienen su ámbito web. La importación XML tiene vista previa, combina estados/progreso/notas y no escribe en la cuenta remota. Rechaza entidades externas y archivos mayores de 10 MB o 5.000 entradas. Las notas importadas permanecen en la web.

Las pruebas OAuth utilizan un proveedor local en `verification/mal_mock.py`; las credenciales ficticias y la sustitución del proveedor solo se habilitan con la base SQLite de pruebas. No se publica el proveedor ni ningún endpoint de diagnóstico. La autorización de una cuenta real requiere que su propietario complete el acceso y consentimiento en MAL.

### Icono web y barra lateral

El retrato frontal de la mascota se generó con la herramienta integrada image_gen a partir de las referencias del usuario: personaje completamente humano, sin orejas de animal y con el cabello negro corto y de poco volumen. El original y los prompts están en `design/`; las versiones PNG de 32, 180, 192 y 512 px se usan en la pestaña, la cabecera lateral, las notificaciones y el manifiesto PWA. La revisión de los iconos y de la caché pública evita reutilizar el icono anterior. No cambia el icono de la aplicación de Windows.

El botón junto a la ruta de navegación oculta o muestra la barra lateral en escritorio y guarda esa elección localmente en el navegador. En móvil abre el menú superpuesto, que se cierra al elegir una sección, pulsar Escape o tocar el fondo. La preferencia de escritorio se conserva al cambiar de tamaño. El menú oculto queda fuera del recorrido del teclado y las transiciones respetan la preferencia de movimiento reducido.

### Filtros del catálogo desde AnimeAV1 — 16 de octubre de 2026

Los géneros, años y emisión se indexan desde las páginas HTML públicas de AnimeAV1 y sus parámetros `genre`, `minYear`, `maxYear`, `status` y `page`, sin su API oficial. El índice compartido `sa1_catalog_source` cubre 4.485 títulos, con 46 géneros, años de 1969 a 2027 y emisión comprobada. Se validaron 1.319 páginas públicas, incluida la partición por años de consultas que alcanzaban el límite. El género Antropomórfico contiene 83 títulos. El índice cubre el directorio, incluso animes que ningún usuario ha vinculado o añadido a MAL. Un vínculo personal de MAL no cambia los metadatos con los que se filtra el catálogo. Biblioteca, descargas, puntuación y capítulos sin ver se aplican solo al elegir esos filtros personales; las secciones personales de la portada se ocultan durante una búsqueda filtrada. Se conservan los nombres antiguos en inglés de los enlaces guardados, traduciéndolos a los nombres de AnimeAV1.

`catalog_facets_seed.py` reconstruye un snapshot completo, con caché reanudable de páginas (24 horas) y pausas entre peticiones. `--refresh` vuelve a consultar los datos aunque la caché sea reciente. Divide las búsquedas por año cuando AnimeAV1 alcanza su límite de 1.000 resultados; valida cada página y no reemplaza el snapshot si está incompleto. Publicar `catalog-taxonomy.json`, `catalog-facets.json.gz` y `catalog-facets-meta.json` importa el índice mediante una transacción sin modificar cuentas, listas, capítulos o descargas existentes. Las consultas normales del catálogo leen MySQL y no lanzan scraping. Las actualizaciones autorizadas de fichas también renuevan sus metadatos de origen. No se crean procesos ni tareas de Windows para este índice.

Las búsquedas de varios géneros incluidos permiten elegir «todos» o «cualquiera», con exclusiones independientes; AnimeAV1 combina sus parámetros repetidos como alternativa, por lo que esta web calcula la intersección sobre el índice completo. Las temporadas requieren una fecha de estreno completa (el directorio de AnimeAV1 solo filtra el año), y el idioma se confirma mediante servidores de capítulos. Se muestran los datos desconocidos sin adivinarlos.


### Entrega 2 · Catálogo, datos y actualización

Los miembros pueden **Solicitar listado completo**, actualizar una ficha o solicitar los servidores de un capítulo conocido. Estas acciones crean un trabajo compartido e idempotente; no otorgan acceso al scraper. Se admiten ocho solicitudes nuevas por cuenta y hora, sesenta globales y cien pendientes de usuarios. Los datos recién comprobados se reutilizan. Solo el administrador o el endpoint de sistema autorizado procesa la cola.

El mantenimiento alterna el horario con el catálogo: recorre páginas recientes sin filtro, divide el directorio por años cuando alcanza 1.000 resultados y renueva las fichas más antiguas, incluidas las que están fuera de temporada. Un quinto de los pasos se reserva para fichas antiguas; las comprobaciones se renuevan después de treinta días. El ciclo de descubrimiento se propone cada siete días y no sustituye otro sin terminar. Un paso obtiene una sola página HTML, con pausas y el límite compartido existente de 120 peticiones por hora. Hay leases recuperables, esperas progresivas y cuarentena tras cinco errores; el administrador puede reintentarlos. Un presupuesto de peticiones agotado espera sin consumir intentos. Si cambia el total durante la paginación se reinicia solo esa partición. Se conservan episodios, biblioteca y archivos anteriores.

En InfinityFree el trabajo avanza **mientras el administrador visita la web**, en lotes de hasta veinte pasos, con reanudación durante las siguientes revisiones de la página visible. No hay cron externo ni procesos nuevos de Windows. Un usuario que solicite datos ve que su solicitud espera al mantenimiento autorizado; no se promete una actualización inmediata ni terminar 4.485 fichas en una visita.

**Sobre los datos del catálogo** muestra cobertura, fecha más antigua y más reciente para directorio, capítulos, servidores, géneros y emisión. Cada ficha conserva las fechas verificadas por separado; comprobar metadatos no marca los capítulos como comprobados. Los servidores se cuentan por capítulo y su caché conserva su caducidad. Las fichas antiguas sin una fecha verificable muestran «Sin comprobar».

**Guardar búsqueda** conserva hasta treinta combinaciones privadas por cuenta, con nombre, filtros y modo de géneros; se pueden restaurar o eliminar. Los filtros siguen en la URL. Los géneros «todos» calculan intersección; «cualquiera» calcula unión, y ambos respetan todas las exclusiones. Los datos personales solo restringen el catálogo cuando se eligen esos filtros.

Las relaciones publicadas por AnimeAV1 se incorporan como propuestas para revisión, leyendo sus etiquetas visibles. El administrador puede aprobarlas, descartarlas, corregir su tipo o añadir una relación entre dos fichas existentes. Solo se muestran relaciones aprobadas al resto de usuarios. Aprobar una secuela crea su precuela inversa; las otras relaciones mantienen una referencia recíproca. No se deducen temporadas por títulos parecidos ni se alteran listas MAL.

Las notificaciones se agrupan por anime, con cantidad, rango y capítulos sin leer; se paginan de cincuenta animes en cincuenta. El contador de campana cuenta animes con avisos pendientes. La actualización del horario conserva una referencia anterior hasta completar la ficha, para recuperar también capítulos intermedios durante una ausencia. Marcar como leído usa el límite del lote consultado, sin incluir avisos posteriores.

El generador del índice incluye directorio, títulos, sinopsis y facetas en su hash y regenera la copia offline automáticamente. La copia distribuida tiene **4.485 títulos**. `catalog-public.php` ofrece exclusivamente título, identificador y formato del catálogo actual con ETag; no incluye cuentas, notas, descargas, MAL ni enlaces privados. El service worker renueva esta proyección al tener conexión, conserva la copia válida ante errores y recupera recursos públicos por su URL canónica aunque cambie `?v=`. No guarda respuestas de APIs personales, OAuth ni videos.

**Calendario:** la exportación admite todo el horario o solo animes seguidos/favoritos sin excluir. También está implementada la suscripción `.ics`, con enlaces aleatorios privados, rotación, revocación, actualización de biblioteca y protección contra renovaciones antiguas que intenten recrear un enlace revocado. Los eventos conservan UID estable, fechas UTC, plegado UTF-8 y horarios expresamente estimados. Se verificó que InfinityFree devuelve HTML de verificación, incluso para un `.ics` estático real consultado sin cookies; los calendarios externos no pueden leerlo. Por eso producción muestra la exportación y explica la limitación. `calendar_subscriptions` solo se activa en la configuración privada de un alojamiento que permita clientes externos. Referencia: https://forum.infinityfree.com/t/browser-security-system-features-and-limitations/49353 . Los calendarios privados generados nunca se incluyen en el ZIP ni en la publicación del código.

Las pruebas nuevas usan SQLite desechable, HTML público previamente guardado y un trabajador con transporte simulado. Se comprueban filtros privados, modos de géneros, solicitudes sin scraping, roles, relaciones, avisos acumulados, suscripciones, recuperación de leases, límites y cambios de paginación. Las regresiones de la entrega 1, autenticación, MAL y reproducción usan un proveedor MAL ficticio. El acceso al navegador sigue deshabilitado, por lo que esta entrega no tiene validación visual nueva en Brave. El ejecutable, sus ajustes y los videos del usuario no se modifican.

## Entrega 3 · reproducción y experiencia

La posición se guarda cada diez segundos y también al saltar, pausar y cerrar. Al reabrir se ofrecen Continuar y Desde el inicio. La última sesión de un capítulo prevalece sobre guardados antiguos. El siguiente capítulo es opcional, con ocho segundos para cancelar; se cancela al ocultar la pestaña o cerrar el reproductor. Volumen, velocidad y servidor con idioma se guardan en la cuenta, globalmente o por anime. El diagnóstico separa extensión, servidor, video, posición y MAL. MP4Upload requiere la extensión para estas funciones; Voe mantiene sus controles propios.

El revisionado mantiene posiciones y marcas separadas, tanto automáticas como manuales, sin modificar el progreso original ni MAL. Empezar un revisionado nuevo crea otra ronda y conserva las anteriores en la base local de la web. Para reducir el progreso original, Editar en MAL pide confirmación y ajusta las marcas web; la ficha ofrece reconciliar en ambas direcciones con el último progreso MAL consultado. Consulta tu lista antes si cambió en MAL. Un reproductor anterior a la corrección no puede deshacerla. La revisión de coincidencias por lotes exige seleccionar cada vínculo mostrando formato, temporada y total.

Las fichas muestran 36 capítulos por página. Rangos como `1-12,14,20.5`, sin ver y no descargados conservan la selección entre páginas y excluyen solicitudes ya preparadas. El resumen permite revisar el envío antes de crear solicitudes.

En Cola para la PC, los controles de cada anime requieren YomaTV **2026.10.18.1**. Prioridad afecta al siguiente anime; pausa, continuación y reintento tienen efecto en la PC, conservando su pausa global. Comprobar archivos consulta existencia y tamaño registrado sin enviar rutas. El historial no se presenta como prueba de presencia. Redescargar requiere comprobación reciente y confirmación expresa; en un equipo nuevo se explica que puede haber otra copia. Las confirmaciones antiguas no completan una redescarga nueva.

La extensión distribuida es **1.2.0**, con los mismos permisos y dominios limitados; 1.1 conserva controles y detección pero no informa su versión exacta. El EXE actualizado está en `../YomaTV/YomaTV.exe` y su ZIP portable en `../YomaTV/build/release/YomaTV-portable.zip`. El enlace público de Drive sigue apuntando al archivo del propietario y debe reemplazarse allí para distribuir esta compilación; la web detecta capacidades y deshabilita controles incompatibles.

La radio permite favoritos y hasta veinte listas de hasta 300 canciones guardadas en este navegador y separadas por cuenta. Nunca se activa sola; intenta como máximo tres videos no disponibles consecutivos. Los formularios de ficha, MAL y preferencias conservan borradores en la pestaña y ofrecen descarte con confirmación. Se incorporan nombres accesibles, foco y fondo inerte en móvil, salto al contenido, `aria-current` y densidad compacta/normal con objetivos táctiles amplios.


## Entrega 4 · infraestructura y seguridad · publicada

Publicada junto con la Sala de anime. Pasaron 13 suites locales, 17 JavaScript, 11 HTTP y 11 comprobaciones MariaDB 11.4.13, además de la revisión visual local con video sintético. La activación, la reversión a `stable-delivery3`, el regreso a la versión nueva y los archivos públicos se verificaron en InfinityFree. El propietario pidió aplazar el respaldo real y Brave; esas comprobaciones no se presentan como realizadas. La limitación de suscripciones `.ics` externas continúa.

### Peticiones, sesiones y límites

El esquema tiene versión `20261018.4`. Una petición normal consulta esa versión y no ejecuta DDL. Un cambio de versión toma un bloqueo de conexión `GET_LOCK` en MySQL o un bloqueo de archivo en SQLite, vuelve a comprobar la versión y aplica los cambios aditivos. La carga de semillas queda separada y conserva su comprobación de versión.

Antes de contactar AnimeAV1/MAL y de esperar entre peticiones se cierra la sesión PHP. El actor original queda fijado en memoria y las escrituras sensibles conservan sus leases/comprobaciones en la base. OAuth guarda el hash del último intento por usuario, comprueba la versión de autenticación y evita que un callback anterior sustituya una autorización o aviso nuevos. Las sesiones reales de dos procesos verificaron que una petición lenta ya no bloquea la segunda.

`transport.js` centraliza AbortController, plazo de respuesta y cancelación al cambiar de cuenta. El plazo cubre también la lectura JSON. Una búsqueda nueva cancela la anterior. Se descartan estados completos atrasados y errores 401 pertenecientes a otra cuenta. Las mutaciones no se repiten automáticamente: tras un timeout se pide comprobar su estado antes de repetirlas.

Los límites usan un UPSERT y lectura bloqueada dentro de la misma transacción. Se aplican por IP y cuenta: lecturas ordinarias hasta 300/minuto por cuenta y 900/IP; otras acciones hasta 180/cinco minutos por cuenta y 540/IP. Autenticación y recuperación mantienen límites propios por IP/correo. Los límites específicos del scraper, MAL y respaldo se conservan. No se confía en encabezados de IP enviados por el cliente.

### Interfaz, caché y salud

`dom-renderer.js` reconcilia componentes y listas por claves, en vez de reconstruir `main` entero durante una actualización de la misma vista/cuenta. Conserva foco, selección, filas existentes y controles de formularios editados; una cuenta/vista distinta comienza un ámbito nuevo. Guardar libera el borrador del control. Limpiar filtros sí actualiza el campo; los valores de un selector se capturan antes de mover sus opciones. La vista del reproductor se separa en `player-view.js`, sin cambiar su ciclo de vida.

Las facetas y la cobertura se guardan en `sa1_public_cache`. Su versión incluye revisión pública, directorio, semilla, versión publicada y vencimiento horario de respaldo. Las escrituras de datos públicos invalidan la caché. El cálculo excluye joins de biblioteca/vínculos personales. En el fixture SQLite, la carga fría usó 89 consultas y la repetida 25; no es una medición de latencia o rendimiento del MySQL de producción.

El administrador dispone de **Salud y mantenimiento** en Preferencias: media/máximo de duración, consultas medidas por petición, errores por clase/código, pendientes y sus fechas, cobertura/antigüedad de datos, planes de consultas y fecha del respaldo. La telemetría agrega por hora y operación; no guarda SQL con parámetros, tokens, cuerpos del proveedor, correos ni mensajes de error completos.

La limpieza se ejecuta con el mantenimiento autorizado o al consultar la salud, como máximo una vez por hora, en lotes. Elimina límites vencidos hace más de un día, métricas/errores de más de 14 días, trabajos de catálogo terminados hace más de 30 días, avisos OAuth viejos y eventos de más de 90 días que no estén entre los 80 últimos de su cuenta. Las cuentas pequeñas no bloquean la limpieza de las demás. Conserva trabajos/confirmaciones que evitan duplicados, archivos, posiciones y avisos personales sin leer.

### Respaldo y restauración

`backup.php` exige POST, sesión administradora, CSRF y un límite de dos respaldos por hora. El archivo `.sa1backup` usa AES-256-GCM por bloques, salt aleatoria, PBKDF2-SHA256 (210.000 iteraciones), número de bloque autenticado y cierre con recuento/hash. La clave se pide en el momento y no se guarda en el servidor. El alta y la generación de códigos de recuperación se confirman juntas: si fallan los códigos, no queda una cuenta creada a medias. Solo se utiliza almacenamiento temporal cifrado. En MySQL se solicita un snapshot REPEATABLE READ y lectura sin buffer de toda la tabla; se comprobó con MariaDB 11.4.13 desechable.

La herramienta `tools/db_backup.php` admite `backup`, `verify` y `restore`, con la clave en la variable de entorno **SEASON_BACKUP_PASSWORD**, nunca en argumentos. Ejemplo: `php tools/db_backup.php verify copia.sa1backup`. `restore` exige una base vacía configurada para el destino; crea el esquema sin importar semillas, autentica el archivo completo antes de insertar y restaura los datos en transacción y orden de claves foráneas. Conserva también las secuencias para no reutilizar IDs eliminados; en MySQL prepara esos contadores en el destino vacío antes de la transacción de datos. Rechaza una clave incorrecta, un archivo truncado/alterado y un destino con datos. Esta restauración se verificó con SQLite y MariaDB desechables, incluidas claves foráneas y secuencias con huecos; no se ejecutó sobre producción.

El respaldo de datos **no incluye** `private/config.local.php` ni `access.local.php`. Guarda esos archivos aparte de forma privada: para reutilizar los tokens cifrados de MAL hace falta conservar su clave de cifrado original. Tampoco guarda los videos de la PC.

### Publicación y reversión preparadas

`release.py` prepara versiones completas en `releases/<id>/`. Verifica cada archivo por FTPS y SHA-256 antes de activar un único `private/current.json` con renombrado atómico. Los entry points raíz cargan la versión seleccionada; los recursos tienen rutas inmutables y el service worker mantiene el ámbito raíz. Los PHP internos de una versión no admiten acceso directo. Las configuraciones privadas y calendarios generados permanecen compartidos fuera de las versiones. El puntero se lee como JSON y no depende de la caché de código PHP.

El primer cambio conserva el snapshot estable de la entrega 3. La activación comprueba `release-health.php`; si falla vuelve al puntero anterior y comprueba su salud. Si el servidor no admite reemplazo atómico se cancela sin borrar el puntero. La activación/reversión se comprobó primero en un sistema de archivos desechable y después en InfinityFree, verificando la salud al volver a ambas versiones. Las migraciones son aditivas para conservar compatibilidad con la versión anterior; una futura migración destructiva necesitará su propia estrategia.

Por defecto, antes de activar el publicador exige una copia cifrada verificada de las últimas 24 horas. `tools/remote_backup.py` usa un endpoint temporal con token aleatorio, vencimiento y limpieza. Guarda únicamente copia cifrada y clave local fuera del paquete. En esta publicación el propietario pidió omitir la copia y se usó explícitamente `--skip-database-backup`; el recibo registra `waived_by_owner`. No existe una copia de producción verificada para esta entrega.

En este workspace, el publicador usa el proveedor local de credenciales ya autorizado de Expedition-7; no se distribuye ese proveedor. Las pruebas HTTP/MySQL ya pasaron. Para otras publicaciones, el flujo predeterminado es crear/verificar el respaldo con `python tools/remote_backup.py`, usar `python release.py --publish entrega4-<identificador-nuevo>` y comprobarlo con `python verification/check_delivery4_published.py --release entrega4-<identificador-nuevo>`. Esta última herramienta revisa anónimamente versión/esquema, catálogo, permisos, recursos inmutables, service worker y ZIP de la extensión; no modifica cuentas ni listas. Se ejecutó contra `watch-room-20261022-1` y comprobó versión, esquema, catálogo, permisos, archivos públicos, service worker y extensión. `--status` consulta el puntero y `--rollback` vuelve a la versión anterior. `deploy.py` redirige al mismo publicador; ya no admite reemplazos parciales ni `--admin-email`. El paquete de fuente también permite instalar `htdocs/` en un alojamiento nuevo configurando privadamente la conexión.

### Evidencia y pendientes

Pasaron **13 suites locales** de PHP/almacenamiento y **17 JavaScript**. Las primeras incluyen migraciones, cifrado/restauración, metadatos, trabajador, rotación, OAuth validado sin transporte, biblioteca de 3.000 animes y 5.200 trabajos, sesiones y contadores con procesos reales y publicación/reversión local. Las de JavaScript incluyen transporte lento, abortos, JSON lento, respuestas fuera de orden, identidad y 2.000 nodos DOM de prueba. Los árboles DOM de prueba no sustituyen una revisión visual del navegador.

Pasaron las once suites HTTP de `run_delivery1.py`, incluidas las nuevas pruebas de roles, CSRF y respaldo cifrado. Se corrigió únicamente una aserción de prueba que comparaba literalmente las barras escapadas del JSON; ahora analiza la cabecera como JSON. `verification/download_mariadb.py` descargó el ZIP oficial 11.4.13 y verificó su SHA-256. `run_mysql.py` ejecutó once comprobaciones en un entorno desechable en 127.0.0.1:33316, sin servicio de Windows, y lo detuvo al terminar. Verificó migraciones idempotentes, códigos de recuperación, cola de 5.200 trabajos, catálogo completo, respaldo/restauración y 32 escritores concurrentes que admitieron exactamente siete solicitudes. Los planes usaron `sa1_jobs_user_added`, `sa1_history_user_id`, `sa1_episodes_slug_number` y `sa1_limits_expiry`; no son medidas del servidor de producción. Los informes HTTP/MySQL guardan hashes del código de aplicación y el resumen no reutiliza un resultado si cambian esos archivos.

Evidencias de esta entrega: `verification/delivery4-local-suite.json`, `delivery4-http-suite.json`, `mysql-check.json`, `infrastructure-check.json`, `concurrency-check.json`, `transport-check.json`, `dom-renderer-check.json`, `large-storage-check.json`, `release-check.json` y `delivery4-status.json`. FTPS/reversión y la comprobación pública pasaron; respaldo real y Brave/extensión/PiP quedan aplazados por el propietario. La Sala de anime tiene sus evidencias adicionales debajo. Ninguna prueba de esta entrega cambió una lista MAL real ni descargó capítulos reales.


## Sala de anime · 22 de octubre de 2026

Los capítulos se abren como una página completa con dirección propia `#watch/<id>`, en lugar de un diálogo. Conserva el video al recibir actualizaciones de fondo, admite recargar y usar Atrás/Adelante, y mantiene reanudación, preferencias, detección del 80 %, siguiente automático y controles del video.

En escritorio, los capítulos aparecen a la derecha, con el actual resaltado, marcas de visto y páginas de 60 para series largas. En móvil la lista pasa debajo. Incluye anterior/siguiente, selección de servidor e idioma y preparación de ese capítulo para la PC. Los servidores conservan sus limitaciones y la detección automática de MP4Upload sigue necesitando la extensión.

El ojo es una alternativa manual que llama a `watch_manual`: actualiza la cuenta real de MAL conectada, sin exigir una posición o duración del video. Exige sesión, CSRF, cuenta MAL y vínculo del anime vigentes, un número entero y la revisión de progreso actual. Conserva la puntuación y nunca reduce un progreso mayor de MAL. Si falla el proveedor, guarda el envío en la cola persistente de reintentos y muestra «MAL pendiente». Solo muestra éxito confirmado y desactiva el ojo cuando MAL lo reconoce. En revisionado, el ojo es una actualización explícita del progreso original; la detección automática sigue conservándolo.

Debajo de los capítulos, «Sigue explorando» tiene dos pestañas. **De esta saga**, seleccionada al abrir, prioriza relaciones aprobadas (secuelas, precuelas, temporadas, películas y especiales) y añade coincidencias por nombre, identificadas como «Nombre parecido» sin afirmar parentesco. **Por géneros** usa los géneros públicos de `sa1_catalog_source` de AnimeAV1 y ordena por cantidad compartida; no restringe las sugerencias a la biblioteca o lista MAL del usuario. Las sugerencias abren la ficha para elegir qué ver.

Validación: `watch-page-http-check.json`, `watch-page-ui-check.json`, `watch-room-browser-check.json` y `mysql-check.json`. Incluye cuenta/proveedor MAL ficticios, marca manual antes del 80 %, reintentos, identidad/revisión antiguas rechazadas, relaciones pendientes excluidas, consultas MariaDB y navegación con video sintético. Revisión visual en el navegador integrado (1365×900 y 390×844), sin cambios en una cuenta MAL real. La verificación en Brave y el respaldo de producción se aplazaron por indicación del propietario.

El publicador usa Python con Pillow para comprobar los iconos PNG que InfinityFree recomprime. Solo se acepta una codificación alternativa con dimensiones, píxeles RGBA y datos de color idénticos. Registra el hash de origen y el hash final en el manifiesto, vuelve a leer todos los archivos por FTPS y exige que PHP, JavaScript y los demás archivos conserven exactamente sus bytes. No se modifica el dibujo del icono.


## Corrección del límite del reproductor · 22 de octubre de 2026

Abrir un capítulo ya no ejecuta el scraper: devuelve los servidores guardados y la sesión de reproducción. La consulta de servidores se hace por separado mediante `player_servers` (POST, CSRF y administrador). Si no hay servidores y los datos caducaron, la página la solicita automáticamente; un límite del scraper devuelve el estado de espera y su próxima hora permitida, sin sustituir la página por un error. Solo hay un temporizador, cancelado al cambiar de capítulo, salir o cambiar de cuenta. Los servidores ya disponibles pueden reproducirse durante la espera; actualizar sus datos conserva el iframe y la sesión activa. Los usuarios normales disponen de «Solicitar servidores», que reutiliza la cola central y sus permisos/cuotas. El mantenimiento automático de la pestaña se pausa mientras se ve un capítulo.

Las regresiones HTTP simulan el cupo global agotado con caché y sin caché, comprueban el formato seguro de los enlaces, los permisos y que actualizar servidores no renueve la sesión de reproducción. Las pruebas JavaScript comprueban el temporizador cancelable, que no se sustituya el video activo y que una cuenta normal solicite trabajo central. Pasaron las once suites HTTP, diecisiete JavaScript, trece locales y once comprobaciones MariaDB; la publicación y los archivos públicos se verificaron por HTTPS. Las pruebas usaron cuentas locales y MAL ficticio, sin descargar capítulos reales. No se repitió la revisión visual en Brave.


## Reproductor simplificado · 23 de octubre de 2026

El siguiente capítulo queda siempre activado, con aviso de ocho segundos y cancelación para esa ocasión. También funciona en pestañas ocultas cuando el navegador permite ejecutar el temporizador. Se retiraron las casillas de siguiente automático y preferencias por anime, el botón de iniciar revisionado y todo el panel de diagnóstico. Volumen, velocidad, servidor e idioma se guardan globalmente. Las preferencias antiguas desactivadas se normalizan a la nueva política; se conservan los datos de revisionados anteriores y se puede volver al seguimiento de MAL desde la ficha.

El siguiente episodio pide reproducción al recibir datos válidos del video. La elección de reanudar una posición guardada se conserva. Funciona con la señal de final de MP4Upload y la extensión; los otros servidores y las políticas de autoplay del navegador mantienen sus limitaciones. Las consultas nuevas de servidores también respetan el idioma y servidor preferidos. Se muestran avisos breves para errores de posición y sesiones reemplazadas.

Pasaron doce suites HTTP (dos hallazgos de revisión reproducidos con MAL ficticio), diecisiete JavaScript, trece suites locales y once comprobaciones MariaDB. En el navegador integrado se comprobó con video sintético el final del capítulo 6, el aviso de ocho segundos, el paso al 7 y su reproducción sin otro clic. No se modificó una lista MAL real ni se descargaron capítulos reales. El publicador finaliza los hashes de iconos después de verificar los archivos de código, comprobando que la recompresión diferida del alojamiento conserve píxeles y colores.

La revisión completa y las recomendaciones pendientes están en [REVISION-WEB-2026-10-23.md](REVISION-WEB-2026-10-23.md). Se distingue lo aplicado de lo recomendado.


## Revisión implementada · 23 de octubre de 2026

Confirmación de vínculos antes de enviar progreso a MAL, capacidad reservada para servidores y ejecutor central por visitas, mensajes y estados reales de tareas, paginación de cola bajo demanda y fallos persistentes informados por la PC. Reanudación exacta en portada, escenario persistente, búsqueda de capítulo, intro por tramo, escenas privadas y recorrido de saga. Colecciones, bandeja MAL, radio sincronizada con control de conflictos, exportación completa por bloques, modo compartido, guía inicial, actualización PWA diferida, caché con concesión y diagnóstico sin secretos.

Los cambios y sus límites se detallan en [CAMBIOS-REVISION-2026-10-23.md](CAMBIOS-REVISION-2026-10-23.md). El comando actual de comprobación/publicación y la recuperación están en [OPERACION.md](OPERACION.md). La revisión original se conserva como diagnóstico previo.

La fuente publicada pasó 13 suites HTTP con MAL ficticio, 19 suites JavaScript, 13 suites locales y 15 comprobaciones MariaDB. El navegador integrado verificó colección, intro, escenas, búsqueda, 80 % y siguiente con video sintético, reanudación y favoritos musicales persistidos, además de la cancelación y las páginas de una cola ficticia de ochenta capítulos. No se descargaron capítulos reales ni se cambió una cuenta MAL real. Se verificaron la salud pública, archivos de la versión y reversión de código en el alojamiento.

Sin visitas ni un ejecutor externo compatible con InfinityFree, la cola de actualización espera. Las versiones de PC que no informan intentos se indican como tales. Brave y la copia real de producción siguen aplazados; la restauración completa se probó en bases aisladas. El contenedor de pantalla completa se conserva, pero la superficie nativa del navegador integrado no sustituye la prueba en Brave.


## Diseño Medianoche · 24 de octubre de 2026

Navegación superior y móvil inferior, tipografía editorial con fuentes locales, paleta tinta/papel/bermellón, catálogo de pósters ampliados, fichas con progreso real y un sistema visual coherente para todos los apartados. [Cambios y alcance](MEDIANOCHE-2026-10-24.md).

La versión pasó 13 suites locales, 20 JavaScript, 13 HTTP y 15 comprobaciones MariaDB. La revisión visual recorrió diez apartados en escritorio y móvil, y comprobó también 320 px, 768 px, tema claro, foco y controles sobre video sintético. Se verificaron la versión pública, sus archivos y la reversión de código. No se alteró una cuenta MAL real ni se descargaron capítulos reales.


## Ajustes móviles · 24 de octubre de 2026

Iconos de instalación para Android y Apple, manifiesto estable y reproducción móvil con los controles originales de MP4Upload. La pantalla completa solicita orientación horizontal y la libera al salir, cuando el sistema lo permite. La campana abre un panel de notificaciones sobre la vista actual, con estados, desplazamiento y marcado como leídas. [Alcance y límites de la comprobación](MOVIL-2026-10-24.md).

Pasaron 13 suites locales, 22 JavaScript, 13 HTTP y 15 comprobaciones MariaDB, además de la verificación de la publicación. La interfaz se revisó con video sintético en el navegador integrado; no se comprobó la rotación física ni la instalación en un teléfono real.


## Cookie del manifiesto · Brave Android

La petición del manifiesto sin cookies recibía HTML de la comprobación de InfinityFree, aunque los PNG eran públicos. El enlace ahora declara `crossorigin="use-credentials"`. La verificación pública reproduce la petición indicada por el HTML sin ejecutar una segunda comprobación del hosting: antes obtenía HTML y después obtiene el JSON correcto. Las pruebas generales pasaron; la instalación nativa del icono requiere confirmación en Android real. [Detalles](MOVIL-2026-10-24.md).


## Cliente Android nativo

El proyecto `../YomaTVAndroid` ofrece descargas locales, reanudación, reproducción sin conexión y envío del 80 % a MAL. Reutiliza la cuenta web; la aplicación Windows se conserva. El plan Android no altera una sesión de reproducción existente. [Contrato y pruebas](ANDROID-2026-10-24.md).

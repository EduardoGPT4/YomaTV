# YomaTV · 2026.10.25.2

Descargador general para **cualquier anime publicado en AnimeAV1**, con descarga por enlace, cola compartida con la web y automatización de temporada opcional. Incluye Python, SQLite, Tk, yt-dlp, FFmpeg y la bandeja de Windows dentro de un único `YomaTV.exe`. Reutiliza el motor, los rangos y los textos del descargador AnimeAV1; funciona sin instalar aquella aplicación ni consultar la API oficial.

## Empezar

1. Abre `YomaTV.exe` o `Iniciar.cmd` desde una carpeta donde puedas escribir. La primera pestaña es **Descargar anime**.
2. Pega la ficha de cualquier anime o el enlace de un capítulo y pulsa **Analizar enlace**. Elige todos, una selección con Ctrl/Shift o rangos como `1-12,15,20-100`; se admiten capítulos decimales.
3. Elige idioma, MP4Upload/Voe, calidad y carpeta, y pulsa **Descargar selección**. La **Cola general** muestra los animes pedidos desde enlaces, web o temporada, con progreso, pausa y errores. **Reintentar fallidos** usa la selección o todos los fallidos si no hay selección. Los completados no se reinician.
4. Puedes cerrar la ventana y continuar desde la bandeja. **Continuar cola** descarga lo pendiente sin consultar todo el horario. En **Configuración** puedes activar el inicio con Windows y guardar las preferencias compartidas.

**Temporada opcional:** en instalaciones nuevas la revisión automática está apagada. Activa **Activar revisión automática de temporada** en Configuración y pulsa **Guardar configuración** si quieres seguir el horario. La hora predeterminada es **12:00**, en hora local de Windows. La configuración antigua de SeasonAV1 se conserva al actualizar: la aplicación no apaga una automatización que ya habías activado.

La primera revisión descarga **todos los capítulos disponibles de todos los animes del horario de lunes a domingo**, uno por uno. La aplicación no limita el primer lote al capítulo más reciente. Los videos que no estén disponibles en los servidores/idiomas permitidos quedan registrados como pendientes de otro intento.

Las preferencias, videos, parciales, códigos de emparejamiento y tareas de esta instalación se conservan al actualizar. Los nombres internos `datos/seasonav1.sqlite3` y la identidad de la tarea anterior se mantienen para evitar dos registros o dos bandejas. El antiguo AnimeAV1.exe también se conserva; no se borra su historial. Al iniciar Windows se muestra únicamente la bandeja.

Con la automatización activada, las revisiones siguientes consultan el horario y revisan los animes de los días vencidos. También detectan capítulos publicados tarde y animes recién incorporados. **Revisar temporada ahora** y **Prueba de temporada** pueden revisar toda la semana de forma manual. Preparar un anime clásico por enlace no lo convierte en una serie seguida automáticamente.

## Organización

```text
<destino>/
└── otoño2026/
    └── nombre-del-anime/
        ├── Nombre - 0001 [SUB].mp4
        ├── Nombre - 0002 [SUB].mp4
        └── archivos/
            ├── Nombre - 0001 [SUB].json
            ├── <identificador>.lock
            ├── parciales/
            └── invalidos/
```

Los nombres eliminan caracteres inválidos de Windows. Se usan cuatro dígitos para ordenar capítulos y se admiten episodios decimales. Los identificadores de anime excesivamente largos se acortan con una huella para evitar colisiones.

La temporada actual se calcula por fecha: invierno ene–mar, primavera abr–jun, verano jul–sep y otoño oct–dic. Por defecto, cada anime conserva la temporada donde SeasonAV1 empezó a descargarlo. Puedes escoger la temporada de estreno como carpeta inicial o separar **los capítulos nuevos** por la temporada actual. Cambiar estas opciones no reorganiza videos anteriores; cada capítulo pendiente conserva la temporada asignada al descubrirlo.

## Automatización y recursos

Con la temporada automática activa, la tarea de Windows tiene una revisión diaria y `StartWhenAvailable` para recuperar una hora perdida. **Iniciar en la bandeja con Windows** añade un disparador de inicio de sesión con 30 segundos de espera. En modo general conserva ese inicio y recupera solamente la cola pendiente; no instala un disparador diario de temporada. Se ejecuta con los permisos normales del usuario y no almacena contraseñas. El mecanismo de recuperación está descrito en [la documentación de Microsoft](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-startwhenavailable-settingstype-element).

Cuando la PC estuvo apagada, al iniciar sesión se revisan los días pendientes, los capítulos interrumpidos y las series previamente conocidas que correspondían a esos días. No se necesita reconstruir cada día por separado: se comparan sus capítulos publicados con SQLite. El sitio solo publica su horario actual; no puede reconstruirse una serie que apareció y desapareció mientras la aplicación nunca la había conocido.

El EXE se compila como aplicación de Windows **sin consola**: el inicio automático no abre CMD ni la ventana principal. Por defecto, la bandeja permanece disponible al terminar la revisión y espera mensajes de Windows y órdenes locales, sin consultar el sitio ni SQLite periódicamente. El Programador de tareas entrega la siguiente revisión a la instancia existente; no crea otra bandeja. Puedes desactivar **Mantener bandeja abierta al terminar** para que el proceso salga al acabar el trabajo.

Hay una sola ventana por carpeta de datos. Pulsar de nuevo el icono, abrir **Historial** o ejecutar otra vez el EXE trae la ventana existente al frente y la restaura si está minimizada. Cerrar la ventana conserva la bandeja y las descargas. FFmpeg usa dos hilos de decodificación durante las muestras de verificación.

La tarea requiere una sesión de usuario iniciada para mostrar la bandeja y las notificaciones. No despierta la PC. Windows puede retrasar una tarea pendiente mientras vuelve a estar disponible; el disparador al iniciar sesión hace la comprobación de recuperación.

**Desactivar horario** apaga la automatización y el inicio con Windows, eliminando solamente la tarea de esta instalación. **Salir** detiene el trabajo actual y conserva los parciales; no elimina la tarea. **Pausar** conserva una pausa persistente hasta pulsar **Continuar**. Guardar configuración conserva esa pausa. Mover el ejecutable requiere desactivar la tarea antigua y volver a activarla desde su nueva ubicación.

## Preferencias y fallos

- Idioma: SUB, LAT o DUB. Si falta, esperar o aceptar SUB, según tu elección.
- Servidor: MP4Upload o Voe. Si falta o falla, esperar o probar otro compatible. Los otros reproductores del sitio no están habilitados.
- Calidad: preferir 1080p o 720p; aceptar la mejor disponible, aceptar una menor o esperar la calidad exacta. No se transcodifica el video automáticamente. Si el servidor no informa la resolución, FFmpeg comprueba la real tras descargar: una fuente rechazada por calidad se conserva en `archivos/parciales/` y no aparece como capítulo completo.
- Favoritos y exclusiones: selección múltiple en el horario; los botones agregan/quitan esa selección de cada lista. **Solo favoritos** limita las descargas a esa lista. Las exclusiones siempre tienen prioridad.
- De 1 a 4 descargas simultáneas después del primer lote, con un único capítulo a la vez por anime. El límite de velocidad de los videos se reparte entre los trabajadores; `0` significa sin límite.
- Consultas HTML separadas por dos segundos por defecto, gzip y validadores HTTP ETag/Last-Modified. No se abre un navegador ni se descargan imágenes del horario. Para descubrir todos los capítulos y sus reproductores sí se necesita consultar el HTML de la ficha y del episodio correspondiente.

yt-dlp tiene reintentos con espera exponencial. Los errores temporales del capítulo se reintentan adicionalmente a los 10, 30 y 90 segundos; si siguen fallando, SQLite conserva un próximo intento con espera creciente. Un servidor/idioma/calidad no disponible se revisa de nuevo más tarde. **Revisar ahora** permite adelantar el reintento manual. Los errores de un anime no impiden continuar los demás.

SQLite registra capítulos únicos por anime, número e idioma solicitado, con idioma real, servidor, ruta, tamaño, SHA-256, fecha y estado. Tras un apagado se recuperan los estados interrumpidos. Si el MP4 ya se guardó pero faltó confirmar la fila en SQLite, se verifica y registra sin descargarlo otra vez. Los bloques `.lock` se liberan por el sistema al terminar el proceso; el archivo puede permanecer en disco.

La verificación exige tamaño mínimo, audio y video, lectura de todos los paquetes y muestras decodificadas al inicio, mitad y final. Detecta truncamientos y numerosos errores; no decodifica todos los fotogramas ni compara con un hash oficial del servidor.

Las notificaciones de descarga/error respetan la configuración de Windows. **Historial** y `datos/seasonav1.log` guardan el detalle. Si el horario cambia su estructura o entrega una verificación antibot, la revisión se detiene y deja un error visible; no marca capítulos como descargados.

## YomaTV Web

La web está en [hk-br035.gt.tc/seasonav1](https://hk-br035.gt.tc/seasonav1/). Pulsa **Conectar web**, copia el código y empareja la página desde **Conectar YomaTV**. Después, Preparar todos o Preparar seleccionados envía la cola directamente al programa y comienza la descarga en la bandeja. Permite el acceso a la red local si lo pide el navegador. Funciona en el mismo PC; la aplicación debe permanecer en la bandeja.

Se aplican las preferencias de idioma, servidor, calidad, horario y favoritos; se conserva tu carpeta y no se reemplazan videos existentes. La importación valida todas las direcciones y no permite URLs de otros sitios. El puente usa únicamente `127.0.0.1:47653` con token y el dominio HTTPS autorizado. El código no va a MySQL y se puede revocar desde la ventana de conexión.

Si la conexión no está disponible, la web descarga un JSON para **Importar cola web**. Mientras la página esté visible, confirma automáticamente los capítulos verificados; conserva el intercambio de resultados mediante archivos como alternativa.

La cola manual se añade sin iniciar una exploración completa del horario. Las revisiones automáticas posteriores continúan funcionando en Windows. Si usas solo favoritos, los capítulos que pediste explícitamente en la web también son elegibles; los excluidos siguen omitiéndose.

El puente de esta versión también recibe preferencias al guardarlas en la web y comunica el estado de cada solicitud: cola, progreso, verificación, pausa o error. Conserva la carpeta elegida y la pausa del usuario. Las referencias web se guardan en SQLite para recuperar confirmaciones de colas antiguas. Las tarjetas y los contadores se actualizan automáticamente mientras la página está visible.

**Exportar resultados web** genera los registros de los capítulos completados y verificados. **Cola para la PC → Opciones de respaldo → Importar resultados** permite confirmarlos manualmente. Los JSON no contienen credenciales ni rutas de tus archivos locales. Los resultados grandes se dividen en archivos menores de 2 MB. La web recibe el progreso y los recibos del puente, sin almacenar los videos.

```powershell
.\YomaTV.exe --import-web .\SeasonAV1-cola.json
.\YomaTV.exe --export-web .\SeasonAV1-resultados.json
```

## Terminal y modo de prueba

```powershell
.\YomaTV.exe --dry-run --report plan.json
.\YomaTV.exe --run-now
.\YomaTV.exe --resume
.\YomaTV.exe --window
.\YomaTV.exe --tray
.\YomaTV.exe --install
.\YomaTV.exe --inspect-task
.\YomaTV.exe --uninstall
```

`--dry-run` consulta el horario y las fichas, muestra qué descargaría y no baja videos, modifica la cola ni consume la revisión pendiente. Puede guardar caché HTML y avisos de diagnóstico. `--install` activa la tarea con la configuración guardada; `--scheduled` es el modo utilizado por Windows. `--data-dir` o `SEASONAV1_DATA_DIR` permiten una carpeta de datos separada.

Al no tener consola, las órdenes pueden guardar su resultado con `--report`, por ejemplo `--inspect-task --report tarea.json`. El motor interno de yt-dlp conserva las tuberías de progreso y errores aunque tampoco tenga consola.

Puedes compartir solo el EXE. Las preferencias, la base de datos y los videos son archivos aparte. Para trasladar una sesión, conserva `datos/`, los videos y sus parciales; mantén una ruta de destino válida y registra la tarea en el equipo nuevo.

## Desarrollo y verificación

Código independiente en `seasonav1/`. `seasonav1/engine/` conserva una copia del motor ya probado, adaptada a SeasonAV1; no importa el programa vecino.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe build_exe.py
```

La mascota original de pelo blanco se generó con ImageGen. PNG, ICO y prompt se conservan en `assets/`. El icono incluye siete tamaños y se aplica a la ventana, bandeja y ejecutable.

La compilación genera `build/release/YomaTV.exe`, para poder verificarla antes de sustituir un ejecutable que esté abierto.

Consulta `VERIFICACION.md` para los resultados comprobados. Ejecutable Windows x64, probado en Windows 11.

El código del descargador anterior se retiró de la carpeta principal; el motor vigente está en `seasonav1/engine/`. Los builds y datos de prueba se pueden regenerar. El diagnóstico `verification/check_general_exe.py` usa el EXE instalado si no hay una compilación nueva y trabaja con datos aislados. El respaldo del código retirado y las evidencias históricas está en `../_archivo/codigo-anterior-2026-10-13.zip`.

## Controles desde la web · entrega 3

La versión 2026.10.25.2 añade prioridad y pausa por anime, reintento de fallidos y comprobación de archivos mediante el puente local emparejado. La prioridad se aplica al siguiente anime; los capítulos mantienen su orden. Una pausa global se conserva. Comprobar usa existencia y tamaño registrado, sin enviar rutas ni leer todos los videos.

La redescarga requiere comprobar primero el archivo y confirmarla en la web. Una revisión de solicitud impide que una confirmación antigua cierre esa redescarga antes de terminar. El ZIP portable solo incluye el ejecutable y este documento, sin datos ni emparejamiento.

# YomaTV Android

Aplicación Android 8 o posterior, versión 1.1.1. Integra el catálogo y la cuenta de la web con un gestor de descargas y un reproductor local nativos. Usa la nueva identidad YomaTV, pestañas independientes e icono compartido con la web y Windows. No necesita la aplicación de Windows.

## Uso

1. Instala el APK firmado. Abre Catálogo e inicia sesión con tu cuenta de YomaTV Web.
2. Conecta MyAnimeList y confirma el vínculo del anime desde la web. Se reutiliza la conexión de tu cuenta; el APK no contiene el Client Secret ni guarda tokens MAL.
3. En la ficha, pulsa **Capítulos para llevar**. Se proponen los siguientes tres sin ver; puedes cambiar la selección o elegir todos, hasta 500 por lote. En el reproductor online aparece **Guardar en el celular** para ese capítulo.
4. Abre **Descargas**. La lista principal agrupa por anime y, al entrar, muestra los capítulos, tamaños, progreso, pausa, reintento, verificación y eliminación.
5. Pulsa **Ver** para reproducir el archivo sin conexión. Se recuerda la posición; al alcanzar el 80 % de la posición se guarda el visto y se prepara su actualización en MAL. Adelantar hasta ese punto también cuenta. Si falta internet, el pendiente permanece guardado.

**Más** reúne biblioteca, MAL, radio, favoritos, colecciones, actividad, estadísticas y ajustes. La aplicación ofrece una sola cabecera y una sola navegación inferior.

## Descargas y almacenamiento

- MP4Upload, idioma elegido en el reproductor o en las preferencias web. Si falta, se informa y no se sustituye silenciosamente. Se conserva la calidad original disponible; no se convierte el video.
- Una descarga a la vez. Por defecto usa una red sin medición, la restricción de Android habitual para «solo Wi-Fi». Puede habilitarse el uso de datos desde los ajustes nativos.
- WorkManager mantiene la cola entre cierres y reinicios. Android puede aplazar tareas por conectividad, batería, espacio o límites de ejecución. Al volver a ejecutarla, se conserva el parcial.
- Hasta cinco intentos por capítulo con espera progresiva. Los enlaces temporales se obtienen nuevamente desde el HTML público; no se usa la API oficial de AnimeAV1.
- Reanudación con Range y ETag/Last-Modified. Si cambia el archivo o el servidor ignora el rango, se reinicia sin añadir bytes a una versión distinta.
- Verificación de tamaño, estructura MP4 y muestra decodificada; se guarda SHA-256 para comprobar modificaciones posteriores. El hash es local: no sustituye una suma publicada por el servidor.
- Archivos específicos de la app: `Movies/cuenta/temporadaAño/anime/capitulos/Título - 0001 [SUB].mp4`. Si se desconoce la temporada de emisión, usa `biblioteca`. La base de datos y los bloqueos están en el almacenamiento interno, separados de los videos.
- Eliminar un video conserva su historial. La limpieza de vistos al cerrar el reproductor es opcional y viene apagada. Android elimina los archivos específicos de la app cuando se desinstala.

## Reproducción y MAL

El reproductor de archivos descargados utiliza Media3, orientación horizontal, saltos de diez segundos, salto de intro, velocidad, picture-in-picture y siguiente automático si el capítulo siguiente está guardado. La posición se conserva al saltar, pausar y cerrar, y periódicamente durante la reproducción.

El 80 % automático fiable corresponde al reproductor local. La reproducción online conserva los controles originales del servidor y el ojo de la web. La app no inventa telemetría de iframes externos.

Los pendientes pertenecen a la cuenta YomaTV y a la identidad MAL capturada al preparar la descarga. Cambiar de cuenta no los atribuye a otra. Una corrección del progreso, un cambio de identidad o un vínculo no confirmado detiene el envío y explica el motivo. Si se preparó sin cuenta MAL, el visto local se conserva; debe revisarse desde la web antes de atribuirlo a una cuenta nueva.

## Compilar

Requiere JDK 17, Android SDK 36 y acceso a Google Maven/Maven Central. En PowerShell:

```powershell
./tools/build.ps1 -Release
```

La primera compilación crea un certificado personal en `private/`. Conserva esa carpeta para firmar futuras actualizaciones con la misma identidad. No se incluye en el ZIP de fuente. El resultado distribuible queda en `artifacts/`.

```powershell
./gradlew.bat :engine:test :app:lintDebug :app:assembleDebug :app:assembleDebugAndroidTest
./tools/verify_android.ps1 -Device emulator-5580
```

El namespace del código es `app.yomatv.mobile`. El ID de instalación QA sigue siendo `app.seasonav1.mobile.qa`; la distribución conserva `app.seasonav1.mobile` y la firma anterior para actualizar sin perder datos. Los fixtures, el acceso HTTP local de pruebas y el video sintético no forman parte del APK público.

## Pruebas y límites

Consulta `RENDIMIENTO.md` y los informes de `verification/`. Las pruebas Android usan un emulador Android 15, cuentas ficticias, un video sintético y una reanudación real de MP4Upload. No se probó un teléfono físico ni se modificó una cuenta MAL real. Las cifras de descarga describen esa red y ese servidor, sin prometer la misma velocidad en otros dispositivos.

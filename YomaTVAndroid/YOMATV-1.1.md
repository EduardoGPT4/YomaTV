# YomaTV Android 1.1.0

APK universal de 1.894.406 bytes, Android 8 o posterior. SHA-256 `c208a8b6bf69ce47c0f5eef9e6e3475185617f6244955e7fc61d1ea25cd58e23`.

- Inicio, Temporada y las secciones web abiertas desde Más conservan WebViews independientes, creados al utilizarlos. Cambiar de apartado no destruye el DOM ni sustituye el capítulo, la búsqueda o el desplazamiento. Las vistas ocultas se pausan.
- Descargas mantiene la agrupación por anime, incorpora portadas, espacio disponible, filtros y acceso a los capítulos. Más es una pantalla completa con las funciones existentes.
- El reproductor online conserva MP4Upload en móvil, controles claros, audio/servidor juntos, visto manual en MAL, episodios señalados y apartados desplegables. El reproductor local y su marca automática al 80 % conservan su comportamiento.
- El nuevo icono se deriva de la imagen suministrada por el propietario. La identidad de instalación, la clave de firma, los datos y dos clases de compatibilidad WorkManager permanecen disponibles.

## Verificación

18 pruebas JVM del motor. El conjunto Android informa nueve escenarios: ocho ejecutados y uno de red real omitido en esta regresión; además pasó la comprobación de presentación y objetivos táctiles de 44 dp. Se probó conservar capítulo, búsqueda, filtros, historial y desplazamiento al pasar por Temporada, Descargas y Más. Se comprobó instalar el APK publicado sobre 1.0.2 con `install -r`: terminó como 1.1.0 sin desinstalación, con el mismo ID y certificado.

Windows pasó 67 regresiones y el autodiagnóstico del EXE compilado. La compilación de ambos programas también pasó en GitHub Actions: ejecución 40174235545. Ese trabajo fue de comprobación: conservó los instaladores ya publicados; la publicación actual se realizó con el proceso local automatizado y se verificó descargando ambos archivos anónimamente con su SHA-256.

Las pruebas Android usan un emulador Android 15, una cuenta ficticia y un video sintético. No equivalen a pruebas de batería, red móvil o temperatura en un teléfono físico. MyAnimeList se prueba con respuestas simuladas. Los datos de velocidad anteriores de `RENDIMIENTO.md` corresponden al motor de 1.0.2 y no se presentan como una nueva medición de esta interfaz.

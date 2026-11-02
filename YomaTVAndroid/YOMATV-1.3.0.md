# YomaTV Android 1.3.0

- MP4Upload online usa el mismo reproductor Media3 que los capítulos guardados: pausa, saltos de diez segundos, intro, velocidad, horizontal y picture-in-picture.
- En la página del capítulo pulsa **Reproducir**. No se crea una descarga; si ya existe una copia completa, se reutiliza.
- Se recuerda la posición. Al alcanzar el 80 % se guarda el visto y se prepara la actualización de MAL, tanto online como sin conexión. Es necesario tener MAL conectado y el anime vinculado; un envío sin internet queda pendiente.
- La reproducción online puede abrir el siguiente capítulo tras ocho segundos. El contador permite cancelarlo.
- Los errores de conexión ofrecen reintento desde la posición guardada. Los enlaces temporales se consultan de nuevo; no se cambia silenciosamente el idioma.
- Las descargas y el historial existentes se conservan. La migración añade un registro independiente para reproducción online, con protección ante cambios de cuenta MAL y de revisión del progreso.
- Otros servidores conservan su reproductor incrustado. Los navegadores y las versiones anteriores del APK mantienen su funcionamiento.

Verificación: pruebas instrumentadas con cuentas ficticias y video sintético, pruebas del puente web, migración de SQLite, compilación firmada y análisis Android. Los informes de entrega documentan los resultados ejecutados. No se escriben datos en una cuenta MAL real durante las pruebas.

# YomaTV Android 1.1.5

Los encabezados Tu biblioteca, Preferencias y Explora más pertenecen ahora a un contenedor con su tarjeta. Se separan 26 dp del bloque anterior y 8 dp de su propia tarjeta; se elimina el margen adicional que alejaba la caja del título. El texto usa peso medio, altura adaptable y semántica de encabezado accesible. Las acciones y sus destinos conservan su comportamiento.

## Verificación

Compilación firmada, Android Lint, seis pruebas Android y ocho comprobaciones del puente correctos. La prueba de presentación mide los tres encabezados en la actividad real y comprueba que estén más cerca de la tarjeta inferior, con espacio suficiente respecto al bloque anterior. Se conservan las comprobaciones de navegación, avatar, texto ampliado y carruseles/formularios.

Las vistas superior e inferior se renderizaron desde el árbol real de Views de la app en el emulador QA y se revisaron visualmente. No son capturas de un teléfono físico; los datos son sintéticos. No se modificó una cuenta MAL real.

APK: 1.899.048 bytes, SHA-256 `2bba1c24739e165154617038f71ffab0cca93a58e4feb6a234f82ecac122f2a4`. Conserva el ID y la firma anteriores, con versionCode 9. Actualiza sin desinstalar para mantener tus descargas.

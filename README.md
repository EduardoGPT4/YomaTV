# YomaTV

Catálogo de AnimeAV1, seguimiento con MyAnimeList y aplicaciones para Android y Windows.

- **YomaTVWeb/**: PHP + MySQL y presentación móvil. La web sigue en https://hk-br035.gt.tc/seasonav1/ para conservar OAuth, sesiones y la instalación PWA.
- **YomaTVAndroid/**: Android 8+, catálogo, pestañas con estado independiente, descargas, reproductor sin conexión y sincronización MAL. El ID APK anterior y la firma se conservan para permitir actualizar sin perder datos.
- **YomaTVPC/**: descargador Windows portátil, temporada opcional y puente local. El módulo Python y los nombres de datos anteriores siguen siendo compatibles.
- **release-tools/**: compilación conjunta y metadatos de descarga.

## Instalar

Descarga los binarios desde [Releases](https://github.com/EduardoGPT4/YomaTV/releases). Cada versión incluye tamaños y SHA-256. El EXE puede copiarse junto a la carpeta `datos` de una instalación anterior para conservar su cola; evita ejecutar simultáneamente una copia con otra carpeta de datos.

## Publicar una versión nueva

1. Incrementa `versionCode` y `versionName` en `YomaTVAndroid/app/build.gradle.kts`. Actualiza `YomaTVPC/seasonav1/brand.py` y `assets/version.txt` si cambia Windows.
2. Sube el código y crea una etiqueta `v<versionName>`; también puedes ejecutar el workflow desde Actions. Se rechazan etiquetas que no coincidan con la versión y releases ya existentes.
3. Actions prueba Windows, compila ambos programas, firma Android con la identidad existente, publica APK/EXE/metadatos y verifica la descarga anónima completa.
4. La portada web consulta la última release y actualiza automáticamente versión, tamaño y enlace. No hace falta Google Drive ni subir archivos manualmente.

Los secretos de Actions `ANDROID_KEYSTORE_BASE64` y `ANDROID_KEYSTORE_PASSWORD` contienen la firma cifrada. No están en este repositorio. No se incluyen credenciales MySQL/MAL/FTP, bases de usuarios, videos ni archivos de pruebas privadas. La configuración web de ejemplo requiere valores propios del servidor. La publicación web usa su proceso de releases separado; publicar una aplicación no modifica la base de datos del alojamiento.

Consulta [la migración YomaTV](YomaTVWeb/YOMATV-2026-10-25.md) para los identificadores de compatibilidad y los límites de las pruebas.

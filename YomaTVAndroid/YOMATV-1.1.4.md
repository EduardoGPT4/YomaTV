# YomaTV Android 1.1.4

La cabecera y la tarjeta de Más muestran la foto del perfil MyAnimeList conectado. La web usa la misma foto en la cabecera, Mi cuenta y el panel MAL. La inicial queda de respaldo para cuentas sin foto, desconectadas o imágenes que no cargan.

El servidor consulta el perfil al conectar o comprobar MAL y completa automáticamente las cuentas conectadas anteriormente. El avatar se guarda por usuario e identidad MAL durante un día, usando el almacenamiento personal existente; no requiere una migración de tablas. Los fallos temporales conservan la foto y esperan diez minutos antes de otra consulta. Los clientes solo reciben la URL HTTPS del CDN oficial, sin tokens MAL. Al cambiar de cuenta o desvincular se limpia el avatar y se rechazan respuestas anteriores.

## Verificación

Android Lint, compilación firmada y pruebas del motor correctos. Seis pruebas Android en emulador verificaron avatar, navegación, medidas de texto y presentación; ocho comprobaciones del puente nativo confirmaron también el envío de la foto y el estado de conexión. Las pruebas del componente usan imágenes sintéticas y no consultan una cuenta real.

El flujo HTTP con MAL simulado comprobó caché, cuentas anteriores, imagen ausente o inválida, cambio de identidad, aislamiento y desconexión. Las cinco comprobaciones del cliente incluyen la inicial de respaldo, CDN permitido, fallos de imagen y respuestas tardías de otra cuenta.

APK final: 1.898.844 bytes, SHA-256 `0664086842a550fe7a3adbb0136998d22d05cfd0718dc9adcc0f893221990340`. Conserva la firma e ID anteriores, con versionCode 8. No hubo un teléfono físico conectado durante esta revisión; la prueba Android se hizo en el emulador QA. Actualiza la aplicación sin desinstalar para mantener tus descargas.

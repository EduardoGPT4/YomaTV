# YomaTV Android 1.2.0

Descargas mantiene un solo árbol de vistas. Los avances de bytes, porcentaje y estado actualizan cada fila sin recrear la pantalla, las portadas ni el ScrollView. La posición se restaura después de medir el contenido al volver desde un anime. La portada de Descargas muestra almacenamiento, filtros, transferencias con pausa/cancelación, listas compactas de animes disponibles y la preferencia de Wi-Fi. Los capítulos y las acciones existentes permanecen dentro de cada anime. Cancelar pide confirmación y coordina el acceso al parcial con el bloqueo del escritor.

La cuenta usa una WebView propia. El avatar de la web embebida también abre esta cuenta separada. Más siempre vuelve a su menú nativo, y el capítulo de Inicio conserva su WebView, historial y desplazamiento. No se cambia el diseño de Más.

Inicio usa un destacado horizontal, continuación compacta y progreso real en la lista MAL. Temporada incorpora selector de trimestre, estado, días y tarjetas horizontales en dos columnas. Las temporadas anteriores y los próximos estrenos consultan el catálogo público, sin restringirse a la biblioteca personal. No se inventan horarios de emisión cuando el origen no los proporciona. La guía de instalación de la web se oculta solo dentro del APK.

## Verificación

- Nueve pruebas Android de presentación, labels, avatar, navegación y descargas en emulador. Incluyen cien actualizaciones de progreso sin reemplazar filas ni mover el scroll, regreso desde el anime y cuenta separada de Más/capítulo.
- Nueve comprobaciones del puente JavaScript, incluida la apertura del avatar sin activar acciones de descarga.
- Cinco comprobaciones nuevas del diseño móvil: días, consulta pública de próximos estrenos, cambio de año/trimestre y protección frente a respuestas de otra cuenta.
- Captura del árbol real de Views para Descargas y vista local de Inicio/Temporada con datos de prueba. Las capturas no prueban un teléfono físico ni una descarga real.

Se conserva la firma, el ID de instalación y el almacenamiento de versiones anteriores. Actualiza sobre la instalación existente; no la desinstales para conservar los videos. No se modificó una lista MAL real en las pruebas. Los cambios nativos requieren instalar este APK; los estilos compartidos requieren la publicación web correspondiente.

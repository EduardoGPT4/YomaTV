# YomaTV Android 1.1.2

- Los doce accesos de Más usan iconos vectoriales, independientes de la fuente y los emoji del teléfono. Las filas tienen icono, etiqueta y flecha separados, respuesta táctil y altura de 56 dp.
- La tarjeta Servidor / Audio usa una columna adaptable. Los servidores pueden envolver a otra línea y Actualizar servidores conserva su ancho dentro de la tarjeta.
- Se conserva el certificado y el identificador de instalación de las versiones anteriores. La actualización no requiere desinstalar ni migrar los datos.

## Comprobaciones

Compilación firmada, Android Lint y puente nativo de descargas correctos. Pasaron las tres regresiones de navegación y presentación, incluidos los doce accesos, en emulador. La revisión física se hizo sobre la aplicación principal en un teléfono Android 16 de 1220 × 2712 píxeles: iconos de Más, objetivos táctiles y regreso al mismo capítulo después de cambiar de pestaña. Se usaron capturas y acciones manuales del propietario; no se ejecutó el APK de pruebas en el teléfono. No se marcaron capítulos ni se modificó la lista real de MyAnimeList.

La revisión final confirmó que Actualizar servidores queda dentro de la tarjeta en ese teléfono. También se revisaron Temporada y el estado vacío de Descargas; no se iniciaron descargas para esta revisión visual. El APK instalado se extrajo y comparó por SHA-256 con el archivo final: `65068f210db4872f48927fb73ed68518dd40d482847aca6dac7e051fe5886269` (1.895.862 bytes).

Las capturas y los datos de la sesión quedan en verification/phone-ui, fuera del repositorio público. capture_phone_design.py acepta el dispositivo por argumento y captura únicamente YomaTV en primer plano.

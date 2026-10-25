# YomaTV Android 1.1.3

- Cada pestaña inferior tiene un label centrado bajo el icono, sin heredar el padding de los párrafos. Admite hasta dos líneas y su altura se adapta al texto ampliado.
- Los textos nativos comparten reglas de alineación, interlineado y padding de fuente. Las filas de Más, filtros y cabeceras crecen cuando hace falta; los switches separan el texto del control.
- Los carruseles MAL usan tarjetas con ancho explícito y contenido aislado. Título, progreso y acciones permanecen en su propia tarjeta, también al desplazar horizontalmente.
- La lupa del buscador se centra sobre el alto del campo. Los labels de formularios conservan un espacio propio antes del input; botones, barras de acciones y textos largos pueden envolver.
- El reproductor local adapta su cabecera a la altura real de sus controles; su título y mensajes tienen alineación explícita.

## Verificación

Compilación, Android Lint y las siete comprobaciones del puente nativo correctos. Cinco pruebas Android de layout, navegación y presentación pasaron; la matriz de layouts usa anchos de 320, 360, 412 y 480 dp con escalas de texto entre 90 % y 200 %. Los casos web se construyen a partir del CSS y los renderizadores MAL/buscador reales, con datos sintéticos. Se comprueban solapamientos, recortes, posición de la lupa y separación entre labels y campos.

También pasaron las dos ejecuciones de presentación nativa y reproducción local con la fuente del emulador al 160 %, restaurando la configuración después. Son comprobaciones de medidas internas; las capturas con un aviso de System UI del emulador no se usan como evidencia visual de la aplicación.

En el teléfono Android 16 del propietario se revisaron las tarjetas MAL que antes tenían texto superpuesto, la navegación inferior y el buscador de Temporada. Las capturas físicas confirmaron las correcciones. No se hicieron escrituras reales en MAL. El APK instalado coincide por SHA-256 con el final: `1cbbcc7935cbc1b30f9ce0da2988712d415a89208a8824bb3a18894c9f53760d` (1.897.972 bytes).

Los APK, las capturas y las evidencias privadas están fuera del repositorio público. El CSS de presentación viaja en el APK, de modo que la corrección se aplica sobre la web existente sin cambiar sus datos.

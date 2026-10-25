# Pruebas y rendimiento · YomaTV Android 1.0.2

El APK firmado está publicado y sus bytes se verificaron por HTTPS. La aplicación y su core compilaron con análisis de Android sin errores. Pasaron 18 pruebas del motor, siete escenarios Android, incluida la reanudación real, y siete comprobaciones de integración web. La prueba de biblioteca fuerza marcas de tiempo iguales para comprobar que los capítulos mantienen el orden numérico de preparación.

| Comprobación | Resultado observado |
|---|---|
| APK universal firmado | 1.60 MB; Android 8 o posterior |
| MP4Upload, archivo completo, motor JVM en Windows | 107.24 MiB; 821.9 s; 0.130 MiB/s (1.09 Mbps) |
| Motor JVM, servidor local sintético de 64 MiB | 229.2 MiB/s; no representa velocidad de internet ni de un teléfono |
| Android 15 emulado, reanudación real | Últimos 8 MiB en 70.92 s; 0.113 MiB/s; pausa intermedia y SHA-256 idéntico |
| Reproducción local de prueba | Lista en 2.52 s; horizontal; visto al saltar a 25/30 s |
| Biblioteca de 100 capítulos | Una tarjeta de anime; lectura caliente media 2.34 ms; vista inicial 1.66 s |
| Reposo, compilación QA instrumentada | CPU visible 2.80 %; segundo plano 0.18 %; PSS del proceso 96.9 MiB |
| Decodificación del archivo completo | 17345 fotogramas; sin errores de audio/video |

La prueba Android recibió un parcial de 99.24 MiB para simular una interrupción. Descargó los 8 MiB restantes desde MP4Upload, se pausó, se reanudó y verificó el archivo completo. No se presenta como una descarga completa iniciada en el teléfono.

La CPU se muestreó durante cinco segundos en un emulador acelerado de dos núcleos. PSS es la memoria proporcional del proceso, no el consumo agregado de todos los servicios del sistema. No se midió batería, temperatura, una red móvil ni un teléfono físico. La velocidad depende del servidor y de la ruta de red; hubo también intentos de conexión que agotaron su tiempo de espera.

El archivo de origen contiene una referencia QuickTime a una pista de capítulos ausente. FFmpeg completó la decodificación y no informó errores de audio/video; ese aviso de metadatos se conserva en el informe, separado de los errores de reproducción. No se silenció un fallo de medios para aprobar la prueba.

Se probaron rangos ignorados o incorrectos, cambios de ETag, cortes, respuestas HTML, duplicados, eliminación y nueva preparación, aislamiento de cuentas, recuperación tras renombrar el archivo y antes de confirmar SQLite, transporte con cookies y CSRF, orientación y marca por posición. MAL se probó con respuestas ficticias y las regresiones PHP existentes; no se cambió una lista MAL real.

SHA-256 del APK: `1704f3dfde25542bb08da7cd729c40958fe237126c2b9f956a9b7f294986de0e`.

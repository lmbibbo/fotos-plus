# Proposal

## Why

El escaneo ya produce las sugerencias de viajes y períodos, pero no hay forma de mirarlas.
El usuario no puede revisar si un viaje está bien agrupado ni ver qué fotos contiene sin abrir
el JSON a mano, así que el archivo provisional queda sin auditar. Hoy la única salida es leer el
archivo de sugerencias en un editor de texto.

Además, el índice de fotos y el archivo de sugerencias están separados: el índice tiene las
fotos y el archivo de sugerencias tiene los viajes, pero ninguno enlaza al otro. El visualizador
necesita cruzarlos, y ese cruce todavía no existe.

## What Changes

- Se agrega el subcomando `fotos-plus view <index.json>`, que genera un archivo HTML
  autocontenido con un grid de las fotos ya escaneadas. Es aditivo: no cambia ningún
  comando ni formato existente.
- El visor muestra una tarjeta por viaje sugerido, una por período sugerido y una por las fotos
  que no caen en ninguno de los dos, ordenadas por fecha ascendente. Un viaje o período
  declarado que se quede sin fotos propias, porque caen dentro de otro grupo, conserva su
  tarjeta y lo indica.
- Cada tarjeta muestra cinco miniaturas de 200 px extraídas de las fotos de ese grupo, la
  cantidad de fotos del grupo, el rango de fechas y el país cuando existe.
- Si el archivo de sugerencias contiguo al índice no existe, el visor genera el mismo HTML con
  un grid plano de todas las fotos, sin agrupar.
- Las miniaturas se embeben en base64 y el HTML se escribe junto al índice de entrada.
- La orientación EXIF se aplica al generar la miniatura, de modo que la proporción final es
  correcta y el visor no interpreta el tag.
- El cruce entre el índice de fotos y el archivo de sugerencias se calcula al generar el
  visor, en tiempo de ejecución, sin modificar el formato de ninguno de los dos archivos.

Fuera de alcance en esta etapa: pantalla completa, navegación con teclado y zoom al original.

## Capabilities

### New Capabilities

- `photo-viewing`: Genera un archivo HTML autocontenido que presenta las fotos ya escaneadas,
  agrupadas según el archivo de sugerencias cuando existe, o en un grid plano cuando no existe.

### Modified Capabilities

Ninguna. El escaneo y la emisión de sugerencias no cambian de comportamiento.

## Impact

- `fotos_plus/cli.py`: nuevo subcomando `view` y su wiring en el parser.
- `fotos_plus/viewer.py`: módulo nuevo, responsable de cruzar el índice con las sugerencias,
  generar las miniaturas y componer el HTML.
- `fotos_plus/photos.py`: reutilización de la apertura de imágenes de Pillow para generar
  miniaturas; se le aplica la transformación EXIF.
- Sin cambios en el formato del índice ni del archivo de sugerencias, así que los archivos ya
  escaneados siguen siendo válidos y no hace falta reescanear.
- Sin dependencias nuevas: ya se usa Pillow y la biblioteca estándar.
- Sigue siendo una herramienta local sin servidor: el HTML generado no necesita conexión.

## Rollback

- Revertir el commit del cambio elimina el subcomando `view` y el módulo `viewer.py`. No hay
  migraciones de datos ni cambios de formato, así que el rollback es limpio.
- Los archivos HTML generados son derivados y se pueden borrar sin consecuencia: se vuelven a
  generar con `fotos-plus view` cuando se quiera.
- Los índices y los archivos de sugerencias no se tocan, así que un rollback no puede dejarlos
  en un estado inconsistente.

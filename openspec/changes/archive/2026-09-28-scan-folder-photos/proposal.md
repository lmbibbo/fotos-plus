# Proposal

## Why

Hoy no hay ninguna forma de saber qué fotos hay en una carpeta. La organización por
fechas, lugares y personas, así como el visualizador, necesitan partir de un inventario
confiable: sin él, cada criterio tendría que recorrer el disco por su cuenta. Este
primer cambio resuelve solo esa base: recorrer una carpeta, identificar las fotos que
contiene y dejar un índice reutilizable.

## What Changes

- Nuevo comando de línea `fotos-plus scan <ruta>` que recibe la carpeta a explorar.
- El escaneo es recursivo: incluye la carpeta indicada y todos sus subdirectorios, y
  registra la ruta de cada foto relativa a la raíz escaneada.
- Por cada foto se registra: ruta, nombre, extensión, tamaño en bytes, fecha de captura
  EXIF (cuando exista) y un hash del contenido para detectar duplicados.
- Se ignoran los archivos que no son fotos. Un archivo con extensión de foto pero
  ilegible o corrupto se registra con su error y no aborta el escaneo.
- El resultado se escribe en un índice local en formato JSON, reemplazando el índice
  anterior de esa misma carpeta.
- El escaneo nunca mueve, renombra, copia ni modifica los archivos de la carpeta.
- Una ruta inexistente o sin permiso de lectura se reporta como error y el comando
  termina con código de salida distinto de 0.

## Capabilities

### New Capabilities

- `photo-scanning`: Recorrido recursivo de una carpeta, identificación de los archivos
  que son fotos, extracción de sus datos básicos y de la fecha de captura EXIF,
  detección de duplicados por hash y persistencia del resultado en un índice local.

### Modified Capabilities

Ninguna. Es la primera capacidad del proyecto.

## Rollback plan

- El único efecto sobre el disco, aparte del código, es el archivo de índice local; se
  elimina borrando ese archivo y las carpetas `__pycache__`.
- Revertir la rama de la funcionalidad deja el repositorio como estaba: no hay
  migraciones de esquema, ni cambios en la base de datos, ni modificación de las fotos
  originales.
- El índice es regenerable, así que una versión defectuosa se descarta y se vuelve a
  escanear sin pérdida de datos.

## Impact

- Nuevo paquete Python `fotos_plus/` con el escaneo de carpetas, la extracción de
  metadatos y la CLI (basada en `argparse`).
- Nueva dependencia de lectura: Pillow, usada para validar imágenes y leer EXIF.
- Nuevo archivo de índice local, agregado a `.gitignore` para que nunca se versionen
  índices de máquinas personales.
- Pruebas con `pytest` sobre carpetas temporales que contienen imágenes reales,
  imágenes corruptas y archivos que no son fotos.
- PostgreSQL no se toca en este cambio: el índice local es un puente explícito hacia
  la persistencia definitiva (ver `design.md`).

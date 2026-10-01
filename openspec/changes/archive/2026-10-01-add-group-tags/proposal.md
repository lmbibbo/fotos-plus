# Proposal

## Why

El escaneo devuelve dos cajones, "con GPS encadenado" y "sin GPS por huecos de días", y ninguno de los dos
significa "vacaciones". En una colección donde la mayoría de las fotos son vida cotidiana, el escaneo devuelve
decenas de viajes que no fueron viajes, y no existe en los metadatos ninguna característica que lo distinga.
El usuario es la única autoridad posible sobre qué es un viaje, así que el sistema tiene que darle una forma
de decirlo.

Hoy las etiquetas solo cambian el título de una tarjeta (`group-labels`), y el visor las muestra en una lista
plana ordenada por fecha. Un usuario que marca treinta y cinco tarjetas como "vida cotidiana" sigue viéndolas
como treinta y cinco tarjetas más, indistinguibles de los cinco viajes reales. El tag resuelve las dos cosas
juntas: dice qué es cada grupo y hace que la pantalla lo refleje.

## What Changes

- El archivo de edición pasa de versión 1 a versión 2 y agrega un catálogo de tags definidos por el usuario.
- Cada grupo acepta **como máximo un** tag, que convive con el título: el título nombra, el tag clasifica.
- El usuario elige un tag existente o crea uno nuevo escribiendo el nombre.
- El visor agrupa las tarjetas en secciones, una por tag, en lugar de una lista plana.
- Las secciones se ordenan por la fecha más temprana de su primera tarjeta, y la sección "Sin tag" va al final.
- Arrastrar una tarjeta sobre una sección le asigna ese tag; sobre otra tarjeta, adopta el tag de esa tarjeta;
  sobre "Sin tag", se lo quita.
- El export estático muestra las secciones y no ofrece controles de edición, igual que hoy con las etiquetas.
- Los archivos de edición v1 existentes se migran a v2 sin perder las etiquetas ya guardadas.

Fuera de alcance, a propósito:

- No se modifican los rangos de fechas de los grupos: siguen siendo los del escaneo.
- No se fusionan ni se parten grupos. Unir y partir exigiría elegir límites de fecha declarados por el
  usuario y revisar el modelo de datos; este cambio solo clasifica lo que el escaneo ya agrupó.
- Más de un tag por tarjeta. Con varios tags la agrupación deja de ser una partición y una tarjeta tendría
  que aparecer en más de una sección.

## Capabilities

### New Capabilities

Ninguna. El trabajo se apoya en dos capacidades existentes.

### Modified Capabilities

- `group-labels`: el archivo de edición crece a versión 2 con catálogo de tags y asignación por grupo, y
  deja de rechazar los archivos v1 para migrarlos.
- `photo-viewing`: las tarjetas pasan de una lista plana ordenada por fecha a secciones por tag, y el modo
  servidor acepta el borrado del tag además de las ediciones de título.

## Impact

- `fotos_plus/labels.py`: versión del archivo, migración, catálogo, validación y operaciones de tag.
- `fotos_plus/server.py`: acciones de tag sobre el endpoint existente.
- `fotos_plus/viewer.py`: agrupación en secciones, zonas de destino y arrastre.
- `tests/`: migración de v1, catálogo, asignación y agrupación.
- No se toca `grouping.py`, `scanner.py` ni el escaneo. El archivo de sugerencias sigue siendo escrito solo por
  el escaneo y el archivo de edición solo por el editor.
- El formato del archivo de edición cambia de versión. Es el único cambio incompatible, y se mitiga migrando
  los archivos existentes al leerlos.

## Rollback

- **Código**: revertir el commit del change en la rama de feature, o revertir el squash en `main`. No hay
  migraciones de esquema de base de datos ni estado externo: todo vive en un archivo que el usuario controla.
- **Archivo de edición**: si ya se guardaron tags y hay que volver atrás, `EDITION_VERSION` vuelve a 1 y las
  claves `tags` quedan como campos desconocidos que la lectura v1 ignora. Las etiquetas de título se
  conservan porque viven en `labels`, que no se toca.
- **Reescaneo**: no aplica. El escaneo nunca lee el archivo de edición, así que ningún cambio de tags
  interactúa con el índice ni con el archivo de sugerencias.
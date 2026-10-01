# Proposal

## Why

El visualizador no permite nombrar nada, y las tarjetas resultantes casi no se distinguen entre sí: sobre el índice real, 37 de 51 viajes se titulan "Argentina" y 14 períodos se titulan igual entre sí, así que el usuario solo cuenta con una línea de fechas para saber cuál es cuál.

La única vía actual para cambiar lo que el visor muestra es editar a mano el archivo de sugerencias, lo cual no está soportado: `scan` lo reemplaza entero en cada ejecución y una modificación accidental lo deja ilegible (hoy un carácter sobrante en la línea 18 hace que `view` termine con error y no muestre nada).

El usuario necesita poder poner su propio nombre a un grupo sugerido y que ese nombre sobreviva a los rescaneos, sin tocar el archivo que el escaneo produce.

## What Changes

- Se agrega el flag `--serve` al subcomando `view`: sirve el visualizador desde un servidor local que solo escucha en el loopback, para que el navegador pueda enviar ediciones.
- Se agrega un archivo hermano del índice, `<id>-edicion.json`, que guarda las etiquetas escritas por el usuario. Lo escribe únicamente el servidor y lo lee `view`.
- El título de cada tarjeta pasa a ser la etiqueta del usuario cuando existe y, si no, el título derivado actual (el país, o "Viaje").
- Una etiqueta guardada nunca puede estar vacía: quitarla es una operación explícita, no el resultado de borrar el texto.
- Si el archivo de sugerencias fue reescrito desde que se escribieron las etiquetas, el visor informa cuántas siguen resolviendo y cuántas no.
- El export estático se sigue generando, aplica las etiquetas y se declara explícitamente como de solo lectura, sin controles de edición que no podrían funcionar sin servidor.
- `scan` no cambia: sigue siendo una función pura de las fotos y sigue reescribiendo el archivo de sugerencias completo. Cada archivo tiene un solo escritor.

Fuera de alcance: mover fotos entre grupos, dividir grupos y unir grupos. Son la motivation del enfoque por membresía explícita, pero requieren la lista real de fotos por grupo y quedan para un cambio posterior.

## Capabilities

### New Capabilities

- `group-labels`: persiste etiquetas escritas por el usuario sobre los grupos sugeridos, en un archivo separado del que produce el escaneo, con una clave de grupo estable, la invariante de etiqueta no vacía y el reporte de deriva ante un rescaneo.

### Modified Capabilities

- `photo-viewing`: agrega el modo servidor de `view` y el uso de la etiqueta en el título de la tarjeta, conservando la garantía de que el HTML exportado muestra su contenido sin necesitar un servidor.

## Impact

- Código nuevo: un módulo para leer y escribir el archivo de edición, y otro para el servidor local.
- Código modificado: `fotos_plus/viewer.py` (precedencia del título, marcador de solo lectura), `fotos_plus/cli.py` (el flag `--serve`) y `fotos_plus/models.py` (lectura del archivo de edición).
- Sin dependencias nuevas: el servidor se arma con la biblioteca estándar.
- El índice y el archivo de sugerencias no se modifican en ningún flujo de este cambio.
- Se agrega cobertura de pruebas para la resolución de claves, la rechazo de etiquetas vacías, la precedencia del título y las defensas del servidor.

### Rollback plan

1. Borrar `<id>-edicion.json` devuelve el visor a su comportamiento actual. Ningún otro archivo queda afectado, porque ese archivo es el único que este cambio escribe y nadie más lee.
2. Revertir el commit del cambio deja `view` funcionando exactamente como antes: el flag `--serve` desaparece y el export estático no cambia de comportamiento.
3. El archivo de sugerencias nunca es tocado, así que no hace falta restaurarlo ni regenerar el escaneo para volver atrás.
4. Los cuatro requisitos vigentes de `photo-viewing` siguen cumpliéndose durante el rollback, en particular el que exige que el HTML exportado muestre su contenido sin un servidor local.

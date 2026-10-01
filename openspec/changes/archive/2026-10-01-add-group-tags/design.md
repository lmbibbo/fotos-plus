# Design

## Context

El archivo de edición vive en `labels.py` y hoy tiene una sola forma: `labels`, un mapa de
`first_captured_at` a texto. La lectura rechaza cualquier versión distinta de la esperada:

```
EDITION_VERSION = 1                                    labels.py:12
if version != EDITION_VERSION:                         labels.py:62
    raise LabelError("version de edicion no soportada")
```

Ese `raise` es el punto que obliga a migrar. Un archivo v1 real en la máquina del usuario no puede seguir
cargándose con la regla actual.

El visor arma las tarjetas en `viewer.py:108-179` y las devuelve en una lista plana ordenada por
`first_captured_at`. Dos hechos de ese código condicionan el resto del diseño:

```
viewer.py:139-147   la foto entra en el PRIMER grupo cuyo rango de fechas la contiene;
                    los viajes se prueban antes que los períodos y hay break en el primero
viewer.py:124-131   se crea una tarjeta por cada grupo del escaneo, aunque quede con cero fotos
```

O sea: los grupos no tienen lista de fotos, son rangos. Y no hay forma actual de que una tarjeta desaparezca.

El modo servidor ya tiene un endpoint, `POST /api/labels`, que centraliza token, host de loopback y
verificación previa de JSON (`server.py:99-146`). El HTML se genera con las tarjetas ya renderizadas y el
JavaScript vive en un único bloque `EDIT_SCRIPT` (`viewer.py:318`) que solo se incluye cuando hay token.

## Goals / Non-Goals

**Goals:**

- Que el usuario pueda decir qué grupos son viajes y cuáles son vida cotidiana, y que la pantalla lo muestre.
- Un solo gesto de arrastre que sirva tanto para etiquetar como para agrupar.
- No tocar el escaneo ni el modelo de agrupación.

**Non-Goals:**

- Cambiar los rangos de fechas. Los límites siguen siendo los del escaneo.
- Fusionar o partir grupos. Requeriría que el usuario declarara límites propios y revisar el modelo de
  datos entero; acá solo se clasifica lo que el escaneo ya agrupó.
- Más de un tag por grupo. Ver "Decisiones".

## Decisions

### 1. Catálogo explícito, no derivado de las asignaciones

El catálogo se guarda como lista ordenada de nombres, en paralelo al mapa de asignaciones.

```json
{
  "version": 2,
  "based_on_scanned_at": "...",
  "labels":  { "2023-07-19T10:32:39": "Navidad" },
  "tags":    ["Viaje", "Familia"],
  "tagged":  { "2023-07-19T10:32:39": "Familia" }
}
```

Se guardan los nombres tal como el usuario los escribió, no el `first_captured_at` del grupo como clave de
tag: la clave es la misma que ya usan las etiquetas, y así un grupo tiene su título y su tag en el mismo
par de claves.

Alternativa descartada: derivar el catálogo de los valores de `tagged`. Es más chico, pero un tag con cero
grupos asignados no podría existir, y el selector no podría ofrecer un tag que el usuario quiere usar. El
catálogo explícito también da un orden estable para el selector, que el derivado no tendría.

### 2. Un tag por grupo

`tagged` es un mapa, no una lista de listas, así que la unicidad sale de la estructura y no de una
validación.

Consecuencia asumida: con dos tags por grupo, una tarjeta tendría que aparecer en dos secciones y el arrastre
debería soportar varios destinos. Se deja fuera a propósito; el modelo lo admite después sin romper lo
hecho.

### 3. Identidad del tag insensible a mayúsculas, presentación fiel

Dos entradas que solo difieren en mayúsculas o espacios son el mismo tag. Se compara con el nombre recortado
y normalizado a minúsculas, pero se guarda y se muestra la forma con la que se creó el tag por primera vez.

Alternativa descartada: guardar siempre minúsculas. Rompería la presentación: el usuario escribe "Viaje" y ver
"viaje" en el encabezado de sección se lee como un bug.

### 4. Se extender el endpoint existente en vez de crear uno nuevo

`POST /api/labels` gana las acciones `set_tag` y `clear_tag`, en vez de agregar `/api/tags`.

El endpoint ya concentra el token, la comprobación de host de loopback, el `Content-Type` JSON que obliga al
navegador a la verificación previa, y el rechazo de hosts ajenos (`server.py:99-146`). Duplicar todo eso en
un segundo endpoint sería repetir las garantías de seguridad del servidor en otro lugar, que es exactamente
donde no conviene repetirlas.

### 5. El arrastre va en `EDIT_SCRIPT`, y por eso el export lo hereda sin trabajo

`EDIT_SCRIPT` solo se inyecta cuando hay token (`viewer.py:467`). Poner ahí el arrastre conserva gratis el
requisito de que el HTML exportado sea de solo lectura: no hay que emitir nada extra en el export, porque nunca
incluye ese bloque.

## Riesgos

El objetivo de soltar se toma de atributos `data-`, que el HTML ya usa:

```
data-tag="Familia"     la tarjeta arrastrada lleva su tag vigente
data-key="2023-07-19..."   ya existe y sirve para identificar el grupo destino
```

Un tag vacío en `data-tag` significa "sin tag", que es lo que hace que arrastrar sobre una tarjeta sin tag
quite el tag en vez de asignar un valor vacío.

```
   arrastrar ▢ "Marr del Plata" sobre la seccion Familia -> toma el tag "Familia"
   arrastrar ▢ "Navidad" sobre la tarjeta "Aniversario"  -> toma SU tag
   arrastrar ▢ "Japan" sobre "Sin tag"                   -> se lo quita
```

Las tres acciones salen del mismo manejador: se lee el `data-tag` del destino y se manda `set_tag`, o
`clear_tag` cuando viene vacío. No hay una rama de código por gesto.

### 6. Resolución de tags al estilo de las etiquetas

`resolve_labels` ya separa resueltos, no resueltos y ambiguos contra los grupos vigentes, y avisa por la vía de
la deriva. Los tags se resuelven con el mismo criterio y con la misma señal de deriva, así que el aviso de
"3 etiquetas no resuelven" pasa a cubrir también las asignaciones sin tocar el contrato de las etiquetas.

```
lectura v1 --> sin tags --> se resuelve como edicion v2 vacia --> escritura v2
```

Un archivo v1 no se reescribe en disco al leerlo. La migración ocurre en memoria y el archivo pasa a v2 la
primera vez que el usuario guarda algo. Si el archivo v1 está corrupto o tiene una versión futura, se sigue
rechazando con motivo.

## Migration Plan

1. Subir `EDITION_VERSION` a 2 y aceptar `1` y `2` en la lectura, normalizando ambas a la estructura actual.
2. Leer un archivo v1 devuelve el overlay con `labels` y sin tags: no hace falta tocar nada más para no romper.
3. La primera escritura emite v2 con `tags` y `tagged`, aunque estén vacíos.

Deshacer es cambiar `EDITION_VERSION` a 1: las claves `tags` y `tagged` quedan como campos desconocidos que la
lectura v1 ignora, y `labels` conserva los títulos. No hay migración de datos ni estado fuera del archivo.

## Risks / Trade-offs

- **El arrastre es la única forma cómoda de quitar un tag si no se usa el selector** → también hay una acción
  explícita de quitar tag en la tarjeta, para no depender de acertar el destino del arrastre.

- **Reordenar el DOM después de cada arrastre** puede descartar el elemento que se está arrastrando y cortar
  la interacción a mitad de camino → el manejador del `drop` recarga la página desde el servidor, igual que
  ya hace hoy al guardar un título. Es el camino probado y evita reconciliar el DOM a mano.

- **El catálogo puede quedar con tags que ya no usa nadie** → se conserva a propósito, para que volver a
  usar un tag anterior no requiera escribirlo de nuevo. Un tag sin grupos asignados no produce sección.

- **Arrastrar sobre una tarjeta que quedó con cero fotos** → es un caso real (`viewer.py:124-131`), pero se
  comporta igual que cualquier otra: adopta el tag de la tarjeta destino.

- **Más de un tag por grupo queda afuera** → si aparece la necesidad, `tagged` pasa de mapa a multimapa y las
  secciones dejan de ser una partición. El formato del archivo cambia, pero ni `labels` ni el escaneo se
  tocan.

## Open Questions

Ninguno que afecte a las specs, al enfoque o al reparto de tareas.
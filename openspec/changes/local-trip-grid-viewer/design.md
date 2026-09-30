# Design

## Context

El escaneo escribe dos archivos separados (ver `proposal.md` - Why):

- el índice de fotos, con una entrada por foto y su `relative_path`
- el archivo de sugerencias, con los viajes y los períodos, pero **sin** la lista de fotos

Ninguno enlaza al otro. Los viajes declaran `first_captured_at`, `last_captured_at` y
`photo_count`, pero no qué fotos contienen. El índice declara `captured_at` por foto, pero no
a qué viaje pertenece. El visor tiene que resolver ese cruce.

Restricciones relevantes del código actual:

- `fotos_plus/photos.py` ya abre cada imagen con Pillow para leer fecha y GPS, así que generar
  miniaturas no necesita una dependencia nueva.
- `fotos_plus/index.py` ya tiene `suggestions_path_next_to`, que define la convención del
  nombre del archivo de sugerencias contiguo. El visor la reutiliza en vez de inventar otra.
- El CLI solo tiene el subcomando `scan`; `view` será el primero que **lee** un índice.

Dimensionado sin datos de ninguna colección real: una miniatura de 200 px a calidad 70 ronda
los 6 KB en JPEG, ~8 KB en base64. Con cinco miniaturas por tarjeta, una biblioteca de un
par de miles de fotos produce un HTML de unos pocos MB, que abre al instante.

## Goals / Non-Goals

Goals:

- Generar un HTML autocontenido con un subcomando, sin servidor y sin red.
- Cruzar índice y sugerencias en tiempo de generación, sin tocar el formato de ninguno.
- Que la orientación de la miniatura sea correcta sin que el visor interprete EXIF.

Non-Goals:

- No se agregan campos al índice ni al archivo de sugerencias. Los archivos ya escaneados
  siguen siendo válidos; no hace falta reescanear.
- No hay pantalla completa, navegación con teclado ni zoom (quedan para una etapa posterior).
- No se auditan ni corrigen las sugerencias: el visor las muestra como son.

## Decisions

### 1. El cruce se calcula en `view`, no en el escaneo

Se cruzan los dos archivos en tiempo de generación, no al escanear.

Alternativa descartada: que el escaneo escriba a qué viaje pertenece cada foto (campo nuevo en
el índice). Es lo correcto a largo plazo, pero cambia el formato del índice, rompe la lectura de
todos los índices ya escritos y obliga a reescanear para "arreglar" datos que no estaban mal.

Consecuencia de la decisión elegida: el cruce se recalcula en cada `view`, pero es barato
(un recorrido de las fotos por viaje, ordenados una vez) y no deja estado que pueda quedar
desactualizado. El precio real —generar miniaturas— se paga igual en ambas alternativas.

### 2. El cruce empareja por rango de fechas

El agrupado se resuelve asignando cada foto al viaje cuyo intervalo
`[first_captured_at, last_captured_at]` la contiene; los períodos se tratan igual con su propio
intervalo. Sobre la colección real los intervalos de viaje no se solapan, así que cada foto cae
en un único grupo.

```
secuencia del cruce (por foto, index ya ordenada por captured_at)
--------------------------------------------------------------
escaneo/view    idx       viaje       resultado
    |           |          |             |
    |--sort()-->|          |             |
    |           |          |             |
    |  para cada foto f (por orden de fecha)
    |           |          |             |
    |-- ¿ f.fecha dentro de viaje v ? --->| sí -> f -> v
    |           |          |             |
    |-- ¿ f.fecha dentro de periodo p ? -->| sí -> f -> p
    |           |          |             |
    |           |          |             <- no -> f -> "huérfanas"
```

Fotos que caen en un viaje tienen prioridad sobre un período: el viaje es el grupo con
información de lugar. Si una foto no cae en ninguno, va a la tarjeta de huérfanas. No se
descarta ninguna foto: la tarjeta de huérfanas es un grupo más, no un error.

### 3. La orientación se resuelve al generar la miniatura

La miniatura se genera aplicando la transformación EXIF antes de guardarla, así que la imagen
embebida ya sale con la proporción correcta.

Alternativa descartada: guardar la orientación en el índice y dejar que el visor la aplique. Eso
obliga a persistir un campo en `Photo` y en `to_dict`/`from_dict`, lo que cambia el formato del
índice para todos, y obliga al visor a parsear los ocho valores posibles de Orientation (incluidos
los reflejados 5-8, poco frecuentes). Resolverlo al generar mantiene el índice intacto y deja la
miniatura autoexplicativa.

Consecuencia: el visor no puede voltear ni reorientar imágenes que no sean miniaturas suyas. Para
esta etapa (solo miniaturas) no importa.

### 4. Standalone: miniaturas embebidas en base64

El HTML lleva las miniaturas embebidas en base64 y los datos de las sugerencias en un `<script>`.
No depende de `fetch()` ni de un servidor.

Restricción del navegador que motiva esto: sobre `file://`, `fetch()` de un archivo local está
bloqueado por CORS, así que el visor no podría leer el JSON de sugerencias en runtime. Los datos
van embebidos. Un `<img src="file://...">` sí funciona sobre `file://`, pero esa vía queda para
la etapa de pantalla completa, no para las miniaturas de esta etapa.

Costo: el HTML pesa unos pocos MB y generar significa producir una miniatura por cada tarjeta
con fotos. Es un costo único por invocación de `view` y produce un archivo que abre al
instante.

### 5. Si no hay sugerencias, se muestra un grid plano

`view` deriva la ruta del archivo de sugerencias. Si ese archivo no existe, en lugar de fallar
genera el mismo HTML con todas las fotos en una grilla suelta, sin agrupar.

Esto cubre el caso real de un índice viejo, escrito antes de que existiera el archivo de
sugerencias. El comando nunca falla por falta de sugerencias; solo cambia de forma.

### 6. Orden ascendente por fecha

Las tarjetas se ordenan por la fecha más temprana del grupo, de forma ascendente. El índice se
ordena por `captured_at` una vez y el agrupado es un recorrido lineal sobre esa lista.

### 7. Un grupo declarado sin fotos conserva su tarjeta

Como los viajes tienen prioridad sobre los períodos, un período contenido dentro de un viaje se
queda sin fotos propias: las fotos van al viaje. La tarjeta del período se muestra igual, con un
aviso de que no tiene fotos propias, para que un grupo declarado por el usuario no desaparezca
en silencio del visor.

El grupo de fotos sin clasificar es la excepción: solo se crea si de verdad hay fotos sin
clasificar, porque "Fotos sin clasificar · 0 fotos" no aporta nada.

### 8. La tarjeta muestra el tamaño real del grupo, no el de la sugerencia

El `photo_count` de una sugerencia cuenta las fotos que contribuyeron a la agrupación, es decir
las que tienen posición; no es el total de fotos del rango. Mostrarlo como tamaño de la tarjeta
subreporta de forma importante, y en un rango amplio la diferencia es de un orden de magnitud.

Por eso la tarjeta muestra la cantidad de fotos que el visor realmente asignó al grupo. El
`photo_count` de la sugerencia sigue viajando en el bloque de datos del HTML, por si hace
falta contrastarlo.

## Risks / Trade-offs

- **[El HTML pesa unos pocos MB y se regenera en cada `view`]** → Aceptable para esta etapa: es un
  comando explícito del usuario, no un proceso continuo. Si molesta, un paso futuro podría
  cachear por fecha de modificación del índice, pero hoy no se justifica.

- **[Las miniaturas son imágenes de 200 px, no el original]** → Riesgo aceptado y acotado:
  las miniaturas son lo único que se muestra en esta etapa. No hay resolución ni zoom.

- **[Fotos huérfanas forman un grupo heterogéneo]** → Es intencional: son fotos que el agrupado
  no pudo asignar. Mostrarlas juntas hace visible que existen, en vez de ocultarlas. El criterio
  de asignación queda fijado en las specs.

- **[Las rutas del HTML apuntan a la colección local]** → El HTML generado es específico de la
  máquina y carpeta donde se generó. Es coherente con que el visor es local. Se documenta en el
  README.

- **[Photos corrupta o ilegible entre las 5 que se eligen]** → Se seleccionan candidatos y si una
  falla al generar la miniatura, se pasa a la siguiente. Una tarjeta puede quedar con menos de
  cinco miniaturas; no debe fallar el comando entero por una foto ilegible.

## Migration Plan

No hay migración. No se cambia el formato del índice ni del archivo de sugerencias. Los archivos
ya escaneados siguen siendo válidos.

Rollback: revertir el commit elimina `view` y `viewer.py`. Los HTML generados son derivados y se
pueden borrar sin consecuencia.

## Open Questions

Ninguna que afecte specs, enfoque o tareas. La orientación de pantalla completa y las flechas
quedan como cambio futuro separado.

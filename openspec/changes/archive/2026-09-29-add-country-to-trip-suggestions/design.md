# Design

## Context

Estado actual, en `fotos_plus/`:

- `models.py` define `TripSuggestion` con cinco campos (`photo_count`, `first_captured_at`,
  `last_captured_at`, `location_state`, `status`) y `PeriodSuggestion` con los mismos cinco.
  `TripSuggestion.from_dict` lee los dos últimos con `data.get()`, así que agregar un campo
  opcional y subir `SUGGESTIONS_VERSION` no rompe la lectura de archivos anteriores.
- `grouping.py:build_suggestions(photos, root, scanned_at)` recibe la lista completa de
  `Photo` y devuelve el `SuggestionsResult`. Hoy separa por `has_position` y arma los
  grupos; tiene el material necesario para clasificar antes de agrupar.
- `index.py:write_suggestions` reutiliza `_write_json_atomic`, que escribe en un tempfile
  de la carpeta destino y hace `os.replace`. La atomicidad ya está resuelta y este cambio
  no la toca.
- `cli.py:scan` llama a `build_suggestions` dentro de un `try` que captura `Exception` y
  devuelve `EXIT_OK` avisando por stderr. Un fallo al clasificar el país cae en esa misma
  protección sin cambiar el contrato.
- `pyproject.toml` declara una sola dependencia, `Pillow`, y `packages = ["fotos_plus"]`
  sin `package-data`. El proyecto no tiene ninguna dependencia de red, de base de datos ni
  geográfica.

La forma del problema se midió sobre una colección de prueba local, que no se versiona y
cuyos números no se reproducen acá. Sobre una colección con GPS intermitente, la medición
que condiciona el diseño tiene esta forma:

```
fotos con posicion valida:                  ~78% de la coleccion
fotos sin posicion valida:                  ~22% de la coleccion
  - en un dia que SI tiene gps:              ~15% de las anteriores  (referencia)
  - en un dia SIN gps:                       ~85% de las anteriores  (periodos)
paises distintos entre las fotos con gps:      una decena
viajes sugeridos:                              decenas
```

El caso que decide el diseño es un **viaje que cruza una frontera**: se agrupó en una sola
sugerencia porque el recorrido fue cruzando el umbral de los 200 km por pasos, y el radio
desde su centroide llegó a cientos de kilómetros. Contiene fotos de los dos lados de una
frontera terrestre, con un país concentrando la gran mayoría y el otro una minoría pequeña. El
conteo exacto se mide con el polígono de cada foto, no estimado:

```
   centroide del viaje en (lat, lon)
                    |
                    v
   +-------------------------------------------+
   |            PAIS A                         |
   |      ~85-90% de las fotos                 |
   |            |                              |
   |     ------ + --------- frontera ---------- |
   |            |                              |
   |        PAIS B                             |
   |      ~10-15% de las fotos                 |
   +-------------------------------------------+

   -> el centroide cae en el pais A y "tacha" las fotos del pais B
```

Un centroide no puede decidir el país de este viaje: no es que de lugar, es que el viaje
no tiene un único lugar. Por eso la clasificación es por foto.

## Goals / Non-Goals

**Goals:**

- Declarar el país de cada viaje sugerido, derivado de las coordenadas de sus fotos.
- Mantener el escaneo completamente offline: cero red, cero coordenadas salientes.
- No romper a un consumidor que ya lee el archivo: `location_state` conserva su significado
  y el campo nuevo es opcional al leer.
- Resolver honestamente el viaje que cruza una frontera, sin forzarlo a un país.
- No agregar dependencias de Python.

**Non-Goals:**

- La ciudad, la provincia y el nombre del lugar. Ver la decisión 7.
- Un país para los 15 períodos. No tienen coordenada; ver la decisión 6.
- Reemplazar `location_state`. Se conserva.
- Un índice espacial persistente o cacheado. El costo se resuelve en memoria, ver la
  decisión 3.
- Detectar por qué un tramo de la colección no tiene GPS. Es un cambio aparte, no de país.

## Decisions

### 1. El país se clasifica por foto, nunca por centroide

Se clasifica cada foto con posición válida en su país y después se cuenta.

La razón es un viaje que cruza una frontera terrestre. Un centroide resume la posición de un
conjunto que se reparte entre dos países, y el resumen no pertenece a ninguno de los dos:
cae en el país con más fotos y borra al otro de la existencia. Clasificando por foto, el
problema no aparece: el viaje tiene fotos de un país y del otro, y eso es un hecho, no una
ambigüedad.

Consecuencia: el país dominante no siempre es "el país del viaje". Es el país donde estuvo
la mayoría de las fotos, y la lista de países deja ver el resto. El archivo declara los dos
datos, así que un consumidor puede mostrar "el país principal, con un pasaje por el otro" en
lugar de escolher en silencio.

Alternativa descartada: centroide del viaje. Se descarta por el caso de arriba, y además por
los otros viajes con radio mayor a 50 km, donde el mismo problema aparece a menor escala.

### 2. El viaje declara país dominante y lista de países, y el empate no se resuelve

Cada viaje con posición declara `country` (el que concentra más fotos) y `countries` (la
lista de todos). Cuando dos países empatan con el mismo máximo, `country` se declara
desconocido y `countries` muestra los dos.

El empate tiene que quedar sin resolver por una razón concreta: con pocos días de fotos, un
viaje de ida y vuelta entre dos ciudades vecinas puede tener 2 fotos de cada lado. Elegir uno
rompe los dos lados igual, y en ese caso la respuesta honesta es que no hay un país
dominante. En la colección real no aparece ningún empate, así que la regla existe para que
el comportamiento esté definido y no porque la colección la exija.

Alternativa descartada: desempatar con el país de la primera foto, o el de la última. Se
descarta porque las dos son arbitrarias y el resultado cambiaría con el orden de lectura,
que es exactamente lo que el diseño quiere evitar.

### 3. Los polígonos se cargan una vez por escaneo y se indexan por caja envolvente

La clasificación es punto en polígono. Con ~180 países y miles de coordenadas, la versión
ingenua serían 670.000 pruebas de segmento por escaneo. Se carga el conjunto una sola vez y
se indexa por caja envolvente: cada polígono entra en una grilla según su caja, y una
consulta solo mira los polígonos de la celda de la coordenada.

El índice es en memoria y se arma una vez por proceso, no se persiste ni se cachea entre
ejecuciones. La razón es que el escaneo ya es idempotente y ya existe como operación, y
porque un archivo de cache es estado que puede quedar desactualizado respecto del conjunto
de polígonos: un bug de versión sería más difícil de detectar que el costo que se ahorra.

Se elige punto en polígono sobre una dependencia como `shapely` o `geopandas` para no
sumar dependencias: son decenas de megabytes de dependencias transitivas, y el algoritmo son
unas 40 líneas. Se mide el costo real sobre la colección antes de aceptar la decisión.

Alternativa descartada: shapely/geopandas. Se descarta por el costo de dependencia, y
porque el proyecto hasta ahora tiene una sola dependencia y agregar un árbol de geospatial
por una consulta de contención es desproporcionado.

### 4. El conjunto de polígonos viaja con el programa y declara su versión

El GeoJSON se incluye en `fotos_plus/data/` y se declara en `pyproject.toml` como
`package-data`, para que se instale con el paquete y se resuelva con `importlib.resources`
en vez de con una ruta relativa al archivo fuente.

La versión del conjunto se escribe en el archivo de sugerencias, junto a `SUGGESTIONS_VERSION`
que pasa a 2. Sin esto, un consumidor no puede distinguir "este viaje no tiene país" de
"este viaje se escaneó con una versión de países que no incluía su país". Es la misma
razón por la que el nombre del archivo lleva "sugerencias" y el contenido lleva
`provisional`: para que un consumidor no pueda interpretar de más lo que tiene delante.

Los polígonos se simplifican al elegir la fuente, para que el conjunto entre en un tamaño
que no vuelva impractical la instalación. La escala elegida tiene que resolver las fronteras
que la colección cruza, y eso se verifica antes de fijar la dependencia de datos.

### 5. El campo nuevo es opcional al leer y `location_state` no se toca

`location` se resuelve con `data.get()` en `from_dict`, y `SUGGESTIONS_VERSION` pasa a 2.

El motivo de no reutilizar `location_state` es que ya significa otra cosa. Hoy vale `known`
cuando hay coordenadas y `unknown` cuando no, y eso sigue siendo exactamente lo que vale
después del cambio. Sobrescribirlo con el nombre del país perdería la distinción entre un
viaje con coordenadas que no caen en ningún país y un período que nunca tuvo coordenadas:
en el primer caso se puede reintentar con otro conjunto; en el segundo no hay nada que
reintentar.

Consecuencia: hay dos campos que hablan de ubicación y ninguno reemplaza al otro. Es
voluntario, y es el mismo criterio que el diseño anterior aplicó al separar `status` de
`location_state`.

Alternativa descartada: reemplazar `location_state` por un objeto `location` único que
contenga país y estado. Se descarta porque rompe a todo consumidor actual y mezcla dos
ejes que el diseño ya decidió mantener separados.

### 6. Los períodos no reciben país, y no se infiere de los vecinos

Los períodos sugeridos agrupan fotos que no tienen coordenada. No hay nada que clasificar: el
geocodificación no es un problema de datos acá, es un problema de información ausente.

Se podría cubrir la mayor parte de la auditoría manual copiando el país del viaje
inmediatamente anterior. Se descarta: el período es una declaración de que no sabemos dónde
estaba el usuario, y completarlo con el país del viaje anterior afirma algo que ninguna
coordenada de ese período respalda. Si el usuario estuvo en un país y se mudó a otro a mitad
de período, el archivo pasa a mentir con seguridad.

La señal de GPS en una colección puede ser intermitente, y hay meses enteros sin posición.
Eso es un incidente del dispositivo o un problema del recorrido, no una lista de lugares
desconocidos, y por eso el paquete de trabajo de este cambio es el país de los viajes y no
la auditoría. Detectar ese incidente, si hace falta, es un cambio aparte.

### 7. La ciudad queda fuera, y no por el tamaño del gazetteer

El país es una categoría cerrada: containment. La ciudad es un concepto abierto: la misma
coordenada puede describirse como ciudad, partido, provincia o área metropolitana, y
elegir una requiere decidir cuál de esas es "el lugar" que el producto quiere mostrar. Esa
decisión es de producto y no tiene respuesta técnica.

A eso se suma que un gazetteer de ciudades pesa órdenes de magnitud más que un conjunto de
polígonos de país, y que la calidad del nombre-city importa: "CABA" contra "Ciudad
Autónoma de Buenos Aires" no es un detalle de formato. Se deja para un cambio propio, con
su propia decisión sobre qué nivel de nombre se quiere.

## Flujo

Clasificación y agregado, sobre la lista de fotos que ya existe en memoria:

```
  scan(carpeta)
        |
        v
  ScanResult.photos  (las que tienen posicion)
        |
        |  +---> load_countries()            una vez por proceso
        |         |  lee data/countries.geojson
        |         |  arma indice de caja envolvente en grilla
        |         v
        |      CountryIndex  (en memoria)
        |
        v
  build_suggestions(photos, root, scanned_at)
        |
        |  [1] separar: con posicion valida / sin posicion
        |
        |  [2] CADA foto con posicion:
        |        country = index.country_of(lat, lon)   <-- por foto, no centroide
        |        acumular en contador por pais
        |        (None si la consulta no devuelve pais)
        |
        |  [3] ordenar por fecha, comparar con la ANTERIOR a 200 km  (sin cambios)
        |
        |  [4] por grupo de viaje:
        |        conteo de paises ya acumulado en [2]
        |        country    = pais con mas fotos, o desconocido si hay empate
        |        countries  = lista de todos los paises presentes
        |        location_state = "known"   (sin cambios, viene de las coordenadas)
        |
        |  [5] periodos: sin cambios, sin pais
        |
        v
  SuggestionsResult (version = 2, countries_version = <n>)
        |
        +---> write_suggestions(...)  [atomico, sin cambios]
        v
  resumen: 45 viajes, 7 paises
```

Consulta de país, sobre el índice en memoria:

```
  country_of(lat, lon)
        |
        +---> celda = celda_de(lat, lon)
        |
        +---> para cada poligono en celda:            pocos, no los ~180
        |      |  |
        |      |  +---> caja_envolvente contiene (lat, lon)?  no -> siguiente
        |      |
        |      +---> punto_en_poligono((lat, lon), poligono)?  si -> su pais
        |
        +---> ninguno -> None  (no se inventa el pais mas cercano)
```

## Riesgos / Trade-offs

- **Un polígono simplificado pone una frontera en el lado equivocado** → se verifica la
  clasificación contra casos de referencia de frontera, que están en los tests y no
  dependen de ninguna colección real. La verificación va antes de fijar el conjunto de
  datos.

- **El tamaño del conjunto de polígonos encarece la instalación** → se elige la fuente más
  simple que resuelva el caso, y el tamaño se mide y se declara en el README antes de
  cerrar la decisión de dependencia de datos.

- **Un viaje cruza una frontera y el consumidor muestra solo el país dominante** → el
  archivo declara la lista completa. Es el mismo problema que ya tienen `status` y
  `location_state` juntos: mitigar en el productor alcanza hasta donde alcanza, y la
  mitigación real es el consumidor.

- **El escaneo se encarece con la clasificación** → se mide. Si el costo resultara
  desproporcionado, la salida es cachear la clasificación por `sha256` de la coordenada
  dentro del mismo archivo de índice, no bajar la resolución de los polígonos.

- **Un consumidor existente no tolera el campo nuevo** → se sube `SUGGESTIONS_VERSION` a 2
  para que pueda decidir, y el campo es opcional al leer. Un consumidor que valida el
  esquema de forma estricta igual va a rejecting los archivos nuevos: es el costo de
  agregar un dato al formato, y se documenta en el README.

- **La colección cruza un país que el conjunto no incluye** → `country` queda desconocido y
  `countries` lo muestra, en lugar de caer al país vecino. Es la razón de que
  "desconocido" sea un valor de primera clase y no un error.

- **La clasificación de un viaje depende de fotos que luego dejan de existir** → el archivo
  se regenera entero en cada escaneo, así que el país se recalcula con la colección
  actual. No hay estado que pueda quedar viejo entre escaneos.

## Migration Plan

1. Incorporar el conjunto de polígonos en `fotos_plus/data/` con su versión declarada, y
   verificar que la instalación del paquete lo incluye.
2. Implementar la carga del conjunto y el índice en memoria, con la consulta de país, y
   probarla por separado del agrupado.
3. Medir el costo de clasificar una colección de fotos de prueba y verificar el cruce de
   frontera con las coordenadas de referencia de los tests.
4. Clasificar por foto dentro de `build_suggestions` y acumular el conteo por país.
5. Agregar el objeto `location` a `TripSuggestion`, subir `SUGGESTIONS_VERSION` a 2 y
   resolverlo con `data.get()` en `from_dict`.
6. Declarar la versión del conjunto de países en el archivo de sugerencias e informarla en
   el resumen del escaneo.
7. Documentar en el README el campo nuevo, su procedencia, el tratamiento del viaje que
   cruza frontera y por qué los períodos no tienen país.

Rollback: revertir el commit. Los archivos de sugerencias con `version: 2` siguen
leyéndose porque el campo nuevo es opcional y `from_dict` lo resuelve con `data.get()`, así
que el código revertido los acepta sin perder sugerencias. No hay migración que deshacer:
el archivo es derivado y se regenera entero. El conjunto de polígonos desaparece con el
revert. Ningún archivo de foto se toca en ningún momento.

## Open Questions

- Qué nivel de nombre de lugar se quiere en el futuro para la ciudad, cuando exista un
  gazetteer. No cambia este diseño: es otro cambio, con su propia decisión de producto.
- Si el conjunto de países debería incluir también la región administrativa. Con los
  polígonos de país ya cargados, agregar la admin es más una elección de fuente que una
  decisión de arquitectura, y no hace falta ahora.
- Si el incidente de "el GPS dejó de escribirse" merece un cambio propio que lo detecte y
  lo exponga. La medición que lo revela está en el contexto de este diseño; el cambio no
  está en el alcance de este.

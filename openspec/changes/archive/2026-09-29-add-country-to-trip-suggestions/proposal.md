# Proposal

## Why

El archivo de sugerencias ya sabe qué viajes tienen coordenadas, pero no dice en qué
país están. En una colección con GPS presente, las fotos que tienen posición válida se
reparten en varios países y lugares distintos, así que el país es la etapa de
enriquecimiento más barata que existe: es una categoría cerrada, se resuelve offline y sin
ambigüedad.

`location_state: "known"` es además un nombre pobre. Hoy significa "tenemos coordenadas",
no "sabemos dónde estamos", y el mismo campo aparece con valor `unknown` en los períodos
que no tienen ninguna coordenada. Agregar el país como dato separado hace que
"dónde" deje de ser implícito.

## What Changes

- El escaneo clasifica cada foto con posición válida dentro de su país, usando un
  conjunto de polígonos de país incluido en el repositorio. La clasificación es local:
  no se abre ninguna conexión de red y no se envía ninguna coordenada a un tercero.
- Cada sugerencia de viaje declara su país, derivado de las fotos que la componen.
- Un viaje cuyas fotos caigan en más de un país NO se fuerza a uno: declara el país
  dominante y la lista completa de países presentes.
- El archivo de sugerencias suma un objeto `location` por viaje, con el país y su
  procedencia, y **conserva `location_state` sin cambios**, de modo que un consumidor que
  ya lee el archivo no se rompe.
- **BREAKING (menor)**: el contenido del archivo de sugerencias cambia de forma. Un
  consumidor que reconstructa el esquema de forma estricta tiene que tolerar el objeto
  nuevo. `SUGGESTIONS_VERSION` pasa a 2 para que un lector pueda distinguir el formato
  nuevo del anterior, sin dejar de poder leer los archivos viejos.
- Los 15 períodos sin ubicación **no** reciben país. No tienen coordenada, así que ningún
  geocodificación puede ubicarlos, y esta versión no infiere un lugar a partir de viajes
  vecinos.

## Capabilities

### New Capabilities

Ninguna. La capacidad de viajes y períodos ya existe y es la que cambia.

### Modified Capabilities

- `trip-periods`: los viajes sugeridos pasan a declarar su país, derivado de polígonos de
  país incluidos en el repositorio, con tratamiento explícito del viaje que cae en más de
  un país. Los períodos sin ubicación siguen sin lugar y su `location_state` no cambia.

## Impact

- `fotos_plus/places.py` (nuevo): carga de los polígonos de país y clasificación de una
  coordenada por punto en polígono.
- `fotos_plus/data/`: conjunto de polígonos de país en formato GeoJSON, incluido en el
  paquete. Es la primera dependencia de datos del proyecto y define su tamaño.
- `fotos_plus/models.py`: `TripSuggestion` gana el objeto `location`; `SUGGESTIONS_VERSION`
  pasa a 2; el campo opcional se lee con `data.get()` para que los archivos anteriores se
  sigan pouvant leerse.
- `fotos_plus/grouping.py`: clasificación por foto antes de construir los viajes, para que
  el país se derive de las fotos reales y no de un centroide.
- `fotos_plus/index.py`: el directorio de datos tiene que viajar con el paquete instalado.
- `pyproject.toml`: `package-data` para que el GeoJSON se instale. No se agrega ninguna
  dependencia de Python: la clasificación se implementa sobre la biblioteca estándar.
- `fotos-plus.bat` y `tests/test_bat.py`: el lanzador sigue funcionando desde una copia del
  proyecto, así que la ruta de los datos tiene que resolverse también en ese caso.
- Tamaño del escaneo: se agrega una clasificación por foto sobre cada coordenada. Con
  índice espacial es despreciable, pero sin él sería lineal por foto contra cada polígono y
  hay que medirlo.
- La ciudad queda fuera de alcance. Resolverla requiere un gazetteer y, sobre todo, decidir
  qué es "el lugar" cuando la coordenada cae en una ciudad, una provincia o un municipio.

## Rollback

Revertir el commit devuelve el escaneo a escribir el archivo de sugerencias sin país.
Los archivos de sugerencias anteriores se siguen pudiendo leer porque el campo nuevo es
opcional y `from_dict` lo resuelve con `data.get()`; no hay que reescanear nada para volver
al estado anterior, y tampoco hay migración que deshacer.

Los archivos de sugerencias con `version: 2` quedan en disco sin efecto: el código
revertido los sigue leyendo porque el campo nuevo se ignora. El conjunto de polígonos se
elimina con el revert y no toca la colección de fotos: el escaneo solo lee.

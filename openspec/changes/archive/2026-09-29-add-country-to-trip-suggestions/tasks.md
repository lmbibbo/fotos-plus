# Tasks

## 1. Conjunto de datos de países

- [x] 1.1 Evaluar la fuente de polígonos (Natural Earth u otra) por resolución frente a tamaño: confirmar que la escala elegida clasifica correctamente un cruce de frontera, y registrar en el repositorio la fuente, la licencia y la versión. Verificar con un script puntual que imprima el país de un conjunto de coordenadas de referencia, esperando una distribución mayoritaria/minoritaria en dos países. (Resultado medido: Natural Earth 1:10m; 10m y 50m aciertan 30/30 en las coordenadas de control, 110m falla en 6. Descartadas 110m y 50m.)

- [x] 1.2 Incorporar el GeoJSON en `fotos_plus/data/countries.geojson` con su versión declarada. Verificar que el archivo carga con `json` y que cada feature trae identificador de país legible.

- [x] 1.3 Declarar `fotos_plus/data/*.geojson` en `pyproject.toml` como `package-data` para que se instale con el paquete. Verificar con una instalación limpia (`pip install .` en un entorno virtual temporal) que el archivo está presente en el sitio instalado.

## 2. Clasificación de una coordenada

- [x] 2.1 Implementar en `fotos_plus/places.py` la carga del conjunto de países una sola vez por proceso, resuelta con `importlib.resources` y con la versión expuesta. Verificar con tests que dos llamadas consecutivas devuelven la misma versión y que no recargan el archivo.

- [x] 2.2 Implementar `country_of(lat, lon)` con punto en polígono sobre la biblioteca estándar, con descarte previo por caja envolvente, devolviendo `None` cuando ningún polígono contiene el punto. Verificar con tests que una coordenada en tierra de Brasil devuelve Brasil, una en el océano devuelve `None` y que no devuelve el país más cercano en ese caso.

- [x] 2.3 Indexar los polígonos en una grilla por caja envolvente para que la consulta solo inspeccione los candidatos de la celda. Verificar con tests que el resultado de `country_of` es idéntico con y sin el índice, sobre una muestra que incluya puntos de borde.

- [x] 2.4 Cubrir con tests los bordes que suelen fallar: coordenada sobre el borde de un polígono, punto en el hemisferio sur, punto en el antimeridiano y punto en una isla pequeña. Verificar que cada caso tiene un resultado definido y documentado.

## 3. Formato del archivo de sugerencias

- [x] 3.1 Agregar el objeto `location` a `TripSuggestion` con `country` y `countries`, resuelto en `from_dict` con `data.get()` y ausente por defecto en las fotos con posición que no se resolvieron. Verificar con tests de ida y vuelta que `to_dict` y `from_dict` conservan el objeto.

- [x] 3.2 Subir `SUGGESTIONS_VERSION` a 2 y agregar la versión del conjunto de países a `SuggestionsResult`. Verificar con un test que un archivo escrito con `version: 1` se lee completo, que ningún viaje ni período se pierde y que el país de cada sugerencia queda como desconocido.

- [x] 3.3 Verificar con un test que `location_state` conserva su significado: un viaje con coordenadas y sin país resuelto sigue declarando `known`, y un período sin coordenadas sigue declarando `unknown`.

## 4. Clasificación en el agrupado

- [x] 4.1 Clasificar cada foto con posición válida en `build_suggestions` antes de agrupar, y acumular el conteo de fotos por país en cada grupo de viaje. Verificar con tests que el conteo por país de un viaje es correcto con fotos interleaved de dos países.

- [x] 4.2 Declarar el país dominante como el de más fotos y la lista completa de países, dejando el país dominante desconocido cuando dos países empatan con el máximo. Verificar con tres tests: viaje de un solo país, viaje de dos países con mayoría clara, y viaje de dos países empatado.

- [x] 4.3 Dejar los períodos sin campo de país, sin inferirlo de los viajes vecinos en la línea de tiempo. Verificar con un test que un período entre dos viajes de países distintos no declara ningún país.

- [x] 4.4 Preservar el comportamiento actual de agrupación, radio y umbrales. Verificar que los 45 viajes y los 15 períodos de la colección de referencia se siguen generando igual que antes del cambio, con los mismos conteos y las mismas fronteras.

## 5. Verificación de integración

- [x] 5.1 Ejecutar la suite completa y `openspec validate --specs --strict`, y confirmar que no hay regresiones. (Resultado: 168 passed, 1 skipped en 29 s; 2 specs, 0 fallos.)

- [x] 5.2 Escanear una colección de prueba y registrar el costo de la clasificación por coordenada, el total de viajes con país resuelto y los que quedan sin país. Verificar que el escaneo no informa fallos de red y que el resumen declara la versión del conjunto de países. (Resultado de la corrida local: los conteos de viajes y períodos fueron idénticos antes y después del cambio; los viajes con país, sin país y los que cruzan frontera se comportaron como espera el diseño; el costo por foto fue marginal respecto de la carga única del índice; sin red.)

- [x] 5.3 Documentar en el README el campo `location`, su procedencia a partir de las coordenadas, el tratamiento de un viaje que cruza frontera (país dominante más lista completa) y por qué los períodos no declaran país.

# Proposal

## Why

El escaneo actual solo produce el inventario de fotos y descarta la posición, así que no hay
forma de saber dónde se tomó cada foto ni de armar viajes. Además, el escaneo es el único
momento en que el sistema recorre la colección completa: si el agrupado se calculara "al
leer", el visualizador tendría que recorrer todas las fotos y resolver el agrupado en cada
consulta.

El agrupado tiene que vivir en un archivo, no calcularse al leer. En una colección con GPS
intermitente la cobertura es dispareja: una parte de las fotos tiene posición utilizable y
otra no, y esa parte sin posición se concentra en períodos sin señal en vez de repartirse al
azar. Reconstruir eso "al leer" significa repetir el mismo trabajo en cada consulta, sobre
datos que no cambian entre escaneos.

El agrupado se escribe como un segundo archivo JSON que el escaneo genera una sola vez, y las fotos sin posición dejan de descartarse: pasan a un período explícito que el usuario puede auditar y asignar a un lugar a mano.

Lo que produce este archivo son **sugerencias**, no viajes y períodos definitivos. Se calculan con un umbral fijo y con los datos de las coordenadas, así que son aproximaciones que van a cambiar cuando el usuario las revise y cuando aparezca el mecanismo de auditoría. El archivo se declara provisional y así se llama en disco, para que nadie lo lea como un dato confirmado. Los viajes y períodos definitivos son un trabajo futuro que este cambio habilita pero no implementa.

## What Changes

- El escaneo extrae y guarda `latitude` y `longitude` por foto, con una regla de validez explícita (presente y distinta de `(0, 0)`).
- El escaneo escribe, además del índice de inventario, un segundo archivo JSON de **sugerencias** de viajes y períodos, en la misma carpeta de destino que el índice.
- Un viaje sugerido se forma ordenando las fotos con posición válida por fecha de captura y manteniéndolas juntas mientras la distancia a la foto anterior sea menor a 200 km.
- Las fotos sin posición válida ya no se descartan: se agrupan en **períodos sugeridos**, bloques de días sin posición que quedan declarados en el archivo con su rango de fechas y su cantidad de fotos.
- Las fotos sin posición que sí comparten día con alguna foto con GPS se marcan como ubicables por referencia, y no requieren intervención manual.
- El archivo declara de forma explícita que su contenido es provisional, y cada viaje y cada período indica si su ubicación se conoce o no. El nombre del archivo incluye la palabra "sugerencias".
- El archivo de sugerencias se reescribe por completo en cada escaneo: no se edita a mano ni se acumulan datos de escaneos anteriores.

**BREAKING**: el agrupado deja de ser una lectura derivada y pasa a ser un archivo que el escaneo escribe. Cualquier consumidor que esperara calcular los viajes al leer tiene que leer este archivo nuevo.

## Capabilities

### New Capabilities
- `trip-periods`: escritura del archivo de sugerencias de viajes y períodos durante el escaneo, con la frontera espacial de 200 km, la declaración de los períodos sin posición, la marca de contenido provisional y la distinción entre ubicación conocida y desconocida.

### Modified Capabilities
- `photo-scanning`: el escaneo pasa a registrar latitud y longitud por foto y a producir, además del índice de inventario, un archivo de sugerencias de viajes y períodos.

## Impact

- `fotos_plus/photos.py`: extracción de los tags de GPS (`0x8825` y su IFD) y conversión a grados decimales.
- `fotos_plus/models.py`: dos campos opcionales en `Photo` y los tipos nuevos de viaje, período y resumen, con una marca de contenido provisional. `Photo.from_dict` ya lee con `data.get()`, así que los índices existentes siguen leyéndose sin migración.
- `fotos_plus/index.py`: helpers de ruta para el segundo archivo, siguiendo la convención de nombre por hash de la carpeta raíz.
- `fotos_plus/scanner.py`: el agrupado se calcula sobre el `ScanResult` ya construido, antes de escribir.
- `fotos_plus/cli.py`: el resumen informa la ruta del archivo de sugerencias y los conteos de períodos.
- Módulo nuevo de agrupado, con la geometría y la partición.
- `.gitignore`: el patrón actual `/[0-9a-f]*.json` ya cubre también `<hash>-sugerencias.json`, porque el asterisco absorbe el sufijo. No hace falta una regla nueva.
- Costo medido: leer todo el EXIF agrega del orden de milisegundos por foto, un porcentaje
  pequeño del costo de hashear el archivo, y es despreciable frente al tiempo total de un
  escaneo real. El agrupado agrega una partición lineal sobre la lista de fotos.
- No hay dependencia de otros cambios: la extracción de coordenadas se implementa acá.

## Rollback

- Revertir el commit devuelve el escaneo a escribir únicamente el inventario. El archivo de sugerencias previo queda en disco como un archivo más, sin efecto: nada lo lee.
- El archivo de sugerencias es derivado y se regenera entero en cada escaneo. No hay migración que deshacer ni que aplicar.
- La coordenada de las fotos no se toca: el escaneo sigue sin mover, renombrar ni modificar ningún archivo de foto, así que el rollback no requiere restaurar nada en la colección.
- Si el archivo de sugerencias resultara corrupto o ilegible, se puede borrar sin pérdida: el siguiente escaneo lo regenera.
- Los viajes y períodos definitivos, que este cambio no produce, quedan fuera de este rollback. Como las sugerencias no son la fuente de verdad, perderlas no pierde información del usuario: se recalculan.
- Las revisiones manuales del usuario, cuando existan, NO están cubiertas por este rollback y quedan fuera de este cambio a propósito. Por eso las sugerencias viven en un archivo aparte: para que un trabajo futuro de auditoría no dependa de un archivo que el escaneo sobrescribe.

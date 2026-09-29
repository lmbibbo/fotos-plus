# trip-periods Specification

## Purpose

Permite que el escaneo escriba, junto al inventario de fotos, un archivo de sugerencias de viajes y períodos, que son aproximaciones derivadas de las coordenadas y de la fecha. Ninguna de esas sugerencias es un dato confirmado: existen para que el usuario pueda revisarlas y convertirlas, con el tiempo, en viajes y períodos definitivos.

## Requirements

### Requirement: Los viajes y los períodos son sugerencias

El sistema DEBE (MUST) declarar que los viajes y los períodos que produce son sugerencias, no un dato confirmado. El archivo DEBE declarar su carácter provisional de forma explícita, y NO DEBE presentar ningún viaje ni ningún período como definitivo. La distinción entre una foto cuya ubicación se conoce y otra que no se conoce NO DEBE confundirse con la distinción entre una sugerencia y un hecho confirmado.

#### Scenario: El archivo se declara provisional

- **GIVEN** un archivo de sugerencias recién escrito por un escaneo
- **WHEN** se consulta el archivo
- **THEN** el archivo declara que su contenido es provisional
- **AND** quien lo consulta puede distinguir que sus viajes y sus períodos son sugerencias

#### Scenario: Una sugerencia con coordenadas sigue siendo una sugerencia

- **GIVEN** un viaje sugerido a partir de fotos con posición válida
- **WHEN** se consulta el archivo
- **THEN** ese viaje figura como sugerido y con su ubicación conocida
- **AND** NO figura como confirmado

#### Scenario: Un período sin ubicación sigue siendo una sugerencia

- **GIVEN** un período sugerido de fotos sin posición válida
- **WHEN** se consulta el archivo
- **THEN** ese período figura como sugerido y sin ubicación conocida
- **AND** NO figura como un lugar que el usuario haya confirmado

#### Scenario: El archivo por sí solo no alcanza para afirmar un viaje

- **GIVEN** un archivo de sugerencias de viajes y períodos
- **WHEN** un proceso lo consume para afirmar dónde estuvo el usuario
- **THEN** ese proceso DEBE presentar la información como sugerida
- **AND** NO DEBE presentarla como un hecho verificado

### Requirement: Sugerencias de viaje por frontera espacial

El sistema DEBE (MUST) sugerir viajes a partir de las fotos con posición válida, ordenándolas por fecha de captura y manteniéndolas en la misma sugerencia mientras la distancia a la foto anterior sea menor a 200 km. La fecha DEBE ordenar las fotos dentro de la sugerencia pero NO DEBE actuar por sí sola como criterio de separación.

#### Scenario: Fotos tomadas en un mismo lugar

- **GIVEN** fotos tomadas en un mismo lugar, en días distintos
- **WHEN** el escaneo construye las sugerencias
- **THEN** todas esas fotos quedan en una misma sugerencia de viaje
- **AND** la sugerencia informa la cantidad de fotos y la primera y la última fecha

#### Scenario: Traslado entre dos lugares alejados

- **GIVEN** fotos tomadas en un lugar y luego fotos tomadas en otro lugar distante
- **WHEN** el escaneo construye las sugerencias
- **THEN** el traslado genera una sugerencia de viaje nueva
- **AND** el paso de un lugar a otro se produce por la distancia, no por el tiempo transcurrido

#### Scenario: Estancia larga en un mismo lugar

- **GIVEN** fotos tomadas durante varias semanas en un mismo lugar
- **WHEN** el escaneo construye las sugerencias
- **THEN** esas fotos permanecen en una misma sugerencia
- **AND** la sugerencia no se fragmenta por el paso de los días

#### Scenario: Colección sin ninguna posición válida

- **GIVEN** una colección en la que ninguna foto tiene posición válida
- **WHEN** el escaneo construye las sugerencias
- **THEN** el archivo se escribe sin ninguna sugerencia de viaje
- **AND** todas las fotos quedan declaradas en los períodos sugeridos sin ubicación

### Requirement: Validez de la posición de una foto

El sistema DEBE (MUST) considerar que una foto tiene posición válida únicamente cuando su latitud y su longitud están presentes y no son ambas cero. Una coordenada de cero en ambos ejes NO DEBE interpretarse como una posición.

#### Scenario: Coordenada de origen

- **GIVEN** una foto cuyos metadatos tienen GPS con coordenada distinta de (0, 0)
- **WHEN** el escaneo lee esa foto
- **THEN** la foto queda registrada con esa posición

#### Scenario: GPS presente pero vacío

- **GIVEN** una foto que declara un bloque de GPS sin ningún valor
- **WHEN** el escaneo lee esa foto
- **THEN** la foto queda registrada sin posición

#### Scenario: Coordenada (0, 0)

- **GIVEN** una foto cuyos metadatos tienen GPS con latitud y longitud en cero
- **WHEN** el escaneo lee esa foto
- **THEN** la foto queda registrada sin posición
- **AND** no se la asigna a ningún lugar de la superficie terrestre

### Requirement: Períodos sugeridos sin ubicación conocida

El sistema DEBE (MUST) sugerir los períodos de fotos sin posición válida, en lugar de descartarlas. Un período sugerido DEBE incluir la primera y la última fecha de sus fotos y la cantidad de fotos que contiene. Los períodos DEBE permanecer separados entre sí, sin fusionarse en un único período que abarque todo el conjunto.

#### Scenario: Días consecutivos sin posición

- **GIVEN** fotos sin posición tomadas en días consecutivos
- **WHEN** el escaneo construye las sugerencias
- **THEN** esas fotos forman un mismo período sugerido
- **AND** el período declara su rango de fechas y su cantidad de fotos

#### Scenario: Hueco entre dos tramos sin posición

- **GIVEN** dos tramos de fotos sin posición separados por un intervalo en el que no se tomó ninguna foto
- **WHEN** el escaneo construye las sugerencias
- **THEN** cada tramo se declara como un período sugerido distinto
- **AND** no existe ningún período que abarque el intervalo sin fotos

#### Scenario: Ninguna foto sin posición

- **GIVEN** una colección en la que todas las fotos tienen posición válida
- **WHEN** el escaneo construye las sugerencias
- **THEN** el archivo se escribe sin períodos sin ubicación

### Requirement: Fotos sin fecha de captura

El sistema DEBE (MUST) declarar por separado cuántas fotos no tienen fecha de captura, en lugar de inventarles una fecha o de incorporarlas a un grupo al que no pertenecen. Esas fotos NO DEBE entrar en las sugerencias de viaje ni en los períodos sugeridos, porque no se pueden ordenar por fecha ni asignar a un día. La declaración DEBE permitir que la suma de fotos del archivo cuadre con la del inventario.

#### Scenario: Foto sin fecha entre fotos fechadas

- **GIVEN** una colección con fotos fechadas y al menos una foto sin fecha de captura
- **WHEN** el escaneo construye las sugerencias
- **THEN** la foto sin fecha no aparece en ninguna sugerencia de viaje ni en ningún período
- **AND** el archivo declara cuántas fotos quedaron sin fecha
- **AND** la fecha de esa foto no se inventa

#### Scenario: Fotografías de pantalla sin fecha

- **GIVEN** una captura de pantalla sin fecha de captura en sus metadatos
- **WHEN** el escaneo construye las sugerencias
- **THEN** esa foto se cuenta entre las fotos sin fecha
- **AND** no se la asigna a ningún día ni a ningún período

### Requirement: Fotos sin posición que se pueden ubicar por referencia

El sistema DEBE (MUST) distinguir las fotos sin posición válida que comparten día con al menos una foto con posición válida, y marcarlas como ubicables por referencia, de modo que no requieran asignación manual. Las fotos sin posición que no comparten día con ninguna foto con posición DEBE quedar dentro de un período sugerido.

#### Scenario: Foto sin posición en un día con GPS

- **GIVEN** un día que tiene fotos con posición válida y también fotos sin posición
- **WHEN** el escaneo construye las sugerencias
- **THEN** esas fotos sin posición se marcan como ubicables por referencia
- **AND** no forman parte de ningún período sin ubicación

#### Scenario: Foto sin posición en un día sin ninguna otra foto con posición

- **GIVEN** un día en el que ninguna foto tiene posición válida
- **WHEN** el escaneo construye las sugerencias
- **THEN** las fotos de ese día pertenecen a un período sugerido sin ubicación

### Requirement: Archivo de sugerencias de viajes y períodos

El sistema DEBE (MUST) guardar las sugerencias de viajes y de períodos en un archivo propio, consultable por otros procesos, escrito en la misma carpeta que el índice de inventario. El archivo DEBE indicar la carpeta raíz escaneada, el momento del escaneo y la versión de su formato, y DEBE ser reemplazado por completo en cada escaneo, sin conservar datos de escaneos anteriores. El nombre del archivo DEBE indicar que su contenido son sugerencias, de modo que no se confunda con un archivo de viajes y períodos definitivos.

#### Scenario: Primer escaneo

- **GIVEN** una carpeta sin archivo de sugerencias previo
- **WHEN** se escanea
- **THEN** se crea el archivo de sugerencias de viajes y períodos con los viajes sugeridos y los períodos sin ubicación

#### Scenario: Rescaneo de la misma carpeta

- **GIVEN** una carpeta ya escaneada, con un archivo de sugerencias previo y fotos nuevas
- **WHEN** se escanea nuevamente
- **THEN** el archivo de sugerencias refleja las fotos actuales
- **AND** no quedan datos del escaneo anterior

#### Scenario: Carpeta de destino indicada

- **GIVEN** una carpeta de destino indicada por el usuario
- **WHEN** se escanea una carpeta de fotos
- **THEN** el archivo de sugerencias se escribe dentro de la carpeta de destino
- **AND** su nombre corresponde a la misma carpeta raíz que el del índice de inventario

#### Scenario: Varias carpetas escaneadas al mismo destino

- **GIVEN** una misma carpeta de destino indicada para dos carpetas de fotos distintas
- **WHEN** se escanean las dos
- **THEN** cada carpeta de fotos tiene su propio archivo de sugerencias dentro del destino
- **AND** ninguno de los dos archivos se sobrescribe con el contenido del otro

#### Scenario: El nombre no se confunde con un archivo definitivo

- **GIVEN** el archivo de sugerencias de una carpeta escaneada
- **WHEN** se observa su nombre en el disco
- **THEN** el nombre indica que su contenido son sugerencias
- **AND** no se confunde con un archivo de viajes y períodos ya confirmados

#### Scenario: Archivo de sugerencias ausente

- **GIVEN** un archivo de sugerencias que no existe
- **WHEN** se escanea una carpeta de fotos
- **THEN** el escaneo no falla
- **AND** el archivo se crea con los datos del escaneo actual

### Requirement: Visibilidad de lo que está pendiente de auditar

El sistema DEBE (MUST) marcar de forma explícita si la ubicación de una sugerencia de viaje o de un período se conoce a partir de las coordenadas, o si no se conoce. El archivo NO DEBE presentar como confirmada una ubicación que no se conoce, ni una ubicación que solo proviene de una sugerencia.

#### Scenario: Sugerencia de viaje con coordenadas

- **GIVEN** un viaje sugerido a partir de fotos con posición válida
- **WHEN** se consulta el archivo
- **THEN** ese viaje aparece con su ubicación conocida y marcada como sugerida
- **AND** con la cantidad de fotos y su rango de fechas

#### Scenario: Período sin ubicación conocida

- **GIVEN** un período sugerido de fotos sin posición válida
- **WHEN** se consulta el archivo
- **THEN** ese período aparece sin ubicación
- **AND** con la cantidad de fotos y su rango de fechas

#### Scenario: Inventario de lo que falta auditar

- **GIVEN** una colección con fotos sin posición
- **WHEN** se consulta el archivo
- **THEN** se conoce cuántas fotos quedaron en períodos sin ubicación
- **AND** se conoce cuántas de ellas se marcaron como ubicables por referencia

### Requirement: El agrupado no altera las fotos

El sistema DEBE (MUST) limitarse a leer los archivos de la carpeta escaneada al construir las sugerencias: NO DEBE mover, renombrar, copiar, modificar ni eliminar ningún archivo de foto, ni cambiar sus permisos o fechas.

#### Scenario: Carpeta escaneada dos veces

- **GIVEN** una carpeta con fotos
- **WHEN** se escanea dos veces
- **THEN** los archivos de la carpeta están en las mismas rutas, con los mismos contenidos, después de cada escaneo

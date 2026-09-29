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

### Requirement: País de las sugerencias de viaje

El sistema DEBE (MUST) declarar el país de cada sugerencia de viaje, derivado de las fotos que la componen, cuando esas fotos tengan posición válida. El país DEBE derivarse de las coordenadas de las fotos individuales y NO DEBE derivarse de un punto representativo del viaje, porque un centroide puede caer en un país que no contiene ninguna de sus fotos.

Cuando las fotos de un viaje caigan en más de un país, el sistema DEBE declarar el país dominante, que es el que concentra más fotos, y DEBE declarar además la lista completa de países presentes en el viaje. Cuando dos países empateen con la misma cantidad de fotos, el sistema NO DEBE elegir uno: DEBE declarar que no hay un país dominante y listar los empates.

Cuando ninguna foto de un viaje pueda resolverse a un país, el sistema DEBE declarar que el país es desconocido, en lugar de dejar el campo vacío o de asignarle el país más cercano. Un viaje puede tener su ubicación conocida por sus coordenadas y aun así no tener país: son hechos distintos y ambos se declaran por separado.

Los períodos sugeridos NO DEBE recibir un país. Los períodos agrupan fotos sin posición válida, y una foto sin posición no se puede clasificar en ningún país. El sistema NO DEBE inferir el país de un período a partir de los viajes que lo anteceden o siguen en el tiempo, porque esa inferencia no está respaldada por ninguna coordenada de ese período.

#### Scenario: Viaje entero dentro de un país

- **GIVEN** un viaje sugerido cuyas fotos tienen posición válida y todas caen dentro de
  un mismo país
- **WHEN** el escaneo construye las sugerencias
- **THEN** el viaje declara ese país
- **AND** el país declarado es el que concentra la totalidad de sus fotos

#### Scenario: Viaje que cruza una frontera

- **GIVEN** un viaje sugerido cuyas fotos tienen posición válida y caen en dos países
- **WHEN** el escaneo construye las sugerencias
- **THEN** el viaje declara como país dominante el que concentra más de sus fotos
- **AND** el viaje declara los dos países presentes en su lista de países
- **AND** NO se descarta ninguno de los dos países por ser minoritario

#### Scenario: Viaje sin país dominante por empate

- **GIVEN** un viaje sugerido cuyas fotos se reparten en dos países con la misma cantidad
  de fotos
- **WHEN** el escaneo construye las sugerencias
- **THEN** el viaje declara que no hay un país dominante
- **AND** el viaje declara los dos países presentes

#### Scenario: Viaje con coordenadas que no caen en ningún país

- **GIVEN** un viaje sugerido cuyas fotos tienen posición válida y ninguna de sus
  coordenadas cae dentro de un país
- **WHEN** el escaneo construye las sugerencias
- **THEN** el viaje declara su país como desconocido
- **AND** el viaje sigue declarando que su ubicación se conoce a partir de las coordenadas
- **AND** NO se le asigna el país más cercano a sus coordenadas

#### Scenario: Período sin ubicación no recibe país

- **GIVEN** un período sugerido de fotos sin posición válida
- **WHEN** el escaneo construye las sugerencias
- **THEN** ese período no declara ningún país
- **AND** ese período sigue declarando que su ubicación se desconoce

### Requirement: La clasificación de país se resuelve localmente

La clasificación de una coordenada en un país DEBE (MUST) resolverse con información que viaja con el programa, sin conexión de red. El escaneo NO DEBE abrir una conexión de red para clasificar coordenadas, y NO DEBE enviar ninguna coordenada de la colección a un servicio externo. El sistema DEBE declarar de forma explícita cuando no puede clasificar una coordenada por falta de la información de países, en lugar de devolver un país aproximado.

Los países que el sistema reconoce DEBE ser un conjunto identificable y estable, para que el mismo conjunto de coordenadas produzca siempre los mismos países, y DEBE quedar identificado en el archivo de sugerencias junto a la versión de su formato.

#### Scenario: El escaneo clasifica sin conexión

- **GIVEN** una colección de fotos con posición válida y una máquina sin conexión de red
- **WHEN** se escanea esa colección
- **THEN** el archivo de sugerencias declara el país de los viajes
- **AND** el escaneo no informa ningún fallo por falta de conexión

#### Scenario: El conjunto de países es identificable

- **GIVEN** un archivo de sugerencias recién escrito
- **WHEN** se consulta el archivo
- **THEN** el archivo declara qué conjunto de países se usó para clasificar
- **AND** el archivo declara la versión de ese conjunto

#### Scenario: Misma colección, mismo resultado

- **GIVEN** una colección de fotos escaneada dos veces con la misma versión del conjunto de
  países
- **WHEN** se comparan los dos archivos de sugerencias
- **THEN** el país declarado para cada viaje es el mismo en los dos archivos

### Requirement: Archivo de sugerencias de viajes y períodos

El sistema DEBE (MUST) guardar las sugerencias de viajes y de períodos en un archivo propio, consultable por otros procesos, escrito en la misma carpeta que el índice de inventario. El archivo DEBE indicar la carpeta raíz escaneada, el momento del escaneo y la versión de su formato, y DEBE ser reemplazado por completo en cada escaneo, sin conservar datos de escaneos anteriores. El nombre del archivo DEBE indicar que su contenido son sugerencias, de modo que no se confunda con un archivo de viajes y períodos definitivos.

El formato del archivo DEBE distinguir la versión que declara el país de las sugerencias de la versión anterior que no lo hacía, para que un lector pueda distinguir ambas sin adivinar. El campo que declara el país DEBE ser opcional al leer: un archivo de sugerencias escrito por una versión anterior del programa DEBE poder leerse sin perder las sugerencias que contiene, y en ese caso el país se considera desconocido.

El campo `location_state` DEBE conservarse con su significado actual, que es si la ubicación se conoce a partir de las coordenadas, y NO DEBE reutilizarse para el nombre del lugar. Son ejes distintos: un viaje puede tener ubicación conocida y a la vez no tener país resuelto, y un consumidor tiene que poder distinguir los dos casos.

#### Scenario: Primer escaneo

- **GIVEN** una carpeta sin archivo de sugerencias previo
- **WHEN** se escanea
- **THEN** se crea el archivo de sugerencias de viajes y períodos con los viajes sugeridos
  y los períodos sin ubicación

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

#### Scenario: El archivo declara la versión de su formato

- **GIVEN** un archivo de sugerencias recién escrito
- **WHEN** se consulta el archivo
- **THEN** el archivo declara la versión de su formato
- **AND** esa versión permite distinguir un archivo que declara el país de uno que no lo
  hace

#### Scenario: Lectura de un archivo escrito antes del campo de país

- **GIVEN** un archivo de sugerencias escrito por una versión anterior del programa, que
  no declara país
- **WHEN** se lee ese archivo
- **THEN** la lectura devuelve todas las sugerencias que el archivo contiene
- **AND** el país de cada sugerencia se considera desconocido
- **AND** NO se pierde ningún viaje ni ningún período por la ausencia del campo

#### Scenario: El país no reemplaza al estado de ubicación

- **GIVEN** un viaje sugerido con ubicación conocida y con su país resuelto
- **WHEN** se consulta el archivo
- **THEN** el viaje declara por separado que su ubicación se conoce y cuál es su país
- **AND** `location_state` sigue significando si la ubicación se conoce, no el nombre del
  lugar

### Requirement: Visibilidad de lo que está pendiente de auditar

El sistema DEBE (MUST) marcar de forma explícita si la ubicación de una sugerencia de viaje o de un período se conoce a partir de las coordenadas, o si no se conoce. El archivo NO DEBE presentar como confirmada una ubicación que no se conoce, ni una ubicación que solo proviene de una sugerencia.

Un país resuelto a partir de las coordenadas NO DEBE presentarse como un lugar confirmado por el usuario. Sigue siendo una derivación automática, y el archivo DEBE poder distinguir un viaje cuyo país se dedujo de sus coordenadas de un lugar que el usuario haya confirmado a mano.

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

#### Scenario: Un país deducido no es un lugar confirmado

- **GIVEN** un viaje sugerido cuyo país se resolvió a partir de las coordenadas de sus
  fotos
- **WHEN** se consulta el archivo
- **THEN** el archivo marca ese país como derivado de las coordenadas
- **AND** el archivo NO lo presenta como un lugar que el usuario haya confirmado

### Requirement: El agrupado no altera las fotos

El sistema DEBE (MUST) limitarse a leer los archivos de la carpeta escaneada al construir las sugerencias: NO DEBE mover, renombrar, copiar, modificar ni eliminar ningún archivo de foto, ni cambiar sus permisos o fechas.

#### Scenario: Carpeta escaneada dos veces

- **GIVEN** una carpeta con fotos
- **WHEN** se escanea dos veces
- **THEN** los archivos de la carpeta están en las mismas rutas, con los mismos contenidos, después de cada escaneo

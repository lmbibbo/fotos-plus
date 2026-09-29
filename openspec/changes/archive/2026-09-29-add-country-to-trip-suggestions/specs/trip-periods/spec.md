# Spec Delta

## ADDED Requirements

### Requirement: País de las sugerencias de viaje

El sistema DEBE (MUST) declarar el país de cada sugerencia de viaje, derivado de las fotos
que la componen, cuando esas fotos tengan posición válida. El país DEBE derivarse de las
coordenadas de las fotos individuales y NO DEBE derivarse de un punto representativo del
viaje, porque un centroide puede caer en un país que no contiene ninguna de sus fotos.

Cuando las fotos de un viaje caigan en más de un país, el sistema DEBE declarar el país
dominante, que es el que concentra más fotos, y DEBE declarar además la lista completa de
países presentes en el viaje. Cuando dos países empateen con la misma cantidad de fotos,
el sistema NO DEBE elegir uno: DEBE declarar que no hay un país dominante y listar los
empates.

Cuando ninguna foto de un viaje pueda resolverse a un país, el sistema DEBE declarar que
el país es desconocido, en lugar de dejar el campo vacío o de asignarle el país más
cercano. Un viaje puede tener su ubicación conocida por sus coordenadas y aun así no
tener país: son hechos distintos y ambos se declaran por separado.

Los períodos sugeridos NO DEBE recibir un país. Los períodos agrupan fotos sin posición
válida, y una foto sin posición no se puede clasificar en ningún país. El sistema NO DEBE
inferir el país de un período a partir de los viajes que lo anteceden o siguen en el
tiempo, porque esa inferencia no está respaldada por ninguna coordenada de ese período.

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

La clasificación de una coordenada en un país DEBE (MUST) resolverse con información que
viaja con el programa, sin conexión de red. El escaneo NO DEBE abrir una conexión de red
para clasificar coordenadas, y NO DEBE enviar ninguna coordenada de la colección a un
servicio externo. El sistema DEBE declarar de forma explícita cuando no puede clasificar
una coordenada por falta de la información de países, en lugar de devolver un país
aproximado.

Los países que el sistema reconoce DEBE ser un conjunto identificable y estable, para que
el mismo conjunto de coordenadas produzca siempre los mismos países, y DEBE quedar
identificado en el archivo de sugerencias junto a la versión de su formato.

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

## MODIFIED Requirements

### Requirement: Archivo de sugerencias de viajes y períodos

El sistema DEBE (MUST) guardar las sugerencias de viajes y de períodos en un archivo
propio, consultable por otros procesos, escrito en la misma carpeta que el índice de
inventario. El archivo DEBE indicar la carpeta raíz escaneada, el momento del escaneo y la
versión de su formato, y DEBE ser reemplazado por completo en cada escaneo, sin conservar
datos de escaneos anteriores. El nombre del archivo DEBE indicar que su contenido son
sugerencias, de modo que no se confunda con un archivo de viajes y períodos definitivos.

El formato del archivo DEBE distinguir la versión que declara el país de las sugerencias de
la versión anterior que no lo hacía, para que un lector pueda distinguir ambas sin adivinar.
El campo que declara el país DEBE ser opcional al leer: un archivo de sugerencias escrito
por una versión anterior del programa DEBE poder leerse sin perder las sugerencias que
contiene, y en ese caso el país se considera desconocido.

El campo `location_state` DEBE conservarse con su significado actual, que es si la
ubicación se conoce a partir de las coordenadas, y NO DEBE reutilizarse para el nombre del
lugar. Son ejes distintos: un viaje puede tener ubicación conocida y a la vez no tener
país resuelto, y un consumidor tiene que poder distinguir los dos casos.

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

El sistema DEBE (MUST) marcar de forma explícita si la ubicación de una sugerencia de viaje
o de un período se conoce a partir de las coordenadas, o si no se conoce. El archivo NO
DEBE presentar como confirmada una ubicación que no se conoce, ni una ubicación que solo
proviene de una sugerencia.

Un país resuelto a partir de las coordenadas NO DEBE presentarse como un lugar confirmado
por el usuario. Sigue siendo una derivación automática, y el archivo DEBE poder distinguir
un viaje cuyo país se dedujo de sus coordenadas de un lugar que el usuario haya
confirmado a mano.

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

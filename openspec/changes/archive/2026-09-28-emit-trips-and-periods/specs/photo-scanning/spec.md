# Spec Delta

## MODIFIED Requirements

### Requirement: Datos básicos de cada foto

El sistema DEBE (MUST) registrar por cada foto su ruta, su nombre de archivo, su
extensión, su tamaño en bytes y un hash calculado sobre su contenido, y DEBE registrar
además su latitud y su longitud cuando los metadatos las provean, dejando esos campos
vacíos cuando la foto no tenga una posición válida.

#### Scenario: Registro de una foto

- **GIVEN** un archivo de foto dentro de la carpeta escaneada
- **WHEN** se completa su procesamiento
- **THEN** el inventario contiene su ruta, nombre, extensión y tamaño en bytes
- **AND** el inventario contiene un hash de su contenido
- **AND** el inventario contiene su latitud y su longitud, o los deja vacíos si la foto
  no tiene una posición válida

#### Scenario: Foto sin posición en los metadatos

- **GIVEN** un archivo de foto cuyos metadatos no incluyen coordenadas
- **WHEN** se completa su procesamiento
- **THEN** el inventario registra esa foto con la latitud y la longitud vacías
- **AND** no se inventa ninguna posición para ella

### Requirement: Fecha de captura desde los metadatos

El sistema DEBE (MUST) obtener de los metadatos EXIF la fecha en que se tomó cada foto
cuando ese dato esté disponible, en zona horaria del dispositivo o sin ella de forma
explícita en el inventario. Cuando la foto no tenga fecha de captura, el inventario DEBE
dejar el campo vacío en lugar de inventar un valor. La fecha de captura DEBE conservarse
sin cambios aunque la foto no tenga posición, porque los períodos sin ubicación se
delimitan por fecha.

#### Scenario: Foto con fecha EXIF

- **GIVEN** una foto con fecha de captura en sus metadatos EXIF
- **WHEN** se escanea la carpeta que la contiene
- **THEN** el inventario registra la fecha de captura de esa foto

#### Scenario: Foto sin fecha EXIF

- **GIVEN** una foto cuyos metadatos no incluyen fecha de captura, por ejemplo una
  captura de pantalla
- **WHEN** se escanea la carpeta que la contiene
- **THEN** el inventario registra esa foto con el campo de fecha de captura vacío

#### Scenario: Foto sin posición pero con fecha

- **GIVEN** una foto que tiene fecha de captura y no tiene posición válida
- **WHEN** se escanea la carpeta que la contiene
- **THEN** el inventario conserva su fecha de captura
- **AND** la foto queda registrada sin latitud ni longitud

### Requirement: Índice local del inventario

El sistema DEBE (MUST) guardar el inventario resultante en un archivo de índice local
consultable por otros procesos, y DEBE reemplazar el índice anterior de esa misma carpeta
en lugar de acumular índices. El índice DEBE indicar la carpeta raíz escaneada y el
momento del escaneo. El usuario DEBE poder elegir la carpeta donde se guardan los índices,
y el sistema DEBE usar la carpeta indicada en lugar de la ubicación por defecto. Cuando el
usuario indique además un archivo concreto, ese archivo DEBE tener prioridad sobre la
carpeta. El escaneo DEBE escribir, en la misma carpeta de destino y con la misma
convención de nombre que el índice, el archivo de sugerencias de viajes y períodos
descrito en `trip-periods`, y el archivo de índice NO DEBE incluir los viajes ni los
períodos.

#### Scenario: Primer escaneo

- **GIVEN** una carpeta sin índice previo
- **WHEN** se escanea
- **THEN** se crea el archivo de índice con la carpeta raíz y el momento del escaneo, y
  con todas las fotos encontradas
- **AND** se crea también el archivo de sugerencias de viajes y períodos para esa misma
  carpeta

#### Scenario: Rescaneo de la misma carpeta

- **GIVEN** una carpeta ya escaneada, con un índice previo y fotos nuevas agregadas
- **WHEN** se escanea nuevamente
- **THEN** el índice resultante refleja las fotos actuales de la carpeta
- **AND** no queda más de un índice vigente para esa carpeta
- **AND** no queda más de un archivo de sugerencias de viajes y períodos vigente para
  esa carpeta

#### Scenario: Carpeta de destino indicada

- **GIVEN** una carpeta de destino indicada por el usuario que todavía no existe
- **WHEN** se escanea una carpeta de fotos
- **THEN** el índice se escribe dentro de la carpeta de destino, que se crea si hace
  falta
- **AND** el nombre del archivo es el mismo que se usaría con la ubicación por defecto
- **AND** el archivo de sugerencias se escribe en esa misma carpeta de destino

#### Scenario: Varias carpetas escaneadas al mismo destino

- **GIVEN** una misma carpeta de destino indicada para dos carpetas de fotos distintas
- **WHEN** se escanean las dos
- **THEN** cada carpeta de fotos tiene su propio archivo de índice dentro del destino
- **AND** ninguno de los dos archivos se sobrescribe con el contenido del otro
- **AND** cada carpeta de fotos tiene su propio archivo de sugerencias de viajes y
  períodos, sin sobrescribir el de la otra

#### Scenario: Carpeta de destino y archivo puntual

- **GIVEN** una carpeta de destino y un archivo de índice indicados a la vez
- **WHEN** se escanea una carpeta de fotos
- **THEN** el índice se escribe en el archivo indicado
- **AND** no se crea ningún archivo en la carpeta de destino
- **AND** el archivo de sugerencias se escribe junto al archivo de índice indicado

#### Scenario: El índice no arrastra los viajes

- **GIVEN** una carpeta escaneada
- **WHEN** se consulta el archivo de índice de esa carpeta
- **THEN** el índice contiene el inventario de las fotos y sus campos
- **AND** el índice no contiene los viajes ni los períodos, que viven en su propio
  archivo

### Requirement: Manejo de errores del escaneo

El sistema DEBE (MUST) informar los errores sin abortar el escaneo por causas
individuales, y DEBE terminar con un código de salida distinto de cero cuando la ruta
indicada no exista o no pueda leerse. Un fallo al calcular las sugerencias de viajes y
períodos no DEBE abortar el escaneo: en ese caso el inventario DEBE escribirse igual y el
sistema DEBE informar que el archivo de sugerencias no se generó.

#### Scenario: Ruta inexistente

- **GIVEN** una ruta que no existe
- **WHEN** se intenta escanear
- **THEN** se informa que la ruta no existe
- **AND** el comando termina con un código de salida de error

#### Scenario: Archivo corrupto en medio del recorrido

- **GIVEN** una carpeta con varias fotos y una de ellas corrupta
- **WHEN** se escanea la carpeta
- **THEN** las demás fotos se registran en el inventario
- **AND** se informa el archivo corrupto

#### Scenario: Fallo al calcular las sugerencias

- **GIVEN** una carpeta que se escanea sin errores
- **WHEN** el cálculo de las sugerencias de viajes y períodos falla
- **THEN** el archivo de índice se escribe igual con todas las fotos
- **AND** se informa que el archivo de sugerencias de viajes y períodos no se generó

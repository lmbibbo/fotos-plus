# photo-scanning Specification

## Purpose

Permite recorrer una carpeta de fotos y obtener el inventario de los archivos que
contiene, con sus datos básicos, la fecha de captura y la detección de duplicados, para
que el resto de la organización y el visualizador trabajen sobre una base conocida.

## Requirements

### Requirement: Escaneo recursivo de una carpeta

El sistema DEBE (MUST) tomar una ruta de carpeta y recorrerla junto con todos sus
subdirectorios, sin límite de profundidad, y localizar los archivos candidatos a foto en
todos los niveles.

#### Scenario: Carpeta con subdirectorios

- **GIVEN** una carpeta raíz que contiene fotos y los subdirectorios con fotos propias
- **WHEN** se escanea esa carpeta raíz
- **THEN** el inventario incluye las fotos de la raíz y las de cada subdirectorio
- **AND** cada foto registrada guarda su ruta relativa a la carpeta raíz

#### Scenario: Carpeta sin fotos

- **GIVEN** una carpeta existente que no contiene ningún archivo de foto
- **WHEN** se escanea esa carpeta
- **THEN** el inventario queda vacío
- **AND** el escaneo termina correctamente informando que no se encontraron fotos

### Requirement: Identificación de los archivos que son fotos

El sistema DEBE (MUST) considerar foto a los archivos de formatos de imagen admitidos
(por ejemplo JPEG, PNG, HEIC, WebP, TIFF, RAW) y DEBE ignorar los archivos de otros
formatos, sin registrarlos en el inventario. La lista de formatos admitidos DEBE ser
consultable por el usuario.

#### Scenario: Archivos que no son fotos

- **GIVEN** una carpeta que contiene un PDF, un video y un archivo de texto, además de
  fotos
- **WHEN** se escanea esa carpeta
- **THEN** el inventario incluye solamente las fotos
- **AND** ningún archivo que no sea foto aparece en el inventario

#### Scenario: Extensión de foto con contenido no válido

- **GIVEN** una carpeta que contiene un archivo con extensión de foto cuyo contenido no
  es una imagen legible
- **WHEN** se escanea esa carpeta
- **THEN** el archivo no se registra como foto
- **AND** el escaneo informa el archivo problemático y continúa con el resto

### Requirement: Datos básicos de cada foto

El sistema DEBE (MUST) registrar por cada foto su ruta, su nombre de archivo, su
extensión, su tamaño en bytes y un hash calculado sobre su contenido.

#### Scenario: Registro de una foto

- **GIVEN** un archivo de foto dentro de la carpeta escaneada
- **WHEN** se completa su procesamiento
- **THEN** el inventario contiene su ruta, nombre, extensión y tamaño en bytes
- **AND** el inventario contiene un hash de su contenido

### Requirement: Fecha de captura desde los metadatos

El sistema DEBE (MUST) obtener de los metadatos EXIF la fecha en que se tomó cada foto
cuando ese dato esté disponible, en zona horaria del dispositivo o sin ella de forma
explícita en el inventario. Cuando la foto no tenga fecha de captura, el inventario DEBE
dejar el campo vacío en lugar de inventar un valor.

#### Scenario: Foto con fecha EXIF

- **GIVEN** una foto con fecha de captura en sus metadatos EXIF
- **WHEN** se escanea la carpeta que la contiene
- **THEN** el inventario registra la fecha de captura de esa foto

#### Scenario: Foto sin fecha EXIF

- **GIVEN** una foto cuyos metadatos no incluyen fecha de captura, por ejemplo una
  captura de pantalla
- **WHEN** se escanea la carpeta que la contiene
- **THEN** el inventario registra esa foto con el campo de fecha de captura vacío

### Requirement: Detección de duplicados

El sistema DEBE (MUST) identificar, a partir del hash de contenido, los grupos de fotos
que son idénticas entre sí y DEBE marcar en el inventario cuáles son duplicados y a qué
foto se refieren.

#### Scenario: Copias de la misma foto

- **GIVEN** una carpeta que contiene dos archivos con el mismo contenido y nombres
  distintos, en carpetas distintas
- **WHEN** se escanea esa carpeta
- **THEN** el inventario conserva ambas fotos
- **AND** una de ellas queda marcada como duplicado de la otra

#### Scenario: Fotos con contenidos distintos

- **GIVEN** una carpeta con fotos cuyos contenidos difieren
- **WHEN** se escanea esa carpeta
- **THEN** ninguna foto del inventario queda marcada como duplicado

### Requirement: Índice local del inventario

El sistema DEBE (MUST) guardar el inventario resultante en un archivo de índice local
consultable por otros procesos, y DEBE reemplazar el índice anterior de esa misma carpeta
en lugar de acumular índices. El índice DEBE indicar la carpeta raíz escaneada y el
momento del escaneo. El usuario DEBE poder elegir la carpeta donde se guardan los índices,
y el sistema DEBE usar la carpeta indicada en lugar de la ubicación por defecto. Cuando
el usuario indique además un archivo concreto, ese archivo DEBE tener prioridad sobre la
carpeta.

#### Scenario: Primer escaneo

- **GIVEN** una carpeta sin índice previo
- **WHEN** se escanea
- **THEN** se crea el archivo de índice con la carpeta raíz y el momento del escaneo, y
  con todas las fotos encontradas

#### Scenario: Rescaneo de la misma carpeta

- **GIVEN** una carpeta ya escaneada, con un índice previo y fotos nuevas agregadas
- **WHEN** se escanea nuevamente
- **THEN** el índice resultante refleja las fotos actuales de la carpeta
- **AND** no queda más de un índice vigente para esa carpeta

#### Scenario: Carpeta de destino indicada

- **GIVEN** una carpeta de destino indicada por el usuario que todavía no existe
- **WHEN** se escanea una carpeta de fotos
- **THEN** el índice se escribe dentro de la carpeta de destino, que se crea si hace
  falta
- **AND** el nombre del archivo es el mismo que se usaría con la ubicación por defecto

#### Scenario: Varias carpetas escaneadas al mismo destino

- **GIVEN** una misma carpeta de destino indicada para dos carpetas de fotos distintas
- **WHEN** se escanean las dos
- **THEN** cada carpeta de fotos tiene su propio archivo de índice dentro del destino
- **AND** ninguno de los dos archivos se sobrescribe con el contenido del otro

#### Scenario: Carpeta de destino y archivo puntual

- **GIVEN** una carpeta de destino y un archivo de índice indicados a la vez
- **WHEN** se escanea una carpeta de fotos
- **THEN** el índice se escribe en el archivo indicado
- **AND** no se crea ningún archivo en la carpeta de destino

### Requirement: El escaneo no altera las fotos

El sistema DEBE (MUST) limitarse a leer los archivos de la carpeta escaneada: no DEBE
mover, renombrar, copiar, modificar ni eliminar ningún archivo de foto, ni cambiar sus
permisos o fechas.

#### Scenario: Carpeta escaneada dos veces

- **GIVEN** una carpeta con fotos
- **WHEN** se escanea dos veces
- **THEN** los archivos de la carpeta están en las mismas rutas, con los mismos
  contenidos, después de cada escaneo

### Requirement: Manejo de errores del escaneo

El sistema DEBE (MUST) informar los errores sin abortar el escaneo por causas
individuales, y DEBE terminar con un código de salida distinto de cero cuando la ruta
indicada no exista o no pueda leerse.

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

### Requirement: Informe de progreso del escaneo

El sistema DEBE (MUST) informar el avance del escaneo mientras procesa las fotos, con la
cantidad de fotos procesadas, el total, el porcentaje, la velocidad y el tiempo estimado
restante. El informe DEBE actualizarse en una sola línea, y el sistema NO DEBE emitirlo
cuando la salida no sea un terminal. El resumen final DEBE seguir mostrando los totales.

#### Scenario: Escaneo de una carpeta grande

- **GIVEN** una carpeta con suficientes fotos como para que el escaneo tarde más de unos
  segundos
- **WHEN** se escanea desde un terminal
- **THEN** el sistema informa periódicamente cuántas fotos procesó, cuántas faltan, el
  porcentaje, la velocidad y el tiempo estimado restante
- **AND** la información se mantiene en una sola línea que se sobrescribe

#### Scenario: Escaneo con la salida redirigida

- **GIVEN** la salida del comando redirigida a un archivo en lugar de un terminal
- **WHEN** se escanea una carpeta de fotos
- **THEN** no se escribe ninguna línea de progreso en la salida
- **AND** el resumen final se escribe igual

#### Scenario: Carpeta sin fotos

- **GIVEN** una carpeta existente que no contiene fotos
- **WHEN** se escanea desde un terminal
- **THEN** el escaneo termina informando que no se encontraron fotos
- **AND** no se emite progreso de fotos que no existen

# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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

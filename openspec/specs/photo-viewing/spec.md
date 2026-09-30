# photo-viewing Specification

## Purpose
Permite generar, desde el índice de fotos ya escaneado, un archivo HTML autocontenido que presenta las fotos agrupadas según las sugerencias de viajes y períodos, de modo que el usuario pueda revisarlas visualmente sin abrir el JSON ni un servidor.

## Requirements

### Requirement: Generación del visualizador desde el índice

El sistema DEBE (MUST) ofrecer un subcomando `view` que reciba la ruta de un índice de fotos ya escaneado y genere un archivo HTML con el visualizador. DEBE (MUST) escribir ese HTML junto al índice de entrada. El comando NO DEBE alterar el índice ni el archivo de sugerencias.

Si no puede escribir el archivo HTML, el comando DEBE (MUST) informar el motivo y terminar con un código de salida distinto de cero.

#### Scenario: Visualizador generado desde un índice existente

- **GIVEN** un índice de fotos escaneado previamente y su archivo de sugerencias contiguo
- **WHEN** se ejecuta el subcomando `view` con la ruta del índice
- **THEN** se genera un archivo HTML junto al índice
- **AND** el índice y el archivo de sugerencias quedan sin modificar

#### Scenario: No se puede escribir el HTML

- **GIVEN** una ruta de salida que no se puede escribir como archivo
- **WHEN** se ejecuta el subcomando `view`
- **THEN** el comando informa el motivo por la salida de error
- **AND** termina con un código de salida distinto de cero

#### Scenario: El HTML generado no depende de un servidor

- **GIVEN** un visualizador generado
- **WHEN** se abre el archivo HTML en un navegador sin conexión a internet
- **THEN** las miniaturas y los datos de las sugerencias se muestran
- **AND** el archivo NO requiere un servidor local para mostrar su contenido

### Requirement: Agrupación por viajes, períodos y fotos sin clasificar

Cuando el archivo de sugerencias contiguo al índice existe, el visualizador DEBE (MUST) presentar una tarjeta por cada viaje sugerido, una por cada período sugerido y, si hay fotos que no pertenecen a ningún viaje ni período, una por esas fotos. La tarjeta de fotos sin clasificar NO DEBE aparecer cuando no hay ninguna foto sin clasificar. DEBE (MUST) ordenar las tarjetas de forma ascendente por la fecha más temprana de cada grupo.

Cada tarjeta DEBE (MUST) mostrar la cantidad de fotos que el visor asignó al grupo, su rango de fechas y su país cuando el grupo declare uno. Los períodos NO DEBE mostrar país, porque por diseño no declaran ubicación.

La cantidad mostrada NO DEBE ser el `photo_count` de la sugerencia, porque ese campo cuenta las fotos que contribuyeron a la agrupación y no el total de fotos del rango.

#### Scenario: Viaje con fotos, fechas y país

- **GIVEN** un viaje sugerido con fotos, rango de fechas y país
- **WHEN** se genera el visualizador
- **THEN** aparece una tarjeta que muestra la cantidad de fotos del viaje, su rango de fechas y su país

#### Scenario: Período sin país

- **GIVEN** un período sugerido que no declara país por diseño
- **WHEN** se genera el visualizador
- **THEN** aparece una tarjeta del período que muestra su cantidad de fotos y su rango de fechas
- **AND** la tarjeta NO muestra un país

#### Scenario: Grupo declarado que se queda sin fotos propias

- **GIVEN** un período sugerido contenido dentro de un viaje que se superpone, de modo que sus fotos se asignan al viaje por tener prioridad
- **WHEN** se genera el visualizador
- **THEN** aparece igualmente la tarjeta del período
- **AND** la tarjeta indica que ese grupo no tiene fotos propias
- **AND** las fotos aparecen solo en la tarjeta del viaje, sin duplicarse

#### Scenario: Fotos que no pertenecen a ningún grupo

- **GIVEN** fotos escaneadas que no pertenecen a ningún viaje ni período
- **WHEN** se genera el visualizador
- **THEN** aparece una tarjeta que agrupa esas fotos
- **AND** ninguna foto escaneada queda fuera de toda tarjeta cuando el archivo de sugerencias existe

#### Scenario: Tarjetas en orden ascendente

- **GIVEN** varios viajes y períodos con fechas distintas
- **WHEN** se genera el visualizador
- **THEN** las tarjetas aparecen ordenadas de la fecha más temprana a la más reciente

### Requirement: Miniaturas con orientación correcta

Cada tarjeta DEBE (MUST) mostrar cinco miniaturas extraídas de las fotos de ese grupo. DEBE (MUST) generar las miniaturas aplicando la transformación de orientación EXIF antes de incluirlas, de modo que la miniatura tenga la proporción con la que se ve la foto. NO DEBE requerir que el visor interprete la marca de orientación.

Si un grupo tiene menos de cinco fotos, DEBE (MUST) mostrar todas las que tiene.

#### Scenario: Tarjeta con al menos cinco fotos

- **GIVEN** un grupo con al menos cinco fotos
- **WHEN** se genera el visualizador
- **THEN** su tarjeta muestra cinco miniaturas

#### Scenario: Tarjeta con menos de cinco fotos

- **GIVEN** un grupo con menos de cinco fotos
- **WHEN** se genera el visualizador
- **THEN** su tarjeta muestra todas las fotos del grupo

#### Scenario: Miniatura con orientación vertical

- **GIVEN** una foto tomada en vertical, con los píxeles almacenados apaisados y una marca de orientación EXIF
- **WHEN** se genera el visualizador
- **THEN** la miniatura aparece con la proporción vertical, como se ve la foto

### Requirement: Visualizador sin sugerencias disponibles

Si el archivo de sugerencias contiguo al índice no existe, el visualizador DEBE (MUST) generar el mismo archivo HTML con todas las fotos del índice en una grilla plana, sin agrupar. El comando NO DEBE fallar por la ausencia del archivo de sugerencias.

#### Scenario: Índice sin archivo de sugerencias

- **GIVEN** un índice de fotos sin archivo de sugerencias contiguo
- **WHEN** se ejecuta el subcomando `view`
- **THEN** se genera el mismo tipo de archivo HTML
- **AND** el contenido muestra todas las fotos en una grilla sin agrupar

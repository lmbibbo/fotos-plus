# Spec Delta

## MODIFIED Requirements

### Requirement: Agrupación por viajes, períodos y fotos sin clasificar

Cuando el archivo de sugerencias contiguo al índice existe, el visualizador DEBE (MUST) presentar una tarjeta por cada viaje sugerido, una por cada período sugerido y, si hay fotos que no pertenecen a ningún viaje ni período, una por esas fotos. La tarjeta de fotos sin clasificar NO DEBE aparecer cuando no hay ninguna foto sin clasificar. DEBE (MUST) ordenar las tarjetas de forma ascendente por la fecha más temprana de cada grupo.

Cada tarjeta DEBE (MUST) mostrar la cantidad de fotos que el visor asignó al grupo, su rango de fechas y su país cuando el grupo declare uno. Los períodos NO DEBE mostrar país, porque por diseño no declaran ubicación.

La cantidad mostrada NO DEBE ser el `photo_count` de la sugerencia, porque ese campo cuenta las fotos que contribuyeron a la agrupación y no el total de fotos del rango.

Cuando algún grupo tenga un tag asignado, el visualizador DEBE (MUST) ordenar las tarjetas por sección de tag en lugar de en una única lista, y dentro de cada sección DEBE (MUST) mantener el orden ascendente por fecha más temprana.

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

- **GIVEN** varios viajes y períodos con fechas distintas y sin tags asignados
- **WHEN** se genera el visualizador
- **THEN** las tarjetas aparecen ordenadas de la fecha más temprana a la más reciente

### Requirement: El HTML exportado es de solo lectura

El archivo HTML exportado por `view` DEBE (MUST) aplicar las etiquetas vigentes al generar las tarjetas. El export NO DEBE (MUST NOT) incluir controles de edición, porque sin servidor no podrían guardarse. El export DEBE (MUST) indicar de forma visible que es de solo lectura, y NO DEBE (MUST NOT) crear el archivo de edición como efecto de generar el visualizador. El export DEBE (MUST) presentar las tarjetas agrupadas en secciones por tag cuando haya tags asignados.

#### Scenario: El export refleja las etiquetas

- **GIVEN** un archivo de edición con etiquetas vigentes
- **WHEN** se genera el HTML exportado con `view` sin `--serve`
- **THEN** las tarjetas aparecen con los títulos de las etiquetas

#### Scenario: El export no ofrece edición

- **GIVEN** un HTML exportado
- **WHEN** se abre en un navegador sin servidor
- **THEN** la página indica que es de solo lectura
- **AND** no ofrece ningún control que intente guardar cambios

#### Scenario: El export no crea el archivo de edición

- **GIVEN** un índice sin archivo de edición contiguo
- **WHEN** se genera el HTML exportado
- **THEN** no se crea el archivo de edición junto al índice

#### Scenario: El export refleja las secciones por tag

- **GIVEN** un archivo de edición con tags asignados a algunos grupos
- **WHEN** se genera el HTML exportado con `view` sin `--serve`
- **THEN** las tarjetas aparecen agrupadas en secciones por tag
- **AND** no aparece ningún control de arrastre ni de asignación de tag

## ADDED Requirements

### Requirement: Secciones por tag en el visualizador

El visualizador DEBE (MUST) presentar las tarjetas en secciones, una por cada tag asignado a algún grupo, más una sección para los grupos sin tag. Las secciones DEBEN (MUST) ordenarse de forma ascendente por la fecha más temprana de su primera tarjeta, y la sección de grupos sin tag DEBE (MUST) ir al final. Un tag del catálogo sin ningún grupo asignado NO DEBE (MUST NOT) producir una sección. Cada sección DEBE (MUST) mostrar su nombre y la cantidad de grupos que contiene.

Cuando no haya ningún tag asignado, el visualizador DEBE (MUST) presentar las tarjetas como hasta ahora, en una única lista ordenada por fecha.

#### Scenario: Una sección por tag

- **GIVEN** un archivo de edición que asigna el tag "Viaje" a dos grupos y el tag "Familia" a uno
- **WHEN** se genera el visualizador
- **THEN** aparecen una sección "Viaje" con las dos tarjetas y una sección "Familia" con la otra
- **AND** cada sección muestra la cantidad de grupos que contiene

#### Scenario: Los grupos sin tag van en su propia sección

- **GIVEN** un archivo de edición que asigna un tag a un solo grupo y deja los demás sin tag
- **WHEN** se genera el visualizador
- **THEN** los grupos sin tag aparecen en una sección propia
- **AND** esa sección aparece al final, después de las secciones con tag

#### Scenario: Orden de las secciones

- **GIVEN** un archivo de edición que asigna "Familia" a un grupo de 2020 y "Viaje" a uno de 2019
- **WHEN** se genera el visualizador
- **THEN** la sección "Viaje" aparece antes que la sección "Familia"

#### Scenario: Un tag del catálogo sin grupos asignados

- **GIVEN** un catálogo con un tag al que no se le asignó ningún grupo
- **WHEN** se genera el visualizador
- **THEN** ese tag no produce ninguna sección

#### Scenario: Sin tags asignados

- **GIVEN** un archivo de edición sin tags asignados
- **WHEN** se genera el visualizador
- **THEN** las tarjetas aparecen en una única lista ordenada por fecha

### Requirement: Arrastre de tarjetas para asignar y quitar tags

En el modo servidor, el visualizador DEBE (MUST) permitir asignar el tag de un grupo arrastrando su tarjeta. Arrastrar una tarjeta sobre una sección DEBE (MUST) asignar a ese grupo el tag de la sección. Arrastrar una tarjeta sobre otra tarjeta DEBE (MUST) asignar a ese grupo el tag que tenga esa tarjeta, o quitárselo si la tarjeta de destino no tiene tag. Arrastrar una tarjeta sobre la sección de grupos sin tag DEBE (MUST) quitarle el tag. Un tag NO DEBE (MUST NOT) guardarse si la operación no llega a completarse, y el visor DEBE (MUST) informar el resultado de la operación.

#### Scenario: Arrastrar una tarjeta sobre una sección

- **GIVEN** un servidor en ejecución y una tarjeta sin tag
- **WHEN** el usuario la arrastra sobre la sección "Familia"
- **THEN** el grupo queda con el tag "Familia"
- **AND** el archivo de edición guarda la asignación

#### Scenario: Arrastrar una tarjeta sobre otra tarjeta

- **GIVEN** un servidor en ejecución y una tarjeta con el tag "Viaje"
- **WHEN** el usuario arrastra sobre ella una tarjeta sin tag
- **THEN** el grupo de la tarjeta arrastrada queda con el tag "Viaje"

#### Scenario: Arrastrar sobre una tarjeta sin tag

- **GIVEN** un servidor en ejecución y una tarjeta con el tag "Viaje" y otra sin tag
- **WHEN** el usuario arrastra la primera sobre la segunda
- **THEN** a la segunda se le quita el tag

#### Scenario: La operación se rechaza

- **GIVEN** un servidor en ejecución
- **WHEN** el servidor rechaza la asignación de un tag
- **THEN** el visor informa el motivo
- **AND** la tarjeta conserva el tag que tenía antes de arrastrarla

### Requirement: Edición y borrado de tags por el servidor

El servidor DEBE (MUST) aceptar la asignación y el borrado de un tag de un grupo aplicando las mismas garantías que las ediciones de etiqueta: token aleatorio válido, encabezado de host de loopback y tipo de contenido JSON. El servidor DEBE (MUST) validar la asignación contra los grupos vigentes antes de escribirla, y DEBE (MUST) rechazar con un motivo el tag vacío, la referencia que no resuelve y la referencia ambigua. Cada operación aceptada DEBE (MUST) reescribir únicamente el archivo de edición.

#### Scenario: Asignación de tag válida

- **GIVEN** un servidor en ejecución y una página abierta con el token válido
- **WHEN** el usuario asigna un tag no vacío a un grupo existente
- **THEN** el servidor persiste la asignación y confirma la operación

#### Scenario: Petición de tag sin el token válido

- **GIVEN** un servidor en ejecución
- **WHEN** llega una petición de tag sin el token o con un token incorrecto
- **THEN** el servidor rechaza la petición
- **AND** no escribe ningún archivo

#### Scenario: Asignación de tag con etiqueta vacía

- **GIVEN** un servidor en ejecución y una página abierta con el token válido
- **WHEN** el usuario envía un tag vacío o solo con espacios
- **THEN** el servidor rechaza la operación e informa que el tag no puede estar vacío
- **AND** el archivo de edición queda sin cambios
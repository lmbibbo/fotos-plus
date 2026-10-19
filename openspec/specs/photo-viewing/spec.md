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

### Requirement: Miniaturas con orientación correcta

Cada tarjeta DEBE (MUST) mostrar cinco miniaturas extraídas de las fotos de ese grupo. DEBE (MUST) generar las miniaturas aplicando la transformación de orientación EXIF antes de incluirlas, de modo que la miniatura tenga la proporción con la que se ve la foto. NO DEBE requerir que el visor interprete la marca de orientación.

Cada tarjeta DEBE (MUST) incluir también los videos de ese grupo entre sus cinco miniaturas. La miniatura de un video DEBE (MUST) ser un fotograma del video en formato JPEG cuando la máquina disponga de un decodificador, y DEBE (MUST) ser una ficha genérica con su duración cuando no disponga de uno. La ficha genérica DEBE identificar al video como tal para que no se confunda con una foto.

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

#### Scenario: Tarjeta con videos y decodificador disponible

- **GIVEN** un grupo con videos y una máquina con decodificador disponible
- **WHEN** se genera el visualizador
- **THEN** cada video aparece con un fotograma en JPEG entre las miniaturas de su tarjeta

#### Scenario: Tarjeta con videos sin decodificador disponible

- **GIVEN** un grupo con videos y una máquina sin decodificador disponible
- **WHEN** se genera el visualizador
- **THEN** cada video aparece con una ficha genérica que muestra su duración
- **AND** la ficha se distingue de la miniatura de una foto

### Requirement: Visualizador sin sugerencias disponibles

Si el archivo de sugerencias contiguo al índice no existe, el visualizador DEBE (MUST) generar el mismo archivo HTML con todas las fotos del índice en una grilla plana, sin agrupar. El comando NO DEBE fallar por la ausencia del archivo de sugerencias.

#### Scenario: Índice sin archivo de sugerencias

- **GIVEN** un índice de fotos sin archivo de sugerencias contiguo
- **WHEN** se ejecuta el subcomando `view`
- **THEN** se genera el mismo tipo de archivo HTML
- **AND** el contenido muestra todas las fotos en una grilla sin agrupar

### Requirement: Título de la tarjeta con etiqueta propia

El título de cada tarjeta DEBE (MUST) ser la etiqueta del usuario cuando el grupo tiene una etiqueta vigente y, cuando no la tiene, DEBE (MUST) ser el título derivado de la sugerencia. Aplicar una etiqueta NO DEBE (MUST NOT) alterar el resto de los datos que la tarjeta muestra: la cantidad de fotos, el rango de fechas y el país, cuando el grupo declare uno, DEBEN (MUST) seguir mostrándose igual que sin etiqueta.

#### Scenario: Grupo con etiqueta

- **GIVEN** un viaje sugerido con una etiqueta guardada
- **WHEN** se genera el visualizador
- **THEN** la tarjeta se titula con la etiqueta del usuario
- **AND** la tarjeta sigue mostrando su cantidad de fotos, su rango de fechas y su país

#### Scenario: Grupo sin etiqueta

- **GIVEN** un viaje sugerido sin etiqueta guardada
- **WHEN** se genera el visualizador
- **THEN** la tarjeta se titula con el país, o con el texto genérico cuando la sugerencia no declara país

#### Scenario: Etiqueta sobre un período

- **GIVEN** un período sugerido con una etiqueta guardada
- **WHEN** se genera el visualizador
- **THEN** la tarjeta se titula con la etiqueta del usuario
- **AND** la tarjeta NO DEBE (MUST NOT) mostrar país, porque los períodos no declaran ubicación

### Requirement: Modo servidor local del comando view

El subcomando `view` DEBE (MUST) admitir un flag `--serve` que sirva el visualizador desde un servidor local en lugar de limitarse a escribir el archivo. El servidor DEBE (MUST) escuchar únicamente en la dirección de loopback y NO DEBE (MUST NOT) aceptar conexiones desde otras interfaces de red. El modo servidor DEBE (MUST) generar igualmente el archivo HTML estático junto al índice antes de escuchar, de modo que el export no deje de existir. Si el puerto pedido está ocupado, el comando DEBE (MUST) informar el motivo y terminar con un código de salida distinto de cero. Al recibir una interrupción, el servidor DEBE (MUST) liberar el puerto y terminar de forma ordenada.

#### Scenario: Servidor disponible solo en loopback

- **GIVEN** el subcomando `view` ejecutado con `--serve`
- **WHEN** el servidor queda escuchando
- **THEN** responde en la dirección de loopback del puerto indicado
- **AND** no está accesible desde una dirección de red de la máquina

#### Scenario: El export estático se sigue generando en modo servidor

- **GIVEN** el subcomando `view` ejecutado con `--serve`
- **WHEN** el servidor termina de arrancar
- **THEN** existe un archivo HTML estático junto al índice
- **AND** ese archivo muestra su contenido sin necesitar el servidor

#### Scenario: Puerto ocupado

- **GIVEN** un puerto que ya está en uso
- **WHEN** se ejecuta `view --serve` sobre ese puerto
- **THEN** el comando informa que el puerto está ocupado por la salida de error
- **AND** termina con un código de salida distinto de cero

#### Scenario: Interrupción del servidor

- **GIVEN** un servidor de revisión en ejecución
- **WHEN** el usuario lo interrumpe
- **THEN** el proceso termina de forma ordenada y el puerto queda libre

### Requirement: Aceptación segura de ediciones por el servidor

El servidor DEBE (MUST) aceptar ediciones de etiquetas por un endpoint que exija un token aleatorio generado al arrancar y presente en la página servida. El token NO DEBE (MUST NOT) viajar en la URL, para que no quede en el historial del navegador ni en el Referer; se valida contra el cuerpo de la petición y contra un encabezado propio que obliga al navegador a hacer una verificación previa. El servidor DEBE (MUST) rechazar cualquier petición cuyo encabezado de host no sea una dirección de loopback, y DEBE (MUST) exigir que las ediciones se envíen declarando tipo de contenido JSON, de modo que el navegador precludeda una verificación previa. El servidor NO DEBE (MUST NOT) enviar cabeceras que permitan el acceso desde un origen distinto. Cada edición recibida DEBE (MUST) validarse contra los grupos vigentes antes de escribirse: una referencia que no resuelva o que sea ambigua DEBE (MUST) rechazarse con un motivo, y una etiqueta vacía o solo con espacios DEBE (MUST) rechazarse con un motivo.

#### Scenario: Edición válida

- **GIVEN** un servidor en ejecución y una página abierta con el token válido
- **WHEN** el usuario guarda una etiqueta no vacía para un grupo existente
- **THEN** el servidor la persiste y confirma la operación

#### Scenario: Petición sin el token válido

- **GIVEN** un servidor en ejecución
- **WHEN** llega una petición de edición sin el token o con un token incorrecto
- **THEN** el servidor rechaza la petición
- **AND** no escribe ningún archivo

#### Scenario: Petición desde un host que no es loopback

- **GIVEN** un servidor en ejecución
- **WHEN** llega una petición cuyo encabezado de host no corresponde a una dirección de loopback
- **THEN** el servidor rechaza la petición

#### Scenario: Edición con etiqueta vacía

- **GIVEN** un servidor en ejecución y una página abierta con el token válido
- **WHEN** el usuario envía una etiqueta vacía o solo con espacios
- **THEN** el servidor rechaza la edición e informa que la etiqueta no puede estar vacía
- **AND** el archivo de edición queda sin cambios

#### Scenario: Edición con referencia que no resuelve

- **GIVEN** un servidor en ejecución y una página abierta con el token válido
- **WHEN** el usuario envía una etiqueta cuya referencia no corresponde a ningún grupo vigente
- **THEN** el servidor rechaza la edición e informa que la referencia no resuelve
- **AND** el archivo de edición queda sin cambios

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

### Requirement: Browsing the photos of a group in the served viewer

In `--serve` mode the viewer MUST offer, for each group that owns at least one photo, a way to open
a grid page showing every photo and video of that group, each with a thumb at the scale the group
cards use. Selecting an element of the grid MUST open the full-screen browser at that item. The
browser SHALL advance to the previous and next photo, SHALL be operable from the keyboard for both
directions, and SHALL show which photo of the group is currently displayed and how many the group
holds. When the displayed photo carries a capture date, the browser SHALL also show that date in
the `YYYY-MM-DD` form next to that position. When the displayed photo carries no capture date, the
browser SHALL show the position alone, without a placeholder standing in for the date. Reaching the
first or the last photo SHALL leave the viewer on that photo rather than moving past the ends of
the group.

#### Scenario: Opening the browser from a group

- **GIVEN** a running server and a group card that owns photos
- **WHEN** the user follows that group's "Ver fotos" action
- **THEN** a grid page opens showing a thumb for every photo and video of the group
- **AND** it shows the position within the group and the group's total photo count

#### Scenario: Opening the browser on the selected element

- **GIVEN** the grid page of a group open in the browser
- **WHEN** the user selects one of its elements
- **THEN** the full-screen browser opens at that item rather than at the first one
- **AND** it shows the position within the group and the group's total photo count

#### Scenario: Grid thumbs at the card-thumbnail scale

- **GIVEN** a running server and a group that owns photos
- **WHEN** the grid page of that group opens
- **THEN** every cell shows a thumb at the same scale as the thumbnails on the group cards
- **AND** a group of many photos reads as a dense contact sheet rather than a page of large images

#### Scenario: A displayed photo that carries a capture date

- **GIVEN** the browser open on a photo whose capture date is known
- **WHEN** the browser displays that photo
- **THEN** it shows that capture date next to the position within the group
- **AND** the date is rendered in the `YYYY-MM-DD` form

#### Scenario: A displayed photo with no capture date

- **GIVEN** the browser open on a photo that carries no capture date
- **WHEN** the browser displays that photo
- **THEN** it shows the position within the group and the group's total photo count
- **AND** it shows neither a date nor a placeholder where the date would have been

#### Scenario: The shown date follows the displayed photo

- **GIVEN** the browser open on a group whose photos carry different capture dates
- **WHEN** the user moves to the next photo
- **THEN** the shown date is that of the photo now displayed rather than the one left behind

#### Scenario: Moving between photos

- **GIVEN** the browser open on a group of more than one photo
- **WHEN** the user requests the next photo
- **THEN** the browser shows the following photo of that group

#### Scenario: Moving with the keyboard

- **GIVEN** the browser open on a photo
- **WHEN** the user presses the next-photo key
- **THEN** the browser advances one photo without needing a pointer

#### Scenario: The last photo of the group

- **GIVEN** the browser open on the last photo of a group
- **WHEN** the user requests the next photo
- **THEN** the browser still shows that last photo

#### Scenario: A group that owns no photos

- **GIVEN** a group card reporting that it owns no photos
- **WHEN** the viewer offers a way to browse that group
- **THEN** no grid page is opened

#### Scenario: Closing the browser

- **GIVEN** the browser open on a group
- **WHEN** the user closes it
- **THEN** the grid page that opened it is shown again
- **AND** no mark is added or removed by opening and closing the browser

### Requirement: Serving a screen-sized render of a single photo

The served viewer SHALL obtain the displayable version of a photo from an endpoint that returns a
render whose longest edge is capped, so that the displayed image does not scale with the size of the
original file. The render SHALL carry the EXIF orientation already applied, so the viewer does not
interpret the orientation tag. The endpoint SHALL serve only photos that the scanned index contains.

#### Scenario: Requesting the displayable version of a photo

- **GIVEN** a running server and a photo in the index
- **WHEN** the viewer requests that photo's displayable version
- **THEN** it receives an image
- **AND** the longest edge of that image is within the cap

#### Scenario: A large original is not served whole

- **GIVEN** a photo whose original file is large
- **WHEN** the viewer requests that photo's displayable version
- **THEN** the bytes returned are far smaller than the original file

#### Scenario: An orientation-marked photo appears upright

- **GIVEN** a photo stored sideways with an orientation mark
- **WHEN** the viewer requests that photo's displayable version
- **THEN** the returned image already has its final orientation applied

#### Scenario: A photo that is not in the index

- **GIVEN** a running server
- **WHEN** a render is requested for something the index does not contain
- **THEN** the request is refused with a reason
- **AND** no file outside the library root is served

### Requirement: Serving a thumbnail for the grid

The served viewer MUST obtain a grid cell's photo from an endpoint that returns a
thumbnail-scale render — the same size and quality as the thumbnails embedded in the
cards — so that a screenful of cells stays light even when the group holds hundreds of
photos. The endpoint MUST serve only photos that the scanned index contains, and MUST
refuse video references with a reason: grid video cells are shown through their posters
instead.

#### Scenario: Requesting the thumbnail of a photo

- **GIVEN** a running server and a photo in the index
- **WHEN** the grid requests that photo's thumbnail
- **THEN** it receives an image at thumbnail scale rather than the screen render
- **AND** the bytes are far smaller than the render of the same photo

#### Scenario: A thumbnail is produced once and stored

- **GIVEN** a photo with no stored thumbnail
- **WHEN** its thumbnail is requested twice
- **THEN** the second request returns the stored thumbnail instead of reprocessing the original

#### Scenario: A photo that is not in the index

- **GIVEN** a running server
- **WHEN** a thumbnail is requested for something the index does not contain
- **THEN** the request is refused with a reason
- **AND** no file outside the library root is served

#### Scenario: A video reference is refused

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested from the thumbnail endpoint
- **THEN** the endpoint refuses it with a reason
- **AND** the grid shows that video through its poster

### Requirement: The media endpoints require the token and resolve through the index

The render and thumbnail endpoints MUST require the same random token the served page
already carries, and MUST refuse a request whose host header is not a loopback address,
matching the guarantees already required of edits. Both endpoints MUST accept a photo
reference that names a photo in the index and MUST resolve it through the index, so that
a caller-supplied value is never used directly to read or write a filesystem path. A
reference that the index does not contain MUST be refused with a reason.

#### Scenario: Request without the valid token

- **GIVEN** a running server
- **WHEN** a render is requested with no token or an incorrect token
- **THEN** the server refuses the request
- **AND** no image bytes are returned

#### Scenario: Request from a host that is not loopback

- **GIVEN** a running server
- **WHEN** a render is requested with a host header that is not a loopback address
- **THEN** the server refuses the request

#### Scenario: A reference that escapes the library root

- **GIVEN** a running server
- **WHEN** a render is requested with a reference that climbs out of the library root
- **THEN** the server refuses the request
- **AND** no file outside the library root is returned

#### Scenario: A reference that is not a photo in the index

- **GIVEN** a running server
- **WHEN** a render is requested for a reference the index does not contain
- **THEN** the server refuses the request and reports that the reference does not resolve

### Requirement: Renders are produced lazily and cached by content hash

The displayable version of a photo SHALL be produced the first time it is asked for and stored, so
that asking again returns the stored render without reprocessing the original. The stored render
SHALL be identified by the photo's content hash rather than by its name or path. Asking for a photo
whose content hash has no stored render yet SHALL produce and store one. The stored renders SHALL be
disposable: deleting them costs time on the next request and no data.

#### Scenario: The first request is slower than the second

- **GIVEN** a photo with no stored render
- **WHEN** its displayable version is requested twice
- **THEN** the second request returns the stored render instead of reprocessing the original

#### Scenario: A changed photo gets a new render

- **GIVEN** a photo whose content changed, so its content hash is different
- **WHEN** its displayable version is requested
- **THEN** the render stored for the earlier content is not served
- **AND** a render for the new content is produced and stored

#### Scenario: A moved photo keeps its render

- **GIVEN** a photo that has a stored render, at one path
- **WHEN** the photo is moved and its displayable version is requested at the new path
- **THEN** the stored render for that content is served

#### Scenario: Stored renders can be deleted

- **GIVEN** a photo that has a stored render
- **WHEN** the stored renders are deleted and the displayable version is requested again
- **THEN** the render is produced again from the original photo
- **AND** no information about the library is lost

### Requirement: The static export is unaffected by browsing

The exported HTML SHALL keep showing five thumbnails per card and SHALL stay self-contained. The
export SHALL NOT include the group browser, SHALL NOT request renders, and SHALL NOT offer any
control that depends on the server.

#### Scenario: The export keeps its thumbnails

- **GIVEN** a served session in which renders exist
- **WHEN** the exported HTML is opened from disk with no server running
- **THEN** the cards still show five thumbnails each
- **AND** the page needs no network access to show its content

#### Scenario: The export has no browsing control

- **GIVEN** an exported HTML file
- **WHEN** it is opened in a browser
- **THEN** no control that opens a group's photos is offered

### Requirement: Photo bucket sections on the landing page

When at least one photo belongs to a bucket, the landing page MUST present one card for each
bucket that holds at least one photo. Each card MUST show the bucket name, the number of photos it
holds, the earliest and latest capture dates when known, and at most five thumbnails from the
bucket, using the same card presentation as a group card. If the bucket has fewer than five
photos, the card MUST show all of them. The card MUST NOT show a country and MUST NOT offer group
label or tag controls, because a bucket is not a group. A bucket in the catalogue that holds no
photo MUST NOT produce a card. Photos that belong to no bucket MUST NOT appear in any photo card.

The marked card, when present, MUST appear before the bucket cards. The bucket cards MUST appear
after the group cards and group sections, in the order the bucket catalogue lists them. In the
served viewer, each bucket card MUST offer a control that opens the full bucket in the photo grid.
The photos in a bucket MUST be ordered by the same order the photos are browsed in.

#### Scenario: One section per bucket

- **GIVEN** an edition file that places two photos in "Favoritas" and one photo in "Para imprimir"
- **WHEN** the landing page is generated
- **THEN** a "Favoritas" card reporting two photos and a "Para imprimir" card reporting one appear
- **AND** each card shows at most five thumbnails

#### Scenario: A photo may appear in more than one section

- **GIVEN** a photo that belongs to both "Favoritas" and "Para imprimir"
- **WHEN** the landing page is generated
- **THEN** the photo appears in the "Favoritas" card
- **AND** the photo also appears in the "Para imprimir" card

#### Scenario: Photos in no bucket get their own section

- **GIVEN** an edition file that places one photo in "Favoritas" and leaves every other photo in no bucket
- **WHEN** the landing page is generated
- **THEN** the "Favoritas" card appears
- **AND** no card appears for the photos in no bucket

#### Scenario: An empty bucket produces no section

- **GIVEN** a bucket catalogue holding "Favoritas" and "Para imprimir"
- **WHEN** no photo belongs to "Para imprimir" and the landing page is generated
- **THEN** a "Favoritas" card appears
- **AND** no "Para imprimir" card appears

#### Scenario: No buckets means no photo sections

- **GIVEN** an edition file in which no photo belongs to any bucket
- **WHEN** the landing page is generated
- **THEN** no bucket card and no untagged photos card appear

#### Scenario: Bucket sections follow the group sections

- **GIVEN** an edition file that assigns a group tag to one group, marks one photo and places two photos in "Favoritas"
- **WHEN** the landing page is generated
- **THEN** the group sections appear first
- **AND** the "Marcadas" card appears after them
- **AND** the "Favoritas" card appears after the "Marcadas" card

#### Scenario: A bucket with more than five photos shows a bounded preview

- **GIVEN** an edition file that places twelve photos in "Favoritas"
- **WHEN** the landing page is generated
- **THEN** the "Favoritas" card reports twelve photos
- **AND** it shows exactly five thumbnails

#### Scenario: Opening a bucket card shows the full bucket

- **GIVEN** a served viewer and a "Favoritas" bucket holding twelve photos
- **WHEN** the user activates the control that opens the bucket
- **THEN** the photo grid lists all twelve photos
- **AND** it lists them in the order the photos are browsed in

### Requirement: Both axes coexist on one page

The landing page MUST present the group cards and group sections together with the marked and
bucket cards, in a single page, with the group cards and group sections first. A library with no
group tags, no marks and no buckets MUST be presented exactly as it is before this change: one
flat list of group cards ordered by date. Adding buckets or marks MUST NOT change how any group
card is titled, how many photos it reports, or which group it belongs to. A marked or bucketed
photo MUST remain in its group card as well as appearing in the photo cards that contain it.

#### Scenario: The two axes on one page

- **GIVEN** an edition file that assigns the group tag "Familia" to one group and places two photos in "Favoritas"
- **WHEN** the landing page is generated
- **THEN** a "Familia" section holding that group's card and a "Favoritas" card both appear in the same document
- **AND** the "Familia" section appears before the "Favoritas" card

#### Scenario: A library with neither tags nor marks is unchanged

- **GIVEN** an edition file holding no group tags, no marks and no buckets
- **WHEN** the landing page is generated
- **THEN** the cards appear in a single list ordered by date
- **AND** no section heading appears

#### Scenario: Buckets do not alter the group cards

- **GIVEN** a group card reporting a photo count, a date range and a country
- **WHEN** two of its photos are placed in a bucket
- **THEN** the card still reports the same photo count, date range and country
- **AND** the card is still in the same group

#### Scenario: A marked or bucketed photo remains in its group card

- **GIVEN** a photo that belongs to a group, is marked, and is placed in a bucket
- **WHEN** the landing page is generated
- **THEN** the photo still belongs to the same group card
- **AND** it also appears in the "Marcadas" card
- **AND** it also appears in the bucket card

### Requirement: Photos in the viewer open at the photo itself

A photo shown in the photo grid opened from a marked or bucket card MUST open the served browser
at that photo when the user selects it, so that a photo reached from a bucket is immediately
bucketed and markable. A photo with no capture date MUST still be reachable this way, and MUST NOT
be excluded from any photo card or its grid because its date is unknown.

#### Scenario: Selecting a photo opens the browser at it

- **GIVEN** a served viewer and a photo listed in the "Favoritas" bucket card
- **WHEN** the user opens the card's photo grid and selects that photo
- **THEN** the browser opens showing that photo
- **AND** the picker shows the buckets that photo belongs to

#### Scenario: A photo without a capture date is still listed

- **GIVEN** a photo with no capture date that belongs to "Favoritas"
- **WHEN** the landing page is generated
- **THEN** the photo is part of the "Favoritas" card and its full bucket
- **AND** selecting it in the photo grid opens the browser at that photo

### Requirement: Dragging does not assign buckets

Dragging a group card onto a marked or bucket card MUST NOT assign any bucket to any photo, and the
viewer MUST report that photo cards do not accept a dragged card, because a photo may belong to
several buckets at once and a drag cannot express which of them is meant. Photo cards MUST NOT be
draggable and MUST NOT offer a drop target for group cards. This MUST NOT change what dragging a
card onto a group section does.

#### Scenario: A card dropped on a photo section is refused

- **GIVEN** a running server and a group card with no group tag
- **WHEN** the user drags that card onto the "Favoritas" card
- **THEN** the viewer reports that photo cards do not accept a dragged card
- **AND** no bucket assignment is stored

#### Scenario: Photo sections offer no drop target

- **GIVEN** a running server and a landing page with a "Favoritas" card
- **WHEN** the page reports what can be dragged onto
- **THEN** the photo cards are not among the drop targets

#### Scenario: Photo cards are not draggable

- **GIVEN** a served landing page with a "Marcadas" card and a "Favoritas" card
- **WHEN** the user tries to drag either photo card
- **THEN** no drag starts
- **AND** no group tag or bucket assignment changes

#### Scenario: Dragging a card onto a group section is unaffected

- **GIVEN** a served landing page with a group card with no tag and a group section "Familia"
- **WHEN** the user drags the card onto the "Familia" section
- **THEN** the group's tag assignment is stored as before

### Requirement: The exported HTML shows the photo sections read-only

The exported HTML MUST present the marked and bucket cards. It MUST NOT present a flat photo
section or an untagged photos card. It MUST NOT offer any control that opens the served browser,
changes a bucket assignment, or creates a bucket name. The exported document MUST contain no
bucket picker and no drop target, exactly as it contains no tag editor.

#### Scenario: Sections in the export

- **GIVEN** an edition file that marks two photos and places one photo in "Favoritas"
- **WHEN** the exported HTML is generated with `view` and no `--serve`
- **THEN** the "Marcadas" and "Favoritas" cards appear in the export
- **AND** each card shows at most five thumbnails
- **AND** no flat photo section appears

#### Scenario: The export has no bucket controls

- **GIVEN** an exported HTML document that shows a bucket card
- **WHEN** the document is inspected
- **THEN** it offers no control to change a bucket assignment or to write a new bucket name

#### Scenario: The export has no picker

- **GIVEN** an exported HTML document
- **WHEN** the document is inspected
- **THEN** it contains no bucket picker for any photo

#### Scenario: The export has no browsing control

- **GIVEN** an exported HTML document that shows a marked or bucket card
- **WHEN** it is opened in a browser
- **THEN** no control that opens the served browser is offered

### Requirement: Videos in the served browser play automatically on arrival

In `--serve` mode, arriving at a video in the group browser MUST start playback with
native browser controls, using its poster still as the pre-playback frame. Playback MUST
start automatically every time the browser arrives at a video — when it opens on one and
when navigation moves onto one. When the browser refuses to start playback under its own
autoplay policy, the viewer MUST leave the poster still in place with the native controls
available, MUST NOT report an error, and MUST NOT move away from the video. Arrow keys MUST
keep moving between items; seeking within a video happens through its native controls. A
`/video` endpoint MUST serve the original file with single-range partial responses under the
same guarantees as `/render` (random token, loopback host, cross-origin refusal,
index-resolved reference). Media-element URLs (`<video src>`, `poster`) carry the token as a
query parameter, since tags cannot set headers; subresource URLs are never stored in browser
history. The `/render` endpoint keeps serving photos only and MUST refuse video references
with a reason. Video blobs MUST never be embedded in the static export; the export shows
video posters exactly like photo thumbnails.

#### Scenario: Browser opened on a video

- **GIVEN** a group holding a video, served with `view --serve`
- **WHEN** the browser opens on that video
- **THEN** a `<video>` element appears with native controls and the poster still
- **AND** playback starts automatically, without a press on the play control

#### Scenario: Navigation moves onto a video

- **GIVEN** the browser open on a photo of a group that also holds a video
- **WHEN** the user presses the arrow key that moves onto that video
- **THEN** playback of the video starts automatically

#### Scenario: The browser refuses to start playback

- **GIVEN** a group holding a video, served with `view --serve`
- **WHEN** the browser arrives at that video and its autoplay policy refuses playback
- **THEN** the poster still stays visible with the native controls available
- **AND** no error is reported and the browser stays on that video

#### Scenario: Moving off a playing video stops it

- **GIVEN** a video playing in the browser
- **WHEN** the user presses the arrow key that moves onto the next item
- **THEN** playback stops before the next item is shown

#### Scenario: Arrow keys keep navigating on a video

- **GIVEN** the browser opened on a video
- **WHEN** the user presses an arrow key
- **THEN** the browser moves to the previous or next item
- **AND** no seek is performed by the viewer

#### Scenario: Video bytes are served with ranges

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested from the `/video` endpoint without a Range header
- **THEN** the endpoint answers 200 with the full file and `Accept-Ranges: bytes`
- **AND** a request with a single satisfiable byte range answers 206 with that slice
  and a matching `Content-Range`

#### Scenario: Unsatisfiable range is refused

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested with a byte range past the end of the file
- **THEN** the endpoint answers 416

#### Scenario: Video endpoint keeps the render guarantees

- **GIVEN** the `/video` endpoint
- **WHEN** it is requested without the random token, from a non-loopback host, with a
  cross-site fetch mode, or with a reference the index does not contain
- **THEN** it refuses exactly like `/render` does

#### Scenario: Media tag authenticates with the token in the URL

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested from `/video` with the token as a query
  parameter and no header token
- **THEN** the endpoint serves the bytes

#### Scenario: Render endpoint refuses a video

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested from the `/render` endpoint
- **THEN** the endpoint refuses it with a reason instead of serving a render

#### Scenario: Export embeds posters, never video blobs

- **GIVEN** an exported HTML document for a group holding videos
- **WHEN** the document is inspected
- **THEN** video posters appear exactly like photo thumbnails
- **AND** the document embeds no video blob
- **AND** the document contains no `<video>` element

### Requirement: An unavailable library folder is resolved or reported

The viewer and the served endpoints MUST resolve photo files against the library folder the index
declares. When that folder is not available, they MUST resolve them against the folder the paired
suggestions file declares, so an index whose own folder is missing still shows previews. When
neither folder is available, the viewer MUST report that the library folder could not be found and
MUST NOT present the photo sets as empty.

#### Scenario: The folder the index declares is unavailable

- **GIVEN** an index whose declared folder no longer exists and a paired suggestions file whose declared folder does exist
- **WHEN** the landing page is generated
- **THEN** the cards show thumbnails from the folder the suggestions file declares

#### Scenario: Neither declared folder is available

- **GIVEN** an index and a paired suggestions file whose declared folders do not exist
- **WHEN** the landing page is generated
- **THEN** the document reports that the library folder could not be found
- **AND** the missing previews are not explained as photos belonging to another group

### Requirement: Photo-set previews fail without the group explanation

A photo-set card that cannot produce its thumbnails MUST keep reporting the real number of photos in
the set and MUST state that its previews could not be produced. It MUST NOT state that the photos
fall into another group, because that explanation only fits a declared group card. The served grid
MUST show a placeholder for a photo whose thumbnail cannot be served, and selecting that cell MUST
still open the browser, which reports its own failure when the full render cannot be produced.

#### Scenario: A bucket whose previews cannot be produced

- **GIVEN** a bucket whose photo files cannot be read
- **WHEN** the landing page is generated
- **THEN** the bucket card reports the number of photos it holds
- **AND** it states that its previews could not be produced
- **AND** it does not say the photos fall into another group

#### Scenario: A grid cell whose thumbnail cannot be served

- **GIVEN** a served viewer and a bucket whose photo thumbnail cannot be produced
- **WHEN** the user opens the bucket's grid
- **THEN** the cell for that photo shows a placeholder instead of a broken image
- **AND** selecting the cell still opens the browser at that photo

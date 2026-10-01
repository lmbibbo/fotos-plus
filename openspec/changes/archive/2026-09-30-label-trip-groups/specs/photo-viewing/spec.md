# Spec Delta

## ADDED Requirements

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

El archivo HTML exportado por `view` DEBE (MUST) aplicar las etiquetas vigentes al generar las tarjetas. El export NO DEBE (MUST NOT) incluir controles de edición, porque sin servidor no podrían guardarse. El export DEBE (MUST) indicar de forma visible que es de solo lectura, y NO DEBE (MUST NOT) crear el archivo de edición como efecto de generar el visualizador.

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

# Spec Delta

## Purpose

Permite que el usuario ponga su propio nombre a los grupos de viajes y períodos que el escaneo sugiere, y que ese nombre se persista en un archivo separado del que produce el escaneo, de modo que sobreviva a los rescaneos y pueda revertirse sin tocar ningún otro archivo.

## ADDED Requirements

### Requirement: Archivo de edición de etiquetas

El sistema DEBE (MUST) almacenar las etiquetas escritas por el usuario en un archivo de edición contiguo al índice, con el nombre base del índice y el sufijo `-edicion`. El archivo de sugerencias DEBE (MUST) ser escrito únicamente por el escaneo y el archivo de edición DEBE (MUST) ser escrito únicamente por el editor: cada archivo tiene un único escritor. El escaneo NO DEBE (MUST NOT) leer ni borrar el archivo de edición. El sistema DEBE (MUST) escribir el archivo de edición de forma atómica, de modo que una interrupción no deje un archivo parcial.

#### Scenario: Guardar una etiqueta sin afectar otros archivos

- **GIVEN** un índice escaneado con su archivo de sugerencias
- **WHEN** el usuario guarda una etiqueta para un grupo
- **THEN** se crea o actualiza el archivo de edición contiguo al índice
- **AND** el índice y el archivo de sugerencias quedan sin modificar

#### Scenario: Un escaneo posterior conserva las etiquetas

- **GIVEN** un archivo de edición con etiquetas ya guardadas
- **WHEN** se vuelve a ejecutar el escaneo sobre el mismo índice
- **THEN** el archivo de sugerencias se reemplaza por completo
- **AND** el archivo de edición permanece igual, con todas sus entradas

#### Scenario: Escritura interrumpida

- **GIVEN** una escritura del archivo de edición que se interrumpe antes de completarse
- **WHEN** se vuelve a leer el archivo de edición
- **THEN** el archivo contiene una versión completa y legible
- **AND** nunca queda un archivo parcial ni truncado

### Requirement: Identificación del grupo etiquetado

Cada etiqueta DEBE (MUST) referenciar un grupo por la fecha más temprana de ese grupo, que es el mismo dato que el visor ya usa para ordenar las tarjetas. La fecha más temprana DEBE (MUST) ser única entre todos los grupos, y el sistema NO DEBE (MUST NOT) aceptar una referencia que resuelva a más de un grupo. El sistema DEBE (MUST) rechazar una etiqueta cuya referencia no resuelva a ningún grupo vigente, en lugar de guardarla.

#### Scenario: Etiqueta sobre un grupo existente

- **GIVEN** un grupo sugerido cuya fecha más temprana es `2023-07-19T10:32:39`
- **WHEN** el usuario guarda la etiqueta "Viaje a Bariloche" para ese grupo
- **THEN** la etiqueta queda registrada bajo esa fecha
- **AND** al volver a mostrar las tarjetas, ese grupo se identifica con ese texto

#### Scenario: Referencia que ya no resuelve

- **GIVEN** una etiqueta guardada bajo una fecha que el escaneo ya no produce
- **WHEN** se intenta guardar o conservar esa etiqueta
- **THEN** el sistema informa que la etiqueta no corresponde a ningún grupo actual
- **AND** no la escribe en el archivo de edición

#### Scenario: Referencia ambigua

- **GIVEN** una fecha más temprana que corresponde a más de un grupo
- **WHEN** se intenta guardar una etiqueta para esa fecha
- **THEN** el sistema rechaza la etiqueta e informa que la referencia es ambigua

### Requirement: Invariante de etiqueta no vacía

El sistema NO DEBE (MUST NOT) almacenar una etiqueta vacía ni una compuesta únicamente por espacios. Quitar la etiqueta de un grupo DEBE (MUST) ser una operación explícita que elimina su entrada del archivo de edición, y NO DEBE (MUST NOT) depender de enviar el texto vacío. Un grupo sin etiqueta DEBE (MUST) mostrar el título que se deriva de las sugerencias.

#### Scenario: Intento de guardar una etiqueta vacía

- **GIVEN** un grupo con etiqueta visible en el visor
- **WHEN** el usuario envía el texto vacío o solo espacios para ese grupo
- **THEN** el sistema rechaza la operación e informa que la etiqueta no puede estar vacía
- **AND** la etiqueta anterior del grupo permanece sin cambios

#### Scenario: Quitar la etiqueta de un grupo

- **GIVEN** un grupo con una etiqueta guardada
- **WHEN** el usuario elige quitarle la etiqueta
- **THEN** la entrada correspondiente desaparece del archivo de edición
- **AND** el grupo vuelve a mostrar el título derivado de las sugerencias

### Requirement: Detección de deriva respecto del escaneo

El archivo de edición DEBE (MUST) registrar el instante del escaneo con el que se construyó. Cuando el archivo de sugerencias vigente sea posterior a ese instante, el visor DEBE (MUST) informar cuántas etiquetas siguen resolviendo a un grupo actual y cuántas ya no. El sistema NO DEBE (MUST NOT) descartar ni reescribir etiquetas por el hecho de que el escaneo haya cambiado.

#### Scenario: Sin cambios en el escaneo

- **GIVEN** un archivo de edición cuyo instante de escaneo coincide con el del archivo de sugerencias vigente
- **WHEN** se genera el visualizador
- **THEN** todas las etiquetas se aplican sin avisos

#### Scenario: Rescaneo posterior a las etiquetas

- **GIVEN** un archivo de edición escrito contra un escaneo anterior
- **WHEN** se generó un escaneo nuevo y se abre el visualizador
- **THEN** el visor informa cuántas etiquetas siguen resolviendo y cuántas no
- **AND** las etiquetas permanecen guardadas para que el usuario decida qué hacer

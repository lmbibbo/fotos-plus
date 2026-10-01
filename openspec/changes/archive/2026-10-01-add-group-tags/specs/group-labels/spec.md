# Spec Delta

## MODIFIED Requirements

### Requirement: Archivo de edición de etiquetas

El sistema DEBE (MUST) almacenar las etiquetas escritas por el usuario en un archivo de edición contiguo al índice, con el nombre base del índice y el sufijo `-edicion`. El archivo de sugerencias DEBE (MUST) ser escrito únicamente por el escaneo y el archivo de edición DEBE (MUST) ser escrito únicamente por el editor: cada archivo tiene un único escritor. El escaneo NO DEBE (MUST NOT) leer ni borrar el archivo de edición. El sistema DEBE (MUST) escribir el archivo de edición de forma atómica, de modo que una interrupción no deje un archivo parcial. El archivo DEBE (MUST) declarar su versión y DEBE (MUST) admitir los archivos de versión anterior, migrándolos al leerlos sin perder las etiquetas ya guardadas.

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

#### Scenario: Archivo de edición de versión anterior

- **GIVEN** un archivo de edición escrito con la versión anterior del formato, con etiquetas ya guardadas
- **WHEN** se lee el archivo de edición
- **THEN** se migra a la versión vigente y todas las etiquetas se conservan
- **AND** al guardar cualquier edición posterior, el archivo queda escrito en la versión vigente

## ADDED Requirements

### Requirement: Catálogo de tags definidos por el usuario

El archivo de edición DEBE (MUST) almacenar un catálogo ordenado de tags definidos por el usuario, y el visor DEBE (MUST) ofrecer elegir un tag del catálogo o escribir uno nuevo. Un tag nuevo se agrega al catálogo al guardarlo. Dos entradas del catálogo NO DEBE (MUST NOT) diferir solo en mayúsculas o en espacios alrededor.

#### Scenario: Elegir un tag del catálogo

- **GIVEN** un catálogo con los tags "Viaje" y "Familia"
- **WHEN** el usuario asigna "Familia" a un grupo
- **THEN** el grupo queda con el tag "Familia"
- **AND** el catálogo no cambia

#### Scenario: Crear un tag nuevo

- **GIVEN** un catálogo con el tag "Viaje"
- **WHEN** el usuario escribe "Trabajo" como tag para un grupo y lo guarda
- **THEN** el grupo queda con el tag "Trabajo"
- **AND** "Trabajo" queda disponible en el catálogo para los demás grupos

#### Scenario: Un tag nuevo es indistinguible de uno existente

- **GIVEN** un catálogo con el tag "Familia"
- **WHEN** el usuario intenta crear el tag " familia "
- **THEN** el sistema lo reconoce como el mismo tag que ya existe
- **AND** el catálogo no queda con dos entradas que solo difieren en mayúsculas o espacios

### Requirement: Un solo tag por grupo

Cada grupo DEBE (MUST) admitir como máximo un tag, y ese tag DEBE (MUST) convivir con el título: el título sigue nombrando el grupo y el tag lo clasifica. Asignar un tag a un grupo que ya tiene uno DEBE (MUST) reemplazar el anterior. Quitar el tag DEBE (MUST) ser una operación explícita que elimina la asignación, y NO DEBE (MUST NOT) depender de enviar un tag vacío.

#### Scenario: Grupo con título y tag a la vez

- **GIVEN** un grupo con la etiqueta "Navidad" guardada
- **WHEN** el usuario le asigna el tag "Familia"
- **THEN** el grupo muestra el título "Navidad" y el tag "Familia"
- **AND** el tag no altera el rango de fechas, la cantidad de fotos ni el país

#### Scenario: Reasignar el tag de un grupo

- **GIVEN** un grupo con el tag "Familia"
- **WHEN** el usuario le asigna el tag "Viaje"
- **THEN** el grupo queda con el tag "Viaje" y ya no con "Familia"
- **AND** el catálogo conserva ambos tags

#### Scenario: Quitar el tag de un grupo

- **GIVEN** un grupo con el tag "Familia" asignado
- **WHEN** el usuario elige quitarle el tag
- **THEN** la asignación de ese grupo desaparece del archivo de edición
- **AND** el tag sigue disponible en el catálogo para otros grupos

### Requirement: Tag no vacío y asignación vigente

El sistema NO DEBE (MUST NOT) almacenar un tag vacío ni uno compuesto únicamente por espacios. Una asignación DEBE (MUST) referenciar un grupo por la fecha más temprana del grupo, igual que la etiqueta, y el sistema DEBE (MUST) rechazarla si la referencia no resuelve a ningún grupo vigente o si es ambigua. Una asignación que quedó sin resolver por un rescaneo NO DEBE (MUST NOT) descartarse ni reescribirse: DEBE (MUST) seguir guardada para que el usuario decida.

#### Scenario: Tag vacío

- **GIVEN** un grupo con el tag "Viaje"
- **WHEN** el usuario intenta guardar un tag vacío o solo con espacios
- **THEN** el sistema rechaza la operación e informa que el tag no puede estar vacío
- **AND** el tag anterior del grupo permanece sin cambios

#### Scenario: Tag sobre una referencia que no resuelve

- **GIVEN** un archivo de edición con un tag guardado bajo una fecha que el escaneo ya no produce
- **WHEN** el usuario intenta asignar un tag a esa fecha
- **THEN** el sistema rechaza la asignación e informa que la referencia no corresponde a ningún grupo actual
- **AND** no escribe nada en el archivo de edición

#### Scenario: Tag que quedó sin resolver tras un rescaneo

- **GIVEN** un archivo de edición con un tag guardado bajo una fecha que el escaneo ya no produce
- **WHEN** se genera el visualizador
- **THEN** el visor informa cuántas asignaciones siguen resolviendo a un grupo actual y cuántas no
- **AND** la asignación permanece guardada
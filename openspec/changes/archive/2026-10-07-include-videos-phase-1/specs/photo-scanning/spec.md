# Spec Delta

## MODIFIED Requirements

### Requirement: Identificación de los archivos que son fotos

El sistema DEBE (MUST) considerar foto a los archivos de formatos de imagen admitidos
(por ejemplo JPEG, PNG, HEIC, WebP, TIFF, RAW) y DEBE considerar video a los archivos
de contenedores admitidos (`.mp4`, `.mov`, `.3gp`), y DEBE ignorar los archivos de otros
formatos, sin registrarlos en el inventario. La lista de formatos admitidos DEBE ser
consultable por el usuario.

#### Scenario: Archivos que no son fotos

- **GIVEN** una carpeta que contiene un PDF y un archivo de texto, además de
  fotos y videos
- **WHEN** se escanea esa carpeta
- **THEN** el inventario incluye solamente las fotos y los videos
- **AND** ningún archivo de otro formato aparece en el inventario

#### Scenario: Video con contenedor admitido

- **GIVEN** una carpeta que contiene un archivo `.mp4`, uno `.mov` y uno `.3gp`
- **WHEN** se escanea esa carpeta
- **THEN** los tres archivos quedan registrados en el inventario como videos

#### Scenario: Extensión de foto con contenido no válido

- **GIVEN** una carpeta que contiene un archivo con extensión de foto cuyo contenido no
  es una imagen legible
- **WHEN** se escanea esa carpeta
- **THEN** el archivo no se registra como foto
- **AND** el escaneo informa el archivo problemático y continúa con el resto

#### Scenario: Extensión de video con contenido no válido

- **GIVEN** una carpeta que contiene un archivo con extensión de video cuyo contenedor
  no se puede leer
- **WHEN** se escanea esa carpeta
- **THEN** el archivo no se registra como video
- **AND** el escaneo informa el archivo problemático y continúa con el resto

### Requirement: Datos básicos de cada foto

El sistema DEBE (MUST) registrar por cada foto su ruta, su nombre de archivo, su
extensión, su tamaño en bytes y un hash calculado sobre su contenido, y DEBE registrar
además su latitud y su longitud cuando los metadatos las provean, dejando esos campos
vacíos cuando la foto no tenga una posición válida. Cada entrada DEBE declarar su clase
de medio (`photo` o `video`), y cada video DEBE registrar además su duración en segundos
cuando el contenedor la declare.

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

#### Scenario: Registro de un video

- **GIVEN** un archivo de video con contenedor admitido dentro de la carpeta escaneada
- **WHEN** se completa su procesamiento
- **THEN** el inventario contiene su ruta, nombre, extensión, tamaño en bytes y hash
  de su contenido
- **AND** el inventario declara su clase de medio como `video` y su duración en
  segundos cuando el contenedor la declara

### Requirement: Fecha de captura desde los metadatos

El sistema DEBE (MUST) obtener de los metadatos EXIF la fecha en que se tomó cada foto
cuando ese dato esté disponible, y DEBE obtener de los metadatos del contenedor la fecha
en que se grabó cada video cuando ese dato esté disponible, en zona horaria del
dispositivo o sin ella de forma explícita en el inventario. Cuando la foto o el video no
tenga fecha de captura, el inventario DEBE dejar el campo vacío en lugar de inventar un
valor. La fecha de captura DEBE conservarse sin cambios aunque la foto o el video no
tenga posición, porque los períodos sin ubicación se delimitan por fecha.

#### Scenario: Foto con fecha EXIF

- **GIVEN** una foto con fecha de captura en sus metadatos EXIF
- **WHEN** se escanea la carpeta que la contiene
- **THEN** el inventario registra la fecha de captura de esa foto

#### Scenario: Video con fecha en el contenedor

- **GIVEN** un video con fecha de grabación en los metadatos de su contenedor
- **WHEN** se escanea la carpeta que la contiene
- **THEN** el inventario registra la fecha de captura de ese video

#### Scenario: Foto sin fecha EXIF

- **GIVEN** una foto cuyos metadatos no incluyen fecha de captura, por ejemplo una
  captura de pantalla
- **WHEN** se escanea la carpeta que la contiene
- **THEN** el inventario registra esa foto con el campo de fecha de captura vacío

#### Scenario: Video sin fecha en el contenedor

- **GIVEN** un video cuyos metadatos no incluyen fecha de grabación
- **WHEN** se escanea la carpeta que la contiene
- **THEN** el inventario registra ese video con el campo de fecha de captura vacío

#### Scenario: Foto sin posición pero con fecha

- **GIVEN** una foto que tiene fecha de captura y no tiene posición válida
- **WHEN** se escanea la carpeta que la contiene
- **THEN** el inventario conserva su fecha de captura
- **AND** la foto queda registrada sin latitud ni longitud

# fotos-plus
Organizador de fotos

## Objetivo

Explorar un directorio o carpeta con fotos tomadas con un celular o una cámara digital
y organizarlas automáticamente según distintos criterios:

- **Fechas**: agrupar por año, mes o día, o por el momento en que se tomó la foto.
- **Lugares**: geolocalizar las fotos y agruparlas por ubicación.
- **Gente**: detectar a las personas que aparecen y agrupar las fotos de cada una.

El objetivo es dejar de acumular archivos sueltos sin criterio y poder encontrar las
fotos por su contenido, no solo por el nombre del archivo.

## Visualizador

Incluye un visualizador para recorrer las fotos ya organizadas, mostrando un orden
estable y coherente con el criterio por el que se agruparon.

## Estado

Proyecto en fase inicial: el escaneo de carpetas ya está implementado; la organización
por fechas, lugares y gente, y el visualizador, siguen pendientes.

## Uso

```bash
pip install -e ".[dev]"

# Escanear una carpeta y escribir el índice
fotos-plus scan "C:\fotos\vacaciones"

# Escanear guardando el índice en una ruta concreta
fotos-plus scan "C:\fotos\vacaciones" --index ./escaneo.index.json
```

Para ver los formatos admitidos: `fotos-plus scan --help`.
Si el directorio de scripts de Python no está en el PATH, el comando también corre como
`python -m fotos_plus scan <carpeta>`.

El escaneo recorre la carpeta y sus subdirectorios, y **no mueve, renombra ni modifica**
ninguna foto.

## Qué se registra por foto

Cada entrada del índice incluye:

| Campo | Contenido |
| --- | --- |
| `relative_path` | Ruta de la foto respecto de la carpeta escaneada |
| `name`, `extension`, `size_bytes` | Nombre, extensión y tamaño del archivo |
| `sha256` | Hash del contenido, base de la detección de duplicados |
| `captured_at` | Fecha de captura en ISO 8601, o `null` si no hay dato |
| `captured_at_source` | De dónde salió la fecha: `exif-datetime-original` o `exif-datetime` |
| `duplicate_of` | Ruta de la foto original, o `null` si no es duplicado |

Un escaneo escribe un solo archivo con `version`, `root`, `scanned_at`, `photos` y
`errors`. Cada intento de escaneo **reemplaza** el índice anterior de esa carpeta, así que
nunca se acumulan índices. La copia original de un grupo de duplicados es la que tiene la
ruta relativa más corta.

## Dónde queda el índice

Por defecto, en el directorio de estado del usuario:

- Windows: `%LOCALAPPDATA%\fotos-plus\indexes\<hash-de-la-carpeta>.json`
- Linux y macOS: `~/.local/state/fotos-plus/indexes/<hash-de-la-carpeta>.json`

Con `--index` se elige la ruta a mano. La carpeta de fotos no se modifica en ningún caso.

## Códigos de salida

| Código | Significado |
| --- | --- |
| `0` | Escaneo terminado (puede haber archivos con error, que se informan) |
| `1` | Argumentos inválidos |
| `2` | La ruta indicada no existe, no es una carpeta o no se puede leer |

## Formatos admitidos

Leídos por completo (imagen y EXIF): `.bmp`, `.gif`, `.jpeg`, `.jpg`, `.png`, `.tif`,
`.tiff`, `.webp`.

Aceptados por extensión, con metadatos parciales: `.arw`, `.cr2`, `.dng`, `.heic`,
`.heif`, `.nef`.

Cualquier otro archivo se ignora en silencio.

## Limitaciones conocidas

- **HEIC y RAW**: Pillow no los decodifica sin el plugin `pillow-heif`, y los RAW de
  Nikon, Canon y Sony no están soportados. Por eso se aceptan por extensión: la foto
  entra al índice con su hash y su tamaño, pero puede quedar con `captured_at` en `null`
  aunque tenga EXIF.
- **Sin EXIF, la fecha queda vacía**: no se completa con la fecha de modificación del
  archivo, para no confundir "tomada sin fecha" con "modificada después".
- **EXIF no guarda zona horaria**: `captured_at` se guarda tal cual, sin ajuste.
- **Un archivo con extensión de foto pero ilegible** no se registra como foto: aparece en
  `errors` y el escaneo sigue con el resto.
- **Un directorio sin permiso de lectura** no corta el escaneo: se anota en `errors` y se
  continúa con los demás directorios.
- El escaneo no es incremental: cada corrida vuelve a hashear todos los archivos.

## Desarrollo

```bash
pip install -e ".[dev]"
python -m pytest
```

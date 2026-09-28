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

# Guardar todos los índices en una carpeta elegida
fotos-plus scan "C:\fotos\vacaciones" --index-dir "D:\fotos-plus"

# Escanear guardando el índice en un archivo concreto
fotos-plus scan "C:\fotos\vacaciones" --index ./escaneo.index.json
```

Para ver los formatos admitidos: `fotos-plus scan --help`.

El escaneo recorre la carpeta y sus subdirectorios, y **no mueve, renombra ni modifica**
ninguna foto.

### Lanzador para Windows

En la raíz del proyecto hay `fotos-plus.bat`, pensado para no depender de que el
comando `fotos-plus` esté instalado ni de que el directorio de scripts de Python esté
en el PATH:

```bat
REM asume scan: equivale a "fotos-plus scan"
fotos-plus.bat "C:\fotos\vacaciones"

REM con el subcomando explícito
fotos-plus.bat scan "C:\fotos\vacaciones"

REM otra carpeta para el índice
fotos-plus.bat scan "C:\fotos\vacaciones" --index-dir "D:\fotos-plus"

REM un archivo de índice puntual
fotos-plus.bat scan "C:\fotos\vacaciones" --index indice.json

REM la ayuda general
fotos-plus.bat
```

Si el primer argumento no es un subcomando ni `-h`/`--help`, el lanzador antepone `scan`
automáticamente. Usa `python` si está disponible y, si no, `py -3`. Devuelve el mismo
código de salida que el comando, así que se puede usar desde scripts.

**El lanzador guarda el índice en la carpeta desde la que lo ejecutás**, no en el
directorio de estado: el nombre del archivo es el hash de la ruta escaneada, así que
escanear dos carpetas distintas desde el mismo lugar no se pisa. Si pasás `--index` o
`--index-dir`, se respeta esa indicación y no se usa la carpeta de invocación.

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

El nombre del archivo es siempre el hash de la ruta escaneada, así que dos carpetas
distintas nunca comparten índice. Lo que cambia es la carpeta.

Con el comando `fotos-plus`, por defecto va al directorio de estado del usuario:

- Windows: `%LOCALAPPDATA%\fotos-plus\indexes\<hash-de-la-carpeta>.json`
- Linux y macOS: `~/.local/state/fotos-plus/indexes/<hash-de-la-carpeta>.json`

> En Windows, si usás la versión de Python de la Microsoft Store, ese directorio queda
> dentro de la carpeta de la aplicación
> (`%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python…\LocalCache\Local\…`) y no
> se ve en el explorador. Por eso el lanzador `.bat` usa otro destino por defecto.

Con `--index-dir <carpeta>` se elige dónde se guardan los índices: todos van a esa
carpeta, un archivo por carpeta de fotos escaneada. La carpeta se crea si no existe.
Sirve, por ejemplo, para tener los índices en otro disco o en una carpeta sincronizada.

Con `--index <archivo>` se escribe el índice en ese archivo puntual. Si se pasan los dos,
**gana `--index`** y no se crea nada en `--index-dir`.

`fotos-plus.bat` usa por defecto la carpeta desde la que se lo ejecuta, en lugar del
directorio de estado. La ruta exacta siempre la imprime el resumen, en la línea
`Indice:`.

La carpeta de fotos no se modifica en ningún caso.

## Progreso del escaneo

En una terminal, mientras se escanea, se muestra una sola línea que se va
sobrescribiendo:

```text
Escaneando... 1200/4927 (24%) - 18.3 fotos/s - faltan 3m 22s
```

Al terminar queda la línea completa al 100% y después el resumen habitual. `faltan` es
una estimación de lo que queda, y se muestra como `?` mientras todavía no hay datos
suficientes. Antes de tener el total, el porcentaje y la velocidad se muestran como `--`.

El progreso **solo** se escribe si la salida es un terminal interactivo. Si se redirige
a un archivo o a otro proceso:

```bash
fotos-plus scan "C:\fotos\vacaciones" > escaneo.txt
```

el archivo solo tendrá el resumen, sin caracteres de control. Se puede desactivar en
cualquier momento, incluso en una terminal, con la variable de entorno
`FOTOS_PLUS_NO_PROGRESS=1`.

Una carpeta sin fotos no muestra ninguna línea de progreso.

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

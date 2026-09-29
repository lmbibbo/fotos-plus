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

Proyecto en fase inicial: el escaneo de carpetas y las sugerencias de viajes y períodos ya
están implementados; la organización definitiva, la auditoría manual y el visualizador,
siguen pendientes.

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
ninguna foto. El resumen informa los dos archivos escritos:

```text
Carpeta escaneada: C:\fotos\vacaciones
Fotos encontradas: 4805
Duplicados: 0
Archivos con error: 0
Indice: C:\...\5d863d53b7cdd449.json
Sugerencias de viaje: 45
Periodos sugeridos sin ubicacion: 15
Fotos por auditar: 919
Fotos ubicables por referencia: 155
Fotos sin fecha: 0
Sugerencias: C:\...\5d863d53b7cdd449-sugerencias.json
```

Si el cálculo de sugerencias falla, el inventario se escribe igual y el comando avisa por
stderr que el archivo de sugerencias no se generó, sin abortar el escaneo.

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
| `latitude`, `longitude` | Coordenadas decimales, o `null` si la foto no tiene posición válida |
| `duplicate_of` | Ruta de la foto original, o `null` si no es duplicado |

Una foto se considera con posición válida solo cuando **ambas** coordenadas están
presentes y no son `(0, 0)`. Se descartan los tres casos por separado: el bloque de GPS
ausente, el bloque de GPS presente pero vacío, y la coordenada de origen. La regla vive
en un solo lugar, así que el índice y las sugerencias no pueden discrepar.

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

## Sugerencias de viajes y períodos

Junto al índice, cada escaneo escribe un segundo archivo:

```text
<hash-de-la-carpeta>.json              índice de inventario
<hash-de-la-carpeta>-sugerencias.json  sugerencias de viajes y períodos
```

Los dos archivos van siempre juntos, en la misma carpeta: si usás `--index-dir`, ahí; si
usás `--index`, junto al archivo indicado.

**El archivo contiene sugerencias, no viajes ni períodos confirmados.** Por eso la
palabra "sugerencias" está en el nombre, y además el contenido declara `"provisional":
true` y un aviso. Un consumidor tiene que presentar esa información como sugerida.

El archivo trae, por grupo, la cantidad de fotos y la primera y la última fecha. **No
lista las fotos de cada grupo**: se cruza con el inventario por rango de fechas.

Dos ejes van separados a propósito:

| Eje | Valores | Qué significa |
| --- | --- | --- |
| `status` | siempre `sugerido` | Es una aproximación, no un dato confirmado |
| `location_state` | `known` / `unknown` | Si la ubicación se conoce o no |

Una sugerencia de viaje puede tener la ubicación **conocida** y seguir siendo una
**sugerencia**. Son cosas distintas: la primera viene de las coordenadas, la segunda
depende de que el agrupado sea automático.

Cómo se agrupan:

- **Sugerencias de viaje**: se ordenan las fotos con posición válida por fecha de captura
  y se mantiene la misma sugerencia mientras la distancia a la foto anterior sea menor a
  **200 km**. Un traslado parte la sugerencia; un traslado largo dentro de un mismo lugar
  también. La fecha ordena, pero nunca parte por sí sola.
- **Períodos sin ubicación**: las fotos sin posición válida se agrupan por día, y dos
  días se unen en el mismo período cuando hay **1 día vacío o menos** entre ellos. Un
  período nunca dice que su ubicación se conoce.
- **Ubicables por referencia**: las fotos sin posición que comparten día con alguna foto
  con posición válida se marcan con un conteo (`reference_locatable_count`) y quedan
  fuera de los períodos: ese día ya está anclado a un lugar, así que no necesitan
  asignación manual. No se les copia la coordenada de la foto con GPS del mismo día,
  porque un día puede tener dos lugares distintos.
- **Fotos sin fecha**: se declaran aparte en `undated_photo_count` y no entran en ningún
  viaje ni período, porque no se pueden ordenar por fecha ni asignar a un día. No se les
  inventa ninguna.

El archivo se **reescribe por completo en cada escaneo** y no admite edición manual: es
derivado y provisional. Cualquier revisión manual tendrá que vivir más adelante en otro
archivo, que el escaneo lea y no sobrescriba.

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
  archivo, para no confundir "tomada sin fecha" con "modificada después". Una foto sin
  fecha tampoco entra en las sugerencias de viajes ni en los períodos; se cuenta aparte
  en `undated_photo_count`.
- **Las sugerencias no son definitivas**: el archivo se reescribe en cada escaneo y no
  guarda ninguna revisión manual. Los viajes y períodos definitivos, con su lugar
  confirmado, todavía no existen.
- **El umbral de 200 km no se puede ajustar sin reescanear**: está fijo en esta versión.
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

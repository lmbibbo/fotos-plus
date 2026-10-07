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

`fotos-plus view` genera un archivo HTML autocontenido con las fotos ya escaneadas, agrupadas
según el archivo de sugerencias. No necesita servidor ni conexión: las miniaturas van
embebidas en el propio archivo, así que se abre haciendo doble clic.

La página ordena en **dos ejes distintos**:

- Los **tags** agrupan *viajes y períodos*: cada tarjeta es un grupo y arrastrarla a otra
  sección le cambia el tag.
- Los **cubos** nombran *fotos sueltas*: una foto puede estar en varios y se eligen con el
  selector del recorrido, no arrastrando.

El orden de la página es siempre el mismo:

1. Las secciones de los tags, por fecha de su primera tarjeta.
2. La sección `Marcadas`.
3. Una sección por cada cubo que tenga fotos, en el orden del catálogo.

Las fotos que no están en ningún cubo no aparecen en ninguna sección de fotos.

Las secciones de fotos usan miniaturas, no renders: es lo que permite que la página abra
rápido con una biblioteca grande.

## Estado

Proyecto en fase inicial: el escaneo de carpetas, las sugerencias de viajes y períodos y el
primer visualizador ya están implementados; la organización definitiva y la auditoría manual
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
ninguna foto. El resumen informa los dos archivos escritos (ejemplo con datos inventados,
para que ningún dato real de una colección aparezca en esta documentación):

```text
Carpeta escaneada: C:\fotos\vacaciones
Fotos encontradas: 1200
Duplicados: 0
Archivos con error: 0
Indice: C:\...\a1b2c3d4e5f60718.json
Sugerencias de viaje: 12
Viajes con pais: 11
Viajes sin pais: 1
Viajes que cruzan paises: 2
Version del conjunto de paises: 1
Periodos sugeridos sin ubicacion: 3
Fotos por auditar: 210
Fotos ubicables por referencia: 90
Fotos sin fecha: 0
Sugerencias: C:\...\a1b2c3d4e5f60718-sugerencias.json
```

Si el cálculo de sugerencias falla, el inventario se escribe igual y el comando avisa por
stderr que el archivo de sugerencias no se generó, sin abortar el escaneo.

### Generar el visualizador

```bash
# Escribir el HTML junto al índice
fotos-plus view ./indice.json

# Escribirlo en otra ruta
fotos-plus view ./indice.json --output ./salida/visor.html
```

El comando **no toca** el índice ni el archivo de sugerencias: solo los lee y escribe el HTML.

Cómo se agrupan las fotos:

- Una tarjeta por cada viaje sugerido y una por cada período sugerido, ordenadas de la fecha
  más antigua a la más reciente.
- Cada tarjeta muestra hasta cinco miniaturas de 200 px con la orientación EXIF ya aplicada,
  el rango de fechas, el país cuando el viaje lo declara y cuántas fotos tiene el grupo.
- Como los viajes tienen prioridad, un período contenido dentro de un viaje se queda sin fotos
  propias. Su tarjeta se muestra igual, avisando de eso, para que el grupo no desaparezca.
- La cantidad de fotos que muestra cada tarjeta es la real del grupo. El `photo_count` de las
  sugerencias cuenta solo las fotos con posición, así que queda muy por debajo del total.
- Las fotos que no caen en ningún viaje ni período van a una tarjeta final de "sin clasificar".

Si el índice no tiene archivo de sugerencias contiguo, el comando no falla: genera el mismo HTML
con todas las fotos en una grilla plana, sin agrupar.

### Editar con un servidor local

El HTML exportado es de **solo lectura**: es un archivo suelto, y sin nadie detrás no hay
dónde guardar un cambio. Para poner nombre a las tarjetas, marcar fotos y recorrerlas hay que
arrancar el servidor local.

```bash
# Servir el visualizador y permitir renombrar los grupos
fotos-plus view ./indice.json --serve

# Elegir el puerto a mano (si no se indica, se busca uno libre)
fotos-plus view ./indice.json --serve --port 8123
```

El servidor:

- Escribe el mismo HTML de antes, junto al índice, y **no lo modifica**: ese archivo sigue
  siendo de solo lectura.
- Escucha únicamente en `127.0.0.1`. No es alcanzable desde la red.
- Levanta una copia de la página en memoria con los controles de edición. Al guardar un
  título, el de la tarjeta se actualiza sin recargar. Al cambiar un tag la página **se
  recarga**, porque las secciones se reordenan.
- Muestra la dirección al arrancar. Ctrl+C lo cierra y libera el puerto.

El token de sesión se genera en cada arranque y viaja en la página servida: sin él, los
endpoints de escritura responden `403`. El token va **siempre en un encabezado**
(`X-Fotos-Plus-Token`), nunca en la URL: un encabezado propio obliga al navegador a pedir
permiso antes, y esa es la barrera que corta el acceso desde otra página. El servidor tampoco
envía cabeceras CORS y además rechaza las peticiones que el navegador marca como
`Sec-Fetch-Site: cross-site` o `same-site`, que es lo que impide que otra web incruste una
`<img>` con una foto de tu biblioteca.

#### Dónde se guardan los nombres

En un archivo hermano del índice, `<indice>-edicion.json`:

```json
{
  "version": 4,
  "based_on_scanned_at": "2026-01-01T00:00:00",
  "labels": {
    "2024-05-01T00:00:00": "Viaje a Bariloche"
  },
  "tags": ["Viaje", "Familia"],
  "tagged": {
    "2024-05-01T00:00:00": "Familia"
  },
  "marked": [
    "9f2c1e0a4b6d8f3a5c7e1b9d0f4a6c8e2b5d7f1a3c9e5b7d1f3a5c7e9b1d3f5a7"
  ],
  "photo_tags": ["Favoritas", "Para imprimir"],
  "photo_tagged": {
    "9f2c1e0a4b6d8f3a5c7e1b9d0f4a6c8e2b5d7f1a3c9e5b7d1f3a5c7e9b1d3f5a7": [
      "Favoritas",
      "Para imprimir"
    ]
  }
}
```

Las etiquetas, los tags y las marcas se guardan con dos claves distintas:

- `labels`, `tags` y `tagged` nombran **grupos**. La clave es la fecha de la primera foto del
  grupo (`first_captured_at`), la misma que ya usa el visor para ordenar. Cada grupo arranca en una
  foto distinta, así que esa clave es única.
- `marked`, `photo_tags` y `photo_tagged` nombran **fotos**. La clave es el hash del contenido de
  la foto, que no cambia al moverla de carpeta ni al renombrarla.

Reglas de las etiquetas:

- Una etiqueta **nunca se guarda vacía**. Borrar el texto no la quita: hay un botón
  "Quitar etiqueta", que es una operación aparte.
- El texto se guarda sin espacios alrededor.
- Si la referencia no corresponde a ningún grupo del escaneo vigente, el servidor lo dice y
  **no escribe nada**. El archivo de etiquetas no se toca.

Reglas de los cubos:

- `photo_tags` es un catálogo **aparte** de `tags`. El mismo nombre puede ser un tag de grupo y un
  cubo de foto sin que los dos se refieran a la misma cosa.
- En `photo_tagged` el valor es una **lista**, porque una foto puede estar en varios cubos a la vez.
- Un nombre de cubo vacío no se guarda, y un nombre que no esté en `photo_tags` se rechaza al
  escribir, igual que un tag que no está en `tags`.
- Las asignaciones de fotos que el índice ya no tiene se podan al leer, pero **no se borran del
  archivo**: si la foto vuelve, recupera su cubo. Los nombres del catálogo tampoco se borran.

Un archivo `version: 1`, `version: 2` o `version: 3` de antes todavía se lee: la primera
modificación lo reescribe como `version: 4` conservando los nombres, los tags y las marcas que
tuviera. Leerlo nunca lo reescribe por sí solo.

#### Tags: agrupar a mano

El escaneo agrupa por parecido de fecha yno sabe qué fue un viaje y qué fue una tarde en casa.
Para eso está el **tag**: un nombre corto y libre que escribes vos, que decide cómo se ordena
la página.

- Cada tarjeta tiene **un solo tag**, distinto del título. Un grupo puede tener título "Viaje a
  Bariloche" y tag "Familia" al mismo tiempo.
- Los nombres del tag salen de vos: escribís uno nuevo en el selector y queda en el catálogo
  para reutilizarlo. El catálogo no se borra cuando un tag queda sin tarjetas.
- Un tag se compara **sin distinguir mayúsculas ni espacios**, así que `Familia`, `familia` y
  `  Familia  ` son el mismo tag. Se guarda la forma en que lo escribiste la primera vez.

Cómo se agrupa la página:

- Las tarjetas con el mismo tag van en una sección, y las secciones se ordenan por la fecha de
  su primera tarjeta. `Sin tag` va siempre al final.
- **Arrastrá** una tarjeta a otra sección y adopta su tag. Soltala sobre `Sin tag` para quitarle
  el tag. Soltarla sobre otra tarjeta le toma el tag de esa tarjeta.
- El HTML exportado con `view` (sin `--serve`) muestra las mismas secciones, pero sin selector
  ni arrastre: no hay servidor donde guardar.

Los tags no cambian los rangos de fechas ni a qué fotos pertenece cada grupo. Solo ordenan lo
que ya estaba agrupado.

#### Recorrer las fotos de un grupo

Con el servidor arrancado, cada tarjeta que tiene fotos propias ofrece **Ver fotos**: abre un
recorrido a pantalla completa con las fotos del grupo, una a una.

- Arriba se ve **en cuál de las fotos del grupo estás** (`3 de 120`).
- `Anterior` y `Siguiente`, o las **flechas del teclado**. En el primer y en el último foto el
  recorrido se queda quieto: no da la vuelta ni se sale del grupo.
- Las flechas no interfieren con escribir: si estás con el cursor en un campo de texto, la
  flecha escribe en el campo.
- `Escape` o `Cerrar` vuelven a las tarjetas. Cerrar no marca ni desmarca nada.

Un grupo declarado por el escaneo que se quedó sin fotos propias no ofrece el botón: no hay
nada que recorrer. El grupo de fotos sin clasificar **sí** se puede recorrer.

Lo que se ve no es el archivo original, sino una copia más chica: el lado largo de la imagen
se limita a 2000 píxeles y se guarda como JPEG. Un JPEG de 13 MB pesa unos 300 KB, así que
recorrer un grupo entero no baja fotos de 3 MB cada una. La orientación EXIF se aplica antes de
achicar, así que las fotos verticales salen verticales.

El recorrido funciona **solo en la página servida**. El HTML exportado con `view` (sin
`--serve`) no lo trae, y no trae ningún control: sigue siendo un archivo suelto de solo lectura.

#### Marcar fotos

Dentro del recorrido, `Marcar` deja la foto apuntada para después; el mismo botón pasa a
`Quitar la marca`. El botón se pinta distinto cuando la foto está marcada.

- Una foto está **marcada o no marcada**. No hay un tercer estado: "sin decidir" y "no me
  interesa" no se distinguen.
- La marca se ve al instante, sin recargar la página.
- Marcar es **decidir qué mirar después**, no borrar nada: no se borra, no se mueve y no se
  renombra ninguna foto. Lo que hagas después con las fotos marcadas es otro tema y otro
  comando.
- El botón se puede apretar en cualquier foto del grupo, no solo en la primera.

Las marcas se guardan como una lista de **hashes de contenido** en `marked`, dentro del mismo
`<indice>-edicion.json`. Van por hash y no por ruta para que la marca sobreviva a mover o
renombrar la foto.

Si una marca apunta a una foto que el escaneo ya no tiene (una unidad sin conectar, por
ejemplo), no se muestra ni cuenta, pero **sigue en el archivo**: si la foto vuelve, la marca
vuelve con ella. Lo que sí pasa es que el próximo guardado reescribe el archivo sin ella.

#### Cubos: nombrar fotos

Al lado del botón `Marcar`, el recorrido trae un **selector de cubos**. Un cubo es un nombre
corto que vos escribís y al que metés las fotos que te interesan de esa manera: `Favoritas`,
`Para imprimir`, `Mandar a Marta`. El selector va aparte del botón de marcar a propósito:
marcar sigue siendo **un solo clic**, y elegir cubos es otra decisión.

- Una foto puede estar en **cuantos cubos quieras a la vez**. Los controles se encienden y se
  apagan, uno por cubo.
- Los nombres salen de vos: escribís uno nuevo en el casillero y queda en el catálogo para
  reutilizarlo. El catálogo no se borra cuando un cubo se queda sin fotos.
- Un nombre se compara **sin distinguir mayúsculas ni espacios**, así que `Favoritas` y
  `  favorita  ` son el mismo cubo. Se guarda la forma en que lo escribiste la primera vez.
- Los cubos son un **eje aparte de los tags**. El mismo nombre puede ser un tag de grupo y un
  cubo de foto sin que los dos significan lo mismo, y el catálogo de cada uno se lleva por
  separado.
- El cambio se ve al instante, sin recargar la página. Si el servidor lo rechaza, el selector
  vuelve a lo que el servidor de verdad tiene y avisa por qué.

Quién escribe cada archivo, para que no se pisen:

| Archivo | Lo escribe |
| --- | --- |
| `<indice>.json` | solo `scan` |
| `<indice>-sugerencias.json` | solo `scan` |
| `<indice>-edicion.json` | solo el servidor de edición |
| `<indice>.html` | solo `view` |
| `<indice>-renders/` | solo el servidor de edición |

#### La carpeta de renders

El servidor guarda las copias chicas en una carpeta hermana del índice, `<indice>-renders/`, con
un archivo por foto: `<hash>.jpg`. El nombre es el hash de contenido, así que dos fotos
idénticas comparten render.

Es una **caché descartable**: si la borrás, la siguiente visita a esa foto la vuelve a hacer y
listo. No hace falta conservarla para nada, y podés dejarla fuera de tus copias de seguridad.
Solo crece cuando se recorren fotos: una biblioteca que no se abre no genera renders.

Nunca se escribe nada dentro de la carpeta de fotos.

Un `scan` posterior **no borra** las etiquetas ni los tags: como `first_captured_at` es la fecha
de la primera foto del grupo, sigue resolviendo al mismo grupo. Si el escaneo se rehizo después de
escribir los nombres o los tags, la página avisa de que puede haber deriva.

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

### El país de cada viaje

Cada foto con posición válida se clasifica en su país **por separado**, comparando su
coordenada contra los polígonos de país que viajan dentro del propio paquete. Después se
cuenta cuántos de cada país tiene cada viaje, y de ahí sale un objeto `location` en cada
sugerencia de viaje (los nombres de abajo son ilustrativos):

```json
"location": {
  "country": "Pais A",
  "countries": ["Pais A", "Pais B"],
  "source": "coordenadas"
}
```

| Campo | Qué es |
| --- | --- |
| `country` | El país donde estuvo la mayoría de las fotos del viaje, o `null` |
| `countries` | Todos los países en los que caía alguna foto del viaje, en orden de cantidad |
| `source` | `coordenadas` si al menos una foto se resolvió, `no-disponible` si ninguna |

Tres cosas que conviene tener claras:

- **El país se cuenta foto por foto, nunca con el centroide del viaje.** El caso genérico que
  obliga a hacerlo: un viaje que cruza una frontera y queda agrupado en una sola sugerencia
  porque se cruzó el umbral de los 200 km por pasos, con fotos a ambos lados de la frontera.
  Su centroide cae de un lado y "borraría" de la existencia las fotos del otro lado.
  Clasificando cada foto, el viaje declara un país como dominante y el otro en la lista: las
  dos cosas son verdad al mismo tiempo.
- **Un empate no se resuelve.** Si dos países tienen la misma cantidad de fotos, `country`
  queda en `null` y los dos aparecen en `countries`. Se declara que no hay dominante en lugar
  de elegir uno en silencio.
- **Que el país no se resuelva no vuelve la foto_unknown.** Una foto con GPS en el mar sigue
  teniendo `location_state: known` (el dato GPS existe) y a la vez `country: null` (nadie
  sabe qué país es). Son dos hechos independientes y el archivo guarda los dos.

`countries_version` declara qué versión de los polígonos se usó. Sin eso, un consumidor no
podría distinguir "este viaje no tiene país" de "este viaje se escaneó con una versión del
conjunto que no incluía su país". Es el mismo motivo por el que `SUGGESTIONS_VERSION` subió
a 2.

**Los períodos no declaran país.** Un período agrupa fotos que no tienen posición, así que
no hay nada que clasificar. Copiarle el país del viaje vecino afirmaría algo que ninguna foto
del período respalda: un tramo del recorrido es "estuve en un país" y otro "me mudé a
otro", y ese "me mudé" no se puede poner con nombre. El campo `location` no existe en los
períodos, ni siquiera vacío.

La clasificación es **completamente offline**: los polígonos se leen del paquete instalado,
no hay red, no hay consultas a servicios de geocodificación y ninguna coordenada sale de la
máquina. La fuente y la licencia de los datos están en
[`fotos_plus/data/README.md`](fotos_plus/data/README.md).

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
| `0` | Terminó bien (puede haber archivos con error, que se informan) |
| `1` | Argumentos inválidos |
| `2` | La ruta indicada no existe, no es una carpeta, no se puede leer, o no se pudo escribir el HTML |

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
- **El visualizador no permite ver el original**: solo miniaturas de 200 px, sin pantalla
  completa, sin zoom y sin navegación por teclado. Agrandar la miniatura significa agrandar el
  HTML, así que el tamaño está fijo en esta etapa.
- **Las secciones de fotos dibujan como mucho 300 fotos**: cada sección dibuja hasta 300 y el
  encabezado dice cuántas tiene en total. Lo que queda afuera no se dibuja, y un aviso te dice cuántas
  son y que las veas desde `Ver fotos` del grupo, que las lista todas sin agrandar el HTML. Para llegar a la foto 301 y siguientes
  de un cubo grande hay que usar el recorrido.
- **El visualizador se regenera entero en cada `view`**: no hay caché, así que abrirlo varias
  veces sobre el mismo índice vuelve a generar todas las miniaturas.

## Desarrollo

```bash
pip install -e ".[dev]"
python -m pytest
```

### Entrega de cambios

Cada change se trabaja en una rama `feature/<nombre-del-cambio>`. El archive se
ejecuta sobre esa misma rama, de modo que el PR a `main` lleva el código, los
tests, las specs sincronizadas y el change archivado, todo junto.

Al aplicar la etiqueta `archive` al pull request, la CI corre la suite de tests y
la validación de specs. Si ambos pasan, el PR se mergea automáticamente a `main`
con squash y la rama se elimina. Si alguno falla, no hay merge.

El paso de merge usa el token que GitHub provee al workflow; no hay credenciales
que configurar en el repositorio.

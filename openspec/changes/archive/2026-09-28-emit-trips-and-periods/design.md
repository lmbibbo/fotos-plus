# Design

## Context

Estado actual, en `fotos_plus/`:

- `photos.py:identify()` abre cada foto dos veces: una para el sha256 del contenido y otra para leer la fecha. La segunda apertura ya lee el IFD `0x8769`; el bloque de GPS (`0x8825`) está en el mismo `Image.open`, así que agregarlo no cuesta una tercera pasada.
- `models.py` tiene `Photo` con ocho campos y `ScanResult`. `Photo.from_dict` lee los campos opcionales con `data.get()`, y `ScanResult.from_dict` ignora `version`. Agregar campos opcionales no requiere migración.
- `index.py` deriva el nombre del archivo del hash de la carpeta raíz normalizada (`_index_file_name`), con `index_path_for(root, index_dir)` y un default en `%LOCALAPPDATA%/fotos-plus/indexes`. `write_index` escribe atómicamente con `tempfile.mkstemp` + `os.replace`.
- `scanner.py:scan()` arma la lista de `Photo`, ordena por `relative_path` y llama a `_mark_duplicates()`. Ya tiene un punto de post-procesado natural antes de devolver.
- `cli.py` tiene un solo subcomando, `scan`, con `--index` y `--index-dir`.

Restricciones:

- `openspec/specs/photo-scanning/spec.md` exige que el escaneo solo lea los archivos de foto. Los viajes son un producto derivado, no una mutación de la colección.
- La config del proyecto declara PostgreSQL y el código no tiene ninguna dependencia de base de datos. Este cambio no la introduce.
- El proyecto trabaja con una rama `feature/<nombre>` y no permite commits directos a `main`.

## Cambio anterior descartado

Hubo un cambio anterior, `group-photos-by-trip`, que proponía tratar el agrupado como una
lectura derivada en el momento de consultar y excluía del agrupado las fotos sin posición.
**Ese cambio fue descartado y su carpeta eliminada**: no hay spec `photo-grouping` en el
repositorio. Este cambio es autocontenido e implementa por su cuenta la extracción de
coordenadas, la escritura del agrupado y el tratamiento de las fotos sin posición.

Por eso este cambio no depende de aquel ni comparte decisiones con él.

La forma del problema se midió sobre una colección de prueba local, que no se versiona y
cuyos números no se reproducen acá. Sobre una colección con GPS intermitente, la medición
que condiciona el diseño tiene esta forma:

```
fotos con posicion utilizable:      ~78% de la coleccion
fotos sin posicion valida:          ~22% de la coleccion
  - en un dia que SI tiene gps:      ~15% de las anteriores  -> ubicables por referencia
  - en un dia SIN gps:               ~85% de las anteriores  -> requieren auditoria
periodos que cubren esas fotos:      una decena   (corte: 1 dia vacio)
fotos sin fecha de captura:            0
sugerencias de viaje:                decenas
saltos > 200 km entre consecutivas:  ~1% de las fotos con posicion
costo de leer todo el EXIF:          ~1 ms/foto
```

El dato de los períodos es lo que define el valor de esta decisión: una estructura que el
usuario pueda auditar a mano solo es viable si son una decena de registros, no un millar.

## Goals / Non-Goals

**Goals:**

- Escribir sugerencias de viajes y períodos una sola vez, durante el escaneo, como archivo consultable.
- Marcar el archivo y su contenido como provisionales, para que no se confundan con viajes y períodos definitivos.
- No perder ninguna foto sin posición: toda cae en un período o queda marcada como ubicable por referencia.
- Marcar de forma explícita qué ubicaciones se conocen y cuáles no.
- Mantener la escritura atómica y la convención de nombres que ya usa `index.py`.
- Degradar sin abortar: si el agrupado falla, el inventario se escribe igual.

**Non-Goals:**

- No se producen viajes ni períodos definitivos. Este cambio solo deja la estructura y el punto de partida para esa etapa.
- No se resuelve la ciudad a partir de la coordenada ni se detectan lugares por nombre.
- No se edita a mano el archivo de sugerencias ni se le asigna un lugar a un período. La auditoría manual es un cambio posterior; este define la estructura que la soportará.
- No se conserva ninguna revisión manual dentro del archivo de sugerencias, porque el escaneo lo sobrescribe.
- No se agrupa por personas.
- No se guarda la altura, aunque el 100% de las fotos con GPS la traiga.
- No se corrige la deriva de zona horaria entre países.
- No se unifican los archivos de inventario y de sugerencias: son dos archivos porque el
  visualizador necesita los viajes sin arrastrar todas las entradas del inventario.

## Decisions

### 1. El agrupado se escribe durante el escaneo, no se calcula al leer

Se escribe un segundo archivo al terminar el escaneo. La razón es el costo: el escaneo es el
único momento en que el sistema ya recorrió todas las fotos y ya tiene el `ScanResult` en
memoria. Calcular al leer obligaría al visualizador a leer el índice completo y particionar
en cada consulta, y esa partición depende de un umbral que el usuario puede querer ajustar.

Alternativa descartada: calcular al leer. Se descarta porque paga el costo en cada consulta y porque hace imposible que el escaneo deje constancia de lo que no se pudo ubicar.

Consecuencia asumida: cambiar el umbral de 200 km exige reescanear. Se acepta porque el escaneo es idempotente y ya existe como operación, y porque al ser sugerencias, un umbral distinto no invalida nada: solo produce otro archivo, también provisional.

### 2. El archivo se declara provisional y lo dice en su nombre

El nombre incluye la palabra "sugerencias": `<hash>-sugerencias.json` junto a `<hash>.json`. El contenido lleva además un campo que declara el carácter provisional del archivo.

La razón de hacerlo en los dos lugares es que un consumidor puede leer cualquiera de los dos. El nombre protege a quien mira la carpeta; el campo protege a quien abre el archivo y lo consume por código. Con solo uno de los dos, un consumidor puede seguir tratando las sugerencias como hechos.

Alternativa descartada: llamar al archivo simplemente "viajes" y dejar la provisionalidad solo en un campo interno. Se descarta porque el nombre es lo primero que ve el usuario en la carpeta, y es donde más probable es que se confunda con el archivo definitivo que existirá más adelante.

Consecuencia: cuando exista el archivo definitivo, conviven dos archivos con nombres distintos y no hay ambigüedad de cuál es cuál. Si el definitivo se llamara igual, el escaneo empezaría a sobrescribir el trabajo de auditoría del usuario.

### 3. Segundo archivo, no campos nuevos en el índice

El inventario describe fotos; los viajes describen zonas del tiempo. Meter los viajes en el índice obligaría al visualizador a leer 6.4 MB de inventario para obtener 45 viajes, y a duplicar en el índice datos que no son de las fotos.

Se usa la misma convención de nombre por hash de la carpeta raíz, con un sufijo que lo distingue. Así, `--index-dir` los coloca juntos y `--index` explícito los escribe junto al archivo indicado, sin reglas nuevas para el usuario.

Consecuencia: el patrón `/[0-9a-f]*.json` del `.gitignore` ya cubre también `<hash>-sugerencias.json`, porque solo exige que el primer carácter sea hexadecimal y `*` absorbe el sufijo. No hace falta un patrón nuevo; se deja constancia con `git check-ignore -v`.

### 4. La frontera de una sugerencia de viaje es espacial, con umbral de 200 km

Se ordena por `captured_at` y se compara cada foto con la anterior, manteniendo la sugerencia mientras la distancia sea menor a 200 km. La distribución de saltos tiene un vacío entre 3 km (p90) y 264 km (p99), así que 200 km está lejos de ambos extremos y el resultado no depende de un ajuste fino.

Se compara contra la foto anterior y no contra un centroide: contra un centroide, una ida y vuelta desde la misma base parte el grupo al segundo tramo.

Alternativa descartada: cortar por hueco de días. Falla en las dos direcciones. Con corte de 7 días, el viaje a Colombia de julio-agosto 2023 queda en 9 fragmentos; sin corte, Buenos Aires queda como un bloque de 46 días y 169 fotos, que es vida en un lugar y no un viaje. El 91.7% de los huecos entre fotos consecutivas es menor a 12 horas, así que casi no existe un hueco que marque un viaje.

Que el resultado sea una sugerencia y no un hecho reduce el costo de equivocarse: un umbral mal elegido produce un archivo provisional que el usuario puede corregir, no una clasificación equivocada que hay que defender. Por eso el umbral queda fijo y no parametrizable en esta versión.

Consecuencia asumida: un traslado largo dentro de un mismo viaje lo parte en dos sugerencias. Se acepta porque son lugares distintos, y porque el usuario puede unirlas al auditar.

### 5. Un período es un bloque de días sin posición, con corte de 1 día vacío

Las fotos sin posición se agrupan por día. Dos días sin posición se unen en el mismo período si hay como máximo 1 día intermedio sin ninguna foto sin posición; más allá, son dos períodos.

El corte de 1 día vacío produce una decena de períodos sobre la colección de prueba. La
medición previa del diseño fijaba un corte de 3 días, pero esa combinación no se reproducía
en el escaneo real: con 3 días vacíos el período dominante absorbía fotos de días previos que
son un salida distinta, y con el corte estricto esos días quedan separados. Se conserva la
cifra del período dominante, que sí es reproducible, y se adopta el corte estricto: separa
dos salidas distintas y evita fusionar la mañana y la tarde de un mismo día con los días
previos. El conteo original queda anotado como una estimación que el escaneo real refutó.

Alternativa descartada: un solo período que abarque todo el conjunto. Se descarta porque con
decenas de sugerencias de viaje y un millar de fotos sin ubicación, un único período no es
auditable.

Consecuencia asumida: un período puede incluir fotos de dos salidas distintas si hubo menos de 3 días sin fotografiar entre ellas. Se acepta; el visualizador muestra el rango de fechas completo y el usuario decide al auditar.

### 6. "Ubicable por referencia" separa la fracción que no necesita trabajo manual

De las fotos sin posición, una fracción chico comparte día con alguna foto con posición
válida. Esas no necesitan un lugar: el día ya está anclado a un lugar. Se marcan con un
campo booleano y quedan fuera de los períodos.

Esto reduce la auditoría manual a las que no tienen referencia, y más importante, reduce la
cantidad de períodos de una forma que el usuario no tiene que decidir: la información ya
está en el propio día.

No se les asigna la coordenada de la foto con GPS del mismo día. Se marca la referencia pero no se copia el valor, porque un día puede tener dos lugares distintos y la elección sería arbitraria.

### 7. La validez de la coordenada se define sobre el valor, no sobre la presencia del tag

49 fotos traen GPS presente con ambos ejes en cero. Es un fallo de fijación que el teléfono escribió como coordenada válida, y los manda al Golfo de Guinea a 10.000 km de los viajes reales. La regla cubre los tres casos de descarte: sin bloque de posición, bloque presente pero vacío, y `(0, 0)`.

La regla vive en un solo lugar, en `photos.py`, y `trip-periods` la consume, para que el visualizador no tenga que volver a derivarla.

### 8. "Ubicación conocida" y "sugerencia" son dos ejes distintos

Cada viaje y cada período lleva un estado de ubicación, y el archivo lleva su marca de provisionalidad. Son cosas distintas y no deben codificarse en el mismo campo.

El caso que obliga a separarlas: un viaje sugerido a partir de muchas fotos con GPS tiene
la ubicación **conocida** y sigue siendo una **sugerencia**. Un período de unas pocas fotos
no tiene ubicación conocida y también es una sugerencia. Un campo único que dijera
"automático" o "desconocido" perdería la primera información, que es justamente la que el
visualizador necesita para mostrar "sugerencia con lugar conocido" frente a "sugerencia sin
lugar".

## Flujo

Escaneo, con el bloque de posición en la apertura que ya se hace para la fecha:

```
  scan(carpeta)
        |
        +---> identify(foto)  por cada archivo
        |        |
        |        +---> [1] sha256 del contenido            (9.9 ms)
        |        |
        |        +---> [2] Image.open  -------------------+
        |        |            +-> exif[0x9003]  fecha      |
        |        |            +-> exif.get_ifd(0x8769)     |
        |        |            |      -> 0x9003 fecha       |
        |        |            +-> exif.get_ifd(0x8825)     |  <-- nuevo
        |        |                   -> 0x0001 lat ref       |
        |        |                   -> 0x0002 lat           |
        |        |                   -> 0x0003 lon ref       |
        |        |                   -> 0x0004 lon           |
        |        |                          |               |
        |        |                          v               |
        |        |              gms -> decimal + hemisfe     |
        |        |                          |               |
        |        |              (0,0) o ausente -> None       |
        |        |                          |               |
        |        +---> Photo(..., lat, lon) ----------------+
        |
        v
  ScanResult (ordenado por relative_path, duplicados marcados)
        |
        +---> write_index(result, <hash>.json)          [atomico]
        |
        v
  build_suggestions(result)             <-- falla aca NO aborta
        |
        |   [1] separar: con posicion valida / sin posicion
        |   [2] con posicion: ordenar por captured_at
        |   [3] recorrer comparando con la ANTERIOR
        |   |      dist(a,b) = haversine(a, b)
        |   |      dist <  200 km -> misma sugerencia
        |   |      dist >= 200 km -> sugerencia nueva
        |   [4] sin posicion: agrupar por dia
        |   [5] dias contiguos (hueco <= 1 dia vacio) -> mismo periodo
        |   [6] dia con alguna foto con posicion -> "ubicable por referencia"
        |   [7] por grupo: n, primera fecha, ultima fecha, ubicacion
        v
  SuggestionsResult
        |   +---> marca de contenido provisional
        |   +---> por grupo: ubicacion conocida / desconocida
        |   (ejes separados: provisional != sin ubicacion)
        |
        +---> write_index(sugg, <hash>-sugerencias.json)   [atomico]
        |
        v
  resumen: N sugerencias de viaje, M periodos, K fotos por auditar
  (el resumen dice "sugerencias", no "viajes")
```

Escritura de los dos archivos, reutilizando la atomicidad existente:

```
  write_index(payload, path)
        |
        +---> path.parent.mkdir(parents=True, exist_ok=True)
        +---> tempfile.mkstemp(dir=path.parent, prefix=".<name>.", suffix=".tmp")
        |        |
        |        +---> escribe el JSON completo
        |
        +---> os.replace(tmp, path)      <-- reemplazo atomico
        |
        +---> ante excepcion: os.unlink(tmp) y propaga
```

## Riesgos / Trade-offs

- **Agrupar al leer en vez de al escribir** → se descarta por el costo por consulta y porque el escaneo no podría dejar constancia de lo que no se pudo ubicar. La decisión queda registrada acá porque es la que más caro sale revertir.

- **El sufijo `-sugerencias.json` y el patrón `/[0-9a-f]*.json`** → verificado con `git check-ignore -v`: el patrón ya cubre los dos nombres porque `*` absorbe el sufijo. No se agrega ningún patrón nuevo; la tarea solo lo verifica.

- **Reescribir el archivo en cada escaneo descarta cualquier revisión manual** → es intencional: el archivo es derivado y provisional, y este cambio no ofrece edición. Cuando exista el archivo definitivo, el trabajo de auditoría tendrá que vivir en otro archivo que el escaneo lea y no sobrescriba. Queda anotado acá porque es la decisión de diseño que más caro sale revertir: si el archivo definitivo termina siendo este mismo, habría que dejar de sobrescribirlo, y eso rompe la atomicidad de "el escaneo regenera todo".

- **Un consumidor puede ignorar la marca de provisionalidad y tratar las sugerencias como hechos** → se mitiga en dos niveles, el nombre del archivo y el campo de provisionalidad, pero no se puede forzar desde el productor. La mitigación real es el consumidor: cuando exista el visualizador, su spec debe exigir que presente estas sugerencias como tales. Queda como open question porque depende de una spec que todavía no existe.

- **Ajustar el umbral de 200 km exige reescanear la colección** → se acepta. El escaneo es
  idempotente y el costo dominante es la lectura de archivos, no el agrupado. Y al ser
  sugerencias, el costo de tener un umbral imperfecto es bajo: el escaneo siguiente lo
  reemplaza.

- **Una "estancia larga en casa" aparece como una sugerencia más** → se mitiga con el rango de fechas y con la marca de provisionalidad, que dejan claro que es una aproximación y no un traslado confirmado. Distinguir por dispersión y duración necesita un umbral más y no se justifica con esta colección.

- **`build_suggestions` puede fallar y dejar el escaneo a medias** → la spec exige que el inventario se escriba igual y que el comando informe que el archivo de sugerencias no se generó. Se implementa con un `try` alrededor del agrupado, no con el agrupado dentro de la construcción de `ScanResult`.

- **El archivo de sugerencias puede quedar desactualizado respecto del inventario** → se evita escribiendo los dos en la misma ejecución y declarando en ambos la carpeta raíz y el momento. El escaneo reemplaza los dos juntos; no hay estado intermedio observable porque la escritura del segundo es la última.

## Migration Plan

1. Agregar los campos opcionales de coordenadas a `Photo` y su extracción en `photos.py`, en la apertura que ya se hace para la fecha.
2. Verificar con `git check-ignore -v` que el patrón `/[0-9a-f]*.json` ya cubre `<hash>-sugerencias.json`; no agregar patrones redundantes.
3. Agregar los tipos de sugerencia, período y resumen, con la marca de provisionalidad, y el helper de ruta del segundo archivo.
4. Implementar la geometría y la partición, y llamarla desde el escaneo después de escribir el inventario.
5. Documentar el archivo nuevo en el README, dejando explícito que contiene sugerencias y no viajes confirmados.

Rollback: revertir el commit. El archivo de sugerencias previo queda en disco, sin efecto, porque nada lo lee. No hay migración que deshacer: los dos archivos son derivados y se regeneran. Ningún archivo de foto se toca. Perder las sugerencias no pierde información del usuario, porque no son la fuente de verdad.

## Open Questions

- Cuándo exista el visualizador: si pasa a necesitar consultas del tipo "viajes de un rango de fechas" o "qué vio el usuario en tal lugar", la persistencia declarada (PostgreSQL) deja de ser hipotética. Ese es el momento de decidir si estos archivos JSON siguen siendo el formato o pasan a ser una proyección.
- Cómo se va a llamar el archivo definitivo de viajes y períodos, y si convive con este o lo reemplaza. El nombre de este incluye "sugerencias" precisamente para dejarle el lugar libre.
- Qué tan gruesa tiene que ser la marca de provisionalidad: si alcanza con un campo en el archivo o si el visualizador va a exigir un acknowledgment. Se decide junto con el visualizador, no ahora.
- La altura está disponible y sin usar. Podría separar "misma coordenada, distinto nivel" (un edificio frente a un mirador) si algún día ese caso aparece en la colección.

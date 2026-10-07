# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Videos in the served browser show a still without playback

In `--serve` mode, opening a video in the group browser MUST show a still image of that
video with its duration marked, and MUST NOT offer playback in this phase. The `/render`
endpoint keeps serving photos only and MUST refuse video references with a reason. Video
blobs MUST never be embedded in the static export; the export shows video posters exactly
like photo thumbnails.

#### Scenario: Browser opened on a video

- **GIVEN** a group holding a video, served with `view --serve`
- **WHEN** the browser opens on that video
- **THEN** a still image of the video appears with its duration marked
- **AND** no playback control is offered

#### Scenario: Render endpoint refuses a video

- **GIVEN** a video recorded in the scanned index
- **WHEN** its reference is requested from the `/render` endpoint
- **THEN** the endpoint refuses it with a reason instead of serving a render

#### Scenario: Export embeds posters, never video blobs

- **GIVEN** an exported HTML document for a group holding videos
- **WHEN** the document is inspected
- **THEN** video posters appear exactly like photo thumbnails
- **AND** the document embeds no video blob

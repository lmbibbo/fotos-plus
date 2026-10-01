# Design

## Context

Hoy `view` genera un archivo HTML autocontenido con las tarjetas ya renderizadas en el servidor: no hay ningún JavaScript ejecutable, y el bloque `<script type="application/json" id="viewer-data">` que ya existe no lo lee nadie. El título de cada tarjeta se deriva en tiempo de render con la regla `país o "Viaje"`, y como 37 de 51 viajes son del mismo país, el título no distingue tarjetas.

Dos restricciones del proyecto condicionan el diseño:

- La especificación vigente de `photo-viewing` exige que el HTML exportado muestre su contenido **sin** necesitar un servidor local, así que el modo servidor puede añadirse pero no puede reemplazar al export.
- `scan` no se modifica: sigue reescribiendo el archivo de sugerencias completo y sigue sin leer ningún archivo de edición.

Dos observaciones medidas sobre el índice real sostienen el diseño de la clave:

- `first_captured_at` ya es la clave de ordenamiento de las tarjetas (`viewer.py:143`), así que no hace falta introducir un concepto nuevo de identidad.
- Es única entre los 65 grupos (0 colisiones), y lo es por construcción: como las fotos se reparten sin solaparse, el mínimo de cada grupo es una foto distinta.

## Goals / Non-Goals

**Goals:**

- Que el usuario ponga su propio nombre a un grupo y que ese nombre sobreviva a los rescaneos.
- Que el título priorice la etiqueta sin alterar ningún otro dato de la tarjeta.
- Que todo el cambio se revierta borrando un solo archivo.
- Conservar intacta la garantía del export estático.
- Que ninguna etiqueta inválida llegue a escribirse: se rechaza en el servidor, no en el formulario.

**Non-Goals:**

- Membresía explícita de fotos: mover fotos entre grupos, dividir y unir. Necesitan la lista real de fotos por grupo y rompen el invariante de rangos disjuntos del que hoy depende la asignación del visor. Ver "Decisiones" más abajo.
- Servir miniaturas bajo demanda y cargar todas las fotos en el DOM. No hace falta para etiquetar.
- Tocar `scan` de cualquier forma.
- Disparar un escaneo desde el navegador.
- Definir qué significa "confirmar" un grupo para los próximos escaneos.

## Decisions

### D1. La clave de un grupo es su fecha más temprana

No se agrega un identificador al escaneo. La etiqueta se referencia con `first_captured_at`.

Se compararon cuatro candidatos:

| Candidata | Sobrevive si... | Problema |
|---|---|---|
| `first_captured_at` | se agregan fotos al medio del viaje | ya está en el JSON, legible |
| hash de la membresía | nada | cambia al agregar una sola foto |
| ruta de la primera foto | se agregan fotos al medio | se rompe al renombrar el archivo |
| id asignado en el escaneo | todo | exigiría modificar `scan` |

La clave elegida nunca pierde contra el hash de la membresía: agregar una foto al medio rompe el hash y no la clave; quitar la primera foto rompe las dos; agregar una foto anterior rompe las dos.

### D2. El archivo de edición es hermano del índice y tiene un solo escritor

```
   scan   --->  x.json               escritor: scan
              x-sugerencias.json    escritor: scan
   editor --->  x-edicion.json       escritor: editor
   view   --->  x.html               escritor: view
```

Como ningún flujo toca un archivo de otro, no hay carrera posible entre el escaneo y el editor. También hace que el rollback sea borrar un archivo.

Se descartó escribir las etiquetas dentro del archivo de sugerencias: el escaneo lo reemplaza entero, y hoy una edición manual mínima de ese archivo ya deja el comando inutilizable.

### D3. Una etiqueta vacía no es representable

El vacío se descarta en tres capas, y ninguna interpreta el texto vacío como borrar:

```
  formulario   el campo vacío no se puede enviar: hay una accion
               separada para quitar la etiqueta
  servidor     una etiqueta vacía o solo con espacios se rechaza
               con un motivo, y el archivo queda igual
  archivo      una entrada con valor vacío nunca se escribe
```

Quitar una etiqueta es una operación distinta: elimina la clave del mapa. Así no existe el estado ambiguo "vacío significa volver al título derivado" frente a "vacío significa borrar", que es exactamente la ambigüedad que había que cerrar.

### D4. El servidor es aditivo y el export se declara de solo lectura

`view --serve` sigue escribiendo el HTML estático junto al índice antes de escuchar, para que el export no deje de existir. Ese export aplica las etiquetas al renderizar los títulos, pero no incluye ningún control de edición: un botón "Guardar" que no puede guardar es peor que ningún botón. En su lugar, la página indica que es de solo lectura.

### D5. El servidor se expone solo a loopback y con defensas capas

El endpoint de edición reescribe a qué grupo pertenece cada tarjeta, así que es una primitiva de escritura alcanzable desde cualquier página abierta en el navegador del usuario. Se acumulan cuatro defensas baratas, cada una cortando un vector distinto:

```
  bind a 127.0.0.1              no alcanzable desde la red local
  token aleatorio en la URL     no alcanzable desde otra pestaña o sitio
  encabezado Host debe ser loopback   evita DNS rebinding
  Content-Type application/json  fuerza preflight; sin CORS el
                                 cross-origin no llega a la escritura
  sin cabeceras CORS            el navegador no puede leer respuestas
```

Se descartó escuchar en todas las interfaces: el servidor da acceso a la biblioteca de fotos y a la estructura de carpetas de la descarga de la cámara.

### D6. No hay endpoint de miniaturas en este cambio

Renombrar no necesita más que las miniaturas que el HTML ya embebe. Agregar un endpoint de miniaturas arrastraría el trabajo de cachear `make_thumbnail`, que hoy no tiene caché, y quedaría sin uso hasta que la edición por membresía lo requiera. Se deja para el cambio que la necesite.

### D7. La etiqueta reemplaza al título y el país sigue en la línea de metadatos

Hoy el país aparece dos veces: como título y en la línea de metadatos. Reemplazar el título por la etiqueta elimina la duplicación sin perder información, porque el país sigue mostrándose aparte. La precedencia es: etiqueta vigente si la hay, si no el título derivado.

## Flujos

Guardar una etiqueta:

```
  navegador        servidor              disco
     |                 |                   |
     |  GET /?t=<token>|                   |
     |---------------->|                   |
     |                 |  lee indice +     |
     |                 |  sugerencias +    |
     |                 |  x-edicion.json   |
     |                 |------------------>|
     |  HTML con       |                   |
     |<----------------|                   |
     |                 |                   |
     |  POST /api/labels                     |
     |  {clave, texto} |                   |
     |---------------->|                   |
     |                 |  1. texto vacio?  |
     |                 |     -> rechaza     |
     |                 |  2. la clave      |
     |                 |     resuelve?      |
     |                 |     -> si no,      |
     |                 |        rechaza     |
     |                 |  3. clave ambigua?|
     |                 |     -> rechaza     |
     |                 |  4. escribe       |
     |                 |     atomico con   |
     |                 |     scanned_at    |
     |                 |------------------>|
     |  200 {ok}       |                   |
     |<----------------|                   |
```

Carga y deriva:

```
  navegador        servidor              disco
     |                 |                   |
     |  GET /?t=<token>|                   |
     |---------------->|                   |
     |                 |  scanned_at del    |
     |                 |  overlay vs del    |
     |                 |  archivo vigente   |
     |                 |------------------>|
     |                 |                   |
     |                 |  1. indexa overlay |
     |                 |     por clave      |
     |                 |  2. para cada      |
     |                 |     grupo: resuelve |
     |                 |     o no           |
     |                 |  3. si el escaneo  |
     |                 |     es posterior:  |
     |                 |     cuenta drifting|
     |                 |                   |
     |  HTML con        |                   |
     |  titulos y       |                   |
     |  aviso de deriva |                   |
     |<----------------|                   |
```

## Risks / Trade-offs

- **Un rescaneo cambia la primera foto de un viaje y su etiqueta se pierde** → el overlay registra el `scanned_at` con el que se construyó y la vista informa cuántas etiquetas siguen resolviendo. La etiqueta no se borra, así que el usuario puede reasignarla.
- **Las etiquetas huérfanas se acumulan** → el aviso de deriva las lista. Una acción de reasignación queda para un cambio posterior.
- **Editar el overlay a mano lo puede dejar ilegible, igual que pasó con el archivo de sugerencias** → el esquema se valida al leer y el error se informa de forma explícita. El archivo es chico y su formato es simple a propósito.
- **El texto que el usuario está escribiendo en el navegador y el export pueden discrepar** → el export lee el overlay al generarse, así que refleja lo último guardado. El texto no guardado nunca fue parte del modelo.
- **El token puede quedar en el historial del navegador** → la página no carga recursos externos, así que no hay referrer que lo arrastre, y el servidor no sirve contenido de terceros.
- **Las tarjetas siguen sin distinguirse cuando no se renombran** → es esperado: el cambio agrega la capacidad de renombrar, no cambia los títulos por defecto. Ver "Open Questions".

## Migration Plan

No hay datos que migrar: el archivo de edición es nuevo y opcional, y si no existe el visor se comporta exactamente como hoy.

Despliegue:

1. Publicar el cambio.
2. `view` sin `--serve` sigue funcionando sin cambios para el usuario.
3. El usuario adopts `--serve` cuando quiera etiquetar.

Rollback:

1. Borrar `<id>-edicion.json` y se pierden solo las etiquetas.
2. Revertir el commit: el flag `--serve` desaparece y el export estático queda igual que antes del cambio.
3. El índice y el archivo de sugerencias no se tocaron en ningún momento, así que no hace falta regenerar nada.

## Open Questions

- **Título por defecto de las tarjetas sin renombrar.** Se conserva el actual `país o "Viaje"`, que duplica el país de la línea de metadatos. La alternativa sería un título que no repita esa información. Es aplazable: la especificación solo dice "el título derivado de la sugerencia", así que cambiar el valor por defecto no altera ningún requisito ni bloquea ninguna tarea.
- **Si conviene una acción para reasignar etiquetas que quedaron huérfanas** tras un rescaneo. Depende de cuán seguido se escanee.
- **Si el archivo de edición debe admitir también una nota o descripción por grupo.** Sería la misma maquinaria de claves, sin resolver el problema de la membresía.

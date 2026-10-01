# Tasks

## 1. Formato del archivo de edición y migración

- [x] 1.1 Subir `EDITION_VERSION` a 2 y agregar `tags` y `tagged` al overlay, con `tags` como lista ordenada
  y `tagged` como mapa de `first_captured_at` a nombre de tag. Verificar que un overlay nuevo serializa las
  dos claves.
- [x] 1.2 Aceptar las versiones 1 y 2 en la lectura y normalizar ambas a la estructura vigente: un archivo v1
  se resuelve con sus etiquetas y sin tags. Verificar con un archivo v1 escrito a mano que conserva las
  etiquetas.
- [x] 1.3 Rechazar con motivo una versión distinta de 1 o 2, como hoy se rechaza la que no corresponde.
  Verificar que el mensaje dice la versión encontrada.
- [x] 1.4 Normalizar el nombre de un tag recortando espacios y comparando sin mayúsculas, conservando la
  forma con la que se creó por primera vez. Verificar que `" familia "` se reconoce como el tag ya existente
  y que el catálogo no queda con dos entradas equivalentes.
- [x] 1.5 Validar que `tagged` no referencia un tag ausente del catálogo y que `tags` no tiene entradas
  vacías ni duplicadas equivalentes. Verificar que un archivo editado a mano con esasidez se rechaza con motivo.
- [x] 1.6 Mantener la escritura atómica y agregar los tests de que un `tagged` inválido no llegue al archivo en
  disco: la validación previa a la escritura cubre tanto etiquetas como tags.

## 2. Operaciones de tag

- [x] 2.1 Implementar la asignación de un tag que crea el tag en el catálogo cuando no existe y devuelve un
  overlay nuevo sin mutar el de entrada. Verificar que el catálogo gana la entrada nueva.
- [x] 2.2 Implementar el borrado del tag de un grupo como operación explícita, sin depender de enviar un tag
  vacío, y sin quitar el tag del catálogo. Verificar que el catálogo queda intacto.
- [x] 2.3 Rechazar con motivo el tag vacío o solo con espacios, la referencia que no resuelve a ningún grupo
  vigente y la referencia ambigua. Verificar un caso por cada motivo.
- [x] 2.4 Resolver los tags contra los grupos vigentes con el mismo criterio de las etiquetas, separando
  resueltos, no resueltos y ambiguos, y extender la señal de deriva para que el aviso de "no resuelven" los
  cubra. Verificar que una asignación que quedó huérfana por un rescaneo sigue guardada y se reporta.

## 3. Agrupación en secciones

- [x] 3.1 Agregar el tag resuelto al modelo de grupo que arma el visor, sin tocar cómo se asignan las fotos a
  las tarjetas. Verificar que el conteo y el rango de fechas de cada tarjeta quedan igual que antes.
- [x] 3.2 Agrupar las tarjetas en secciones, una por tag asignado más la sección de grupos sin tag. Verificar
  que con dos grupos con el mismo tag aparece una sola sección con las dos tarjetas.
- [x] 3.3 Ordenar las secciones por la fecha más temprana de su primera tarjeta y dejar la sección sin tag al
  final. Verificar con un tag de 2020 y otro de 2019 que el de 2019 aparece primero.
- [x] 3.4 Mostrar en cada encabezado de sección su nombre y la cantidad de grupos que contiene, y no generar
  sección para un tag del catálogo sin grupos asignados. Verificar los dos casos.
- [x] 3.5 Mantener la lista única ordenada por fecha cuando no hay ningún tag asignado. Verificar que el
  HTML generado es equivalente al anterior en esa situación.

## 4. Arrastre y selector en el modo servidor

- [x] 4.1 Emitir el tag vigente en un atributo `data-` de cada tarjeta, con valor vacío cuando el grupo no
  tiene tag. Verificar sobre el HTML generado con y sin tags.
- [x] 4.2 Agregar las acciones `set_tag` y `clear_tag` al endpoint existente, reutilizando la validación de
  token, host de loopback y tipo de contenido JSON ya presente. Verificar que una petición sin token válido
  se rechaza y no escribe ningún archivo.
- [x] 4.3 Agregar al bloque `EDIT_SCRIPT` el arrastre: soltar sobre una sección asigna el tag de la sección,
  soltar sobre una tarjeta adopta el de esa tarjeta, y soltar sobre la sección sin tag lo quita. Verificar que
  un destino sin tag produce `clear_tag` y no una asignación vacía.
- [x] 4.4 Agregar el selector de tags por tarjeta, con la opción de elegir uno del catálogo o escribir uno
  nuevo, y una acción explícita para quitar el tag sin depender del arrastre. Verificar que un tag escrito se
  guarda y queda disponible para las demás tarjetas.
- [x] 4.5 Informar el resultado de cada operación y dejar la tarjeta sin cambios visibles cuando el servidor
  rechaza la asignación. Verificar el mensaje ante un rechazo por tag vacío.

## 5. Verificación de integración

- [x] 5.1 Confirmar que el HTML exportado sin token muestra las secciones por tag y no incluye ni el bloque de
  arrastre ni el selector, y que sigue indicando que es de solo lectura. Verificar sobre el archivo generado.
- [x] 5.2 Confirmar que `scan` sigue sin leer el archivo de edición y que un reescaneo conserva tags y
  etiquetas. Verificar comparando el archivo de edición antes y después de un escaneo.
- [x] 5.3 Actualizar el README con el archivo de edición en versión 2, el catálogo de tags, el gesto de
  arrastre y el hecho de que el tag clasifica mientras el título nombra. Verificar que lo documentado
  corresponde a lo implementado.
- [x] 5.4 Correr la suite completa y `openspec validate --specs --strict`, y confirmar que pasan los dos.



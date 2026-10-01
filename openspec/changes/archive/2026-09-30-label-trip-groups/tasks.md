# Tasks

## 1. Archivo de edición

- [x] 1.1 Derivar la ruta del archivo de edición a partir de la ruta del índice, junto al helper existente de sugerencias, y verificar con un test que el nombre es `<base>-edicion.json` y que no colisiona con `<base>-sugerencias.json`
- [x] 1.2 Leer el archivo de edición cuando existe e indexar sus entradas por `first_captured_at`, validando el esquema; verificar con tests para overlay ausente, válido y corrupto, este último debe informar un error explícito y no una excepción opaca
- [x] 1.3 Escribir el archivo de edición de forma atómica reutilizando la disciplina de escritura atómica existente en el módulo de índice, registrando el `scanned_at` del escaneo vigente; verificar con un test que el archivo resultante es completo y que el temporal no queda en el disco
- [x] 1.4 Rechazar en la escritura una etiqueta vacía o compuesta solo por espacios; verificar con un test que la operación falla y que el archivo previo queda idéntico

## 2. Resolución de claves y detección de deriva

- [x] 2.1 Resolver una etiqueta contra los grupos vigentes del archivo de sugerencias: exactamente una coincidencia es válida, cero coincidencias se rechaza por no resolver y más de una se rechaza por ambigüedad; verificar con un test por cada uno de los tres casos
- [x] 2.2 Calcular la deriva comparando el `scanned_at` registrado en el archivo de edición contra el del archivo de sugerencias vigente, contando cuántas etiquetas siguen resolviendo y cuántas no; verificar con tests para un overlay anterior al escaneo, uno posterior y uno alineado

## 3. Precedencia de la etiqueta en las tarjetas

- [x] 3.1 Usar la etiqueta vigente como título de la tarjeta cuando exista y mantener el título derivado cuando no, sin alterar el resto de los datos; verificar con un test que el título cambia y que cantidad, rango de fechas y país se muestran igual antes y después
- [x] 3.2 Mantener la regla de que un período con etiqueta no muestra país; verificar con un test del período etiquetado
- [x] 3.3 Marcar el HTML exportado como de solo lectura, sin ningún control de edición, y confirmar que exportar no crea el archivo de edición; verificar con tests del marcador de solo lectura, de la ausencia de controles y de la ausencia del archivo tras exportar

## 4. Servidor local

- [x] 4.1 Agregar el flag `--serve` al subcomando `view` generando el HTML estático junto al índice antes de escuchar; verificar con un test que el archivo HTML existe una vez que el servidor arrancó
- [x] 4.2 Escuchar únicamente en la dirección de loopback y rechazar peticiones cuyo encabezado de host no sea de loopback; verificar con un test que el socket queda en la interfaz de loopback y con un test que rechaza una petición con host ajeno
- [x] 4.3 Exigir un token aleatorio generado al arrancar para toda petición de edición; verificar con tests de petición sin token y con token incorrecto
- [x] 4.4 Exigir que las ediciones declaren tipo de contenido JSON y no enviar ninguna cabecera que permita acceso desde otro origen; verificar con un test del tipo de contenido y un test de la ausencia de cabeceras de acceso cruzado
- [x] 4.5 Validar cada edición contra los grupos vigentes antes de escribirla, rechazando con motivo la referencia que no resuelve, la ambigua y la etiqueta vacía, y dejar el archivo intacto en esos casos; verificar con un test por rechazo que compruebe además que el archivo no cambió
- [x] 4.6 Informar por la salida de error y terminar con código distinto de cero cuando el puerto pedido esté ocupado; verificar con un test que ocupa el puerto antes de arrancar
- [x] 4.7 Liberar el puerto y terminar de forma ordenada al recibir una interrupción; verificar con un test que detiene el servidor y comprueba que el puerto vuelve a quedar libre
- [x] 4.8 Documentar `--serve` y el archivo de edición en el README, incluyendo que el export estático es de solo lectura y que cada archivo tiene un único escritor; verificar ejecutando los comandos documentados tal como están escritos

## 5. Interacción en la página servida

- [x] 5.1 Renderizar las etiquetas vigentes en los títulos y agregar un control por tarjeta para cambiar la etiqueta; verificar con un test que el HTML servido contiene el título con la etiqueta y el control de edición
- [x] 5.2 Enviar la edición al endpoint y refrescar el título en la página sin recargarla; verificar con un test del flujo de guardado completo
- [x] 5.3 Ofrecer quitar la etiqueta como una acción separada, distinta de vaciar el campo, que elimina la entrada del archivo y devuelve el título al derivado; verificar con un test que la entrada desaparece del archivo y que el título vuelve al derivado
- [x] 5.4 Impedir en el cliente el envío de una etiqueta vacía; verificar con un test que ante un campo vacío no se emite ninguna petición al servidor

## 6. Verificación integral

- [x] 6.1 Ejecutar la suite completa de pruebas y `openspec validate --strict`; verificar que la suite termina en verde y que la validación del cambio no reporta errores
- [x] 6.2 Recorrer el flujo completo contra el índice real: arrancar el servidor, etiquetar un viaje cuyo título actual sea el país, confirmar que la etiqueta sobrevive a un rescaneo posterior y que aparece el aviso de deriva; verificar dejando registrada la salida de cada paso
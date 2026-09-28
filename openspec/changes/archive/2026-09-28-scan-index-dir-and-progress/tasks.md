# Tasks

## 1. Carpeta de destino del índice

- [x] 1.1 Agregar a `index.py` la función `index_path_for(root, index_dir=None)` que
      devuelve la misma ruta que hoy cuando `index_dir` es `None`, y que usa `index_dir`
      como carpeta padre cuando viene informado; verificar con un test que sin destino
      sigue yendo al directorio de estado y que el nombre del archivo no cambia
- [x] 1.2 Verificar con un test que dos carpetas de fotos distintas escaneadas con el mismo
      destino producen dos archivos distintos, y que ninguno sobrescribe al otro
- [x] 1.3 Verificar con un test que un destino que no existe se crea y queda con el índice
      adentro
- [x] 1.4 Agregar `--index-dir` a la CLI, resuelto antes que `--index-dir` por defecto, y
      verificar con un test que el índice se escribe en la carpeta indicada
- [x] 1.5 Verificar con un test que, pasando `--index` y `--index-dir` juntos, gana
      `--index` y no se crea ningún archivo en el destino
- [x] 1.6 Actualizar el README con la opción `--index-dir`, su prioridad frente a
      `--index` y un ejemplo; verificar que lo documentado coincide con la salida real del
      comando

## 2. Informe de progreso

- [x] 2.1 Agregar a `scanner.scan()` un parámetro `progress` opcional que reciba
      `(procesadas, total)` y que nunca propague una excepción de la callback; verificar
      con un test que una callback que lanza no aborta el escaneo
- [x] 2.2 Contar los candidatos por extensión antes de procesar, sin leer los archivos,
      y pasar ese total a la callback; verificar con un test que el total coincide con la
      cantidad de fotos registradas y que no incluye archivos que no son fotos
- [x] 2.3 Implementar el formateo de la línea de progreso (procesadas, total, porcentaje,
      velocidad y tiempo restante) con salto de carriage return y refresco cada 25 fotos o
      0,5 s; verificar con un test unitario del formateo con valores conocidos, incluido el
      caso de tiempo restante todavía no disponible
- [x] 2.4 Emitir el progreso desde la CLI solo cuando `stdout` es un terminal, y
      desactivarlo con `FOTOS_PLUS_NO_PROGRESS=1`; verificar con un test que con la salida
      capturada no aparece ninguna línea de progreso y que el resumen final sí aparece
- [x] 2.5 Verificar con un test que al terminar se emite una línea de progreso completa y
      luego el resumen, sin dejar la línea a medias
- [x] 2.6 Verificar con un test que una carpeta sin fotos no emite progreso y termina con
      el mensaje de que no se encontraron fotos
- [x] 2.7 Documentar en el README el formato del progreso, que se omite al redirigir la
      salida y cómo desactivarlo; verificar contra la salida real

## 3. Lanzador `fotos-plus.bat`

- [x] 3.1 Agregar una prueba que ejecute el lanzador con `subprocess` sobre una carpeta
      temporal, sin subcomando y con `scan` explícito, y verifique que ambas formas
      escriben el mismo índice; saltar la prueba si `cmd.exe` no está disponible
- [x] 3.2 Verificar con la misma prueba que el lanzador propaga los códigos de salida 0, 1
      y 2 del comando
- [x] 3.3 Documentar `fotos-plus.bat` en el README: para qué sirve, que asume `scan` si no
      se pasa subcomando y que sirve cuando el directorio de scripts de Python no está
      en el PATH

## 4. Verificación final

- [x] 4.1 Correr `python -m pytest` completo y verificar que pasan todas las pruebas,
      incluidas las de los cambios anteriores
- [x] 4.2 Escanear una carpeta real grande y verificar que el progreso aparece, que el
      porcentaje llega al 100% y que el índice escrito coincide con el resumen

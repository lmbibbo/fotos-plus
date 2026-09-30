# Tasks

## 1. Generacion de miniaturas

- [x] 1.1 Anadir en `fotos_plus/photos.py` una funcion que genere una miniatura de una foto a
      partir de una ruta, aplicando la transformacion de orientacion EXIF antes de reducir, y
      devolviendo los bytes JPEG. Debe usar el tamano de salida acordado (200 px) y una calidad
      fija, y no debe depender de la ruta del indice.
- [x] 1.2 Cubrir con tests la generacion de miniaturas: una foto apaisada, una vertical con
      marca de orientacion EXIF que produce una miniatura vertical, y una foto ilegible que
      informa el error sin propagarlo como fallo del escaneo completo.

## 2. Cruce del indice con las sugerencias

- [x] 2.1 Anadir en `fotos_plus/viewer.py` la carga del indice y del archivo de sugerencias
      contiguo, reutilizando `suggestions_path_next_to` de `fotos_plus/index.py` para derivar la
      ruta. Debe distinguir el caso en que el archivo de sugerencias no existe.
- [x] 2.2 Implementar la asignacion de cada foto a un grupo: primero al viaje cuyo intervalo
      `first_captured_at..last_captured_at` la contiene, despues al periodo que la contiene, y
      si no cae en ninguno, al grupo de fotos sin clasificar. Cargar el indice una sola vez
      ordenado por `captured_at` y recorrerlo linealmente.
- [x] 2.3 Cubrir con tests el cruce: una foto dentro de un viaje, una foto dentro de un periodo,
      una foto que no cae en ninguno, y una foto cuya fecha cae en el borde de un intervalo.
      Verificar que ninguna foto escaneada queda fuera de todo grupo.

## 3. Composicion del HTML

- [x] 3.1 Implementar la composicion del documento: una tarjeta por grupo con la cantidad de
      fotos, el rango de fechas, el pais cuando exista, y cinco miniaturas. Los periodos se
      muestran sin pais. Las tarjetas se ordenan de forma ascendente por la fecha mas temprana.
- [x] 3.2 Implementar el caso sin archivo de sugerencias: el mismo documento con todas las fotos
      en una grilla plana, sin agrupar. El comando no debe fallar por la ausencia del archivo.
- [x] 3.3 Embeber las miniaturas en base64 dentro del documento e incluir los datos de las
      sugerencias en un bloque `script`, de modo que el HTML no dependa de `fetch` ni de un
      servidor. Verificar que abrir el archivo sin conexion muestra el contenido.
- [x] 3.4 Si un grupo tiene menos de cinco fotos, mostrar todas las que tiene. Si una miniatura
      falla al generarse, pasar a la siguiente foto del grupo sin abortar el comando; una tarjeta
      puede quedar con menos de cinco miniaturas.
- [x] 3.5 Cubrir con tests la composicion: verificar que el HTML contiene una tarjeta por cada
      grupo esperado, que las tarjetas estan en orden ascendente, que los periodos no muestran
      pais, y que el HTML generado no contiene una referencia a un servidor.

## 4. Subcomando view

- [x] 4.1 Registrar el subcomando `view` en `fotos_plus/cli.py` con su ruta de indice como
      argumento, siguiendo el estilo de los subparsers existentes, e informar la ruta del HTML
      generado por stdout.
- [x] 4.2 Conectar el subcomando con la composicion del HTML y escribir el archivo junto al
      indice de entrada, con un nombre derivado del nombre del indice.
- [x] 4.3 Verificar end-to-end sobre una coleccion de prueba: `view` genera un HTML valido, el
      indice y el archivo de sugerencias quedan sin modificar, y abrir el HTML muestra una
      tarjeta por viaje, una por periodo y una por las fotos sin clasificar.
- [x] 4.4 Verificar el camino sin sugerencias: `view` sobre un indice sin archivo de
      sugerencias contiguo genera el grid plano y no informa error.

## 5. Cierre

- [x] 5.1 Correr la suite completa y el escaneo end-to-end sobre una coleccion de prueba.
- [x] 5.2 Actualizar el README para describir el subcomando `view`, el hecho de que el HTML es
      local y no requiere servidor, y que el archivo generado es especifico de la carpeta de
      fotos donde se creo.
- [x] 5.3 Anotar en el README que la pantalla completa, la navegacion con teclado y el zoom
      quedan fuera de esta etapa, para una etapa posterior.

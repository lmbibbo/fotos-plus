# Tasks

## 1. Preflight

- [x] 1.1 Confirmar que la extracción de coordenadas no existe todavía y que este cambio la implementa por completo. Verificar con `grep -n "latitude" fotos_plus/photos.py fotos_plus/models.py` que no hay resultados.
- [x] 1.2 Crear la rama `feature/emit-trips-and-periods` desde `main` actualizado. Verificar con `git branch --show-current` que la rama activa es la nueva y que `main` no tiene commits directos nuevos.

## 2. Coordenadas en el escaneo

- [x] 2.1 Agregar `latitude` y `longitude` como campos opcionales a `Photo`, incluidos en `to_dict` y leídos con `data.get()` en `from_dict`. Verificar con un test que un índice viejo sin esos campos se sigue leyendo y que `latitude` queda en `None`.
- [x] 2.2 Implementar en `photos.py` la lectura del IFD de GPS (`0x8825`: `0x0001` lat ref, `0x0002` lat, `0x0003` lon ref, `0x0004` lon) y la conversión de grados, minutos y segundos a grados decimales aplicando el hemisferio. Verificar con un test que una foto con GPS conocido produce la coordenada esperada.
- [x] 2.3 Implementar la regla de validez: devolver `None` cuando falta el bloque de posición, cuando el bloque está vacío, o cuando ambos ejes son cero. Verificar con un test por cada uno de los tres casos, incluido el caso `(0, 0)`.
- [x] 2.4 Verificar que la extracción de coordenadas no agrega una tercera apertura del archivo y que el escaneo completo sigue informando progreso. Verificar con el test de conteo de aperturas existente en `tests/test_photos.py` y ejecutando la suite completa.

## 3. Geometría y construcción de sugerencias y períodos

- [x] 3.1 Implementar la distancia entre dos coordenadas por la fórmula de haversine, en kilómetros. Verificar con un test que dos puntos conocidos a una distancia conocida dan el valor esperado con tolerancia de 1%.
- [x] 3.2 Implementar la partición en sugerencias de viaje: ordenar las fotos con posición válida por `captured_at` e iniciar una sugerencia nueva cuando la distancia a la anterior sea de 200 km o más. Verificar con un test de dos fotos en el mismo lugar, uno de dos lugares alejados y uno de una estancia larga en un mismo lugar.
- [x] 3.3 Implementar la construcción de períodos: agrupar por día las fotos sin posición válida y unir días consecutivos mientras el hueco sea de 1 día vacío o menos. Verificar con un test de días consecutivos, uno de dos tramos separados por un intervalo sin fotos, y uno de que los períodos no se fusionan en uno solo.
- [x] 3.4 Marcar como ubicables por referencia las fotos sin posición que comparten día con al menos una foto con posición válida, y excluirlas de los períodos. Verificar con un test que esas fotos no aparecen en ningún período y que sí aparecen en el conteo de ubicables por referencia.
- [x] 3.5 Calcular por cada sugerencia y por cada período la cantidad de fotos, la primera y la última fecha, y por separado el estado de la ubicación, que indica si se conoce o no. Verificar con un test que un grupo con coordenadas y un grupo sin ellas exponen ese estado, y que el estado de un período nunca dice que su ubicación se conoce.

## 4. Archivo de sugerencias

- [x] 4.1 Agregar los tipos de sugerencia, período y resultado con su `to_dict` y `from_dict`, y una versión de formato propia. Verificar con un test de ida y vuelta que el resultado sobrevive a `to_dict` seguido de `from_dict` sin perder campos.
- [x] 4.2 Agregar en `index.py` el helper que deriva la ruta del archivo de sugerencias a partir de la misma carpeta raíz y el mismo destino que el índice, con un sufijo que incluya la palabra "sugerencias", y escribirlo con la misma atomicidad de `write_index`. Verificar con un test que el nombre resultante contiene "sugerencias" y que dos carpetas distintas escaneadas al mismo destino no se pisan, y que `--index` explícito deja los dos archivos juntos.
- [x] 4.3 Agregar al contenido del archivo la marca de que es provisional, y verificar que un consumidor que solo lee el archivo puede distinguir que su contenido son sugerencias. Verificar con un test que el campo está presente después de `to_dict` y sobrevive a `from_dict`.
- [x] 4.4 Verificar que el patrón `/[0-9a-f]*.json` del `.gitignore` ya cubre el archivo de sugerencias y que sigue cubriendo el índice de inventario, sin agregar patrones redundantes. Verificar con `git check-ignore -v` sobre los dos nombres de archivo.
- [x] 4.5 Invocar la construcción desde el escaneo después de escribir el inventario, y agregar al resumen de la CLI la ruta del archivo de sugerencias y los conteos de sugerencias, períodos y fotos por auditar, usando la palabra "sugerencias" y no "viajes". Verificar con un test de CLI que el resumen informa los tres conteos, la ruta, y que ninguna línea presenta las sugerencias como viajes confirmados.

## 5. Robustez y cierre

- [x] 5.1 Verificar que un fallo en la construcción de sugerencias no impide escribir el inventario: forzar el fallo en un test y comprobar que el índice queda escrito, que el comando informa que el archivo de sugerencias no se generó y que el escaneo no aborta. Verificar con el test del caso "Fallo al calcular las sugerencias".
- [x] 5.2 Verificar el comportamiento con una colección sin ninguna posición válida y con una colección sin ninguna foto, en ambos casos sin excepción y con el archivo escrito igual. Verificar con un test por cada colección vacía de posiciones y de fotos.
- [x] 5.3 Correr la suite completa y el escaneo real sobre la colección de 4805 fotos, y contrastar contra la medición de referencia: 3731 fotos con posición, 1074 sin posición, 155 ubicables por referencia, 919 en períodos y 45 sugerencias de viaje. Verificar que los números coinciden o anotar la desviación en el mensaje de commit.
- [x] 5.4 Documentar en el README el archivo de sugerencias, la convención de nombre, la regla de validez de la coordenada, el significado de los períodos y de "ubicable por referencia", y dejar explícito que el archivo contiene sugerencias y no viajes confirmados, y que se reescribe en cada escaneo. Verificar que los comandos del README se ejecutan tal como están escritos.
- [x] 5.5 Revisar que ningún punto de la documentación, del resumen de la CLI ni del nombre del archivo presenta las sugerencias como viajes o períodos definitivos. Verificar con una revisión del README, de la salida de la CLI y del nombre del archivo en disco.
- [x] 5.6 Confirmar que el cambio anterior `group-photos-by-trip` fue descartado: que su carpeta no existe, que no hay spec `photo-grouping` en el repositorio, y que este cambio no arrastra su módulo de agrupado. Dejar constancia en el mensaje de commit de que sus decisiones quedaron reemplazadas. Verificar con `openspec list` y revisando la rama.

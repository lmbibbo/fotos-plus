# Proposal

## Why

El escaneo funciona pero es incómodo de usar en la práctica. La carpeta donde se guarda
el índice no se puede elegir, así que cada biblioteca queda escondida en un directorio de
estado del sistema que hay que adivinar; y sobre una biblioteca real de 4.927 fotos
(32 GB) el comando pasa varios minutos sin escribir nada, con lo que parece un cuelgue.
Ambos son problemas de uso de la etapa inicial, y conviene cerrarlos ahora que el cambio
anterior ya está archivado y el spec de `photo-scanning` existe como base.

## What Changes

- Nueva opción `--index-dir <carpeta>` en `scan`: todos los índices se escriben en esa
  carpeta, un archivo por carpeta escaneada, con el mismo nombre derivado de la ruta que
  ya se usa hoy. Si no se indica, sigue el directorio de estado del usuario.
- `--index` se conserva para escribir un índice en un archivo puntual, y tiene prioridad
  sobre `--index-dir` cuando se pasan los dos.
- El escaneo informa el progreso en la consola: fotos procesadas, total, porcentaje,
  velocidad y tiempo estimado restante, en una línea que se sobrescribe.
- El progreso se omite cuando la salida no es un terminal (por ejemplo al redirigir a un
  archivo), para no ensuciar el log.
- Se documenta `fotos-plus.bat` en el README y se cubre con una prueba, sin cambiar su
  comportamiento: si el primer argumento no es un subcomando, se asume `scan`.
- La carpeta de destino se crea si no existe.

## Capabilities

### Modified Capabilities

- `photo-scanning`: cambia el requisito `Índice local del inventario`, que pasa a admitir
  una carpeta de destino elegida por el usuario, y agrega el requisito `Informe de
  progreso` del escaneo.

## Rollback plan

- Los cambios son de la línea de comandos y de la salida por consola: no tocan el
  formato del índice, así que un índice escrito antes se sigue leyendo igual.
- Revertir la rama deja el comportamiento anterior. Si quedó un índice escrito en la
  carpeta elegida, se borra a mano: es un archivo más, sin nada que dependa de él.
- La carpeta de destino que se haya creado queda vacía y se puede eliminar.

## Impact

- `fotos_plus/index.py`: resolución de la ruta del índice a partir de una carpeta destino.
- `fotos_plus/scanner.py`: callbacks de progreso y total de candidatos, para poder dar
  porcentaje y velocidad sin recorrer dos veces.
- `fotos_plus/cli.py`: opciones `--index-dir` y el formateo del progreso.
- `fotos-plus.bat`: sin cambios de comportamiento, solo pruebas y documentación.
- Sin dependencias nuevas y sin cambios en la base de datos.
- Pruebas nuevas para el destino del índice, el progreso y el lanzador.

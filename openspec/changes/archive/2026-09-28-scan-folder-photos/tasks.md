# Tasks

## 1. Estructura del proyecto

- [x] 1.1 Crear la rama `feature/scan-folder-photos` y verificar que sale de `main` con `git branch --show-current` y verificar que sale de `main` con `git branch --show-current`
- [x] 1.2 Crear `pyproject.toml` con setuptools, metadatos del proyecto, dependencia de Pillow, `requires-python` y pytest como dependencia de desarrollo; verificar que `pip install -e ".[dev]"` completa sin errores
- [x] 1.3 Crear el paquete `fotos_plus/` con `__init__.py`, `models.py`, `photos.py`, `scanner.py`, `index.py` y `cli.py`, más `__main__.py`; verificar que `python -c "import fotos_plus.cli"` no falla
- [x] 1.4 Declarar el entry point de consola `fotos-plus` y verificar que `fotos-plus --help` responde
- [x] 1.5 Agregar a `.gitignore` el directorio de índices por defecto y `*.json` de índice de pruebas; verificar con `git check-ignore` que ambos quedan ignorados
- [x] 1.6 Agregar a `README.md` la sección de uso con el ejemplo `fotos-plus scan <carpeta>` y verificar que el comando documentado es el mismo que expone `--help`

## 2. Identificación y metadatos de una foto

- [x] 2.1 Definir en `photos.py` la lista de extensiones y formatos admitidos, separando los que se leen por completo de los que solo se aceptan por extensión; verificar con un test que un `.pdf` y un `.txt` no se aceptan y que un `.heic` sí
- [x] 2.2 Implementar el hash SHA-256 por bloques de 1 MiB; verificar con un test que dos archivos con el mismo contenido dan el mismo hash y que un archivo grande se hashea sin cargarlo entero en memoria
- [x] 2.3 Implementar la lectura de `DateTimeOriginal` y, como respaldo, `DateTime`, devolviendo fecha vacía cuando no hay ninguna; verificar con tests una foto con `DateTimeOriginal`, una con solo `DateTime` y una sin EXIF
- [x] 2.4 Implementar `identify()` con `Image.verify()` y manejo de los formatos que Pillow no decodifica; verificar con un test que un archivo con extensión de foto y contenido basura devuelve error en lugar de una foto
- [x] 2.5 Definir la dataclass `Photo` con ruta relativa, nombre, extensión, tamaño, hash, fecha y origen de la fecha; verificar con un test que una foto sin EXIF queda con la fecha vacía y no con la hora de modificación

## 3. Recorrido de la carpeta

- [x] 3.1 Implementar el recorrido recursivo con `os.scandir`, sin seguir enlaces simbólicos de directorio; verificar con un test que encuentra fotos en subdirectorios a distintos niveles
- [x] 3.2 Calcular la ruta relativa de cada foto respecto de la raíz escaneada; verificar con un test que la ruta relativa coincide con la posición del archivo dentro del árbol
- [x] 3.3 Acumular los errores por archivo y continuar el recorrido; verificar con un test que una foto corrupta y un directorio sin permiso aparecen en los errores y que el resto de las fotos se registra
- [x] 3.4 Ordenar las fotos por ruta relativa para que el resultado sea determinista; verificar con un test que dos escaneos de la misma carpeta dan la misma lista en el mismo orden
- [x] 3.5 Calcular los grupos de duplicados por hash, eligiendo por ruta relativa más corta la original; verificar con un test que dos copias idénticas quedan una original y un `duplicate_of` que la apunta

## 4. Índice local

- [x] 4.1 Implementar la escritura atómica del índice (archivo temporal en el mismo directorio más `os.replace`); verificar con un test que queda un solo archivo de índice y que no queda el temporal
- [x] 4.2 Serializar el índice con `version`, `root`, `scanned_at`, `photos` y `errors`; verificar con un test de ida y vuelta que el índice escrito se vuelve a leer con los mismos valores
- [x] 4.3 Resolver la ruta por defecto del índice a partir de un hash de la ruta absoluta de la raíz, usando el directorio de estado del usuario; verificar con un test que la misma carpeta da siempre la misma ruta y que `--index` la reemplaza
- [x] 4.4 Reemplazar el índice previo de la misma carpeta en lugar de acumular índices; verificar con un test que tras un rescaneo existe un único índice vigente con las fotos actuales

## 5. Línea de comandos

- [x] 5.1 Implementar el subcomando `scan` con la ruta obligatoria y la opción `--index`; verificar con un test que `fotos-plus scan <carpeta>` termina con código 0 y escribe el índice
- [x] 5.2 Devolver código 2 con un mensaje claro cuando la ruta no existe o no se puede leer, y código 1 con los argumentos inválidos; verificar con un test para cada código
- [x] 5.3 Mostrar al final un resumen con cantidad de fotos encontradas, duplicadas y archivos con error; verificar con un test que el resumen coincide con el índice escrito
- [x] 5.4 Verificar de punta a punta que el escaneo no altera la carpeta: comparar listado, tamaños y contenidos antes y después de dos escaneos en una carpeta de prueba

## 6. Documentación

- [x] 6.1 Documentar en `README.md` los formatos admitidos, qué se registra por foto, dónde queda el índice y cómo se consulta; verificar que lo documentado coincide con la salida real del comando
- [x] 6.2 Documentar la limitación de HEIC y los RAW sin lectura completa de EXIF, y cómo se comporta el escaneo cuando falla la identificación de un archivo; verificar contra el comportamiento implementado

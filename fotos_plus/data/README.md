# Datos de países

`countries.geojson` es el conjunto de polígonos que usa `fotos_plus.places` para
clasificar una coordenada en un país. Viaja con el paquete para que la clasificación
funcione sin conexión.

- **Fuente:** Natural Earth, `ne_10m_admin_0_countries` (1:10m admin 0 countries).
- **Licencia:** dominio público. Natural Earth publica sus datos como dominio público;
  no requiere atribución, pero se cita igual por transparencia.
- **Lic downloads:** <https://www.naturalearthdata.com/downloads/10m-cultural-vectors/>
- **Versión del conjunto:** `version` en la raíz del GeoJSON.
- **Derivado:** las coordenadas se redondean a 4 decimales (~11 m) y se conservan solo
  `name` y `code` (`ADM0_A3`) por feature. Los anillos degenerados se descartan.

## Por qué 1:10m y no una escala menor

Medido sobre los polígonos de este repositorio, contra un conjunto de coordenadas de
referencia de los tests (`tests/test_places.py`), que cubre siete países:

| escala | tamaño | aciertos | falla en |
| --- | --- | --- | --- |
| 1:110m | 819 KB | 26/30 | ciudades costeras del Atlántico |
| 1:50m | 3.0 MB | 26/30 | Punta del Este y una frontera terrestre |
| 1:10m | 13.0 MB | 30/30 | (ninguna) |

Las escalas 1:110m y 1:50m cortan la costa y, en 1:50m, desplazan una frontera terrestre
cerca de una ciudad fronteriza. Ambas fallan en el mismo tipo de caso: ciudades costeras y
fronteras. Sobre la colección de prueba del repositorio, 1:10m clasifica la gran mayoría de
las coordenadas con posición; las restantes caen en agua.

## Cómo regenerarlo

1. Descargar `ne_10m_admin_0_countries.geojson` de Natural Earth.
2. Redondear a 4 decimales, quedarse con `NAME_EN` y `ADM0_A3`, descartar anillos
   degenerados y dejar solo `name` y `code` por feature.
3. Verificar contra las coordenadas de referencia de `tests/test_places.py` antes de
   reemplazar este archivo.

Al cambiar el conjunto hay que subir `version` en la raíz del GeoJSON: ese valor se escribe
en el archivo de sugerencias para que un consumidor pueda distinguir dos escaneos hechos
con conjuntos distintos.

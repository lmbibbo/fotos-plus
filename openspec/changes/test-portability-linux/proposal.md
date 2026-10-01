# Proposal

## Why

El workflow de CI (`archive-merge`, mergeado en `304be8c`) corre la suite de
tests en Linux. La suite pasa en Windows pero falla en Linux con 2 errores, lo
que impide activar `verify` como required status check en `main`: con tests
rojos, ningun PR se podria mergear.

Ninguno de los dos fallos es un bug del codigo. Ambos tests asumen
comportamiento de Windows, mientras que el codigo bajo prueba ya es
consciente de la plataforma.

## What Changes

- `tests/test_cli.py::test_default_index_path_is_used_when_not_given`: el test
  setea `LOCALAPPDATA`, que el codigo solo lee en `win32`. En POSIX usa
  `XDG_STATE_HOME`.
- `tests/test_index.py::test_default_index_path_follows_case_insensitive_paths`:
  espera que `Fotos` y `fotos` hashtreen igual, apoyandose en
  `os.path.normcase()`, que es identidad en POSIX.

No hay cambios en codigo de produccion. `fotos_plus/index.py` ya branchinga
correctamente (`index.py:18-21` para la base del estado, `index.py:30` para el
hash de la carpeta raiz).

No hay cambios rompientes: en Windows los tests siguen ejecutandose igual.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

Ninguna.

Opt-out de specs: `.openspec.yaml` declara `skip_specs: true`. El codigo de
produccion no cambia de comportamiento; lo que cambia es que la suite se
ejecute tambien fuera de Windows. Ninguna de las cuatro specs actuales
(`group-labels`, `photo-scanning`, `photo-viewing`, `trip-periods`) describe
requisitos sobre la portabilidad de los tests, y forzar una seria inventar un
requisito para satisfacer la validacion.

## Impact

- Modificado: `tests/test_cli.py`, `tests/test_index.py`.
- Sin cambios en `fotos_plus/`, sin dependencias nuevas.
- Desbloquea la task 3.2 del change `add-archive-pr-automation`
  (branch protection con el check `verify`).
- El PR #5 (`test/archive-merge-smoke`) queda abierto como fixture del fallo y
  puede reutilizarse para el smoke test definitivo.

## Rollback

- Revertir el commit de los dos tests restaura el comportamiento anterior:
  la suite vuelve a fallar en Linux y `verify` no se puede activar. No afecta al
  codigo de produccion ni a los resultados en Windows.

## Nota de alcance

La suite muestra `260 passed, 1 skipped` en Windows y `244 passed, 15 skipped`
en Linux. Los 15 skips de Linux son correctos y explicados
(`tests/test_bat.py` necesita `cmd.exe`, `tests/test_scanner.py` necesita
permisos POSIX). Este change solo atiende los 2 fallos, no los skips.
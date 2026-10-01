# Tasks

## 1. Arreglar la base del estado en test_cli

- [x] 1.1 En `tests/test_cli.py::test_default_index_path_is_used_when_not_given`, setear tambien `XDG_STATE_HOME` ademas de `LOCALAPPDATA`, apuntando ambos al mismo `tmp_path / "estado"`. El test debe seguir siendo valido en Windows sin cambios
      Verificar: en Windows, `python -m pytest tests/test_cli.py -q` mantiene el mismo resultado que antes del cambio
- [x] 1.2 Calcular la ruta esperada del indice segun plataforma en vez de hardcodear `state / "fotos-plus" / "indexes"`, para que apunte a la base que el codigo efectivamente usa
      Verificar: `python -m pytest tests/test_cli.py -q` en verde en Windows

## 2. Marcar el test de case-insensitivity como Windows-only

- [x] 2.1 En `tests/test_index.py::test_default_index_path_follows_case_insensitive_paths`, agregar `@pytest.mark.skipif(os.name != "nt", reason=...)` siguiendo el patron de `tests/test_scanner.py:86`. Confirmar que `os` ya esta importado en el archivo
      Verificar: en Windows, el test se ejecuta y pasa; el conteo de skips en Windows no cambia
- [x] 2.2 Documentar en el `reason` por que POSIX se salta: `os.path.normcase` es identidad fuera de `win32`, asi que "Fotos" y "fotos" son carpetas legitimately distintas
      Verificar: el `reason` menciona `normcase` y la condicion es `os.name != "nt"`

## 3. Verificacion

- [x] 3.1 Ejecutar la suite completa en Windows: `python -m pytest -q`
      Verificar: `260 passed, 1 skipped` (el conteo no debe cambiar respecto al estado previo, porque en Windows los dos tests ya pasaban)
      Resultado: `260 passed, 1 skipped in 43.42s`. Conteo identico al previo; los dos tests siguen ejecutandose en Windows.
- [ ] 3.2 Commitar en `feature/test-portability-linux` y abrir PR a `main` **sin** la etiqueta `archive`, para que `verify` corra y confirme que la suite pasa en Linux
      Verificar: el PR queda abierto y GitHub muestra el check `verify` en verde
- [ ] 3.3 Confirmado el `verify` en verde, aplicar la etiqueta `archive` al PR para que el workflow lo mergee con squash y borre la rama
      Verificar: el PR figura MERGED, la rama remota `feature/test-portability-linux` ya no existe, y el commit aparece en `main`

## 4. Cierre del ciclo de CI

- [ ] 4.1 Volver al change archivado `2026-10-01-add-archive-pr-automation` y cerrar la task 3.2 activando branch protection en `main` con el check `verify` como required status check
      Verificar: `gh api repos/lmbibbo/fotos-plus/branches/main/protection --jq '.required_status_checks.contexts'` incluye `"verify"`
- [ ] 4.2 Cerrar la task 5.1 reutilizando el PR #5 (`test/archive-merge-smoke`) o creanduno nuevo, segun el estado del PR #5 al momento de ejecutar
      Verificar: existe un PR mergeado automaticamente por el job `merge`, con rama eliminada y commit squash en `main`
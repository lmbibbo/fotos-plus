# Tasks

## 1. Corregir config.yaml (parseo + guidance)

- [x] 1.1 Fix línea 36: usar escalar con comillas para evitar el carácter reservado ` 
      Verificar: abrir config.yaml y comprobar que `npx --yes openspec list --json` NO emite el warning "could not parse" tras el fix
- [x] 1.2 Corregir línea 35 del guidance: cambiar `openspec validate --strict` a `openspec validate --specs --strict`
      Verificar: revisar config.yaml, línea 35 muestra el comando corregido
- [x] 1.3 Limpiar comentarios colgantes o trailing spaces innecesarios en `operations.archive.guidance` (sin modificar el contenido)
      Verificar: YAML parsea correctamente con `python -c "import yaml; yaml.safe_load(open('openspec/config.yaml'))"`

## 2. Crear workflow de CI para verificar y hacer merge con etiqueta

- [x] 2.1 Crear directorio `.github/workflows/` si no existe. Crear `archive-merge.yml` con trigger `pull_request: types: [labeled]`, permisos mínimos (`contents: write`, `pull-requests: write`), job `verify` y job `merge` con `needs: verify` y condición `github.event.label.name == 'archive'`. Usar `runs-on: ubuntu-latest` y `actions/setup-node@v4` con Node 22
      Verificar: el archivo existe en `.github/workflows/archive-merge.yml`
- [x] 2.2 En job `verify`: pasos `checkout` (con fetch-depth completo si necesario), `setup-node`, ejecutar `python -m pytest -q` y `npx --yes openspec validate --all --strict`. El job debe fallar si cualquiera de los dos comandos falla
      Verificar: ejecución simulada o lectura del workflow confirma ambos comandos existen y son obligatorios
- [x] 2.3 En job `merge`: ejecutar `gh pr merge ${{ github.event.pull_request.number }} --squash --delete-branch` usando `env: GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}`. No usar `--auto`
      Verificar: el comando `gh pr merge` aparece con número de PR y flags correctos

## 3. Documentar gating en branch protection (fuera del repo)

- [x] 3.1 Verificar existencia del check `verify` mediante un run de prueba (push del workflow a una rama feature y abrir PR con etiqueta `archive`). Confirmar que aparece el status check con nombre exacto `verify`
      Verificar: en el PR de prueba, GitHub muestra el check `verify` (passed/failed) y es el job name
      Resultado: PR #5 (test/archive-merge-smoke). El check aparece con el nombre exacto `verify`. Falló con exit 1 por 2 tests no portables (tests/test_cli.py::test_default_index_path_is_used_when_not_given, tests/test_index.py::test_default_index_path_follows_case_insensitive_paths). El gate funciono: verify fallo y merge no corrio.
- [ ] 3.2 Activar branch protection en `main` requiriendo el status check `verify` (required status checks). No exigir approvals si se mantiene la política sin revisión previa; documentar el cambio en el PR
      Verificar: `gh api repos/lmbibbo/fotos-plus/branches/main/protection --jq '.required_status_checks.contexts'` incluye `"verify"` tras la activación
      BLOQUEADO: no activar hasta que el suite pase en Linux. Con tests rojos, el required check dejaria `main` sin poder mergear. Depende del change de portabilidad de tests.

## 4. Integración con el flujo de archive (operativo)

- [x] 4.1 Confirmar que al archivar este change se ejecutará `openspec archive --skip-specs` (por `skip_specs: true` en `.openspec.yaml`). Verificar `npx --yes openspec instructions archive --change add-archive-pr-automation --json 2>&1 | Select-String skip_specs` o simplemente leer `.openspec.yaml`
      Verificar: `.openspec.yaml` contiene `skip_specs: true`
- [x] 4.2 Actualizar `README.md` con una breve nota sobre el nuevo flujo: PR con etiqueta `archive` → CI verifica → merge automático a `main` (solo squash). No detallar secretos
      Verificar: `README.md` contiene una mención del flujo (sin incluir credenciales)

## 5. Verificación end-to-end (smoke)

- [ ] 5.1 Crear PR de prueba (rama temporal) que ejecute el workflow: aplicar etiqueta `archive` y comprobar que `verify` pasa y que el PR se mergea a `main` con `--squash`. Borrar la rama temporal tras la prueba
      Verificar: el PR fue mergeado, la rama feature fue borrada y el commit aparece en `main` con mensaje squash
      BLOQUEADO: el PR #5 sigue abierto a proposito (fallo de verify). Rehacer el smoke cuando el suite pase en Linux.
- [x] 5.2 Revertir o dejar branch protection activo y validar que un PR sin etiqueta `archive` NO dispara el job `merge` (aunque `verify` pueda correr si se configura; en este diseño `merge` depende de la etiqueta)
      Verificar: en un PR sin etiqueta, el job `merge` se salta (`if: github.event.label.name == 'archive'`) y no hay intento de merge
      Resultado: verificado de forma implicita. El PR #4 se creo sin etiqueta y no genero ninguna ejecucion (`no checks reported`); el workflow disparo unicamente al aplicar `archive` en el PR #5. La rama test/archive-merge-smoke se conserva como fixture del caso fallido.

## 6. Cierre del change

- [x] 6.1 Ejecutar `npx --yes openspec validate --all --strict` (aunque skip_specs, útil para detectar otros problemas) y verificar que pasa
      Verificar: `npx --yes openspec validate --all --strict 2>&1` no reporta errores
- [x] 6.2 Ejecutar `python -m pytest -q` y confirmar 260 passed, 1 skipped (estado actual)
      Verificar: resultado coincide con 260 passed, 1 skipped
- [x] 6.3 Archivar el change con `openspec archive --skip-specs -y` (sobre la rama feature correspondiente). Commitear el resultado junto al resto en la rama del PR
      Verificar: el change aparece movido a `openspec/changes/archive/...` y los specs no fueron modificados (skip_specs)
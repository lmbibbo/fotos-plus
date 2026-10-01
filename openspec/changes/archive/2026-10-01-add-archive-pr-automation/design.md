# Design

## Context

Estado verificado del repositorio (2026-10-01):

| Dato | Valor |
|---|---|
| Hosting | GitHub, `lmbibbo/fotos-plus` |
| Visibilidad | `public` |
| Rama por defecto | `main` |
| Branch protection en `main` | ninguna (404) |
| Rulesets | ninguno |
| Workflows | ninguno (`.github/` no existe) |
| `gh` local | instalado, scopes `repo` + `workflow` |
| Merge commit / squash / rebase | los tres habilitados |

Ciclo de vida objetivo de un change, segun el guidance de
`openspec/config.yaml`:

```
feature/<nombre>  ->  openspec archive  ->  commit  ->  push  ->  PR a main
```

Los pasos de `archive` ya funcionan y estan verificados (260 tests en verde,
`validate --specs --strict` con 4 specs OK). Lo que falta es la parte de
GitHub: el PR se abre a mano y no hay nada que verifique ni que mergee.

Detalle relevante: `openspec/config.yaml` no parsea, asi que el propio guidance
de arriba esta inactivo para OpenSpec. El fix del parseo forma parte de este
change.

## Goals / Non-Goals

**Goals:**

- Un PR con la etiqueta `archive` se mergea solo a `main` si los tests y la
  validacion de specs pasan.
- `main` exige el check de CI, de modo que el auto-merge tenga un gate real.
- Permisos minimos: ningun secreto de PAT, solo `GITHUB_TOKEN`.
- Corregir el parseo de `openspec/config.yaml`.

**Non-Goals:**

- Reemplazar el flujo local de archive. `openspec archive` sigue siendo manual.
- Escribir el PR automaticamente. La creacion del PR sigue siendo del
  desarrollador; este change solo automatiza la verificacion y el merge.
- La reescritura de historia para los commits `0452a83` y `7680c1e`.
- Politica de aprobaciones: no se exige revision humana (ver Decision 6).

## Decisions

### 1. Trigger: etiqueta `archive` sobre `pull_request`

```yaml
on:
  pull_request:
    types: [labeled]
```

Secuencia de un archive completo:

```
  dev                GitHub                     CI
   |                   |                        |
   | feature/<n>       |                        |
   |------------------>|                        |
   |  codigo + tests   |                        |
   |  + archive        |                        |
   |------------------>|                        |
   |                   | PR abierto             |
   |                   |---------> verify: pytest  |
   |                   |           validate --all--strict
   |                   |                        |
   |  aplica etiqueta  |                        |
   |  "archive" ------->|---------> verify: (re-run, verdes)
   |                   |           |
   |                   |           +--> merge: --squash --delete-branch
   |                   |----------> main
```

**Alternativas descartadas:**

- *Auto-merge en todo PR abierto*: mergea trabajo no archivado. Contradice el
  flujo documentado.
- *Trigger `push` a `feature/**`*: dispara por commit, no por PR, y no puede
  distinguir un archive de un push normal.
- *`workflow_dispatch`*: mergea solo a mano, automatiza nada.

### 2. Un solo workflow con dos jobs, no `gh pr merge --auto`

```yaml
jobs:
  verify:            # corre siempre que se toca el PR
  merge:
    needs: verify
    if: github.event.label.name == 'archive'
```

Se prefiere el merge explicito desde el job `merge` sobre
`gh pr merge --auto`, que requiere activar `allow_auto_merge` en el repo y
agrega una capa de cola que no aporta nada cuando el gate ya esta verificado en
el mismo run.

**Alternativa descartada:** `--auto` quedaria como opcion si en el futuro se
quiere mergear sin que CI disponga de permiso de escritura.

### 3. Gate: tests + validacion de specs, ambos obligatorios

```bash
python -m pytest -q
npx --yes openspec validate --all --strict
```

Ambos, no solo tests: el incidente de `label-trip-groups` fue exactamente un
sync manual que duplico requisitos y污染物 `openspec/specs/photo-viewing/`.
`validate --all --strict` lo habria detectado.

Se usa `--all` y no `--specs` porque el workflow debe cubrir tambien changes
activos. La forma a secas (`openspec validate --strict`) no valida nada, como se
verifico en la CLI.

### 4. `setup-node` explicito

`npx --yes openspec` necesita Node en el runner. Los runners de Ubuntu ya lo
traen, pero se declara el step para que el workflow no dependa de la imagen del
runner. Version fijada a 22 LTS.

### 5. Permisos minimos con `GITHUB_TOKEN`

```yaml
permissions:
  contents: write      #Needed para el merge
  pull-requests: write # Needed para leer labels / hacer merge
```

`GITHUB_TOKEN` alcanza porque el merge ocurre dentro del mismo repositorio. No
se requiere PAT ni secret nuevo, lo que evita agregar material sensible al
repo. La nota: workflows disparados por `GITHUB_TOKEN` no disparan otros
workflows, aceptable porque el unico workflow es este.

### 6. Branch protection con el check requerido

Sin esto, Decision 1 y 2 quedan vacias: el merge seria incondicional.

```
main: require status check  "verify"
```

Se documenta como riesgo critico el nombre exacto del check (ver Riesgos).

### 7. Squash

`--squash --delete-branch`. La rama de feature tiene varios commits (codigo,
tests, specs, archive); en `main` queda uno solo, legible. `--delete-branch`
limpia las ramas `feature/*` ya mergeadas, que hoy se acumulan (hay cuatro
remotas sin mergear).

## Risks / Trade-offs

- **[El nombre del check no coincide con lo configurado en branch protection]**
  → Es el footgun clasico: si branch protection pide `verify` y el job se llama
  `verify-and-merge`, ningun PR se mergea nunca y parece que el workflow esta
  roto. El job se llama `verify` exactamente, y el paso de configuracion de
  protection verifica el nombre contra el workflow antes de aplicarlo.

- **[Cualquiera con permiso de push puede aplicar la etiqueta y disparar el
  merge]** → Se acepta explicitamente como trade-off: no se exige revision
  humana. Mitigacion parcial: el gate tecnico (tests + specs) siempre corre.
  Esto debe revisarse si el equipo crece.

- **[La etiqueta se aplica antes del archive]** → El PR se mergea con specs sin
  sincronizar. Mitigacion: `validate --all --strict` corre igual y el estado de
  specs queda explicito en el commit de archive.

- **[`main` es publica y el historial contiene posible data privada]**
  → Fuera del alcance de este change pero con impacto mayor. La reescritura
  deberia tener prioridad sobre esta automatizacion.

- **El workflow corre `npx --yes`, que descarga paquetes en cada ejecucion**
  → Aceptable para el volumen actual. Si molesta, fijar la version de OpenSpec
  en `package.json` y usar `npm ci`.

## Migration Plan

1. Merge del PR de `label-trip-groups` primero (ya esta completo y verificado;
   hoy esta sin commitear sobre `main`).
2. Agregar `.github/workflows/` con `verify` y `merge`.
3. Correr el workflow manualmente sobre un PR de prueba para confirmar que
   `verify` publica el check con el nombre esperado.
4. Recien ahi activar branch protection en `main` exigiendo `verify`.
   Este orden importa: activar protection antes de que exista el check bloquearia
   todos los merges.
5. Documentar el flujo en `README.md`.

**Rollback**: borrar el workflow y quitar la protection. Son pasos
independientes y ambos reversibles.

## Open Questions

- Si en el futuro se quiere exigir una aprobacion humana, cambia el paso 4 y
  la Decision 6. No afecta la estructura del workflow.
- Si `main` necesita protection como *required status check* estricto o
  *strict up to date*. EsDefault, sin impacto en el diseno.
- Si conviene notificar el merge (Discord, Slack). Cosmeticamente, no altera el
  flujo.
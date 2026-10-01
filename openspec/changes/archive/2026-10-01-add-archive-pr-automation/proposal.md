# Proposal

## Why

El repositorio no tiene ninguna puerta de calidad para las entregas. `main` no
esta protegido, `.github/` no existe, y el flujo documentado en
`openspec/config.yaml` describia un merge y push "automaticos" que nunca
existieron. La consecuencia ya se materializo: el change `label-trip-groups`
quedo completo (codigo, tests, specs sincronizadas y archive) sin commitear
sobre `main`. Hoy cada archive llega a `main` sin verificar que los tests sigan
pasando ni que las specs sean validas.

Ademas, el `openspec/config.yaml` actual no parsea (un escalar plano que empieza
con backtick), por lo que OpenSpec descarta el archivo completo: contexto,
reglas y el guidance de `archive` que se acaba de escribir estan inactivos.

## What Changes

- Agregar un workflow de GitHub Actions que, al aplicar la etiqueta `archive` a
  un pull request, ejecute la suite de tests y la validacion de specs.
- Mergear el PR automaticamente con `--squash` unicamente si ambos pasos quedan
  en verde.
- Activar branch protection en `main` exigiendo el check de CI como requisito
  previo al merge.
- Corregir el parseo de `openspec/config.yaml` y el comando `validate` del
  guidance de `operations.archive`, que hoy es descartado por el parser.

No hay cambios rompientes: el repositorio no tiene releases publicadas que
dependan del flujo actual.

## Capabilities

### New Capabilities

Ninguna. Este cambio no introduce comportamiento observable de la aplicacion.

### Modified Capabilities

Ninguna. Ninguna spec existente cambia sus requisitos.

Opt-out de specs: `.openspec.yaml` declara `skip_specs: true`. Es un cambio de
infraestructura, y el criterio de la CLI lo cubre explicitamente
(`--skip-specs`, "useful for infrastructure, tooling, or doc-only changes").
Las cuatro specs actuales (`group-labels`, `photo-scanning`, `photo-viewing`,
`trip-periods`) describen capacidades del organizador de fotos; la entrega por
CI no encaja en ninguna. No se inventa un requisito para satisfacer la
validacion.

## Impact

- Nuevo: `.github/workflows/` con el workflow de auto-merge.
- Modificado: `openspec/config.yaml` (fix de parseo y comando `validate` corregido).
- Modificado: branch protection de `main` en GitHub (configuracion fuera del repo).
- Sin cambios en `fotos_plus/`, sin cambios en la CLI, sin dependencias nuevas.
- Al archivar este change se usara `openspec archive --skip-specs`.

## Rollback

- Borrar el archivo de workflow revierte el auto-merge por completo.
- Quitar la branch protection de `main` revierte el gate; el workflow dejara de
  poder mergear porque el check requerido deja de existir.
- Revertir el commit de `config.yaml` no restaura nada util: el archivo ya esta
  siendo descartado por el parser, asi que el estado previo es el de "sin
  configuracion efectiva". El fix solo puede mejorar las cosas.

## Decisiones asumidas (pendientes de confirmacion)

Estas tres no fueron respondidas y quedan con el valor recomendado, explicito
para poder revisarlas:

1. **Trigger**: el merge se dispara solo al aplicar la etiqueta `archive`, no
   automaticamente en todo PR abierto.
2. **Branch protection**: se incluye como parte de este change. Sin el, el
   auto-merge queda sin ningun gate y mergea siempre.
3. **Fuera de alcance pero urgente**: los commits `0452a83` y `7680c1e` pueden
   exponer datos privados y el repositorio es publico. La reescritura de
   historia no es parte de este change y conviene atacarla antes.
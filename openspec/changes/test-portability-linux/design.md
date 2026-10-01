# Design

## Context

Ver la negociacion en `proposal.md - Why`. Lo que condiciona el enfoque:

```
os.name == "nt" ?                    index.py:18-22
   |
   +-- si --> base = $LOCALAPPDATA  (o ~/AppData/Local)
   |
   +-- no --> base = $XDG_STATE_HOME (o ~/.local/state)
                    |
                    v
              _root_key(root)                      index.py:30
              os.path.normcase(os.path.normpath(...))
                    |
                    +-- nt   : baja mayusculas  --> "Fotos" == "fotos"
                    +-- posix: identidad         --> "Fotos" != "fotos"
```

El codigo ya hace el branching correcto. Los tests son los que asumen una
sola plataforma.

Evidencia recogida:

- Local (Windows): `260 passed, 1 skipped`
- CI (ubuntu-latest, Python 3.11): `2 failed, 244 passed, 15 skipped`
- Los 15 skips de Linux son correctos y ya estan marcados a proposito
  (`tests/test_bat.py:21` requiere `cmd.exe`, `tests/test_scanner.py:86`
  requiere permisos POSIX).

## Goals / Non-Goals

**Goals:**

- Que la suite pase completa en Linux sin perder cobertura en Windows.
- Reutilizar el patron de skip que el repo ya usa, sin inventar uno nuevo.
- Mantener la distinction entre "el codigo esta mal" y "el test asume Windows".

**Non-Goals:**

- Arreglar los 15 skips: son correctos.
- Cambiar el comportamiento de `fotos_plus/index.py`.
- Activar branch protection (pertenece a `add-archive-pr-automation`).

## Decisions

### 1. `test_default_index_path_is_used_when_not_given`: setear tambien `XDG_STATE_HOME`

No se skipea. El test verifica que `scan` respete la base de estado, y esa
base tiene equivalente en POSIX. Skipearlo dejaria sin cobertura el camino
POSIX, que es justamente el que corre en CI.

La ruta esperada se calcula desde la plataforma en vez de hardcodear
`state / "fotos-plus" / "indexes"`.

**Alternativa descartada:** marcar el test como Windows-only con
`skipif(sys.platform != "win32")`. Es menos trabajo, pero deja el codigo POSIX
sin verificar justo cuando CI pasa a ser la puerta de calidad.

### 2. `test_default_index_path_follows_case_insensitive_paths`: `skipif` en POSIX

Aqui la cobertura no se puede recuperar igual: el comportamiento *depende* de la
plataforma y ambos son correctos. En Windows dos rutas que solo difieren en
mayusculas son el mismo archivo; en POSIX son archivos distintos. No hay una
asercion valida para los dos casos a la vez.

Se marca con `skipif(os.name != "nt")` siguiendo el patron exacto de
`tests/test_scanner.py:86`.

**Alternativa descartada:** invertir el test para afirmar `lower != upper` en
POSIX. Seria covering mas, pero cambia la intencion del test original (que
documenta el comportamiento de Windows) y mezcla dos afirmaciones en un solo
caso.

### 3. Sin parametrizacion nueva

Se usan `monkeypatch.setenv` y `skipif`, que ya estan en el `conftest.py` y en
el resto del suite. No se agrega fixture de plataforma.

## Risks / Trade-offs

- **[El skip esconde una regresion real de case-insensitivity en POSIX]**
  → No aplica: `normcase` es identidad en POSIX por diseño de Python, no es
  comportamiento de `fotos_plus`. El test sigue corriendo en Windows, que es
  donde la garantia tiene sentido.

- **[El conteo de tests sigue variando entre plataformas]** → Es esperable y ya
  documentado en el README del change. Lo que no puede variar es que ambos
  resultados sean verdes.

- **[CI en rojo hasta que se mergee este fix]** → Es el estado actual. No se
  activa `verify` como required check mientras tanto, asi que `main` no queda
  bloqueada.

## Migration Plan

1. Aplicar el fix en los dos tests.
2. Verificar en Windows: `python -m pytest -q` sigue dando `260 passed, 1 skipped`.
3. Commitar en rama `feature/test-portability-linux` y abrir PR **sin** la
   etiqueta `archive`, para que el check corra y confirme el fix.
4. Cuando `verify` pase en verde, aplicar la etiqueta `archive` al mismo PR: el
   job `merge` lo squashea a `main` solo.
5. Volver a `add-archive-pr-automation` y cerrar las tasks 3.2 y 5.1.

**Rollback:** revertir el commit. Sin impacto en produccion.

## Open Questions

- Si en el futuro el repo se desarrolla principalmente en Linux, conviene
  invertir el default de la CI. No afecta este change.
- Si `normcase` llegara a cambiar de comportamiento en alguna version de Python
  POSIX, el skip quedaria obsoleto. Es un comportamiento documentado y estable,
  muy improbable.
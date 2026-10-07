@echo off
setlocal

set "PROJECT_DIR=%~dp0"
pushd "%PROJECT_DIR%" >nul

if "%~1"=="" goto usage
if not "%~2"=="" goto usage

set "BRANCH=%~1"
git check-ref-format --branch "%BRANCH%" >nul 2>nul
if errorlevel 1 goto invalid_branch

for /f "delims=" %%A in ('git branch --show-current') do set "CURRENT_BRANCH=%%A"
if /I not "%CURRENT_BRANCH%"=="main" goto wrong_branch

set "DIRTY_TREE="
for /f "delims=" %%A in ('git status --porcelain --untracked-files^=all') do (
    if not "%%A"=="?? publicar-pr.bat" set "DIRTY_TREE=1"
)
if defined DIRTY_TREE goto dirty_tree

echo Creando la rama %BRANCH% desde main...
git switch -c "%BRANCH%"
if errorlevel 1 goto failed

echo Publicando la rama...
git push -u origin "%BRANCH%"
if errorlevel 1 goto failed

echo Creando el pull request contra main...
gh pr create --base main --head "%BRANCH%"
if errorlevel 1 goto failed

echo.
echo Espera a que el check "verify" pase y a que el PR tenga las aprobaciones necesarias.
choice /C SN /N /M "Cuando este listo, presiona S para mergear; presiona N para dejarlo pendiente: "
if errorlevel 2 goto cancelled

echo Cambiando a main...
git switch main
if errorlevel 1 goto failed

echo Mergeando el PR y eliminando las ramas local y remota...
gh pr merge "%BRANCH%" --merge --delete-branch
if errorlevel 1 goto failed

echo Actualizando main...
git pull origin main
if errorlevel 1 goto failed

echo Listo: PR mergeado y rama eliminada.
goto done

:usage
echo Uso: %~nx0 nombre-de-la-rama
echo Ejemplo: %~nx0 feature/remove_untagged_photos
goto failed

:invalid_branch
echo Error: "%BRANCH%" no es un nombre de rama valido.
goto failed

:wrong_branch
echo Error: ejecuta este script estando en main. Rama actual: %CURRENT_BRANCH%
goto failed

:dirty_tree
echo Error: hay cambios sin commit. Guarda o descarta los cambios antes de continuar.
goto failed

:cancelled
echo PR creado. No se mergeo ni se elimino la rama.
goto done

:failed
echo El proceso se detuvo por un error. Revisa el mensaje anterior; la rama no se elimina salvo que el merge haya tenido exito.
popd >nul
endlocal & exit /b 1

:done
popd >nul
endlocal & exit /b 0

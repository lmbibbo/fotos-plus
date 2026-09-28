@echo off
setlocal

set "PROJECT_DIR=%~dp0"
pushd "%PROJECT_DIR%" >nul

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYTHON=python"
) else (
    set "PYTHON=py -3"
)

rem Sin argumentos: mostrar la ayuda general
if "%~1"=="" (
    %PYTHON% -m fotos_plus --help
    set "EXIT_CODE=%ERRORLEVEL%"
    popd >nul
    endlocal & exit /b %EXIT_CODE%
)

rem El primer argumento ya es un subcomando u opcion: se pasa tal cual
if /I "%~1"=="scan" goto run
if "%~1"=="-h" goto run
if "%~1"=="--help" goto run

rem En cualquier otro caso se asume: fotos-plus.bat scan <args>
set "ARGS=scan %*"

:run
if not defined ARGS set "ARGS=%*"
%PYTHON% -m fotos_plus %ARGS%

set "EXIT_CODE=%ERRORLEVEL%"

popd >nul
endlocal & exit /b %EXIT_CODE%

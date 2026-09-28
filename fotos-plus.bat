@echo off
setlocal

set "PROJECT_DIR=%~dp0"
rem Carpeta desde la que se lanzo el .bat, que es donde se guardan los indices
set "INVOCATION_DIR=%CD%"
pushd "%PROJECT_DIR%" >nul

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYTHON=python"
) else (
    set "PYTHON=py -3"
)

rem Si el usuario ya eligio donde guardar el indice, no se impone la carpeta de invocacion
set "ARGS_RAW=%*"
set "PROBE=%ARGS_RAW:--index=~%"
if not "%PROBE%"=="%ARGS_RAW%" set "HAS_INDEX_OPT=1"

rem Sin argumentos: mostrar la ayuda general
if "%~1"=="" goto no_args
if /I "%~1"=="scan" goto explicit
if "%~1"=="-h" goto help
if "%~1"=="--help" goto help

rem En cualquier otro caso se asume: fotos-plus.bat scan <args>
:implied
set "ARGS=scan %*"
set "USE_INVOCATION_DIR=1"
goto run

rem El primer argumento ya es un subcomando u opcion: se pasa tal cual
:explicit
set "ARGS=%*"
set "USE_INVOCATION_DIR=1"
goto run

:no_args
:help
set "ARGS=%*"
if "%~1"=="" set "ARGS=--help"

:run
if defined HAS_INDEX_OPT goto run_as_is
if not defined USE_INVOCATION_DIR goto run_as_is
%PYTHON% -m fotos_plus %ARGS% --index-dir "%INVOCATION_DIR%"
goto done

:run_as_is
%PYTHON% -m fotos_plus %ARGS%

:done
set "EXIT_CODE=%ERRORLEVEL%"

popd >nul
endlocal & exit /b %EXIT_CODE%

@echo off
REM Avvio di Wikify con la cartella dati esclusa dal repository.
REM
REM I dati di lavoro (database SQLite, chiave di sessione, temporanei di
REM import) risiedono in "dati\lavoro" dentro la cartella di progetto: restano
REM quindi locali e non entrano in eventuali repository o copie condivise.
REM Per usare un percorso diverso basta valorizzare ARCHIVIO_SMART_DATA prima
REM di lanciare questo file.

setlocal
set APP_DIR=%~dp0

if "%ARCHIVIO_SMART_DATA%"=="" (
    for %%I in ("%APP_DIR%..") do set PROGETTO_DIR=%%~fI
    call set ARCHIVIO_SMART_DATA=%%PROGETTO_DIR%%\dati\lavoro
)

if not exist "%ARCHIVIO_SMART_DATA%" mkdir "%ARCHIVIO_SMART_DATA%"
echo Cartella dati: %ARCHIVIO_SMART_DATA%

cd /d "%APP_DIR%"
py app.py
endlocal

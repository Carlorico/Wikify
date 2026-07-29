@echo off
REM Avvio di Wikify con la cartella dati tenuta fuori dalla cartella di progetto.
REM
REM I dati di lavoro (database SQLite, chiave di sessione, temporanei di
REM import) risiedono in "Wikify_dati", cartella sorella di "Wikify": restano
REM quindi locali e non entrano in eventuali repository o copie condivise.
REM Per usare un percorso diverso basta valorizzare ARCHIVIO_SMART_DATA prima
REM di lanciare questo file.

setlocal
set APP_DIR=%~dp0

if "%ARCHIVIO_SMART_DATA%"=="" (
    for %%I in ("%APP_DIR%..\..") do set WORKSHOP_DIR=%%~fI
    call set ARCHIVIO_SMART_DATA=%%WORKSHOP_DIR%%\Wikify_dati
)

if not exist "%ARCHIVIO_SMART_DATA%" mkdir "%ARCHIVIO_SMART_DATA%"
echo Cartella dati: %ARCHIVIO_SMART_DATA%

cd /d "%APP_DIR%"
py app.py
endlocal

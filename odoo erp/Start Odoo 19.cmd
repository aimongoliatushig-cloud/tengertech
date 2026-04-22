@echo off
set "MODULE_SOURCE=%~dp0custom_addons\ops_work_unit"
set "MODULE_TARGET=%LOCALAPPDATA%\OpenERP S.A\Odoo\addons\19.0\ops_work_unit"
set "SERVICE=odoo-server-19.0"
set "URL=http://localhost:8069"

if exist "%MODULE_SOURCE%" (
    if not exist "%MODULE_TARGET%" mkdir "%MODULE_TARGET%"
    robocopy "%MODULE_SOURCE%" "%MODULE_TARGET%" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
)

sc query "%SERVICE%" | find /I "RUNNING" >nul
if errorlevel 1 (
    echo Starting %SERVICE%...
    net start "%SERVICE%"
) else (
    echo %SERVICE% is already running.
)

start "" "%URL%"

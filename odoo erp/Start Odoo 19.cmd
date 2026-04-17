@echo off
set "SERVICE=odoo-server-19.0"
set "URL=http://localhost:8069"

sc query "%SERVICE%" | find /I "RUNNING" >nul
if errorlevel 1 (
    echo Starting %SERVICE%...
    net start "%SERVICE%"
) else (
    echo %SERVICE% is already running.
)

start "" "%URL%"

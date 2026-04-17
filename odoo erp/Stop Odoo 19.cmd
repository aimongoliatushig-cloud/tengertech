@echo off
set "SERVICE=odoo-server-19.0"

echo Stopping %SERVICE%...
net stop "%SERVICE%"

@echo off
chcp 65001 >nul
set PATH=C:\Program Files\nodejs;%PATH%
cd /d "%~dp0"
call node_modules\.bin\electron.cmd .
pause

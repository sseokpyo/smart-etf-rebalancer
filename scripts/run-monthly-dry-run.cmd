@echo off
setlocal

rem Run from the project root so Python can import invest_bot and data files
rem are recorded inside this project. Do not add --live here.
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m invest_bot run

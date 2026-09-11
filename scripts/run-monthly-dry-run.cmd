@echo off
setlocal

rem Run from the project root so Python can import invest_bot and data files
rem are recorded inside this project. The dashboard's automatic-trading switch
rem decides whether this run creates a plan only or sends the planned orders.
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m invest_bot.auto_run

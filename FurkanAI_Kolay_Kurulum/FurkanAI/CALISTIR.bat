@echo off
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw main.py & exit /b)
where pythonw >nul 2>nul && (start "" pythonw main.py & exit /b)
py main.py

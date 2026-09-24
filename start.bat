@echo off
title pso-companion - Skills et documentation
cd /d "%~dp0"
echo.
echo  ====================================
echo   pso-companion - Skills et doc
echo  ====================================
echo.
where node >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Node.js non installe. Telecharge sur https://nodejs.org
    pause & exit /b 1
)
node --version
if not exist "node_modules\" (
    echo Installation des dependances...
    npm install
)
start "" "http://localhost:3011/"
node server.js
pause

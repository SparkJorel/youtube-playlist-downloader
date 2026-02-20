@echo off
chcp 65001 >nul 2>&1
title YouTube Playlist Downloader - Installation
color 0A

echo ================================================================
echo    YouTube Playlist Downloader - Installation automatique
echo ================================================================
echo.

:: Verifier Python
echo [1/5] Verification de Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    Python non trouve. Installation via winget...
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 (
        echo    ERREUR : Impossible d'installer Python.
        echo    Telechargez-le manuellement : https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo    Python installe. Redemarrez ce script.
    pause
    exit /b 0
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo    %%i detecte
)

echo.

:: Installer yt-dlp
echo [2/5] Installation de yt-dlp...
pip install --upgrade yt-dlp >nul 2>&1
if %errorlevel% equ 0 (
    echo    yt-dlp installe avec succes
) else (
    echo    ERREUR : echec de l'installation de yt-dlp
    pause
    exit /b 1
)

echo.

:: Installer Node.js
echo [3/5] Verification de Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    Node.js non trouve. Installation via winget...
    winget install --id OpenJS.NodeJS -e --accept-source-agreements --accept-package-agreements
    echo    Node.js installe
) else (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo    Node.js %%i detecte
)

echo.

:: Installer FFmpeg
echo [4/5] Verification de FFmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo    FFmpeg non trouve. Installation via winget...
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    echo    FFmpeg installe
) else (
    echo    FFmpeg detecte
)

echo.

:: Installer aria2c
echo [5/5] Verification de aria2c...
aria2c --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    aria2c non trouve. Installation via winget...
    winget install --id aria2.aria2 -e --accept-source-agreements --accept-package-agreements
    echo    aria2c installe
) else (
    echo    aria2c detecte
)

echo.
echo ================================================================
echo    Installation terminee avec succes !
echo ================================================================
echo.
echo    IMPORTANT : Redemarrez votre PC ou fermez et rouvrez
echo    votre terminal pour que les outils soient reconnus.
echo.
echo    Pour lancer l'application :
echo    Double-cliquez sur "YouTube Playlist Downloader.exe"
echo    ou tapez : python download_playlist.py
echo.
echo ================================================================
echo.

:: Construire l'executable si pyinstaller est dispo
echo Construction de l'executable...
pip install pyinstaller >nul 2>&1
pyinstaller --onefile --windowed --name "YouTube Playlist Downloader" download_playlist.py >nul 2>&1
if %errorlevel% equ 0 (
    copy "dist\YouTube Playlist Downloader.exe" "YouTube Playlist Downloader.exe" >nul 2>&1
    echo    Executable cree : "YouTube Playlist Downloader.exe"
) else (
    echo    L'executable n'a pas pu etre cree.
    echo    Vous pouvez lancer directement : python download_playlist.py
)

echo.
pause

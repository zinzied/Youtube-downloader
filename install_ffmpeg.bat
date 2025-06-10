@echo off
echo ========================================
echo FFmpeg Installation Helper
echo ========================================
echo.
echo This script will help you install FFmpeg on Windows.
echo.
echo Checking if Chocolatey is installed...
choco --version >nul 2>&1
if %errorlevel% == 0 (
    echo Chocolatey found! Installing FFmpeg...
    choco install ffmpeg -y
    if %errorlevel% == 0 (
        echo.
        echo ✅ FFmpeg installed successfully via Chocolatey!
        echo.
        echo Verifying installation...
        ffmpeg -version
        echo.
        echo ✅ Installation complete! You can now close this window and restart the YouTube Downloader.
    ) else (
        echo ❌ Failed to install FFmpeg via Chocolatey.
        goto manual_install
    )
) else (
    echo Chocolatey not found. Checking for Winget...
    winget --version >nul 2>&1
    if %errorlevel% == 0 (
        echo Winget found! Installing FFmpeg...
        winget install ffmpeg
        if %errorlevel% == 0 (
            echo.
            echo ✅ FFmpeg installed successfully via Winget!
            echo.
            echo Verifying installation...
            ffmpeg -version
            echo.
            echo ✅ Installation complete! You can now close this window and restart the YouTube Downloader.
        ) else (
            echo ❌ Failed to install FFmpeg via Winget.
            goto manual_install
        )
    ) else (
        goto manual_install
    )
)
goto end

:manual_install
echo.
echo ========================================
echo Manual Installation Required
echo ========================================
echo.
echo Neither Chocolatey nor Winget package managers were found.
echo.
echo Please follow these steps for manual installation:
echo.
echo 1. Go to: https://ffmpeg.org/download.html
echo 2. Click "Windows" and download from gyan.dev
echo 3. Extract to C:\ffmpeg
echo 4. Add C:\ffmpeg\bin to your system PATH
echo.
echo Would you like to open the FFmpeg download page now? (Y/N)
set /p choice=
if /i "%choice%"=="Y" (
    start https://ffmpeg.org/download.html
)

:end
echo.
echo Press any key to exit...
pause >nul

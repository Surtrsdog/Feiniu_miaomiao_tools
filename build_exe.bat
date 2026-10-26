@echo off
setlocal
cd /d "%~dp0"

set "PY=python"
where python >nul 2>nul
if errorlevel 1 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    ) else (
        echo [ERROR] Python not found. Install Python 3.11+ first.
        pause
        exit /b 1
    )
)

if not exist ".build\pylibs\PyInstaller" (
    echo [1/3] Installing PyInstaller into .build\pylibs ...
    "%PY%" -m pip install --disable-pip-version-check --no-cache-dir --target ".build\pylibs" pyinstaller
    if errorlevel 1 goto fail
) else (
    echo [1/3] PyInstaller already present.
)

if not exist ".build\app.ico" (
    echo [2/3] Generating icon ...
    "%PY%" make_icon.py
    if errorlevel 1 goto fail
) else (
    echo [2/3] Icon already present.
)

echo [3/3] Building exe ...
set "PYTHONPATH=%CD%\.build\pylibs"
set "TMP=%CD%\.build\tmp"
set "TEMP=%CD%\.build\tmp"
"%PY%" -m PyInstaller build_exe.spec --noconfirm --distpath "dist" --workpath ".build\work" --log-level WARN
if errorlevel 1 goto fail

rem Rename to the localized filename (done in Python to avoid codepage issues)
"%PY%" -c "import os,glob; d=chr(100)+chr(105)+chr(115)+chr(116); src=os.path.join(d,chr(65)+chr(114)+chr(107)+chr(110)+chr(105)+chr(103)+chr(104)+chr(116)+chr(115)+chr(67)+chr(97)+chr(108)+chr(99)+chr(46)+chr(101)+chr(120)+chr(101)); dst=os.path.join(d,chr(0x660E)+chr(0x65E5)+chr(0x65B9)+chr(0x821F)+chr(0x8BA1)+chr(0x7B97)+chr(0x5668)+chr(46)+chr(101)+chr(120)+chr(101)); os.path.isfile(src) and os.replace(src,dst)"

echo.
echo ======================================================
echo   BUILD OK
echo   Output:  dist  folder
echo ======================================================
pause
exit /b 0

:fail
echo.
echo [FAILED] Build did not complete. See messages above.
pause
exit /b 1

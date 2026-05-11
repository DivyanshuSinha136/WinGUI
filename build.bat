@echo off
setlocal EnableDelayedExpansion

echo =====================================
echo        WinGUI Build System
echo =====================================
echo.

set /p file_name=Enter ASM File Name: 

if "!file_name!"=="" (
    echo [ERROR] File name cannot be empty.
    pause
    exit /b
)

if not exist "!file_name!.asm" (
    echo [ERROR] File "!file_name!.asm" not found.
    pause
    exit /b
)

echo.
echo [1/2] Assembling...
nasm -f win64 "!file_name!.asm" -o "!file_name!.obj"
if errorlevel 1 (
    echo [FAILED] NASM assembly error
    pause
    exit /b
)

echo [2/2] Linking...
gcc -shared -o "!file_name!.dll" "!file_name!.obj" -luser32 -lkernel32 -lgdi32 -lcomctl32 -Wl,--out-implib,libwingui2.a

if errorlevel 1 (
    echo [FAILED] GCC linking error
    pause
    exit /b
)

echo.
echo =====================================
echo BUILD SUCCESS: !file_name!.dll
echo =====================================
pause

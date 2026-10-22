@echo off
chcp 65001 >nul
title FurkanAI - Kolay Kurulum
cd /d "%~dp0"
echo.
echo  ==========================================
echo           FurkanAI  -  Kolay Kurulum
echo  ==========================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo  [!] Python bulunamadi. winget ile Python 3.12 kuruluyor...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  echo.
  echo  Python kuruldu. Bu pencereyi KAPAT ve KUR.bat dosyasina tekrar cift tikla.
  echo  Olmazsa https://www.python.org/downloads/ adresinden Python kur
  echo  ^(kurulumda "Add Python to PATH" kutusunu isaretle^).
  pause
  exit /b 1
)

echo  [1/4] Gerekli paketler kuruluyor...
%PY% -m pip install --upgrade pip >nul 2>nul
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo  [!] Paket kurulumunda hata oldu. Internet baglantini kontrol et.
  pause
  exit /b 1
)

echo.
echo  [2/4] Mikrofon destegi ^(PyAudio^) deneniyor...
%PY% -m pip install PyAudio >nul 2>nul
if errorlevel 1 (
  echo  [i] PyAudio kurulamadi. Sesli komut calismayabilir, ama her sey diger isler normal calisir.
) else (
  echo  [OK] Mikrofon destegi hazir.
)

echo.
echo  [3/4] FurkanAI.exe olusturuluyor ^(1-3 dakika surebilir^)...
%PY% -m pip install pyinstaller >nul 2>nul
%PY% -m PyInstaller --noconfirm --clean --windowed --onefile --name FurkanAI --icon icon.ico --add-data "icon.ico;." --hidden-import pyttsx3.drivers --hidden-import pyttsx3.drivers.sapi5 main.py >build_log.txt 2>&1

set "TARGET=%~dp0CALISTIR.bat"
if exist "dist\FurkanAI.exe" (
  if not exist "%USERPROFILE%\FurkanAI" mkdir "%USERPROFILE%\FurkanAI"
  copy /y "dist\FurkanAI.exe" "%USERPROFILE%\FurkanAI\FurkanAI.exe" >nul
  copy /y "icon.ico" "%USERPROFILE%\FurkanAI\icon.ico" >nul
  set "TARGET=%USERPROFILE%\FurkanAI\FurkanAI.exe"
  echo  [OK] EXE hazir.
) else (
  echo  [i] EXE olusturulamadi ^(detay: build_log.txt^). Program yine de CALISTIR.bat ile acilacak.
)

echo.
echo  [4/4] Masaustune kisayol ekleniyor...
powershell -NoProfile -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut($d+'\FurkanAI.lnk'); $s.TargetPath='%TARGET%'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0icon.ico'; $s.Save()"

echo.
echo  ==========================================
echo    TAMAMLANDI!  Masaustundeki FurkanAI
echo    simgesine cift tiklayarak acabilirsin.
echo  ==========================================
echo.
start "" "%TARGET%"
timeout /t 5 >nul

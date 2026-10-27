@echo off
rem SunPet Windows 版一键构建：PyInstaller 打 exe + Inno Setup 出安装包
setlocal
cd /d "%~dp0"

python -m pip install PySide6 PyInstaller || goto :err

python -m PyInstaller --noconfirm --clean --windowed --name SunPet --icon app.ico --add-data "Assets;Assets" SunPet.py || goto :err

set "ISCC=C:\Program Files\Inno Setup 7\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo [提示] 未找到 Inno Setup，跳过安装包；绿色版在 dist\SunPet
    goto :done
)
"%ISCC%" installer.iss || goto :err

:done
echo.
echo 构建完成：installer_output\SunPet-1.1.0-Setup.exe
exit /b 0

:err
echo 构建失败，请检查上面的错误输出。
exit /b 1

@echo off
setlocal
REM 1) ย้ายไดเรกทอรีมายังโฟลเดอร์เดียวกับไฟล์ .bat (กันปัญหา path)
cd /d "%~dp0"

REM 2) ตั้งค่า DB กลาง (แก้ IP/รหัสผ่านให้ตรงกับของคุณ)
set "DB_HOST=192.168.1.10"
set "DB_PORT=3306"
set "DB_USER=simapp"
set "DB_PASS=StrongPass!"
set "DB_NAME=sim_logs"

REM 3) ถ้ามี virtualenv ชื่อ .venv ให้ activate อัตโนมัติ
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

REM 4) รันด้วย py launcher หากมี; ถ้าไม่มีลอง python; ถ้าไม่เจอแจ้ง error
where py >nul 2>&1 && (
  py -3 "%~dp0main.py"
) || (
  where python >nul 2>&1 && (
    python "%~dp0main.py"
  ) || (
    echo [ERROR] ไม่พบ Python ใน PATH (ลองติดตั้ง Python หรือเปิดด้วย venv)
    pause
    exit /b 1
  )
)

REM 5) ค้างหน้าต่างไว้เพื่อดู error (ถ้ามี)
echo.
pause

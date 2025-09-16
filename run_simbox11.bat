@REM @echo off
@REM setlocal
@REM REM 1) ย้ายไดเรกทอรีมายังโฟลเดอร์เดียวกับไฟล์ .bat (กันปัญหา path)
@REM cd /d "%~dp0"

@REM REM 2) ตั้งค่า DB กลาง (แก้ IP/รหัสผ่านให้ตรงกับของคุณ)
@REM set "DB_HOST=192.168.56.1"
@REM set "DB_PORT=3306"
@REM set "DB_USER=simapp"
@REM set "DB_PASS=StrongPass!"
@REM set "DB_NAME=sim_logs"

@REM REM 3) ถ้ามี virtualenv ชื่อ .venv ให้ activate อัตโนมัติ
@REM if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

@REM REM 4) รันด้วย py launcher หากมี; ถ้าไม่มีลอง python; ถ้าไม่เจอแจ้ง error
@REM where py >nul 2>&1 && (
@REM   py -3 "%~dp0main.py"
@REM ) || (
@REM   where python >nul 2>&1 && (
@REM     python "%~dp0main.py"
@REM   ) || (
@REM     echo [ERROR] ไม่พบ Python ใน PATH (ลองติดตั้ง Python หรือเปิดด้วย venv)
@REM     pause
@REM     exit /b 1
@REM   )
@REM )

@REM REM 5) ค้างหน้าต่างไว้เพื่อดู error (ถ้ามี)
@REM echo.
@REM pause

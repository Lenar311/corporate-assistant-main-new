@echo off
chcp 65001 >nul
echo ============================================================
echo    Загрузка Corporate Assistant на GitHub
echo ============================================================
echo.

cd /d C:\corporate-assistant-main-new

:: Проверка Git
where git >nul 2>&1
if errorlevel 1 (
    echo [X] Git не найден! Установите Git
    pause
    exit /b 1
)

echo [OK] Git найден
echo.

:: Удаление старого remote
git remote remove origin 2>nul

:: Добавление нового remote
git remote add origin https://github.com/Lenar311/corporate-assistant-main-new.git
echo [OK] Remote добавлен: https://github.com/Lenar311/corporate-assistant-main-new.git
echo.

:: Создание README.md
if not exist README.md (
    echo # corporate-assistant > README.md
    echo. >> README.md
    echo Корпоративный ассистент для работы с нормативными документами >> README.md
    echo. >> README.md
    echo ## Быстрый старт >> README.md
    echo 1. Установите зависимости: `pip install -r requirements.txt` >> README.md
    echo 2. Запустите: `run_system.bat` >> README.md
    echo [OK] README.md создан
)

:: Создание ветки main-new
git checkout -b main-new 2>nul
if errorlevel 1 (
    git checkout main-new
)
echo [OK] Ветка: main-new
echo.

:: Добавление файлов
git add -A

:: Коммит
git commit -m "Initial commit: Corporate Assistant v1.0"

:: Загрузка
echo.
echo [INFO] Загрузка на GitHub...
git push -u origin main-new --force

echo.
echo ============================================================
echo    ✅ Загрузка завершена!
echo ============================================================
echo.
echo    Репозиторий: https://github.com/Lenar311/corporate-assistant-main-new
echo    Ветка: main-new
echo    Ссылка: https://github.com/Lenar311/corporate-assistant-main-new/tree/main
echo.
pause
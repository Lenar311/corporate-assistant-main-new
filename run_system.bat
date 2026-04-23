@echo off
title Corporate Assistant
chcp 65001 >nul
echo ============================================================
echo    Corporate Assistant v1.0.0
echo ============================================================
echo.

:: Проверяем, что запускаем из корня проекта
if not exist "backend\main.py" (
    echo ❌ Ошибка: запускайте этот файл из корня проекта:
    echo    C:\corporate-assistant-main-new\run.bat
    pause
    exit /b 1
)

:: Создаём .env для бэкенда, если нет
cd backend
if not exist ".env" (
    echo PORT=8080 > .env
    echo HOST=127.0.0.1 >> .env
    echo DEBUG=False >> .env
    echo OLLAMA_MODEL=deepseek-r1:8b >> .env
    echo EMBEDDING_MODEL=BAAI/bge-m3 >> .env
    echo TOP_K=5 >> .env
    echo CHUNK_SIZE=3600 >> .env
    echo CHUNK_OVERLAP=1000 >> .env
    echo PRELOAD_EMBEDDING=true >> .env
    echo EMBEDDING_USE_ONNX=false >> .env
)

:: Запускаем бэкенд (uvicorn через python -m для надёжности)
echo 🚀 Запуск бэкенда на порту 8080...
start "Backend" cmd /k "python -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload"
timeout /t 5 /nobreak >nul

:: Проверяем, что бэкенд запустился
echo 🔍 Проверка бэкенда...
for /L %%i in (1,1,10) do (
    curl -s http://127.0.0.1:8080/health >nul 2>&1 && (
        echo ✅ Бэкенд готов!
        goto :frontend
    )
    timeout /t 1 /nobreak >nul
    echo   Ожидание... (%%i/10)
)
echo ⚠ Бэкенд не ответил за 10 сек, продолжаем запуск фронтенда...

:frontend
cd ../frontend
if not exist ".env" (
    echo REACT_APP_API_URL=http://localhost:8080 > .env
)

:: Запускаем фронтенд
echo 🎨 Запуск фронтенда...
start "Frontend" cmd /k "npm start"

echo.
echo ============================================================
echo    ✅ СИСТЕМА ЗАПУЩЕНА!
echo ============================================================
echo.
echo    🔗 Бэкенд:  http://localhost:8080/docs
echo    🌐 Фронтенд: http://localhost:3000
echo.
echo    📁 Папка документов: backend\data\documents
echo    💾 База векторов: backend\chroma_db
echo.
echo ============================================================
echo.

:: Открываем фронтенд в браузере
start http://localhost:3000

:: Возвращаемся в корень
cd ..

:: Оставляем окно открытым
pause
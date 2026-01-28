#!/bin/bash

# Скрипт запуска PDF Converter Bot

echo "🚀 Запуск PDF Converter Bot..."
echo "================================"

# Проверка наличия Python 3.12
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 не найден. Попробуем использовать python3..."
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python3.12"
fi

# Создание виртуального окружения, если его нет
if [ ! -d ".venv" ]; then
    echo "📦 Создание виртуального окружения..."
    $PYTHON_CMD -m venv .venv
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source .venv/bin/activate

# Обновление pip
echo "⬆️  Обновление pip..."
pip install --upgrade pip -q

# Установка зависимостей
echo "📚 Установка зависимостей..."
pip install -r requirements.txt -q

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Внимание: файл .env не найден!"
    echo "📝 Создайте .env файл на основе .env.example"
    echo "   и добавьте ваши настройки перед запуском."
    exit 1
fi

# Проверка наличия poppler для pdf2image (если используется)
if ! command -v pdftoppm &> /dev/null; then
    echo "⚠️  Предупреждение: poppler-utils не установлен"
    echo "   Для работы с PDF может потребоваться установка:"
    echo "   Ubuntu/Debian: sudo apt-get install poppler-utils"
    echo "   CentOS/RHEL: sudo yum install poppler-utils"
    echo "   Продолжаем запуск..."
fi

echo "================================"
echo "✅ Окружение готово!"
echo "🤖 Запуск бота..."
echo "================================"
echo ""

# Запуск бота
python bot.py

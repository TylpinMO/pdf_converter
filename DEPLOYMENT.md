# Инструкция по запуску бота на сервере

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/TylpinMO/pdf_converter.git
cd pdf_converter
```

### 2. Настройка .env файла

```bash
cp .env.example .env
nano .env  # или vim .env
```

Укажите ваши данные:

```env
BOT_TOKEN=ваш_токен_бота
ADMIN_ID=740416524
CHANNEL_USERNAME=@matvuktuk
DAILY_LIMIT=10
MAX_PHOTO_SIZE_MB=15
MAX_PDF_SIZE_MB=100
LOG_FILE=bot.log
LOG_LEVEL=INFO
```

### 3. Установка poppler (для работы с PDF)

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

**CentOS/RHEL:**

```bash
sudo yum install poppler-utils
```

### 4. Запуск в tmux

**Создание новой tmux сессии:**

```bash
tmux new -s pdf_bot
```

**Запуск бота:**

```bash
./start.sh
```

**Выход из tmux без остановки бота:**
Нажмите `Ctrl+B`, затем `D` (detach)

**Возврат в сессию:**

```bash
tmux attach -t pdf_bot
```

**Остановка бота:**
Нажмите `Ctrl+C` внутри tmux сессии

### 5. Полезные команды tmux

```bash
# Список активных сессий
tmux ls

# Подключиться к сессии
tmux attach -t pdf_bot

# Убить сессию
tmux kill-session -t pdf_bot

# Переименовать сессию
tmux rename-session -t pdf_bot new_name
```

## Проверка логов

```bash
# Просмотр логов в реальном времени
tail -f bot.log

# Последние 100 строк
tail -n 100 bot.log

# Поиск ошибок
grep ERROR bot.log
```

## Обновление бота

```bash
# Остановить бота (Ctrl+C в tmux)
# Затем:
git pull origin main
./start.sh
```

## Автозапуск при перезагрузке сервера (опционально)

Создайте systemd service:

```bash
sudo nano /etc/systemd/system/pdf_bot.service
```

Содержимое:

```ini
[Unit]
Description=PDF Converter Bot
After=network.target

[Service]
Type=simple
User=ваш_пользователь
WorkingDirectory=/путь/к/pdf_converter
ExecStart=/путь/к/pdf_converter/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pdf_bot
sudo systemctl start pdf_bot
sudo systemctl status pdf_bot
```

## Мониторинг

```bash
# Использование памяти
ps aux | grep bot.py

# Дисковое пространство
df -h

# Размер логов
du -h bot.log
```

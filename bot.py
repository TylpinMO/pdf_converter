import asyncio
import logging
from logging.handlers import RotatingFileHandler
from aiogram import Bot, Dispatcher
from database import Database
from config import BOT_TOKEN, LOG_FILE, LOG_LEVEL
from handlers.user_handlers import router as user_router
from handlers.admin_handlers import router as admin_router

# ==================== Логирование ====================
def setup_logging():
    """Настройка логирования в файл и консоль"""
    logger = logging.getLogger()
    logger.setLevel(LOG_LEVEL)
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла (ротация по размеру)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5_000_000,  # 5 МБ
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.WARNING)  # Только WARNING и выше в файл
    logger.addHandler(file_handler)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)  # INFO и выше в консоль
    logger.addHandler(console_handler)
    
    # Отключаем избыточные логи aiogram и aiohttp
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    return logger

# ==================== Инициализация ====================
logger = setup_logging()
bot = Bot(token=BOT_TOKEN)
db = Database()

# Dispatcher создается при запуске бота
dp = None

# ==================== Главная функция ====================
async def main():
    """Главная функция запуска бота"""
    global dp
    dp = Dispatcher()
    
    # Регистрируем роутеры
    dp.include_router(user_router)
    dp.include_router(admin_router)
    
    logger.info("=" * 50)
    logger.info("🤖 Запуск Telegram бота...")
    logger.info("=" * 50)
    
    try:
        # Инициализация БД
        await db.init_db()
        logger.info("✅ База данных инициализирована")
        
        # Запуск бота
        logger.info("🔄 Бот запущен и слушает обновления...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}", exc_info=True)
    finally:
        logger.info("🛑 Бот остановлен")
        await bot.session.close()

# ==================== Точка входа ====================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")

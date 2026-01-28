import logging
from functools import wraps
from aiogram.types import Message, CallbackQuery
from utils.subscription_checker import check_user_subscription
from keyboards.user_keyboards import get_subscription_check_keyboard

logger = logging.getLogger(__name__)


def check_subscription(func):
    """
    Декоратор для проверки подписки на канал перед выполнением функции
    Работает с обработчиками сообщений и callback запросов
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Определяем тип обработчика
        message = None
        callback = None
        bot = None
        user_id = None
        
        # Ищем Message или CallbackQuery в аргументах
        for arg in args:
            if isinstance(arg, Message):
                message = arg
                bot = arg.bot
                user_id = arg.from_user.id
                break
            elif isinstance(arg, CallbackQuery):
                callback = arg
                bot = arg.bot
                user_id = arg.from_user.id
                break
        
        if not bot or not user_id:
            logger.error("Декоратор check_subscription: не найдены bot и user_id")
            return await func(*args, **kwargs)
        
        # Проверяем подписку
        is_subscribed = await check_user_subscription(bot, user_id)
        
        if not is_subscribed:
            # Отправляем сообщение о необходимости подписки
            if message:
                await message.answer(
                    "⚠️ <b>Требуется подписка на канал</b>\n\n"
                    "Чтобы использовать бота, вы должны быть подписаны на @matvuktuk",
                    parse_mode="HTML",
                    reply_markup=get_subscription_check_keyboard()
                )
            elif callback:
                await callback.answer(
                    "⚠️ Вы не подписаны на канал @matvuktuk",
                    show_alert=True
                )
            
            logger.warning(f"Пользователь {user_id} пытался использовать функцию без подписки")
            return
        
        # Если подписан - выполняем функцию
        return await func(*args, **kwargs)
    
    return wrapper

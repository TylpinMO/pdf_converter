import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from config import CHANNEL_USERNAME, ADMIN_ID

logger = logging.getLogger(__name__)


async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """
    Проверка подписки пользователя на канал @matvuktuk
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя Telegram
        
    Returns:
        True если подписан, False если не подписан
        Для админа возвращает True (обходит проверку подписки)
    """
    try:
        # Админ всегда может пользоваться ботом (без проверки подписки)
        if user_id == ADMIN_ID:
            logger.info(f"Проверка подписки админа {user_id}: пропущена (админ)")
            return True
        
        # Получаем информацию о членстве пользователя в канале
        chat_member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )
        
        # Проверяем статус
        # Статусы подписки: 'member', 'administrator', 'creator'
        # Статусы отписки: 'left', 'kicked'
        status = chat_member.status
        
        is_subscribed = status in ['member', 'administrator', 'creator']
        
        logger.info(f"Проверка подписки пользователя {user_id}: {status} → {'Подписан' if is_subscribed else 'Не подписан'}")
        return is_subscribed
        
    except TelegramBadRequest as e:
        # Ошибка доступа к списку участников (канал приватный или бот не админ)
        if "member list is inaccessible" in str(e):
            logger.warning(f"Невозможно проверить подписку {user_id}: канал приватный или бот не админ. Требуется подписка, но проверка невозможна.")
            # Не пускаем пользователя если не можем проверить подписку
            return False
        else:
            logger.error(f"Ошибка Telegram API при проверке подписки {user_id}: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки пользователя {user_id}: {e}", exc_info=True)
        # При других ошибках - не пускаем пользователя для безопасности
        return False

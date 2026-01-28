import logging
from datetime import datetime, timedelta, timezone
from config import DAILY_LIMIT

logger = logging.getLogger(__name__)

# Moscow timezone (UTC+3)
MSK = timezone(timedelta(hours=3))


def get_msk_date():
    """Получение текущей даты в MSK (UTC+3)"""
    return datetime.now(MSK).date()


def get_msk_datetime():
    """Получение текущего времени в MSK (UTC+3)"""
    return datetime.now(MSK)


async def can_user_perform_operation(db, user_id: int) -> tuple[bool, str]:
    """
    Проверка может ли пользователь выполнить операцию
    
    Args:
        db: Экземпляр Database
        user_id: ID пользователя
        
    Returns:
        Кортеж (может_ли_выполнить, сообщение)
    """
    try:
        # Проверяем забанен ли пользователь
        is_banned = await db.is_user_banned(user_id)
        if is_banned:
            return False, "🚫 Вы забанены в боте"
        
        # Если лимит снят - разрешаем
        is_unlimited = await db.is_user_unlimited(user_id)
        if is_unlimited:
            return True, "✅ Лимиты не применяются (безлимит)"
        
        # Проверяем количество операций за сегодня (по MSK)
        today = get_msk_date()
        operations_today = await db.get_user_operations_today(user_id)
        
        if operations_today >= DAILY_LIMIT:
            return False, f"❌ Лимит исчерпан ({operations_today}/{DAILY_LIMIT}). Приходите завтра в 00:00 МСК ⏰"
        
        remaining = DAILY_LIMIT - operations_today
        return True, f"✅ Операций осталось: {remaining}/{DAILY_LIMIT}"
        
    except Exception as e:
        logger.error(f"Ошибка в can_user_perform_operation: {e}", exc_info=True)
        return False, "❌ Ошибка при проверке лимитов"


async def get_user_limit_info(db, user_id: int) -> dict:
    """
    Получение информации о лимитах пользователя
    
    Args:
        db: Экземпляр Database
        user_id: ID пользователя
        
    Returns:
        Словарь с информацией о лимитах
    """
    try:
        is_banned = await db.is_user_banned(user_id)
        is_unlimited = await db.is_user_unlimited(user_id)
        operations_today = await db.get_user_operations_today(user_id)
        
        return {
            'user_id': user_id,
            'is_banned': is_banned,
            'is_unlimited': is_unlimited,
            'operations_today': operations_today,
            'daily_limit': DAILY_LIMIT,
            'remaining': max(0, DAILY_LIMIT - operations_today) if not is_unlimited else float('inf'),
            'msk_date': get_msk_date(),
            'msk_time': get_msk_datetime()
        }
        
    except Exception as e:
        logger.error(f"Ошибка в get_user_limit_info: {e}", exc_info=True)
        return {}

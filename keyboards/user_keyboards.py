from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from config import ADMIN_ID

# ==================== Основное меню ====================
def get_main_menu(user_id: int = None) -> InlineKeyboardMarkup:
    """Главное меню пользователя (inline-кнопки под сообщением)"""
    keyboard = [
        [InlineKeyboardButton(text="📷 → PDF", callback_data="photos_to_pdf")],
        [InlineKeyboardButton(text="📄 → 📷", callback_data="pdf_to_photos")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="info"), 
         InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ]
    
    # Добавляем кнопку админки только для админа
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text="👨‍💼 Админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ==================== Кнопка Главная ====================
def get_home_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с единственной кнопкой Главная"""
    keyboard = [
        [KeyboardButton(text="🏠 Главная")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# ==================== Проверка подписки ====================
def get_subscription_check_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для проверки подписки"""
    keyboard = [
        [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")],
        [InlineKeyboardButton(text="🔗 Подписаться на канал", url="https://t.me/matvuktuk")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== Фото → PDF ====================
def get_photo_to_pdf_keyboard(count: int = 0) -> ReplyKeyboardMarkup:
    """Клавиатура для конвертации фото в PDF"""
    keyboard = [
        [KeyboardButton(text="✅ Создать PDF")],
        [KeyboardButton(text="🗑 Очистить"), KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# ==================== Подтверждение действий ====================
def get_confirm_keyboard(buttons: list = None) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения
    
    Args:
        buttons: Список кортежей (text, callback_data) или None для дефолтных кнопок
    
    Example:
        get_confirm_keyboard()  # Дефолтные кнопки Да/Нет
        get_confirm_keyboard([("❌ Отмена", "admin_menu")])  # Кастомная кнопка
    """
    if buttons is None:
        keyboard = [
            [InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes")],
            [InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text=text, callback_data=callback_data) for text, callback_data in buttons]
        ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

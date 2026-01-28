from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ==================== Главное меню админки ====================
def get_admin_main_menu() -> InlineKeyboardMarkup:
    """Главное меню админ-панели"""
    keyboard = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🔓 Добавить исключение", callback_data="admin_add_unlimited")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="❌ Выход", callback_data="admin_exit")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== Пагинация пользователей ====================
def get_users_pagination_keyboard(page: int, total_pages: int, total_users: int) -> InlineKeyboardMarkup:
    """Клавиатура для пагинации списка пользователей"""
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"admin_users_page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"admin_users_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопка возврата в меню
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== Управление пользователем ====================
def get_user_control_keyboard(user_id: int, is_unlimited: bool, is_banned: bool) -> InlineKeyboardMarkup:
    """Клавиатура управления конкретным пользователем"""
    keyboard = []
    
    # Кнопка лимита
    if is_unlimited:
        limit_button = InlineKeyboardButton(text="🔒 Вернуть лимит", callback_data=f"admin_user_remove_unlimited_{user_id}")
    else:
        limit_button = InlineKeyboardButton(text="🔓 Снять лимит", callback_data=f"admin_user_set_unlimited_{user_id}")
    
    keyboard.append([limit_button])
    
    # Кнопка бана
    if is_banned:
        ban_button = InlineKeyboardButton(text="✅ Разбанить", callback_data=f"admin_user_unban_{user_id}")
    else:
        ban_button = InlineKeyboardButton(text="🚫 Забанить", callback_data=f"admin_user_ban_{user_id}")
    
    keyboard.append([ban_button])
    
    # Кнопка возврата
    keyboard.append([InlineKeyboardButton(text="⬅️ К списку пользователей", callback_data="admin_users_page_1")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== Подтверждение действия ====================
def get_confirm_keyboard(buttons: list) -> InlineKeyboardMarkup:
    """Клавиатура с кастомными кнопками (inline)
    
    Args:
        buttons: Список кортежей (text, callback_data)
    
    Example:
        get_confirm_keyboard([("❌ Отмена", "admin_menu")])
    """
    keyboard = [
        [InlineKeyboardButton(text=text, callback_data=callback_data) for text, callback_data in buttons]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== Настройки ====================
def get_settings_menu() -> InlineKeyboardMarkup:
    """Меню настроек"""
    keyboard = [
        [InlineKeyboardButton(text="📝 Изменить лимит", callback_data="admin_change_limit")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

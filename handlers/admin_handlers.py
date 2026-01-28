import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from config import ADMIN_ID, DAILY_LIMIT
from database import Database
from keyboards.admin_keyboards import (
    get_admin_main_menu,
    get_users_pagination_keyboard,
    get_user_control_keyboard,
    get_confirm_keyboard,
    get_settings_menu
)
from keyboards.user_keyboards import get_main_menu
from utils.states import AdminBroadcastStates, AdminSettingsStates

logger = logging.getLogger(__name__)
router = Router()
db = Database()

USERS_PER_PAGE = 10


# ==================== Фильтр только для админа ====================
async def is_admin(message: Message) -> bool:
    """Проверка, что пользователь - админ"""
    return message.from_user.id == ADMIN_ID


async def is_admin_callback(callback: CallbackQuery) -> bool:
    """Проверка, что пользователь - админ (для callback)"""
    return callback.from_user.id == ADMIN_ID


# ==================== Команда /admin ====================
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Открытие админ-панели"""
    try:
        if not await is_admin(message):
            await message.answer("❌ У вас нет доступа к админ-панели")
            logger.warning(f"Попытка доступа к админ-панели от пользователя {message.from_user.id}")
            return
        
        await message.answer(
            "🔐 <b>Админ-панель</b>\n\n"
            "Выберите раздел:",
            parse_mode="HTML",
            reply_markup=get_admin_main_menu()
        )
        logger.info(f"Админ {message.from_user.id} открыл панель")
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_admin: {e}", exc_info=True)
        await message.answer("❌ Ошибка при открытии админ-панели")


# ==================== Главное меню админки ====================
@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery):
    """Возврат в главное меню админки"""
    try:
        if not await is_admin_callback(callback):
            await callback.answer("❌ У вас нет доступа", show_alert=True)
            return
        
        await callback.message.edit_text(
            "🔐 <b>Админ-панель</b>\n\n"
            "Выберите раздел:",
            parse_mode="HTML",
            reply_markup=get_admin_main_menu()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_menu: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


# ==================== Статистика ====================
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика бота"""
    try:
        if not await is_admin_callback(callback):
            await callback.answer("❌ У вас нет доступа", show_alert=True)
            return
        
        # Получаем статистику
        total_users = await db.get_total_users_count()
        active_today = await db.get_active_users_today()
        unlimited_users = await db.get_unlimited_users_count()
        ops_today = await db.get_operations_count(days=1)
        ops_week = await db.get_operations_count(days=7)
        ops_month = await db.get_operations_count(days=30)
        
        stats_text = (
            "📊 <b>Статистика</b>\n\n"
            f"👥 <b>Пользователи:</b>\n"
            f"   • Всего: {total_users}\n"
            f"   • Активны сегодня: {active_today}\n"
            f"   • С безлимитом: {unlimited_users}\n\n"
            f"📈 <b>Операции:</b>\n"
            f"   • Сегодня: {ops_today}\n"
            f"   • За неделю: {ops_week}\n"
            f"   • За месяц: {ops_month}\n\n"
            f"⚙️ <b>Текущий лимит:</b> {DAILY_LIMIT} операций/день"
        )
        
        await callback.message.edit_text(
            stats_text,
            parse_mode="HTML",
            reply_markup=get_admin_main_menu()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_stats: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)


# ==================== Список пользователей ====================
@router.callback_query(F.data.startswith("admin_users"))
async def admin_users(callback: CallbackQuery):
    """Список пользователей с пагинацией"""
    try:
        if not await is_admin_callback(callback):
            await callback.answer("❌ У вас нет доступа", show_alert=True)
            return
        
        # Определяем страницу
        if callback.data == "admin_users":
            page = 1
        elif callback.data.startswith("admin_users_page_"):
            page = int(callback.data.split("_")[-1])
        else:
            page = 1
        
        # Получаем количество пользователей
        total_users = await db.get_total_users_count()
        total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE
        
        # Проверяем границы страницы
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages
        
        # Получаем пользователей для текущей страницы
        offset = (page - 1) * USERS_PER_PAGE
        users = await db.get_all_users(limit=USERS_PER_PAGE, offset=offset)
        
        if not users:
            users_text = "❌ Пользователей не найдено"
        else:
            users_text = "👥 <b>Список пользователей</b>\n\n"
            for i, user in enumerate(users, start=(page-1)*USERS_PER_PAGE + 1):
                status = "✅" if not user['is_banned'] else "🚫"
                unlimited = "🔓" if user['is_unlimited'] else "🔒"
                users_text += f"{i}. {status} @{user['username'] or user['first_name']} ({user['user_id']}) {unlimited}\n"
        
        users_text += f"\n(Страница {page}/{total_pages})"
        
        await callback.message.edit_text(
            users_text,
            parse_mode="HTML",
            reply_markup=get_users_pagination_keyboard(page, total_pages, total_users)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_users: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при получении списка пользователей", show_alert=True)


# ==================== Просмотр информации о пользователе ====================
@router.callback_query(F.data.startswith("admin_user_info_"))
async def admin_user_info(callback: CallbackQuery):
    """Просмотр информации о конкретном пользователе"""
    try:
        if not await is_admin_callback(callback):
            await callback.answer("❌ У вас нет доступа", show_alert=True)
            return
        
        user_id = int(callback.data.split("_")[-1])
        
        # Получаем информацию о пользователе
        user = await db.get_user(user_id)
        operations_today = await db.get_user_operations_today(user_id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        user_info = (
            f"👤 <b>Информация о пользователе</b>\n\n"
            f"<b>ID:</b> {user['user_id']}\n"
            f"<b>Username:</b> @{user['username'] or 'не установлен'}\n"
            f"<b>Имя:</b> {user['first_name']}\n"
            f"<b>Дата регистрации:</b> {user['registration_date']}\n\n"
            f"<b>Статистика:</b>\n"
            f"   • Операций сегодня: {operations_today}/{DAILY_LIMIT}\n"
            f"   • Лимит снят: {'✅ Да' if user['is_unlimited'] else '❌ Нет'}\n"
            f"   • Статус: {'🚫 Забанен' if user['is_banned'] else '✅ Активен'}"
        )
        
        await callback.message.edit_text(
            user_info,
            parse_mode="HTML",
            reply_markup=get_user_control_keyboard(user_id, user['is_unlimited'], user['is_banned'])
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_user_info: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при получении информации", show_alert=True)


# ==================== Управление лимитом ====================
@router.callback_query(F.data.startswith("admin_user_set_unlimited_"))
async def admin_set_unlimited(callback: CallbackQuery):
    """Снятие лимита пользователю"""
    try:
        if not await is_admin_callback(callback):
            await callback.answer("❌ У вас нет доступа", show_alert=True)
            return
        
        user_id = int(callback.data.split("_")[-1])
        await db.set_user_unlimited(user_id, True)
        
        # Отправляем уведомление пользователю
        try:
            await callback.bot.send_message(
                user_id,
                "🎉 <b>Поздравляем!</b>\n\n"
                "Для вас снят лимит на использование бота!\n"
                "Теперь вы можете выполнять неограниченное количество операций.\n\n"
                "Спасибо за использование нашего бота! 🚀",
                parse_mode="HTML"
            )
        except Exception:
            pass  # Игнорируем ошибки отправки уведомления
        
        await callback.answer(f"✅ Лимит снят для пользователя {user_id}", show_alert=True)
        
        # Обновляем информацию
        user = await db.get_user(user_id)
        if user:
            await admin_user_info(callback)
        
    except Exception as e:
        logger.error(f"Ошибка в admin_set_unlimited: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при изменении лимита", show_alert=True)


@router.callback_query(F.data.startswith("admin_user_remove_unlimited_"))
async def admin_remove_unlimited(callback: CallbackQuery):
    """Возврат лимита пользователю"""
    try:
        if not await is_admin_callback(callback):
            await callback.answer("❌ У вас нет доступа", show_alert=True)
            return
        
        user_id = int(callback.data.split("_")[-1])
        await db.set_user_unlimited(user_id, False)
        
        await callback.answer(f"✅ Лимит возвращен для пользователя {user_id}", show_alert=True)
        
        # Обновляем информацию
        user = await db.get_user(user_id)
        if user:
            await admin_user_info(callback)
        
    except Exception as e:
        logger.error(f"Ошибка в admin_remove_unlimited: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при изменении лимита", show_alert=True)


# ==================== Управление баном ====================
@router.callback_query(F.data.startswith("admin_user_ban_"))
async def admin_ban_user(callback: CallbackQuery):
    """Бан пользователя"""
    try:
        if not await is_admin_callback(callback):
            await callback.answer("❌ У вас нет доступа", show_alert=True)
            return
        
        user_id = int(callback.data.split("_")[-1])
        await db.set_user_banned(user_id, True)
        
        await callback.answer(f"✅ Пользователь {user_id} забанен", show_alert=True)
        
        # Обновляем информацию
        user = await db.get_user(user_id)
        if user:
            await admin_user_info(callback)
        
    except Exception as e:
        logger.error(f"Ошибка в admin_ban_user: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при бане пользователя", show_alert=True)


@router.callback_query(F.data.startswith("admin_user_unban_"))
async def admin_unban_user(callback: CallbackQuery):
    """Разбан пользователя"""
    try:
        if not await is_admin_callback(callback):
            await callback.answer("❌ У вас нет доступа", show_alert=True)
            return
        
        user_id = int(callback.data.split("_")[-1])
        await db.set_user_banned(user_id, False)
        
        await callback.answer(f"✅ Пользователь {user_id} разбанен", show_alert=True)
        
        # Обновляем информацию
        user = await db.get_user(user_id)
        if user:
            await admin_user_info(callback)
        
    except Exception as e:
        logger.error(f"Ошибка в admin_unban_user: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при разбане пользователя", show_alert=True)


# ==================== Выход из админки ====================
@router.callback_query(F.data == "admin_exit")
async def admin_exit(callback: CallbackQuery):
    """Выход из админ-панели"""
    try:
        await callback.message.edit_text(
            "👋 Выход из админ-панели\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_main_menu(callback.from_user.id)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в admin_exit: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


# ==================== ДОБАВЛЕНИЕ ИСКЛЮЧЕНИЯ (Unlimited) ====================

@router.callback_query(F.data == "admin_add_unlimited")
async def admin_add_unlimited(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления исключения - админ вводит ID пользователя"""
    if not await is_admin_callback(callback):
        return
    
    try:
        await callback.message.edit_text(
            "🔓 <b>Добавить исключение</b>\n\n"
            "Введите ID пользователя (целое число):",
            parse_mode="HTML",
            reply_markup=get_confirm_keyboard([("❌ Отмена", "admin_menu")])
        )
        await state.set_state(AdminSettingsStates.waiting_for_unlimited_id)
    except Exception as e:
        logger.error(f"Ошибка в admin_add_unlimited: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(AdminSettingsStates.waiting_for_unlimited_id)
async def receive_user_id_for_unlimited(message: Message, state: FSMContext):
    """Получение ID пользователя для добавления исключения"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        try:
            user_id = int(message.text)
        except ValueError:
            await message.answer("❌ Пожалуйста, введите целое число (ID пользователя)")
            return
        
        # Проверяем, существует ли пользователь
        user = await db.get_user(user_id)
        if not user:
            await message.answer(f"❌ Пользователь с ID {user_id} не найден в базе")
            return
        
        # Снимаем лимит (делаем is_unlimited = 1)
        await db.set_user_unlimited(user_id, True)
        await state.clear()
        
        # Отправляем подтверждение и возвращаем в меню
        await message.answer(
            f"✅ <b>Исключение добавлено</b>\n\n"
            f"Пользователю {user['first_name']} (ID: {user_id}) снят лимит.",
            parse_mode="HTML",
            reply_markup=get_confirm_keyboard([("🏠 Главное меню", "admin_menu")])
        )
        
        
    except Exception as e:
        logger.error(f"Ошибка в receive_user_id_for_unlimited: {e}", exc_info=True)
        await message.answer("❌ Ошибка при обработке")


# ==================== РАССЫЛКА (Broadcast) ====================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начало процесса рассылки - админ вводит сообщение"""
    if not await is_admin_callback(callback):
        return
    
    try:
        await callback.message.edit_text(
            "📢 <b>Рассылка</b>\n\n"
            "Отправьте сообщение (текст или фото) для рассылки всем пользователям:",
            parse_mode="HTML",
            reply_markup=get_confirm_keyboard([("❌ Отмена", "admin_exit")])
        )
        await state.set_state(AdminBroadcastStates.waiting_for_message)
    except Exception as e:
        logger.error(f"Ошибка в admin_broadcast: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(AdminBroadcastStates.waiting_for_message)
async def receive_broadcast_message(message: Message, state: FSMContext):
    """Получение сообщения для рассылки"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        # Сохраняем данные сообщения
        message_data = {}
        
        # Обрабатываем текст
        if message.text:
            message_data['text'] = message.text
        elif message.caption:
            message_data['text'] = message.caption
        
        # Обрабатываем фото
        if message.photo:
            # Берем фото наибольшего размера
            photo = message.photo[-1]
            message_data['photo_file_id'] = photo.file_id
        
        if not message_data:
            await message.answer("❌ Пожалуйста, отправьте текст или фото")
            return
        
        # Получаем количество активных пользователей (не забанены)
        total_users = await db.get_unbanned_users_count()
        
        await state.update_data(**message_data)
        await state.set_state(AdminBroadcastStates.confirming_send)
        
        # Выводим превью и просим подтверждение
        preview_text = f"📢 <b>Подтверждение рассылки</b>\n\n"
        if message_data.get('text'):
            preview_text += f"📝 <b>Текст:</b>\n{message_data['text']}\n\n"
        if message_data.get('photo_file_id'):
            preview_text += "📷 <b>С фото</b>\n\n"
        
        preview_text += f"👥 <b>Получат сообщение:</b> {total_users} пользователей\n\n"
        preview_text += "Отправить рассылку?"
        
        if message_data.get('photo_file_id'):
            await message.answer_photo(
                photo=message_data['photo_file_id'],
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=get_confirm_keyboard([
                    ("✅ Отправить", "admin_send_broadcast"),
                    ("❌ Отмена", "admin_exit")
                ])
            )
        else:
            await message.answer(
                preview_text,
                parse_mode="HTML",
                reply_markup=get_confirm_keyboard([
                    ("✅ Отправить", "admin_send_broadcast"),
                    ("❌ Отмена", "admin_exit")
                ])
            )
        
    except Exception as e:
        logger.error(f"Ошибка в receive_broadcast_message: {e}", exc_info=True)
        await message.answer("❌ Ошибка при обработке сообщения")


@router.callback_query(F.data == "admin_send_broadcast", StateFilter(AdminBroadcastStates.confirming_send))
async def send_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отправка рассылки всем пользователям"""
    if not await is_admin_callback(callback):
        return
    
    try:
        data = await state.get_data()
        await state.clear()
        
        # Получаем всех незабаненных пользователей
        unbanned_users = await db.get_unbanned_users_list()
        
        sent_count = 0
        failed_count = 0
        failed_users = []
        
        # Отправляем сообщение каждому пользователю
        for user_id in unbanned_users:
            try:
                if data.get('photo_file_id'):
                    await callback.bot.send_photo(
                        chat_id=user_id,
                        photo=data['photo_file_id'],
                        caption=data.get('text', ''),
                        parse_mode="HTML" if data.get('text') else None
                    )
                else:
                    await callback.bot.send_message(
                        chat_id=user_id,
                        text=data.get('text', ''),
                        parse_mode="HTML"
                    )
                sent_count += 1
            except Exception as e:
                logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                failed_count += 1
                failed_users.append(user_id)
        
        # Отчет админу
        report_text = f"✅ <b>Рассылка завершена</b>\n\n"
        report_text += f"📤 <b>Отправлено:</b> {sent_count} пользователям\n"
        if failed_count > 0:
            report_text += f"❌ <b>Не отправлено:</b> {failed_count} пользователям\n"
        report_text += f"\n📊 <b>Всего пользователей:</b> {len(unbanned_users)}"
        
        await callback.message.edit_text(
            report_text,
            parse_mode="HTML",
            reply_markup=get_confirm_keyboard([("🏠 Главное меню", "admin_menu")])
        )
        
        logger.info(f"Админ {ADMIN_ID} отправил рассылку {sent_count} пользователям (не отправлено: {failed_count})")
        
    except Exception as e:
        logger.error(f"Ошибка в send_broadcast: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при отправке рассылки", show_alert=True)


# ==================== НАСТРОЙКИ ====================

@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    """Меню настроек администратора"""
    if not await is_admin_callback(callback):
        return
    
    try:
        current_limit = await db.get_setting("DAILY_LIMIT")
        if current_limit is None:
            current_limit = DAILY_LIMIT
        else:
            current_limit = int(current_limit)
        
        settings_text = f"⚙️ <b>Настройки</b>\n\n"
        settings_text += f"📊 <b>Текущий дневной лимит:</b> {current_limit} операций\n\n"
        settings_text += "Выберите действие:"
        
        await callback.message.edit_text(
            settings_text,
            parse_mode="HTML",
            reply_markup=get_settings_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка в admin_settings: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin_change_limit")
async def admin_change_limit(callback: CallbackQuery, state: FSMContext):
    """Начало изменения лимита"""
    if not await is_admin_callback(callback):
        return
    
    try:
        current_limit = await db.get_setting("DAILY_LIMIT")
        if current_limit is None:
            current_limit = DAILY_LIMIT
        else:
            current_limit = int(current_limit)
        
        await callback.message.edit_text(
            f"⚙️ <b>Изменение дневного лимита</b>\n\n"
            f"Текущий лимит: <b>{current_limit}</b> операций\n\n"
            f"Введите новый лимит (целое число, мин. 1):",
            parse_mode="HTML",
            reply_markup=get_confirm_keyboard([("❌ Отмена", "admin_settings")])
        )
        await state.set_state(AdminSettingsStates.waiting_for_new_limit)
    except Exception as e:
        logger.error(f"Ошибка в admin_change_limit: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(AdminSettingsStates.waiting_for_new_limit)
async def receive_new_limit(message: Message, state: FSMContext):
    """Получение нового значения лимита"""
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        # Пытаемся преобразовать в целое число
        try:
            new_limit = int(message.text)
        except ValueError:
            await message.answer("❌ Пожалуйста, введите целое число")
            return
        
        # Проверяем валидность
        if new_limit < 1:
            await message.answer("❌ Лимит должен быть не менее 1")
            return
        
        if new_limit > 1000:
            await message.answer("❌ Лимит не должен превышать 1000")
            return
        
        # Получаем текущий лимит
        current_limit = await db.get_setting("DAILY_LIMIT")
        if current_limit is None:
            current_limit = DAILY_LIMIT
        else:
            current_limit = int(current_limit)
        
        # Сохраняем в state
        await state.update_data(new_limit=new_limit, old_limit=current_limit)
        await state.set_state(AdminSettingsStates.confirming_limit)
        
        # Просим подтверждение
        confirm_text = f"⚙️ <b>Подтверждение изменения лимита</b>\n\n"
        confirm_text += f"Текущий лимит: <b>{current_limit}</b>\n"
        confirm_text += f"Новый лимит: <b>{new_limit}</b>\n\n"
        confirm_text += "Подтвердить изменение?"
        
        await message.answer(
            confirm_text,
            parse_mode="HTML",
            reply_markup=get_confirm_keyboard([
                ("✅ Подтвердить", "admin_confirm_limit"),
                ("❌ Отмена", "admin_settings")
            ])
        )
    except Exception as e:
        logger.error(f"Ошибка в receive_new_limit: {e}", exc_info=True)
        await message.answer("❌ Ошибка при обработке значения")


@router.callback_query(F.data == "admin_confirm_limit", StateFilter(AdminSettingsStates.confirming_limit))
async def confirm_change_limit(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и сохранение нового лимита"""
    if not await is_admin_callback(callback):
        return
    
    try:
        data = await state.get_data()
        new_limit = data.get('new_limit')
        old_limit = data.get('old_limit')
        
        # Сохраняем новый лимит в базу
        await db.set_setting("DAILY_LIMIT", str(new_limit))
        await state.clear()
        
        result_text = f"✅ <b>Лимит обновлен</b>\n\n"
        result_text += f"Было: <b>{old_limit}</b> операций/день\n"
        result_text += f"Стало: <b>{new_limit}</b> операций/день\n\n"
        result_text += "⚠️ <i>Пользователи с безлимитом не затронуты</i>"
        
        await callback.message.edit_text(
            result_text,
            parse_mode="HTML",
            reply_markup=get_confirm_keyboard([("🏠 Главное меню", "admin_menu")])
        )
        
        
    except Exception as e:
        logger.error(f"Ошибка в confirm_change_limit: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при сохранении лимита", show_alert=True)


# ==================== Noop callback (для неактивных кнопок) ====================
@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Пустой callback для кнопок, которые не должны делать ничего"""
    await callback.answer()

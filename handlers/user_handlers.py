import logging
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, User, FSInputFile, InputMediaPhoto, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime
from config import ADMIN_ID, DAILY_LIMIT, MAX_PHOTO_SIZE_MB, MAX_PDF_SIZE_MB
from database import Database
from keyboards.user_keyboards import get_main_menu, get_subscription_check_keyboard, get_photo_to_pdf_keyboard, get_home_keyboard
from utils.states import PhotoToPDFStates, PDFToPhotoStates
from utils.pdf_converter import photos_to_pdf, check_file_size, get_file_size_mb, cleanup_temp_files, pdf_to_photos
from utils.subscription_checker import check_user_subscription
from utils.decorators import check_subscription
from utils.limit_checker import can_user_perform_operation, get_user_limit_info, get_msk_date
import os
from pathlib import Path

logger = logging.getLogger(__name__)
router = Router()
db = Database()

# Временное хранилище фото пользователей
user_photos = {}
# Хранилище ID сообщений со счетчиком
user_counter_messages = {}
# Блокировки для предотвращения гонки при параллельной обработке фото
user_locks = {}

# ==================== Приветственное сообщение ====================
WELCOME_MESSAGE = """
👋 <b>Добро пожаловать в PDF Bot!</b>

Этот бот помогает вам конвертировать:
📷 <b>Фотографии → PDF</b> - объедините до 20 фото в один PDF документ
📄 <b>PDF → Изображения</b> - разбейте PDF на отдельные JPG файлы

⚙️ <b>Основные возможности:</b>
• Быстрая конвертация без потери качества
• Поддержка больших файлов (фото до 15 МБ, PDF до 100 МБ)
• Лимит: 10 операций в день (сброс в 00:00 МСК)
• Все файлы удаляются после обработки

⚠️ <b>Важно:</b> Для работы с ботом вы должны быть подписаны на канал @matvuktuk

Готовы начать? 🚀
"""

HELP_MESSAGE = """
<b>📚 Справка по использованию</b>

<b>📷 → PDF (Конвертация фото в PDF):</b>
1. Нажмите кнопку "📷 → PDF"
2. Отправьте фотографии (до 20 шт, в одном или разных сообщениях)
3. Нажмите "✅ Создать PDF"
4. Скачайте готовый файл

<b>📄 → 📷 (Конвертация PDF в фото):</b>
1. Нажмите кнопку "📄 → 📷"
2. Отправьте PDF файл (до 100 МБ)
3. Подождите обработки
4. Скачайте изображения (по одному или группами)

<b>⚠️ Ограничения:</b>
• Максимум 10 операций в день
• Размер фото: до 15 МБ
• Размер PDF: до 100 МБ
• Максимум 20 фото в одном PDF

<b>❓ У вас остались вопросы?</b>
Напишите в личные сообщения @matvuktuk
"""

PROFILE_MESSAGE = """
<b>👤 Ваш профиль</b>

<b>Статистика:</b>
• Операций сегодня: {operations_today}
• Лимит снят: {is_unlimited}
• Статус: {status}

Лимит сбрасывается каждый день в 00:00 МСК ⏰
"""


# ==================== Команда /start ====================
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        
        # Регистрируем пользователя в БД
        await db.register_user(user_id, username, first_name)

        
        # Отправляем приветствие с кнопкой Главная
        await message.answer(
            WELCOME_MESSAGE,
            parse_mode="HTML",
            reply_markup=get_home_keyboard()
        )
        await message.answer(
            "Проверьте подписку на канал:",
            reply_markup=get_subscription_check_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_start: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


# ==================== Команда /help ====================
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    try:
        await message.answer(
            HELP_MESSAGE,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_help: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")


# ==================== Проверка подписки ====================
@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery):
    """Проверка подписки на канал"""
    try:
        user_id = callback.from_user.id
        
        # Проверяем подписку
        is_subscribed = await check_user_subscription(callback.bot, user_id)
        
        if is_subscribed:
            await callback.answer("✅ Вы подписаны на @matvuktuk!", show_alert=False)
            
            # Удаляем старое сообщение с проверкой подписки и отправляем главное меню
            await callback.message.delete()
            await callback.message.answer(
                "✅ <b>Спасибо за подписку!</b>\n\n"
                "Теперь вы можете использовать все функции бота.\n\n"
                "Выберите действие:",
                parse_mode="HTML",
                reply_markup=get_main_menu(user_id)
            )
        else:
            await callback.answer(
                "⚠️ Вы еще не подписаны на канал @matvuktuk",
                show_alert=True
            )
        
    except Exception as e:
        logger.error(f"Ошибка в check_subscription_callback: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при проверке подписки", show_alert=True)


# ==================== Кнопка "Информация" ====================
@router.callback_query(F.data == "info")
async def info_button(callback: CallbackQuery):
    """Обработчик кнопки 'Информация'"""
    try:
        user_id = callback.from_user.id
        
        # Проверяем подписку
        is_subscribed = await check_user_subscription(callback.bot, user_id)
        if not is_subscribed:
            await callback.message.answer(
                "⚠️ <b>Требуется подписка на канал</b>\n\n"
                "Чтобы использовать бота, вы должны быть подписаны на @matvuktuk",
                parse_mode="HTML",
                reply_markup=get_subscription_check_keyboard()
            )
            await callback.answer()
            return
        
        await callback.message.answer(
            HELP_MESSAGE,
            parse_mode="HTML",
            reply_markup=get_main_menu(callback.from_user.id)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в info_button: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# ==================== Кнопка "Профиль" ====================
@router.callback_query(F.data == "profile")
async def profile_button(callback: CallbackQuery):
    """Обработчик кнопки 'Профиль'"""
    try:
        user_id = callback.from_user.id
        
        # Проверяем подписку
        is_subscribed = await check_user_subscription(callback.bot, user_id)
        if not is_subscribed:
            await callback.message.answer(
                "⚠️ <b>Требуется подписка на канал</b>\n\n"
                "Чтобы использовать бота, вы должны быть подписаны на @matvuktuk",
                parse_mode="HTML",
                reply_markup=get_subscription_check_keyboard()
            )
            await callback.answer()
            return
        
        # Получаем информацию о пользователе и лимитах
        user = await db.get_user(user_id)
        limit_info = await get_user_limit_info(db, user_id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден. Напишите /start", show_alert=True)
            return
        
        status = "✅ Активный" if not user['is_banned'] else "🚫 Забанен"
        unlimited_text = "✅ Да" if limit_info.get('is_unlimited') else "❌ Нет"
        
        # Для безлимитных пользователей показываем ∞ вместо числа
        if limit_info.get('is_unlimited'):
            limit_display = "∞ (безлимит)"
        else:
            limit_display = f"{limit_info.get('operations_today', 0)}/{limit_info.get('daily_limit', DAILY_LIMIT)}"
        
        profile_text = PROFILE_MESSAGE.format(
            operations_today=limit_display,
            daily_limit="",  # Пустая строка, т.к. уже включили в operations_today
            is_unlimited=unlimited_text,
            status=status
        )
        
        await callback.message.answer(
            profile_text,
            parse_mode="HTML",
            reply_markup=get_main_menu(user_id)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в profile_button: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# ==================== Кнопка "Админ-панель" ====================
@router.callback_query(F.data == "admin_panel")
async def admin_panel_button(callback: CallbackQuery):
    """Обработчик кнопки 'Админ-панель' (только для админа)"""
    try:
        user_id = callback.from_user.id
        
        # Проверяем, что это админ
        if user_id != ADMIN_ID:
            await callback.answer("❌ У вас нет доступа к админ-панели", show_alert=True)
            return
        
        # Импортируем функцию из keyboards
        from keyboards.admin_keyboards import get_admin_main_menu
        
        await callback.message.answer(
            "👨‍💼 <b>Админ-панель</b>\n\n"
            "Выберите раздел:",
            parse_mode="HTML",
            reply_markup=get_admin_main_menu()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в admin_panel_button: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# ==================== Заглушки для основных функций ====================
@router.callback_query(F.data == "photos_to_pdf")
async def photo_to_pdf_button(callback: CallbackQuery, state: FSMContext):
    """Начало конвертации фото в PDF"""
    try:
        user_id = callback.from_user.id
        
        # Проверяем подписку
        is_subscribed = await check_user_subscription(callback.bot, user_id)
        if not is_subscribed:
            await callback.message.answer(
                "⚠️ <b>Требуется подписка на канал</b>\n\n"
                "Чтобы использовать эту функцию, вы должны быть подписаны на @matvuktuk",
                parse_mode="HTML",
                reply_markup=get_subscription_check_keyboard()
            )
            await callback.answer()
            return
        
        # Инициализируем хранилище для этого пользователя
        if user_id not in user_photos:
            user_photos[user_id] = []
        
        # Переходим в состояние ожидания фото
        await state.set_state(PhotoToPDFStates.waiting_for_photos)
        
        # Отправляем сообщение с клавиатурой
        await callback.message.answer(
            "📷 <b>Конвертация фото в PDF</b>\n\n"
            "Отправьте от 1 до 20 фотографий (можно несколько сообщениями)\n"
            "Каждое фото должно быть не более 15 МБ",
            parse_mode="HTML",
            reply_markup=get_photo_to_pdf_keyboard(len(user_photos[user_id]))
        )
        await callback.answer()
        
        
    except Exception as e:
        logger.error(f"Ошибка в photo_to_pdf_button: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# ==================== Конвертация PDF → Фото ====================
@router.callback_query(F.data == "pdf_to_photos")
async def pdf_to_photo_button(callback: CallbackQuery, state: FSMContext):
    """Начало конвертации PDF в фото"""
    try:
        user_id = callback.from_user.id
        
        # Проверяем подписку
        is_subscribed = await check_user_subscription(callback.bot, user_id)
        if not is_subscribed:
            await callback.message.answer(
                "⚠️ <b>Требуется подписка на канал</b>\n\n"
                "Чтобы использовать эту функцию, вы должны быть подписаны на @matvuktuk",
                parse_mode="HTML",
                reply_markup=get_subscription_check_keyboard()
            )
            await callback.answer()
            return
        
        await state.set_state(PDFToPhotoStates.waiting_for_pdf)
        
        await callback.message.answer(
            "📄 <b>Конвертация PDF в фото</b>\n\n"
            "Отправьте PDF файл (не более 100 МБ)\n"
            "Каждая страница будет сохранена как JPG",
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в pdf_to_photo_button: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


# ==================== Получение фото ====================
@router.message(PhotoToPDFStates.waiting_for_photos, F.photo)
async def receive_photo(message: Message, state: FSMContext):
    """Получение фото от пользователя"""
    try:
        user_id = message.from_user.id
        
        # Проверяем количество фото
        if len(user_photos[user_id]) >= 20:
            await message.answer(
                "❌ Максимум 20 фото за раз!\n"
                "Нажмите ✅ Создать PDF для завершения"
            )
            return
        
        # Проверяем размер файла
        file_size = message.photo[-1].file_size
        if not check_file_size(file_size, MAX_PHOTO_SIZE_MB):
            size_mb = get_file_size_mb(file_size)
            await message.answer(
                f"❌ Фото слишком большое: {size_mb} МБ (макс. {MAX_PHOTO_SIZE_MB} МБ)\n"
                "Пожалуйста, отправьте меньшее фото"
            )
            return
        
        # Сохраняем информацию о фото
        photo_data = {
            'file_id': message.photo[-1].file_id,
            'file_unique_id': message.photo[-1].file_unique_id
        }
        user_photos[user_id].append(photo_data)
        
        count = len(user_photos[user_id])
        
        # Получаем или создаем блокировку для этого пользователя
        if user_id not in user_locks:
            user_locks[user_id] = asyncio.Lock()
        
        # Используем блокировку для избежания гонки при параллельной обработке
        async with user_locks[user_id]:
            # Проверяем, есть ли уже сообщение со счетчиком для этого пользователя
            counter_message_id = user_counter_messages.get(user_id)
            
            # Если это первое фото - создаем сообщение со счетчиком
            if counter_message_id is None:
                counter_msg = await message.answer(
                    f"📊 Загружено: {count}/20 фото",
                    parse_mode="HTML"
                )
                # Сохраняем ID сообщения в памяти (не в state!)
                user_counter_messages[user_id] = counter_msg.message_id
                logger.info(f"Создано сообщение счетчика для пользователя {user_id}: {counter_msg.message_id}")
            else:
                # Редактируем существующее сообщение со счетчиком
                try:
                    await message.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=counter_message_id,
                        text=f"📊 Загружено: {count}/20 фото",
                        parse_mode="HTML"
                    )
                    logger.debug(f"Обновлен счетчик для пользователя {user_id}: {count}/20")
                except Exception as e:
                    logger.warning(f"Не удалось обновить счетчик для {user_id}: {e}")
                    # Если не удалось отредактировать - создаем новое и обновляем ID
                    counter_msg = await message.answer(
                        f"📊 Загружено: {count}/20 фото",
                        parse_mode="HTML"
                    )
                    user_counter_messages[user_id] = counter_msg.message_id
        
        
    except Exception as e:
        logger.error(f"Ошибка в receive_photo: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении фото. Попробуйте позже.")


# ==================== Создание PDF ====================
@router.message(PhotoToPDFStates.waiting_for_photos, F.text == "✅ Создать PDF")
async def create_pdf(message: Message, state: FSMContext):
    """Создание PDF из загруженных фото"""
    try:
        user_id = message.from_user.id
        
        # Проверяем, загружены ли фото
        if user_id not in user_photos or not user_photos[user_id]:
            await message.answer(
                "⚠️ Сначала загрузите фото",
                reply_markup=get_photo_to_pdf_keyboard(0)
            )
            return
        
        count = len(user_photos[user_id])
        
        # Проверяем лимит используя новый функционал
        can_perform, limit_message = await can_user_perform_operation(db, user_id)
        if not can_perform:
            await message.answer(
                limit_message,
                reply_markup=get_photo_to_pdf_keyboard(count)
            )
            return
        
        await message.answer(
            "⏳ Скачивание фото...",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Скачиваем фото и конвертируем в PDF
        photos_list = user_photos[user_id]
        temp_dir = f"temp_{user_id}"
        
        try:
            os.makedirs(temp_dir, exist_ok=True)
            
            # Скачиваем фото через bot.download()
            photo_paths = []
            for idx, photo_info in enumerate(photos_list, 1):
                try:
                    file_id = photo_info['file_id']
                    file_path = await message.bot.get_file(file_id)
                    photo_path = f"{temp_dir}/photo_{idx:02d}.jpg"
                    await message.bot.download_file(file_path.file_path, photo_path)
                    photo_paths.append(photo_path)
                    
                    # Обновляем статус
                    await message.answer(
                        f"⏳ Скачивание фото... ({idx}/{len(photos_list)})",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Ошибка при скачивании фото {idx}: {e}")
                    await message.answer(f"⚠️ Ошибка при скачивании фото {idx}")
                    return
            
            # Конвертируем в PDF
            await message.answer(
                "🔨 Конвертация фото в PDF...",
                parse_mode="HTML"
            )
            
            success = await photos_to_pdf(photo_paths, f"{temp_dir}/document.pdf")
            if success:
                pdf_file = FSInputFile(f"{temp_dir}/document.pdf")
                await message.answer_document(pdf_file, caption="✅ Ваш PDF готов!")
                await db.increment_user_operations(user_id)
                logger.info(f"Пользователь {user_id} успешно создал PDF из {len(photo_paths)} фото")
            else:
                await message.answer("❌ Ошибка при создании PDF")
                return
            
        finally:
            # Очищаем временные файлы
            if os.path.exists(temp_dir):
                try:
                    for file in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, file)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    os.rmdir(temp_dir)
                except Exception:
                    pass  # Игнорируем ошибки очистки
        
        # Очищаем хранилище фото и счетчика
        user_photos[user_id] = []
        if user_id in user_counter_messages:
            del user_counter_messages[user_id]
        await state.clear()
        
        # Показываем кнопку Главная
        await message.answer(
            "✅ Готово!\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=get_home_keyboard()
        )
        await message.answer(
            "Используйте меню ниже:",
            reply_markup=get_main_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в create_pdf: {e}", exc_info=True)
        await message.answer("❌ Ошибка при создании PDF")


# ==================== Очистка фото ====================
@router.message(PhotoToPDFStates.waiting_for_photos, F.text == "🗑 Очистить")
async def clear_photos(message: Message, state: FSMContext):
    """Очистка загруженных фото"""
    try:
        user_id = message.from_user.id
        user_photos[user_id] = []
        if user_id in user_counter_messages:
            del user_counter_messages[user_id]
        await state.clear()
        
        await message.answer(
            "🗑 Фото очищены. Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_home_keyboard()
        )
        await message.answer(
            "Используйте меню ниже:",
            reply_markup=get_main_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в clear_photos: {e}", exc_info=True)
        await message.answer("❌ Ошибка")


# ==================== Отмена конвертации ====================
@router.message(PhotoToPDFStates.waiting_for_photos, F.text == "❌ Отмена")
async def cancel_pdf_conversion(message: Message, state: FSMContext):
    """Отмена конвертации фото в PDF"""
    try:
        user_id = message.from_user.id
        user_photos[user_id] = []
        if user_id in user_counter_messages:
            del user_counter_messages[user_id]
        await state.clear()
        
        await message.answer(
            "Конвертация отменена. Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_home_keyboard()
        )
        await message.answer(
            "Используйте меню ниже:",
            reply_markup=get_main_menu(user_id)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в cancel_pdf_conversion: {e}", exc_info=True)
        await message.answer("❌ Ошибка")


# ==================== Получение фото ====================
@router.message(PDFToPhotoStates.waiting_for_pdf, F.document)
async def receive_pdf(message: Message, state: FSMContext):
    """Получение PDF файла от пользователя"""
    try:
        user_id = message.from_user.id
        
        # Проверяем расширение файла
        file_name = message.document.file_name or ""
        if not file_name.lower().endswith('.pdf'):
            await message.answer(
                "❌ Это не PDF файл. Пожалуйста, отправьте PDF"
            )
            return
        
        # Проверяем размер файла
        file_size = message.document.file_size
        if not check_file_size(file_size, MAX_PDF_SIZE_MB):
            size_mb = get_file_size_mb(file_size)
            await message.answer(
                f"❌ PDF слишком большой: {size_mb} МБ (макс. {MAX_PDF_SIZE_MB} МБ)\n"
                "Пожалуйста, отправьте меньший файл"
            )
            return
        
        # Проверяем лимит
        can_perform, limit_message = await can_user_perform_operation(db, user_id)
        if not can_perform:
            await message.answer(limit_message)
            await state.clear()
            return
        
        # Сохраняем информацию о файле в FSM контекст
        await state.update_data(
            pdf_file_id=message.document.file_id,
            pdf_file_name=file_name
        )
        
        await message.answer(
            "⏳ Обработка PDF...",
            parse_mode="HTML"
        )
        
        # Скачиваем и конвертируем PDF
        temp_dir = f"temp_pdf_{user_id}"
        
        try:
            os.makedirs(temp_dir, exist_ok=True)
            
            # Скачиваем PDF
            pdf_path = os.path.join(temp_dir, "document.pdf")
            await message.bot.download(
                file=message.document.file_id,
                destination=pdf_path
            )
            
            # Конвертируем PDF в фото
            success, photo_paths = await pdf_to_photos(pdf_path, temp_dir)
            
            if success and photo_paths:
                # Сохраняем пути в контекст для удаления после отправки
                await state.update_data(temp_photos=photo_paths, temp_dir=temp_dir)
                
                # Отправляем фото медиагруппами (по 10 фото за раз)
                total_photos = len(photo_paths)
                sent_count = 0
                
                for i in range(0, total_photos, 10):
                    batch = photo_paths[i:i+10]
                    media = []
                    
                    for j, photo_path in enumerate(batch):
                        if j == 0:
                            # Добавляем caption только к первому фото в группе
                            media.append(InputMediaPhoto(media=FSInputFile(photo_path)))
                        else:
                            media.append(InputMediaPhoto(media=FSInputFile(photo_path)))
                    
                    # Отправляем медиагруппу
                    await message.answer_media_group(media=media)
                    sent_count += len(batch)
                    
                    # Если не последняя группа, показываем прогресс
                    if sent_count < total_photos:
                        await message.answer(
                            f"📸 Отправлено {sent_count}/{total_photos} фото...",
                            parse_mode="HTML"
                        )
                
                # Увеличиваем счетчик операций
                await db.increment_user_operations(user_id)
                
                await message.answer(
                    f"✅ Готово! Отправлено {total_photos} фото\n\n"
                    f"Выберите действие:",
                    parse_mode="HTML",
                    reply_markup=get_home_keyboard()
                )
                await message.answer(
                    "Используйте меню ниже:",
                    reply_markup=get_main_menu(user_id)
                )
                
            else:
                await message.answer(
                    "❌ Ошибка при конвертации PDF. Проверьте файл и попробуйте еще раз"
                )
                logger.error(f"Ошибка конвертации PDF для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке PDF: {e}", exc_info=True)
            await message.answer(
                "❌ Произошла ошибка при обработке PDF. Попробуйте позже."
            )
        
        finally:
            # Очищаем временные файлы
            if os.path.exists(temp_dir):
                try:
                    for file in os.listdir(temp_dir):
                        os.remove(os.path.join(temp_dir, file))
                    os.rmdir(temp_dir)
                except Exception as e:
                    logger.error(f"Ошибка при удалении временной директории: {e}")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в receive_pdf: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        await state.clear()


# ==================== Необработанные сообщения ====================
@router.message(PhotoToPDFStates.waiting_for_photos)
async def unexpected_message_in_photo_mode(message: Message):
    """Обработка неожиданных сообщений при ожидании фото"""
    await message.answer(
        "📸 Пожалуйста, отправляйте только фотографии\n\n"
        "Используйте кнопки для управления"
    )


@router.message(PDFToPhotoStates.waiting_for_pdf)
async def unexpected_message_in_pdf_mode(message: Message):
    """Обработка неожиданных сообщений при ожидании PDF"""
    await message.answer(
        "📄 Пожалуйста, отправляйте только PDF файл",
    )


# ==================== Кнопка Главная ====================
@router.message(F.text == "🏠 Главная")
async def home_button(message: Message):
    """Обработчик кнопки Главная"""
    try:
        user_id = message.from_user.id
        
        # Проверяем подписку
        is_subscribed = await check_user_subscription(message.bot, user_id)
        if not is_subscribed:
            await message.answer(
                "⚠️ <b>Требуется подписка на канал</b>\n\n"
                "Чтобы использовать бота, вы должны быть подписаны на @matvuktuk",
                parse_mode="HTML",
                reply_markup=get_subscription_check_keyboard()
            )
            return
        
        await message.answer(
            "🏠 Главное меню\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=get_main_menu(message.from_user.id)
        )
    except Exception as e:
        logger.error(f"Ошибка в home_button: {e}", exc_info=True)

from aiogram.fsm.state import State, StatesGroup


class PhotoToPDFStates(StatesGroup):
    """Состояния для конвертации фото в PDF"""
    waiting_for_photos = State()  # Ожидание получения фото
    confirming_pdf = State()      # Подтверждение создания PDF


class PDFToPhotoStates(StatesGroup):
    """Состояния для конвертации PDF в фото"""
    waiting_for_pdf = State()     # Ожидание получения PDF


class AdminBroadcastStates(StatesGroup):
    """Состояния для рассылки админом"""
    waiting_for_message = State() # Ожидание текста сообщения
    confirming_send = State()     # Подтверждение отправки


class AdminSettingsStates(StatesGroup):
    """Состояния для управления настройками"""
    waiting_for_new_limit = State()  # Ожидание нового лимита
    confirming_limit = State()       # Подтверждение изменения лимита
    waiting_for_unlimited_id = State()  # Ожидание ID для добавления исключения

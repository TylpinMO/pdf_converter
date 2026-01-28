import aiosqlite
from datetime import datetime, date
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_unlimited BOOLEAN DEFAULT 0,
                    is_banned BOOLEAN DEFAULT 0
                )
            """)
            
            # Таблица статистики использования
            await db.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date DATE,
                    operations_count INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, date)
                )
            """)
            
            # Таблица настроек
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            await db.commit()
            logger.info("База данных инициализирована")

    async def register_user(self, user_id: int, username: Optional[str], first_name: str):
        """Регистрация нового пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                    (user_id, username, first_name)
                )
                await db.commit()
                logger.info(f"Пользователь {user_id} зарегистрирован")
            except Exception as e:
                logger.error(f"Ошибка регистрации пользователя: {e}")

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

    async def is_user_banned(self, user_id: int) -> bool:
        """Проверка, забанен ли пользователь"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT is_banned FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row else False

    async def is_user_unlimited(self, user_id: int) -> bool:
        """Проверка, снят ли лимит у пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT is_unlimited FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row else False

    async def get_user_operations_today(self, user_id: int) -> int:
        """Получение количества операций пользователя за сегодня"""
        today = date.today()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT operations_count FROM usage_stats WHERE user_id = ? AND date = ?",
                (user_id, today)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def increment_user_operations(self, user_id: int):
        """Увеличение счетчика операций пользователя"""
        today = date.today()
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем, есть ли запись за сегодня
            async with db.execute(
                "SELECT operations_count FROM usage_stats WHERE user_id = ? AND date = ?",
                (user_id, today)
            ) as cursor:
                row = await cursor.fetchone()
            
            if row:
                # Обновляем счетчик
                await db.execute(
                    "UPDATE usage_stats SET operations_count = operations_count + 1 WHERE user_id = ? AND date = ?",
                    (user_id, today)
                )
            else:
                # Создаем новую запись
                await db.execute(
                    "INSERT INTO usage_stats (user_id, date, operations_count) VALUES (?, ?, 1)",
                    (user_id, today)
                )
            
            await db.commit()
            logger.info(f"Счетчик операций для пользователя {user_id} увеличен")

    async def set_user_unlimited(self, user_id: int, is_unlimited: bool):
        """Установка/снятие безлимитного режима для пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET is_unlimited = ? WHERE user_id = ?",
                (int(is_unlimited), user_id)
            )
            await db.commit()
            logger.info(f"Безлимитный режим для {user_id}: {is_unlimited}")

    async def set_user_banned(self, user_id: int, is_banned: bool):
        """Бан/разбан пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET is_banned = ? WHERE user_id = ?",
                (int(is_banned), user_id)
            )
            await db.commit()
            logger.info(f"Статус бана для {user_id}: {is_banned}")

    async def get_all_users(self, limit: int = 10, offset: int = 0) -> List[Dict]:
        """Получение списка всех пользователей с пагинацией"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users ORDER BY registration_date DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_total_users_count(self) -> int:
        """Получение общего количества пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_active_users_today(self) -> int:
        """Получение количества активных пользователей сегодня"""
        today = date.today()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(DISTINCT user_id) FROM usage_stats WHERE date = ?",
                (today,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_unlimited_users_count(self) -> int:
        """Получение количества пользователей с безлимитом"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM users WHERE is_unlimited = 1"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_operations_count(self, days: int = 1) -> int:
        """Получение количества операций за последние N дней"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT SUM(operations_count) FROM usage_stats 
                   WHERE date >= date('now', '-' || ? || ' days')""",
                (days,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row and row[0] else 0

    async def get_unbanned_users(self) -> List[int]:
        """Получение списка ID незабаненных пользователей для рассылки"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT user_id FROM users WHERE is_banned = 0"
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def get_unbanned_users_list(self) -> List[int]:
        """Алиас для get_unbanned_users() - получение списка ID для рассылки"""
        return await self.get_unbanned_users()

    async def get_unbanned_users_count(self) -> int:
        """Получение количества незабаненных пользователей"""
        unbanned = await self.get_unbanned_users()
        return len(unbanned)


    async def get_setting(self, key: str) -> Optional[str]:
        """Получение значения настройки"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set_setting(self, key: str, value: str):
        """Установка значения настройки"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            await db.commit()
            logger.info(f"Настройка {key} установлена: {value}")

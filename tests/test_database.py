import asyncio
import tempfile
import unittest
from pathlib import Path

from database import Database


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = Database(str(Path(self.directory.name) / "test.db"))
        await self.db.init_db()
        await self.db.register_user(101, "example", "Тест")

    async def asyncTearDown(self):
        self.directory.cleanup()

    async def test_registration_is_idempotent(self):
        await self.db.register_user(101, "example", "Тест")
        self.assertEqual(await self.db.get_total_users_count(), 1)

    async def test_counter_is_isolated_between_users(self):
        await self.db.register_user(202, None, "Второй")
        await self.db.increment_user_operations(101)
        self.assertEqual(await self.db.get_user_operations_today(101), 1)
        self.assertEqual(await self.db.get_user_operations_today(202), 0)

    async def test_parallel_increments_are_not_lost(self):
        results = await asyncio.gather(
            *(self.db.increment_user_operations(101) for _ in range(8)),
            return_exceptions=True,
        )
        self.assertEqual(results, [None] * 8)
        self.assertEqual(await self.db.get_user_operations_today(101), 8)

    async def test_ban_removes_user_from_broadcast_recipients(self):
        await self.db.set_user_banned(101, True)
        self.assertTrue(await self.db.is_user_banned(101))
        self.assertEqual(await self.db.get_unbanned_users(), [])
        await self.db.set_user_banned(101, False)
        self.assertEqual(await self.db.get_unbanned_users(), [101])

    async def test_unlimited_flag_can_be_reset(self):
        await self.db.set_user_unlimited(101, True)
        self.assertTrue(await self.db.is_user_unlimited(101))
        await self.db.set_user_unlimited(101, False)
        self.assertFalse(await self.db.is_user_unlimited(101))

    async def test_setting_can_be_updated(self):
        await self.db.set_setting("daily_limit", "10")
        await self.db.set_setting("daily_limit", "20")
        self.assertEqual(await self.db.get_setting("daily_limit"), "20")

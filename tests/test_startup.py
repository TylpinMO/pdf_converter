import importlib
import os
import unittest
from unittest.mock import AsyncMock, patch


class StartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_bot_initializes_and_reaches_polling_without_network(self):
        # No real token or channel is used; polling and DB initialization are mocked.
        with patch.dict(os.environ, {
            "BOT_TOKEN": "123456:offline-test", "ADMIN_ID": "1",
            "CHANNEL_USERNAME": "@example_channel",
        }):
            application = importlib.import_module("bot")
        with patch.object(application.db, "init_db", AsyncMock()) as initialize, \
             patch.object(application.Dispatcher, "start_polling", AsyncMock()) as poll:
            await application.main()
            initialize.assert_awaited_once()
            poll.assert_awaited_once()

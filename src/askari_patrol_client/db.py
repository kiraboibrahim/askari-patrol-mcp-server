"""
Database management for Askari Patrol conversation history.

This module provides the ConversationDB class, which handles all interactions
with the SQLite database used to persist conversation messages and structured
agent history.
"""

import logging
from typing import Any

import aiosqlite

DB_PATH = "conversations.db"

# Initialize logger for database operations
logger = logging.getLogger(__name__)


class ConversationDB:
    """
    Handles SQLite database operations for conversation history.

    This class provides methods to initialize the database, save messages,
    load history, and clear records for specific users.
    """

    def __init__(self, db_path: str = DB_PATH):
        """
        Initialize the ConversationDB.

        Args:
            db_path: File path to the SQLite database. Defaults to 'conversations.db'
                in the project root.
        """
        self.db_path = db_path
        self._initialized = False

    async def initialize(self):
        """
        Create the database and necessary tables if they do not exist.

        This method sets up the 'conversation_messages' table with columns for
        phone number, timestamp, and full message JSON.
        It also creates an index on phone_number and timestamp for performance.
        """
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrency during multi-turn interactions
            await db.execute("PRAGMA journal_mode=WAL")

            # Create the main conversation messages table (reduced to JSON only)
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_json TEXT NOT NULL
                )
            """
            )

            # Create an index to speed up history retrieval for specific users
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_phone_number
                ON conversation_messages(phone_number, timestamp DESC)
            """
            )

            await db.commit()

        self._initialized = True
        logger.info("Database initialized at %s", self.db_path)

    async def load_history(
        self, phone_number: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Retrieve recent conversation history for a specific phone number.

        Args:
            phone_number: The identifier for the user.
            limit: Maximum number of recent messages to retrieve.

        Returns:
            A list of dictionary objects representing message rows,
            ordered chronologically (oldest first).
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Fetch the most recent messages for the user
            async with db.execute(
                """
                SELECT message_json, timestamp
                FROM conversation_messages
                WHERE phone_number = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (phone_number, limit),
            ) as cursor:
                rows = await cursor.fetchall()

                # Reverse the rows to return chronological order (oldest first)
                messages = [
                    {"message_json": row["message_json"], "timestamp": row["timestamp"]}
                    for row in reversed(rows)
                ]

                logger.info("Loaded %d messages for %s", len(messages), phone_number)
                return messages

    async def save_message(self, phone_number: str, message_json: str):
        """
        Save a single conversation message to the database.

        Args:
            phone_number: The user identifier.
            message_json: Full JSON serialization of the ModelMessage.
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO conversation_messages (phone_number, message_json)
                VALUES (?, ?)
                """,
                (phone_number, message_json),
            )
            await db.commit()

    async def save_messages(self, phone_number: str, messages: list[dict[str, Any]]):
        """
        Atomically save a batch of messages to the database.

        Args:
            phone_number: The user identifier.
            messages: A list of message dictionaries to persist (each must have 'message_json').
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            for msg in messages:
                await db.execute(
                    """
                    INSERT INTO conversation_messages (phone_number, message_json)
                    VALUES (?, ?)
                    """,
                    (phone_number, msg["message_json"]),
                )
            await db.commit()

        logger.info("Saved %d messages for %s", len(messages), phone_number)

    async def clear_history(self, phone_number: str):
        """
        Remove all conversation history for a specific phone number.

        Args:
            phone_number: The user identifier.
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM conversation_messages WHERE phone_number = ?",
                (phone_number,),
            )
            await db.commit()

        logger.info("Cleared history for %s", phone_number)

    async def get_message_count(self, phone_number: str) -> int:
        """
        Get the total number of messages stored for a specific phone number.

        Args:
            phone_number: The user identifier.

        Returns:
            The total count of messages.
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) as count FROM conversation_messages WHERE phone_number = ?",
                (phone_number,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

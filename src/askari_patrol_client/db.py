"""
Database management for Askari Patrol conversation history.

This module provides the ConversationDB class, which handles all interactions
with the SQLite database used to persist conversation messages and structured
agent history.
"""

import logging
from pathlib import Path
from typing import Any

import aiosqlite

DB_PATH = "data/conversations.db"

# Initialize logger for database operations
logger = logging.getLogger(__name__)


class ConversationDB:
    """
    Handles SQLite database operations for conversation history.

    This class provides methods to initialize the database, save messages,
    load history, and clear records for specific users.

    Attributes:
        db_path (str): Path to the SQLite database file
        _initialized (bool): Whether the database schema has been created

    Example:
        >>> db = ConversationDB()
        >>> await db.save_message("+1234567890", '{"kind":"request",...}')
        >>> messages = await db.load_history("+1234567890", limit=10)
    """

    def __init__(self, db_path: str = DB_PATH):
        """
        Initialize the ConversationDB.

        Args:
            db_path: File path to the SQLite database. Defaults to 'data/conversations.db'
                in the project root.

        Side Effects:
            Creates the parent directory for the database if it doesn't exist
        """
        self.db_path = db_path
        self._initialized = False
        self._ensure_db_directory()

    def _ensure_db_directory(self) -> None:
        """
        Create the database directory if it doesn't exist.

        Side Effects:
            Creates parent directories as needed with appropriate permissions

        Raises:
            OSError: If directory creation fails due to permissions

        Example:
            >>> db = ConversationDB("data/conversations.db")
            # Creates 'data/' directory if it doesn't exist
        """
        db_dir = Path(self.db_path).parent

        if db_dir != Path(".") and not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created database directory: {db_dir}")
            except OSError as e:
                logger.error(f"Failed to create database directory {db_dir}: {e}")
                raise

    async def initialize(self):
        """
        Create the database and necessary tables if they do not exist.

        This method sets up the 'conversation_messages' table with columns for
        phone number, timestamp, and full message JSON.
        It also creates an index on phone_number and timestamp for performance.

        Side Effects:
            - Enables WAL mode for better concurrency
            - Creates conversation_messages table if not exists
            - Creates index on (phone_number, timestamp)
            - Sets self._initialized to True

        Example:
            >>> db = ConversationDB()
            >>> await db.initialize()
            # Database schema ready
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
            phone_number: The identifier for the user (E.164 format)
            limit: Maximum number of recent messages to retrieve

        Returns:
            A list of dictionary objects representing message rows,
            ordered chronologically (oldest first). Each dict contains:
            - message_json: Serialized ModelMessage JSON string
            - timestamp: ISO-8601 timestamp string

        Example:
            >>> messages = await db.load_history("+1234567890", limit=10)
            >>> for msg in messages:
            ...     print(msg['message_json'])

        Note:
            Returns empty list if no messages found or database error occurs
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
            phone_number: The user identifier (E.164 format)
            message_json: Full JSON serialization of the ModelMessage

        Side Effects:
            - Ensures database is initialized
            - Inserts new row into conversation_messages table

        Raises:
            sqlite3.Error: If database operation fails

        Example:
            >>> await db.save_message(
            ...     phone_number="+1234567890",
            ...     message_json='{"kind":"request","parts":[...]}'
            ... )
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
            phone_number: The user identifier (E.164 format)
            messages: A list of message dictionaries to persist
                     (each must have 'message_json' key)

        Side Effects:
            Inserts multiple rows in a single transaction for atomicity

        Example:
            >>> messages = [
            ...     {"message_json": '{"kind":"request",...}'},
            ...     {"message_json": '{"kind":"response",...}'}
            ... ]
            >>> await db.save_messages("+1234567890", messages)
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

        This is a destructive operation that permanently removes all messages
        for the specified phone number.

        Args:
            phone_number: The user identifier (E.164 format)

        Side Effects:
            Deletes all rows where phone_number matches

        Example:
            >>> await db.clear_history("+1234567890")
            # All messages for this user are now deleted
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
            phone_number: The user identifier (E.164 format)

        Returns:
            The total count of messages for this user

        Example:
            >>> count = await db.get_message_count("+1234567890")
            >>> print(f"User has {count} messages")
            User has 42 messages
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) as count FROM conversation_messages WHERE phone_number = ?",
                (phone_number,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

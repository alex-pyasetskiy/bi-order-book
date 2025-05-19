import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

log = logging.getLogger(__name__)

class DataBase:
    """
    Manages the MongoDB connection.
    """
    _client: Optional[AsyncIOMotorClient] = None
    _database: Optional[AsyncIOMotorDatabase] = None

    async def connect(self, mongodb_url: str):
        """
        Connects to the MongoDB database using the provided URL.

        Args:
            mongodb_url (str): The MongoDB connection URL.
        """
        if self._client is None:
            log.info(f"Connecting to MongoDB: {mongodb_url}")
            try:
                self._client = AsyncIOMotorClient(mongodb_url)
                # Force connection on startup
                await self._client.admin.command('ping')
                self._database = self._client["sample_training"]
                log.info("Successfully connected to MongoDB.")
            except Exception as e:
                log.error(f"Failed to connect to MongoDB: {e}")
                self._client = None  # prevents of using an invalid client
                raise
        else:
            log.info("Already connected to MongoDB.")

    async def close(self):
        """
        Closes the MongoDB connection.
        """
        if self._client:
            log.info("Closing MongoDB connection.")
            self._client.close()
            self._client = None
            self._database = None
            log.info("MongoDB connection closed.")
        else:
            log.info("MongoDB connection is already closed.")

    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Returns the MongoDB database instance.

        Raises:
            Exception: If the client is not connected.

        Returns:
            AsyncIOMotorDatabase: The MongoDB database instance.
        """
        if self._database is None:
            raise Exception("Not connected to MongoDB. Call connect() first.")
        return self._database

    @property
    def client(self) -> Optional[AsyncIOMotorClient]:
        """
        Returns the MongoDB client instance.

        Returns:
            Optional[AsyncIOMotorClient]: The MongoDB client instance or None.
        """
        return self._client



db = DataBase()

async def get_database() -> AsyncIOMotorDatabase:
    """
    Gets the MongoDB database instance.  This is the function you should use to get the database.
    """
    return db.get_database()

async def connect_to_db():
    """
    Initialize the database connection.  Call this during startup.
    """
    mongodb_url = os.environ.get("MONGODB_URL")
    if not mongodb_url:
        raise ValueError("MONGODB_URL environment variable not set")
    await db.connect(mongodb_url)


async def close_db_connection():
    """
    Closes the database connection.  Call this during shutdown.
    """
    await db.close()

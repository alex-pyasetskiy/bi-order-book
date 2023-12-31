import os

from motor.motor_asyncio import AsyncIOMotorClient


class DataBase:
    client: AsyncIOMotorClient = None


db = DataBase()

print(os.environ)
async def get_db_conn() -> AsyncIOMotorClient:
    db.client = AsyncIOMotorClient(os.environ["MONGODB_URL"])


async def close_db():
    db.client.close()


async def get_database() -> AsyncIOMotorClient:
    return db.client["sample_training"]
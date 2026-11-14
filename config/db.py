import inspect
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()


class MongoDB:
    def __init__(self):
        self.client = None
        self.database = None

    async def connect(self):
        self.client = AsyncIOMotorClient(os.environ.get("MONGO_DB"))
        self.database = self.client[os.environ.get("DB_NAME")]
        print("Connected to MongoDB!")

    async def close(self):
        """Close the MongoDB connection."""
        if not self.client:
            return
        result = self.client.close()
        if inspect.isawaitable(result):
            await result
        self.client = None
        self.database = None
        print("Disconnected from MongoDB!")

mongodb = MongoDB()

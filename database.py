# database.py
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "raw-personicore")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

routers_collection = db["routers"]

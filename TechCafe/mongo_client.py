# mongo_client.py
from pymongo import MongoClient
from decouple import config

client = MongoClient(config('MONGO_URL'))
user_db = client["techcafe"]
users = user_db["users"]

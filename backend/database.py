from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os
from datetime import datetime

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'test_database')

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Collections
users_collection = db.users
inventory_collection = db.inventory
cases_collection = db.cases
case_results_collection = db.case_results

async def create_or_update_user(steam_id: str, profile_data: dict) -> dict:
    """Create new user or update existing user"""
    existing_user = await users_collection.find_one({"steam_id": steam_id})
    
    user_data = {
        "steam_id": steam_id,
        "username": profile_data.get("personaname", "Unknown"),
        "avatar": profile_data.get("avatarfull", ""),
        "profile_url": profile_data.get("profileurl", ""),
        "last_login": datetime.utcnow()
    }
    
    if existing_user:
        await users_collection.update_one(
            {"steam_id": steam_id},
            {"$set": user_data}
        )
        updated_user = await users_collection.find_one({"steam_id": steam_id})
        return updated_user
    else:
        user_data["balance"] = 0
        user_data["created_at"] = datetime.utcnow()
        result = await users_collection.insert_one(user_data)
        new_user = await users_collection.find_one({"_id": result.inserted_id})
        return new_user

async def get_user_by_steam_id(steam_id: str) -> Optional[dict]:
    """Get user by Steam ID"""
    return await users_collection.find_one({"steam_id": steam_id})

async def update_user_balance(steam_id: str, amount: int) -> bool:
    """Update user balance (amount in kopecks)"""
    result = await users_collection.update_one(
        {"steam_id": steam_id},
        {"$inc": {"balance": amount}}
    )
    return result.modified_count > 0

async def add_item_to_inventory(user_id: str, item_data: dict) -> str:
    """Add item to user inventory"""
    item_data["user_id"] = user_id
    item_data["obtained_at"] = datetime.utcnow()
    result = await inventory_collection.insert_one(item_data)
    return str(result.inserted_id)

async def get_user_inventory(user_id: str) -> list:
    """Get all items in user inventory"""
    cursor = inventory_collection.find({"user_id": user_id})
    items = await cursor.to_list(length=None)
    return items

async def save_case_result(user_id: str, case_id: str, item_data: dict) -> str:
    """Save case opening result"""
    result_data = {
        "user_id": user_id,
        "case_id": case_id,
        "item": item_data,
        "opened_at": datetime.utcnow()
    }
    result = await case_results_collection.insert_one(result_data)
    return str(result.inserted_id)
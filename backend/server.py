from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import aiohttp
import json
import httpx
from enum import Enum

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import custom modules
import steam_auth
from models import *
from database import *

steam_auth_instance = steam_auth.steam_auth

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Case Battle API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Crypto Bot API configuration
CRYPTO_BOT_TOKEN = os.environ.get('CRYPTO_BOT_TOKEN', '')
CRYPTO_BOT_BASE_URL = "https://pay.crypt.bot/api"

# Supported cryptocurrencies
SUPPORTED_CRYPTO = ["USDT", "TON", "TRX", "BTC", "ETH", "LTC", "NOT", "BNB"]

# Payment transaction models
class TransactionStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_steam_id: str
    invoice_id: Optional[str] = None
    amount_usd: float
    amount_rub: float
    crypto_currency: str
    crypto_amount: Optional[float] = None
    status: TransactionStatus = TransactionStatus.PENDING
    exchange_rate: float  # USD to RUB rate at transaction time
    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = None
    is_promocode: bool = False

class PaymentRequest(BaseModel):
    amount_usd: float
    crypto_currency: str

class PromoCodeRequest(BaseModel):
    promo_code: str
    amount_rub: float

class ExchangeRate(BaseModel):
    from_currency: str = "USD"
    to_currency: str = "RUB"
    rate: float
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Crypto Bot API functions
async def get_crypto_bot_me():
    """Test Crypto Bot API connection"""
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CRYPTO_BOT_BASE_URL}/getMe",
            headers=headers
        )
        return response.json()

async def create_crypto_invoice(amount_usd: float, crypto_currency: str, user_steam_id: str):
    """Create invoice via Crypto Bot API"""
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN,
        "Content-Type": "application/json"
    }
    
    payload = {
        "asset": crypto_currency,
        "amount": str(amount_usd),
        "description": f"Пополнение баланса для пользователя {user_steam_id}",
        "paid_btn_name": "callback",
        "paid_btn_url": f"{os.environ.get('FRONTEND_URL', 'https://c098d0b9-3259-4bb7-b2bf-8654441aefdd.preview.emergentagent.com')}/payment-success",
        "payload": user_steam_id
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CRYPTO_BOT_BASE_URL}/createInvoice",
            headers=headers,
            json=payload
        )
        return response.json()

async def get_current_exchange_rate():
    """Get current USD to RUB exchange rate"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.exchangerate-api.com/v4/latest/USD")
            data = response.json()
            usd_to_rub_rate = data.get("rates", {}).get("RUB", 90.0)  # fallback rate
            
            # Update rate in database
            await db.exchange_rates.replace_one(
                {"from_currency": "USD", "to_currency": "RUB"},
                {
                    "from_currency": "USD",
                    "to_currency": "RUB",
                    "rate": usd_to_rub_rate,
                    "updated_at": datetime.utcnow()
                },
                upsert=True
            )
            
            return usd_to_rub_rate
    except Exception as e:
        # Fallback rate if API fails
        logging.error(f"Failed to get exchange rate: {e}")
        return 90.0

# Dependency to get current user
async def get_current_user(token: str = Depends(security)):
    """Get current authenticated user"""
    try:
        payload = steam_auth_instance.verify_jwt_token(token.credentials)
        steam_id = payload.get('steam_id')
        if not steam_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await get_user_by_steam_id(steam_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

# Steam Authentication Routes
@api_router.get("/auth/steam/login", response_model=SteamLoginResponse)
async def steam_login():
    """Initiate Steam login"""
    login_url = steam_auth_instance.generate_steam_login_url()
    return SteamLoginResponse(login_url=login_url)

@api_router.get("/auth/steam/callback")
async def steam_callback(request: Request):
    """Handle Steam authentication callback"""
    try:
        query_params = dict(request.query_params)
        
        # Verify Steam login
        steam_id = await steam_auth_instance.verify_steam_login(query_params)
        if not steam_id:
            raise HTTPException(status_code=403, detail="Steam authentication failed")
        
        # Get user profile from Steam
        profile_data = await steam_auth_instance.get_steam_profile(steam_id)
        
        # Create or update user in database
        user = await create_or_update_user(steam_id, profile_data)
        
        # Generate JWT token
        token = steam_auth_instance.generate_jwt_token(steam_id, profile_data)
        
        # Redirect to frontend with token
        frontend_url = os.environ.get('FRONTEND_URL', "https://c098d0b9-3259-4bb7-b2bf-8654441aefdd.preview.emergentagent.com")
        redirect_url = f"{frontend_url}?token={token}"
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Steam callback error: {e}")
        # Redirect to frontend with error
        frontend_url = os.environ.get('FRONTEND_URL', "https://c098d0b9-3259-4bb7-b2bf-8654441aefdd.preview.emergentagent.com")
        redirect_url = f"{frontend_url}?error=auth_failed"
        return RedirectResponse(url=redirect_url)

# User Routes
@api_router.get("/user/profile")
async def get_profile(current_user = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@api_router.get("/user/inventory")
async def get_inventory(current_user = Depends(get_current_user)):
    """Get user inventory"""
    inventory = await get_user_inventory(current_user["_id"])
    return {"items": inventory}

@api_router.post("/user/balance/add")
async def add_balance(amount: int, current_user = Depends(get_current_user)):
    """Add balance to user account (amount in kopecks)"""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    success = await update_user_balance(current_user["steam_id"], amount)
    if success:
        updated_user = await get_user_by_steam_id(current_user["steam_id"])
        return {"success": True, "new_balance": updated_user["balance"]}
    else:
        raise HTTPException(status_code=500, detail="Failed to update balance")

# Crypto Payment Routes
@api_router.get("/exchange-rate")
async def get_exchange_rate():
    rate = await get_current_exchange_rate()
    return {"usd_to_rub": rate, "updated_at": datetime.utcnow()}

@api_router.post("/create-crypto-payment")
async def create_crypto_payment(payment_request: PaymentRequest, current_user = Depends(get_current_user)):
    """Create crypto payment invoice"""
    # Validate cryptocurrency
    if payment_request.crypto_currency not in SUPPORTED_CRYPTO:
        raise HTTPException(status_code=400, detail="Unsupported cryptocurrency")
    
    # Get current exchange rate
    exchange_rate = await get_current_exchange_rate()
    amount_rub = payment_request.amount_usd * exchange_rate
    
    # Create invoice via Crypto Bot
    invoice_response = await create_crypto_invoice(
        payment_request.amount_usd,
        payment_request.crypto_currency,
        current_user["steam_id"]
    )
    
    if not invoice_response.get("ok"):
        raise HTTPException(status_code=400, detail="Failed to create payment invoice")
    
    invoice_data = invoice_response["result"]
    
    # Create transaction record
    transaction = PaymentTransaction(
        user_steam_id=current_user["steam_id"],
        invoice_id=str(invoice_data["invoice_id"]),
        amount_usd=payment_request.amount_usd,
        amount_rub=amount_rub,
        crypto_currency=payment_request.crypto_currency,
        crypto_amount=float(invoice_data["amount"]),
        exchange_rate=exchange_rate,
        status=TransactionStatus.PENDING
    )
    
    await db.payment_transactions.insert_one(transaction.dict())
    
    return {
        "transaction_id": transaction.id,
        "invoice_id": invoice_data["invoice_id"],
        "pay_url": invoice_data["pay_url"],
        "amount_usd": payment_request.amount_usd,
        "amount_rub": amount_rub,
        "crypto_amount": invoice_data["amount"],
        "crypto_currency": payment_request.crypto_currency,
        "exchange_rate": exchange_rate
    }

@api_router.post("/apply-promocode")
async def apply_promocode(promo_request: PromoCodeRequest, current_user = Depends(get_current_user)):
    """Apply promocode to add balance"""
    # Validate promocode
    if promo_request.promo_code != "YANMAIZI":
        raise HTTPException(status_code=400, detail="Invalid promocode")
    
    # Convert rubles to kopecks
    amount_kopecks = int(promo_request.amount_rub * 100)
    
    # Add balance to user
    success = await update_user_balance(current_user["steam_id"], amount_kopecks)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update balance")
    
    # Get updated user data
    updated_user = await get_user_by_steam_id(current_user["steam_id"])
    
    # Create transaction record for promocode
    transaction = PaymentTransaction(
        user_steam_id=current_user["steam_id"],
        amount_usd=promo_request.amount_rub / 90.0,  # approximate USD equivalent
        amount_rub=promo_request.amount_rub,
        crypto_currency="PROMO",
        exchange_rate=90.0,
        status=TransactionStatus.PAID,
        paid_at=datetime.utcnow(),
        is_promocode=True
    )
    
    await db.payment_transactions.insert_one(transaction.dict())
    
    return {
        "success": True,
        "message": "Promocode applied successfully",
        "new_balance": updated_user["balance"],
        "added_amount_kopecks": amount_kopecks
    }

@api_router.post("/webhook/crypto-bot")
async def crypto_bot_webhook(request: Request):
    """Handle webhooks from Crypto Bot"""
    try:
        data = await request.json()
        
        # Process payment update
        if data.get("update_type") == "invoice_paid":
            invoice_id = str(data["payload"]["invoice_id"])
            
            # Find transaction by invoice_id
            transaction = await db.payment_transactions.find_one({"invoice_id": invoice_id})
            if not transaction:
                return {"status": "error", "message": "Transaction not found"}
            
            # Update transaction status
            await db.payment_transactions.update_one(
                {"invoice_id": invoice_id},
                {
                    "$set": {
                        "status": TransactionStatus.PAID.value,
                        "paid_at": datetime.utcnow()
                    }
                }
            )
            
            # Convert rubles to kopecks and update user balance
            amount_kopecks = int(transaction["amount_rub"] * 100)
            success = await update_user_balance(transaction["user_steam_id"], amount_kopecks)
            
            if success:
                logging.info(f"Payment processed: {amount_kopecks} kopecks added to user {transaction['user_steam_id']}")
        
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@api_router.get("/test-crypto-bot")
async def test_crypto_bot():
    """Test Crypto Bot API connection"""
    try:
        result = await get_crypto_bot_me()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crypto Bot API error: {str(e)}")

@api_router.get("/user/transactions")
async def get_user_transactions(current_user = Depends(get_current_user)):
    """Get user payment transactions"""
    transactions = await db.payment_transactions.find({"user_steam_id": current_user["steam_id"]}).to_list(100)
    return {"transactions": [
        {
            "id": str(t.get("_id")),
            "amount_usd": t.get("amount_usd"),
            "amount_rub": t.get("amount_rub"),
            "crypto_currency": t.get("crypto_currency"),
            "status": t.get("status"),
            "created_at": t.get("created_at"),
            "paid_at": t.get("paid_at"),
            "is_promocode": t.get("is_promocode", False)
        } 
        for t in transactions
    ]}

# Steam Market Integration
async def get_steam_market_price(market_hash_name: str):
    """Get item price from Steam Market"""
    url = "https://steamcommunity.com/market/priceoverview/"
    params = {
        "appid": 730,  # CS2 app ID
        "currency": 5,  # RUB
        "market_hash_name": market_hash_name
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    price_text = data.get("lowest_price", "0 pуб.")
                    # Extract numeric value and convert to kopecks
                    import re
                    price_match = re.search(r'(\d+)', price_text.replace(',', ''))
                    if price_match:
                        return int(float(price_match.group(1)) * 100)
                return 0
    except Exception as e:
        print(f"Error fetching Steam price: {e}")
        return 0

# Case Management
@api_router.get("/cases")
async def get_cases():
    """Get all available cases with updated prices"""
    cases_data = [
        {
            "id": "1",
            "name": "КОНФЕТТИ БУМ",
            "items": 35,
            "price": 1500,  # 15 RUB
            "image": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpou-6kejhz2v_Nfz5H_uO1gb-Gw_alIITCmX5d_MR6mOzG-oLw2w2yrUo5N2j0LI6XdAU-YluE-AS9kOy918Pu6M6YwSE26CB3sGGdwULdGVNUiw/360fx360f",
            "is_new": True
        },
        {
            "id": "2", 
            "name": "КБ КОРМИТ",
            "items": 50,
            "price": 7500,  # 75 RUB
            "image": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot621FAR17PLfYQJD_9W7m5a0mvLwOq7c2DMBupQn2eqVotqkiwHiqhdlMmigJtOWJwE5Zw3X8wS-yea8jcDo7c7XiSw0g89L9us/360fx360f",
            "is_new": True
        },
        {
            "id": "3",
            "name": "КОРОЛЬ КЕЙСОВ", 
            "items": 38,
            "price": 13500,  # 135 RUB
            "image": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpovbSsLQJf3qr3czxb49KzgL-ImOX3NrfUhGRu5Mx2gv2P8Y3w2gS3rkVsYzqlI9edJgI2NAmE-VK3wOe9h8W6uJTJzmwj5Hc3nWGdwUKnJ-gWGw/360fx360f",
            "is_new": True
        },
        {
            "id": "4",
            "name": "АФТЕРПАТИ",
            "items": 49, 
            "price": 55000,  # 550 RUB
            "image": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpovbSsLQJf0Ob3dDFL7929ldaOwfX3MLrFnm5u5Mx2gv2P8I2p3g3l-kY9N2yiI4KcdVVvNQyC_FO2kr3ohpHptZ6fzmwj5HcqeFN1sQ/360fx360f",
            "is_new": True
        },
        {
            "id": "5",
            "name": "ОГНЕННАЯ ШЕСТЕРКА",
            "items": 53,
            "price": 95000,  # 950 RUB
            "image": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpopuP1FA957ODYfi9W7927kYyDgvun4IrqyT5Q5sFo2u2T8I-niwHg8hI5ZGv3ddSSI1I5ZwzY-FO2l-e8h5C4vczXiSw0Oj2SzDo/360fx360f",
            "is_new": True
        },
        {
            "id": "6",
            "name": "СТАНДАРТНЫЙ",
            "items": 27,
            "price": 7000,  # 70 RUB  
            "image": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpopuP1FAR17P7NdTRH-t26q4SClvD7Ib6ukmJE6ct0h-zF_Jn4xlCx-UA-azjxdICWegVtYlyC-lK7wrnshZK06Z_XiSw0PXJwqWo/360fx360f"
        }
    ]
    return {"cases": cases_data}

# Case opening with realistic CS:GO items
@api_router.post("/cases/{case_id}/open")
async def open_case(case_id: str, current_user = Depends(get_current_user)):
    """Open a case and get random item"""
    # Get case data
    cases_response = await get_cases()
    cases_data = cases_response["cases"]
    case_data = next((c for c in cases_data if c["id"] == case_id), None)
    
    if not case_data:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Check user balance
    if current_user["balance"] < case_data["price"]:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Deduct case price from balance
    await update_user_balance(current_user["steam_id"], -case_data["price"])
    
    # CS:GO items with realistic data and Steam image URLs
    items = [
        {
            "name": "AK-47 | Редлайн",
            "rarity": "rare",
            "price": 850000,  # 8500 RUB
            "market_hash_name": "AK-47 | Redline (Field-Tested)",
            "image_url": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot7HxfDhjxszJemkV09-5gZKKkuXLPr7Vn35cppMk3L3Dp96k21Lg_EJuYjqnJNKSdFU2YVrQ_ljrwOzv1MK46pzJwHRkuCR2sCvbgVXp1gcKLrE/360fx360f",
            "color_class": "from-red-400 to-red-600"
        },
        {
            "name": "M4A4 | Хаул",
            "rarity": "epic", 
            "price": 1200000,  # 12000 RUB
            "market_hash_name": "M4A4 | Howl (Field-Tested)",
            "image_url": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpou-6kejhjxszFJTwW09izh4-HluPxDKjBl2hU18l4jeHVu4is0VHi_ENqMG6iI9DEJAU9M1vY_FXqyLvs0JC6tJucm3MxuSgltH7D30vgCRVnojY/360fx360f",
            "color_class": "from-purple-400 to-purple-600"
        },
        {
            "name": "AWP | Азимов",
            "rarity": "legendary",
            "price": 2500000,  # 25000 RUB 
            "market_hash_name": "AWP | Asiimov (Field-Tested)",
            "image_url": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot621FAR17PLfYQJO5du5q4GFk8j4OrzZgiVQuJwg2O2WrdWl2Q21-0duMWH6JoWXcwVqYVyG_gC2xObugJ-16MzPn3Y3vykh5yzZgVXp1hlSLrE/360fx360f",
            "color_class": "from-yellow-400 to-yellow-600"
        },
        {
            "name": "Glock-18 | Выцветший",
            "rarity": "common",
            "price": 15000,  # 150 RUB
            "market_hash_name": "Glock-18 | Fade (Factory New)",
            "image_url": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgposbaqKAxf0Ob3djFN79eJmIyPkuXLNqjFm2pT18l4jeHVu433iVa1qkprYDr7dtWRcQA3MlHS81PtyOa6hZW-6c6YzSNjvykg5H7D30vga1SMHA/360fx360f",
            "color_class": "from-gray-400 to-gray-600"
        },
        {
            "name": "USP-S | Орион",
            "rarity": "rare",
            "price": 320000,  # 3200 RUB
            "market_hash_name": "USP-S | Orion (Factory New)",
            "image_url": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpoo6m1FBRp3_bGcjhQ09-jq5WYh8j_OrfYlDMEuJNz3L3C896h3wLl_xJuNzjyJdWXegZrYV6C8lXsw-3rhpW8uJqfzHYyvSJx5HfZnBS_hRhOaOE6gvfPSg/360fx360f",
            "color_class": "from-blue-400 to-blue-600"
        },
        {
            "name": "★ Карамбит | Убийство",
            "rarity": "mythical",
            "price": 15000000,  # 150000 RUB
            "market_hash_name": "★ Karambit | Slaughter (Factory New)",
            "image_url": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpovbSsLQJf2PLacDBA5ciJlY20kfb5NqjYglRc7cF4n-SPrN2m21Ls_kc-YW77I4ORcQdqMwrV-VK9w7q-15W4vZTNyHZgu3Mm-z-DyLOsxaXl/360fx360f",
            "color_class": "from-orange-400 to-orange-600"
        },
        {
            "name": "P90 | Азимов",
            "rarity": "epic",
            "price": 450000,  # 4500 RUB
            "market_hash_name": "P90 | Asiimov (Factory New)",
            "image_url": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpopuP1FAR17PLJYTJL49uJkIGZkfX5MaexmX5D_8l4jeHVu97ziQLl_0c5MG3wI4aScA8_MlHX-gLqk-3v0J626c7LzCcxuSAq7HzD30vgfAJdKsM/360fx360f",
            "color_class": "from-purple-400 to-purple-600"
        },
        {
            "name": "MAC-10 | Неон Rider",
            "rarity": "common",
            "price": 80000,  # 800 RUB
            "market_hash_name": "MAC-10 | Neon Rider (Factory New)",
            "image_url": "https://community.akamai.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpou7uOFA957PfJYzh97cqJmImMn-O6YriBx2pH18l4jeHVu4-l3wXir0M6YTj3JdSSIVU7NV3X_FG5kLrqgJ-56sDLz3E3syQl43vD30vgrS5vOGY/360fx360f",
            "color_class": "from-green-400 to-green-600"
        }
    ]
    
    # Random item selection with realistic drop rates
    import random
    rarity_weights = {
        "common": 50,
        "rare": 25, 
        "epic": 15,
        "legendary": 8,
        "mythical": 2
    }
    
    # Filter items by rarity and select based on weights
    weighted_items = []
    for item in items:
        weight = rarity_weights.get(item["rarity"], 1)
        weighted_items.extend([item] * weight)
    
    selected_item = random.choice(weighted_items)
    
    # Add item to user inventory
    await add_item_to_inventory(str(current_user["_id"]), selected_item)
    
    # Save case result
    await save_case_result(str(current_user["_id"]), case_id, selected_item)
    
    return {
        "success": True,
        "item": selected_item,
        "remaining_balance": current_user["balance"] - case_data["price"]
    }

# Add original routes
@api_router.get("/")
async def root():
    return {"message": "Case Battle API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
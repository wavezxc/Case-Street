from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
import httpx
import aiohttp
import json
from datetime import datetime
from enum import Enum


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Crypto Bot API configuration
CRYPTO_BOT_TOKEN = os.environ['CRYPTO_BOT_TOKEN']
CRYPTO_BOT_BASE_URL = "https://pay.crypt.bot/api"

# Supported cryptocurrencies
SUPPORTED_CRYPTO = ["USDT", "TON", "TRX", "BTC", "ETH", "LTC", "NOT", "BNB"]

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    balance_rub: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    username: str

class TransactionStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
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
    user_id: str
    amount_usd: float
    crypto_currency: str

class PromoCodeRequest(BaseModel):
    user_id: str
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

async def create_crypto_invoice(amount_usd: float, crypto_currency: str, user_id: str):
    """Create invoice via Crypto Bot API"""
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN,
        "Content-Type": "application/json"
    }
    
    payload = {
        "asset": crypto_currency,
        "amount": str(amount_usd),
        "description": f"Пополнение баланса для пользователя {user_id}",
        "paid_btn_name": "callback",
        "paid_btn_url": f"https://79441248-5b86-4344-a727-9f623d1a33ab.preview.emergentagent.com/payment-success",
        "payload": user_id
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

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Crypto Payment System API"}

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

# User management endpoints
@api_router.post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"username": user_data.username})
    if existing_user:
        return User(**existing_user)
    
    user_obj = User(**user_data.dict())
    await db.users.insert_one(user_obj.dict())
    return user_obj

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)

@api_router.get("/users/by-username/{username}", response_model=User)
async def get_user_by_username(username: str):
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)

# Payment endpoints
@api_router.get("/exchange-rate")
async def get_exchange_rate():
    rate = await get_current_exchange_rate()
    return {"usd_to_rub": rate, "updated_at": datetime.utcnow()}

@api_router.post("/create-payment")
async def create_payment(payment_request: PaymentRequest):
    # Validate user exists
    user = await db.users.find_one({"id": payment_request.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
        payment_request.user_id
    )
    
    if not invoice_response.get("ok"):
        raise HTTPException(status_code=400, detail="Failed to create payment invoice")
    
    invoice_data = invoice_response["result"]
    
    # Create transaction record
    transaction = PaymentTransaction(
        user_id=payment_request.user_id,
        invoice_id=str(invoice_data["invoice_id"]),
        amount_usd=payment_request.amount_usd,
        amount_rub=amount_rub,
        crypto_currency=payment_request.crypto_currency,
        crypto_amount=float(invoice_data["amount"]),
        exchange_rate=exchange_rate,
        status=TransactionStatus.PENDING
    )
    
    await db.transactions.insert_one(transaction.dict())
    
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

@api_router.post("/promocode")
async def apply_promocode(promo_request: PromoCodeRequest):
    # Check if user exists
    user = await db.users.find_one({"id": promo_request.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate promocode
    if promo_request.promo_code != "YANMAIZI":
        raise HTTPException(status_code=400, detail="Invalid promocode")
    
    # Add balance to user
    new_balance = user["balance_rub"] + promo_request.amount_rub
    await db.users.update_one(
        {"id": promo_request.user_id},
        {
            "$set": {
                "balance_rub": new_balance,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Create transaction record for promocode
    transaction = PaymentTransaction(
        user_id=promo_request.user_id,
        amount_usd=promo_request.amount_rub / 90.0,  # approximate USD equivalent
        amount_rub=promo_request.amount_rub,
        crypto_currency="PROMO",
        exchange_rate=90.0,
        status=TransactionStatus.PAID,
        paid_at=datetime.utcnow(),
        is_promocode=True
    )
    
    await db.transactions.insert_one(transaction.dict())
    
    return {
        "success": True,
        "message": "Promocode applied successfully",
        "new_balance": new_balance,
        "added_amount": promo_request.amount_rub
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
            transaction = await db.transactions.find_one({"invoice_id": invoice_id})
            if not transaction:
                return {"status": "error", "message": "Transaction not found"}
            
            # Update transaction status
            await db.transactions.update_one(
                {"invoice_id": invoice_id},
                {
                    "$set": {
                        "status": TransactionStatus.PAID.value,
                        "paid_at": datetime.utcnow()
                    }
                }
            )
            
            # Update user balance
            user = await db.users.find_one({"id": transaction["user_id"]})
            if user:
                new_balance = user["balance_rub"] + transaction["amount_rub"]
                await db.users.update_one(
                    {"id": transaction["user_id"]},
                    {
                        "$set": {
                            "balance_rub": new_balance,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
        
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@api_router.get("/transactions/{user_id}")
async def get_user_transactions(user_id: str):
    transactions = await db.transactions.find({"user_id": user_id}).to_list(100)
    # Convert MongoDB documents to PaymentTransaction objects to ensure proper serialization
    return [
        {
            "id": str(t.get("_id")),
            "user_id": t.get("user_id"),
            "invoice_id": t.get("invoice_id"),
            "amount_usd": t.get("amount_usd"),
            "amount_rub": t.get("amount_rub"),
            "crypto_currency": t.get("crypto_currency"),
            "crypto_amount": t.get("crypto_amount"),
            "status": t.get("status"),
            "exchange_rate": t.get("exchange_rate"),
            "created_at": t.get("created_at"),
            "paid_at": t.get("paid_at"),
            "is_promocode": t.get("is_promocode", False)
        } 
        for t in transactions
    ]

@api_router.get("/test-crypto-bot")
async def test_crypto_bot():
    """Test Crypto Bot API connection"""
    try:
        result = await get_crypto_bot_me()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crypto Bot API error: {str(e)}")

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

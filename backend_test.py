#!/usr/bin/env python3
import httpx
import asyncio
import json
import uuid
import os
from datetime import datetime

# Get the backend URL from frontend/.env
BACKEND_URL = "https://79441248-5b86-4344-a727-9f623d1a33ab.preview.emergentagent.com/api"

# Test user data
TEST_USERNAME = f"testuser_{uuid.uuid4().hex[:8]}"

# Supported cryptocurrencies
SUPPORTED_CRYPTO = ["USDT", "TON", "TRX", "BTC", "ETH", "LTC", "NOT", "BNB"]

# Test results
test_results = {
    "user_model": {"status": "Not tested", "details": ""},
    "exchange_rate": {"status": "Not tested", "details": ""},
    "crypto_bot_integration": {"status": "Not tested", "details": ""},
    "payment_creation": {"status": "Not tested", "details": ""},
    "promocode_system": {"status": "Not tested", "details": ""},
    "transaction_history": {"status": "Not tested", "details": ""}
}

async def test_user_endpoints():
    """Test user creation and retrieval endpoints"""
    print("\n=== Testing User Endpoints ===")
    
    try:
        # Create a test user
        async with httpx.AsyncClient() as client:
            print(f"Creating test user with username: {TEST_USERNAME}")
            response = await client.post(
                f"{BACKEND_URL}/users",
                json={"username": TEST_USERNAME}
            )
            
            if response.status_code != 200:
                test_results["user_model"]["status"] = "Failed"
                test_results["user_model"]["details"] = f"Failed to create user: {response.text}"
                print(f"❌ Failed to create user: {response.text}")
                return None
            
            user_data = response.json()
            user_id = user_data["id"]
            print(f"✅ User created successfully with ID: {user_id}")
            
            # Get user by ID
            response = await client.get(f"{BACKEND_URL}/users/{user_id}")
            if response.status_code != 200:
                test_results["user_model"]["status"] = "Failed"
                test_results["user_model"]["details"] = f"Failed to get user by ID: {response.text}"
                print(f"❌ Failed to get user by ID: {response.text}")
                return None
            
            user_by_id = response.json()
            print(f"✅ Retrieved user by ID: {user_by_id['username']}")
            
            # Get user by username
            response = await client.get(f"{BACKEND_URL}/users/by-username/{TEST_USERNAME}")
            if response.status_code != 200:
                test_results["user_model"]["status"] = "Failed"
                test_results["user_model"]["details"] = f"Failed to get user by username: {response.text}"
                print(f"❌ Failed to get user by username: {response.text}")
                return None
            
            user_by_username = response.json()
            print(f"✅ Retrieved user by username: {user_by_username['username']}")
            
            # Verify user has balance_rub field
            if "balance_rub" not in user_data:
                test_results["user_model"]["status"] = "Failed"
                test_results["user_model"]["details"] = "User model missing balance_rub field"
                print("❌ User model missing balance_rub field")
                return None
            
            print(f"✅ User has balance_rub field: {user_data['balance_rub']}")
            test_results["user_model"]["status"] = "Passed"
            test_results["user_model"]["details"] = f"User created and retrieved successfully. Initial balance: {user_data['balance_rub']}"
            
            return user_data
            
    except Exception as e:
        test_results["user_model"]["status"] = "Failed"
        test_results["user_model"]["details"] = f"Exception: {str(e)}"
        print(f"❌ Exception in user endpoints test: {e}")
        return None

async def test_exchange_rate():
    """Test exchange rate endpoint"""
    print("\n=== Testing Exchange Rate Endpoint ===")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/exchange-rate")
            
            if response.status_code != 200:
                test_results["exchange_rate"]["status"] = "Failed"
                test_results["exchange_rate"]["details"] = f"Failed to get exchange rate: {response.text}"
                print(f"❌ Failed to get exchange rate: {response.text}")
                return None
            
            rate_data = response.json()
            if "usd_to_rub" not in rate_data:
                test_results["exchange_rate"]["status"] = "Failed"
                test_results["exchange_rate"]["details"] = "Exchange rate response missing usd_to_rub field"
                print("❌ Exchange rate response missing usd_to_rub field")
                return None
            
            print(f"✅ Current USD to RUB exchange rate: {rate_data['usd_to_rub']}")
            test_results["exchange_rate"]["status"] = "Passed"
            test_results["exchange_rate"]["details"] = f"Exchange rate retrieved successfully: {rate_data['usd_to_rub']}"
            
            return rate_data["usd_to_rub"]
            
    except Exception as e:
        test_results["exchange_rate"]["status"] = "Failed"
        test_results["exchange_rate"]["details"] = f"Exception: {str(e)}"
        print(f"❌ Exception in exchange rate test: {e}")
        return None

async def test_crypto_bot_connection():
    """Test Crypto Bot API connection"""
    print("\n=== Testing Crypto Bot API Connection ===")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/test-crypto-bot")
            
            if response.status_code != 200:
                test_results["crypto_bot_integration"]["status"] = "Failed"
                test_results["crypto_bot_integration"]["details"] = f"Failed to connect to Crypto Bot API: {response.text}"
                print(f"❌ Failed to connect to Crypto Bot API: {response.text}")
                return False
            
            bot_data = response.json()
            if not bot_data.get("ok"):
                test_results["crypto_bot_integration"]["status"] = "Failed"
                test_results["crypto_bot_integration"]["details"] = f"Crypto Bot API returned error: {bot_data}"
                print(f"❌ Crypto Bot API returned error: {bot_data}")
                return False
            
            print(f"✅ Successfully connected to Crypto Bot API: {bot_data}")
            test_results["crypto_bot_integration"]["status"] = "Passed"
            test_results["crypto_bot_integration"]["details"] = f"Crypto Bot API connection successful"
            
            return True
            
    except Exception as e:
        test_results["crypto_bot_integration"]["status"] = "Failed"
        test_results["crypto_bot_integration"]["details"] = f"Exception: {str(e)}"
        print(f"❌ Exception in Crypto Bot API test: {e}")
        return False

async def test_payment_creation(user_id):
    """Test payment creation with different cryptocurrencies"""
    print("\n=== Testing Payment Creation ===")
    
    if not user_id:
        test_results["payment_creation"]["status"] = "Skipped"
        test_results["payment_creation"]["details"] = "User creation failed, skipping payment test"
        print("⚠️ User creation failed, skipping payment test")
        return None
    
    # Test with a few different cryptocurrencies
    test_cryptos = ["USDT", "BTC", "TON"]
    payment_results = []
    
    try:
        for crypto in test_cryptos:
            print(f"\nTesting payment creation with {crypto}...")
            async with httpx.AsyncClient() as client:
                payment_data = {
                    "user_id": user_id,
                    "amount_usd": 10.0,  # Test with 10 USD
                    "crypto_currency": crypto
                }
                
                response = await client.post(
                    f"{BACKEND_URL}/create-payment",
                    json=payment_data
                )
                
                if response.status_code != 200:
                    print(f"❌ Failed to create {crypto} payment: {response.text}")
                    continue
                
                result = response.json()
                payment_results.append(result)
                print(f"✅ Successfully created {crypto} payment:")
                print(f"   Transaction ID: {result.get('transaction_id')}")
                print(f"   Invoice ID: {result.get('invoice_id')}")
                print(f"   Pay URL: {result.get('pay_url')}")
                print(f"   Amount USD: {result.get('amount_usd')}")
                print(f"   Amount RUB: {result.get('amount_rub')}")
                print(f"   Crypto Amount: {result.get('crypto_amount')} {crypto}")
        
        # Test with invalid cryptocurrency
        print("\nTesting with invalid cryptocurrency...")
        async with httpx.AsyncClient() as client:
            payment_data = {
                "user_id": user_id,
                "amount_usd": 10.0,
                "crypto_currency": "INVALID_CRYPTO"
            }
            
            response = await client.post(
                f"{BACKEND_URL}/create-payment",
                json=payment_data
            )
            
            if response.status_code == 400:
                print("✅ Correctly rejected invalid cryptocurrency")
            else:
                print(f"❌ Failed to reject invalid cryptocurrency: {response.status_code} - {response.text}")
        
        if payment_results:
            test_results["payment_creation"]["status"] = "Passed"
            test_results["payment_creation"]["details"] = f"Successfully created payments with {', '.join(test_cryptos)}"
        else:
            test_results["payment_creation"]["status"] = "Failed"
            test_results["payment_creation"]["details"] = "Failed to create any payments"
        
        return payment_results
            
    except Exception as e:
        test_results["payment_creation"]["status"] = "Failed"
        test_results["payment_creation"]["details"] = f"Exception: {str(e)}"
        print(f"❌ Exception in payment creation test: {e}")
        return None

async def test_promocode(user_id):
    """Test promocode YANMAIZI application"""
    print("\n=== Testing Promocode System ===")
    
    if not user_id:
        test_results["promocode_system"]["status"] = "Skipped"
        test_results["promocode_system"]["details"] = "User creation failed, skipping promocode test"
        print("⚠️ User creation failed, skipping promocode test")
        return False
    
    try:
        # Get initial balance
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/users/{user_id}")
            if response.status_code != 200:
                test_results["promocode_system"]["status"] = "Failed"
                test_results["promocode_system"]["details"] = f"Failed to get initial balance: {response.text}"
                print(f"❌ Failed to get initial balance: {response.text}")
                return False
            
            initial_balance = response.json()["balance_rub"]
            print(f"Initial balance: {initial_balance} RUB")
            
            # Apply valid promocode
            promo_data = {
                "user_id": user_id,
                "promo_code": "YANMAIZI",
                "amount_rub": 1000.0  # Add 1000 RUB
            }
            
            response = await client.post(
                f"{BACKEND_URL}/promocode",
                json=promo_data
            )
            
            if response.status_code != 200:
                test_results["promocode_system"]["status"] = "Failed"
                test_results["promocode_system"]["details"] = f"Failed to apply valid promocode: {response.text}"
                print(f"❌ Failed to apply valid promocode: {response.text}")
                return False
            
            promo_result = response.json()
            print(f"✅ Promocode applied successfully:")
            print(f"   Added amount: {promo_result.get('added_amount')} RUB")
            print(f"   New balance: {promo_result.get('new_balance')} RUB")
            
            # Verify balance was updated
            response = await client.get(f"{BACKEND_URL}/users/{user_id}")
            if response.status_code != 200:
                test_results["promocode_system"]["status"] = "Failed"
                test_results["promocode_system"]["details"] = f"Failed to get updated balance: {response.text}"
                print(f"❌ Failed to get updated balance: {response.text}")
                return False
            
            new_balance = response.json()["balance_rub"]
            print(f"Updated balance from API: {new_balance} RUB")
            
            if new_balance != initial_balance + 1000.0:
                test_results["promocode_system"]["status"] = "Failed"
                test_results["promocode_system"]["details"] = f"Balance not updated correctly. Expected: {initial_balance + 1000.0}, Got: {new_balance}"
                print(f"❌ Balance not updated correctly. Expected: {initial_balance + 1000.0}, Got: {new_balance}")
                return False
            
            # Test invalid promocode
            invalid_promo_data = {
                "user_id": user_id,
                "promo_code": "INVALID_CODE",
                "amount_rub": 1000.0
            }
            
            response = await client.post(
                f"{BACKEND_URL}/promocode",
                json=invalid_promo_data
            )
            
            if response.status_code == 400:
                print("✅ Correctly rejected invalid promocode")
            else:
                print(f"❌ Failed to reject invalid promocode: {response.status_code} - {response.text}")
                
            test_results["promocode_system"]["status"] = "Passed"
            test_results["promocode_system"]["details"] = f"Promocode YANMAIZI applied successfully, balance increased by 1000 RUB"
            
            return True
            
    except Exception as e:
        test_results["promocode_system"]["status"] = "Failed"
        test_results["promocode_system"]["details"] = f"Exception: {str(e)}"
        print(f"❌ Exception in promocode test: {e}")
        return False

async def test_transaction_history(user_id):
    """Test transaction history endpoint"""
    print("\n=== Testing Transaction History ===")
    
    if not user_id:
        test_results["transaction_history"]["status"] = "Skipped"
        test_results["transaction_history"]["details"] = "User creation failed, skipping transaction history test"
        print("⚠️ User creation failed, skipping transaction history test")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/transactions/{user_id}")
            
            if response.status_code != 200:
                test_results["transaction_history"]["status"] = "Failed"
                test_results["transaction_history"]["details"] = f"Failed to get transaction history: {response.text}"
                print(f"❌ Failed to get transaction history: {response.text}")
                return False
            
            transactions = response.json()
            print(f"✅ Successfully retrieved transaction history")
            print(f"   Number of transactions: {len(transactions)}")
            
            # Check if promocode transaction is in history
            promo_transactions = [t for t in transactions if t.get("is_promocode")]
            if promo_transactions:
                print(f"✅ Found promocode transaction in history")
            else:
                print("⚠️ No promocode transaction found in history")
            
            # Check if payment transactions are in history
            payment_transactions = [t for t in transactions if not t.get("is_promocode")]
            if payment_transactions:
                print(f"✅ Found {len(payment_transactions)} payment transactions in history")
            else:
                print("⚠️ No payment transactions found in history")
            
            test_results["transaction_history"]["status"] = "Passed"
            test_results["transaction_history"]["details"] = f"Successfully retrieved transaction history with {len(transactions)} transactions"
            
            return True
            
    except Exception as e:
        test_results["transaction_history"]["status"] = "Failed"
        test_results["transaction_history"]["details"] = f"Exception: {str(e)}"
        print(f"❌ Exception in transaction history test: {e}")
        return False

async def run_tests():
    """Run all tests in sequence"""
    print(f"Starting backend API tests against {BACKEND_URL}")
    
    # Test user endpoints
    user_data = await test_user_endpoints()
    user_id = user_data["id"] if user_data else None
    
    # Test exchange rate
    exchange_rate = await test_exchange_rate()
    
    # Test Crypto Bot connection
    crypto_bot_connected = await test_crypto_bot_connection()
    
    # Test payment creation
    payment_results = await test_payment_creation(user_id)
    
    # Test promocode
    promocode_success = await test_promocode(user_id)
    
    # Test transaction history
    transaction_history_success = await test_transaction_history(user_id)
    
    # Print summary
    print("\n=== Test Summary ===")
    for test_name, result in test_results.items():
        status_symbol = "✅" if result["status"] == "Passed" else "❌" if result["status"] == "Failed" else "⚠️"
        print(f"{status_symbol} {test_name}: {result['status']}")
        if result["details"]:
            print(f"   {result['details']}")
    
    return test_results

if __name__ == "__main__":
    asyncio.run(run_tests())
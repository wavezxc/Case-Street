import os
import re
import urllib.parse
import aiohttp
from datetime import datetime, timedelta
from jose import jwt
from fastapi import HTTPException
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

class SteamAuth:
    """Steam OpenID Authentication Handler"""
    
    def __init__(self):
        self.steam_api_key = os.environ.get('STEAM_API_KEY')
        self.callback_url = os.environ.get('CALLBACK_URL')
        self.base_url = "https://steamcommunity.com/openid/"
        
        # Debug print to check if API key is loaded
        if not self.steam_api_key:
            print("WARNING: Steam API key not found in environment variables!")
        else:
            print(f"Steam API key loaded: {self.steam_api_key[:8]}...") # Print first 8 chars for debugging
        
    def generate_steam_login_url(self, return_to: str = None):
        """Generate Steam OpenID login URL"""
        if not return_to:
            # Use the callback URL from environment, or fallback to a default
            return_to = self.callback_url
            if not return_to:
                # Fallback to the current deployment URL
                return_to = "https://zxca-github-io.onrender.com/api/auth/steam/callback"
        
        # Make sure return_to is the full callback URL with /api/auth/steam/callback path
        if not return_to.endswith('/api/auth/steam/callback'):
            if '/api' not in return_to:
                return_to = f"{return_to}/api/auth/steam/callback"
                
        # Extract the base URL (without /api path)
        base_url = return_to.split('/api')[0] if '/api' in return_to else return_to
            
        params = {
            'openid.ns': 'http://specs.openid.net/auth/2.0',
            'openid.mode': 'checkid_setup',
            'openid.return_to': return_to,
            'openid.realm': base_url,
            'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select'
        }
        
        login_url = f"{self.base_url}login?" + urllib.parse.urlencode(params)
        return login_url
    
    async def verify_steam_login(self, query_params: dict):
        """Verify Steam OpenID response and extract Steam ID"""
        # Check if response is positive
        if query_params.get('openid.mode') != 'id_res':
            return None
            
        # Prepare verification parameters
        verify_params = dict(query_params)
        verify_params['openid.mode'] = 'check_authentication'
        
        # Make verification request to Steam
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}login",
                data=verify_params
            ) as response:
                content = await response.text()
                
        # Check if verification was successful
        if 'is_valid:true' not in content:
            return None
            
        # Extract Steam ID from claimed_id
        claimed_id = query_params.get('openid.claimed_id', '')
        steam_id_match = re.search(r'(\d+)$', claimed_id)
        
        if steam_id_match:
            return steam_id_match.group(1)
        
        return None
    
    async def get_steam_profile(self, steam_id: str):
        """Get Steam user profile from Steam Web API"""
        if not self.steam_api_key:
            raise HTTPException(status_code=500, detail="Steam API key not configured")
            
        url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
        params = {
            'key': self.steam_api_key,
            'steamids': steam_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        print(f"Steam API error: {response.status}")
                        # Return fallback profile if Steam API fails
                        return {
                            'steamid': steam_id,
                            'personaname': f'Player_{steam_id[-4:]}',
                            'avatarfull': 'https://avatars.mds.yandex.net/i?id=f282cbc5d89f99ce4f9a56ee9e8805be_l-7679814-images-thumbs&n=13',
                            'profileurl': f'https://steamcommunity.com/profiles/{steam_id}'
                        }
                    
                    data = await response.json()
                    players = data.get('response', {}).get('players', [])
                    
                    if not players:
                        # Return fallback profile if no player data
                        return {
                            'steamid': steam_id,
                            'personaname': f'Player_{steam_id[-4:]}',
                            'avatarfull': 'https://avatars.mds.yandex.net/i?id=f282cbc5d89f99ce4f9a56ee9e8805be_l-7679814-images-thumbs&n=13',
                            'profileurl': f'https://steamcommunity.com/profiles/{steam_id}'
                        }
                    
                    return players[0]
        except Exception as e:
            print(f"Exception in get_steam_profile: {e}")
            # Return fallback profile on any error
            return {
                'steamid': steam_id,
                'personaname': f'Player_{steam_id[-4:]}',
                'avatarfull': 'https://avatars.mds.yandex.net/i?id=f282cbc5d89f99ce4f9a56ee9e8805be_l-7679814-images-thumbs&n=13',
                'profileurl': f'https://steamcommunity.com/profiles/{steam_id}'
            }
    
    def generate_jwt_token(self, steam_id: str, user_data: dict):
        """Generate JWT token for authenticated user"""
        secret = os.environ.get('SESSION_SECRET')
        if not secret:
            raise HTTPException(status_code=500, detail="Session secret not configured")
            
        payload = {
            'steam_id': steam_id,
            'username': user_data.get('personaname', 'Unknown'),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        
        token = jwt.encode(payload, secret, algorithm='HS256')
        return token
    
    def verify_jwt_token(self, token: str):
        """Verify JWT token and return payload"""
        secret = os.environ.get('SESSION_SECRET')
        if not secret:
            raise HTTPException(status_code=500, detail="Session secret not configured")
            
        try:
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

steam_auth = SteamAuth()
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    steam_id: str
    username: str
    avatar: str
    profile_url: Optional[str] = None
    balance: int = 0  # Balance in kopecks
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime = Field(default_factory=datetime.utcnow)

class InventoryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    image_url: str
    rarity: str  # common, rare, epic, legendary, mythical
    price: int  # Price in kopecks
    market_hash_name: str
    obtained_at: datetime = Field(default_factory=datetime.utcnow)

class CaseItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    rarity: str
    price: int  # Price in kopecks
    image_url: str
    market_hash_name: str
    color_class: str  # CSS gradient class

class Case(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: int  # Price in kopecks
    image_url: str
    items: List[CaseItem]
    is_new: bool = False

class CaseOpenResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    case_id: str
    item: CaseItem
    opened_at: datetime = Field(default_factory=datetime.utcnow)

class SteamLoginResponse(BaseModel):
    login_url: str

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str
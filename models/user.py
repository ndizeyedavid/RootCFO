
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Company:
    id: Optional[int]
    name: str
    contact_email: str
    address: str
    business_hours: str
    created_at: Optional[datetime] = None

@dataclass
class User:
    id: Optional[int]
    company_id: int
    username: str
    password_hash: str
    role: str
    created_at: Optional[datetime] = None

"""Bruce: User and Company dataclasses."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Company:
    """Bruce: Add fields: id, name, contact_email, address, business_hours, created_at"""
    pass


@dataclass
class User:
    """Bruce: Add fields: id, company_id, username, password_hash, role, created_at"""
    pass

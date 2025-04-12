from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field

@dataclass
class Wallet:
    """Model cho ví Bitcoin"""
    address: str            # Địa chỉ ví
    private_key_hex: str    # Private key dạng hex
    wif_key: str           # WIF key
    balance: float         # Số dư
    strategy: str          # Chiến lược tìm kiếm đã sử dụng
    api_source: str        # API được dùng để check balance (blockchain.info, blockchair, etc)
    coin_type: str        # Loại coin (BTC, ETH, etc)
    created_at: datetime
    updated_at: datetime

    def to_dict_str(self):
        """Convert wallet to dictionary"""
        return {
            "address": self.address,
            "balance": self.balance,
            "strategy": self.strategy,
            "api_source": self.api_source,
            "coin_type": self.coin_type,
            "created_at": self.created_at.isoformat(),  # Giữ nguyên datetime
            "updated_at": self.updated_at.isoformat()   # Giữ nguyên datetime
        }
    
    def to_dict(self):
        """Convert wallet to dictionary"""
        return {
            "address": self.address,
            "private_key_hex": self.private_key_hex,
            "wif_key": self.wif_key,
            "balance": self.balance,
            "strategy": self.strategy,
            "api_source": self.api_source,
            "coin_type": self.coin_type,
            "created_at": self.created_at,  # Giữ nguyên datetime
            "updated_at": self.updated_at   # Giữ nguyên datetime
        }

    def __str__(self):
        return f"Wallet(address={self.address}, balance={self.balance})"

class Stats(BaseModel):
    coin_type: str         # Loại coin (BTC, ETH, etc)
    total_wallets: int = 0
    total_balance: float = 0.0
    max_balance: float = 0.0
    min_balance: float = 0.0
    created_at: datetime
    updated_at: datetime

    def to_dict_str(self):
        return {
            "coin_type": self.coin_type,
            "total_wallets": self.total_wallets,
            "total_balance": self.total_balance,
            "max_balance": self.max_balance,
            "min_balance": self.min_balance,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        } 

    def to_dict(self):
        return {
            "coin_type": self.coin_type,
            "total_wallets": self.total_wallets,
            "total_balance": self.total_balance,
            "max_balance": self.max_balance,
            "min_balance": self.min_balance,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        } 
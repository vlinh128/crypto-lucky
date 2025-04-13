from typing import List, Optional
from datetime import datetime
from .connection import DatabaseConnection
from .models import Wallet, Stats
from pymongo import ReturnDocument
import logging

class StatsRepository:
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.collection = db.get_database().stats

    def get_latest(self, coin_type: str = "BTC") -> Stats:
        """Get the latest stats for a specific coin type"""
        try:
            stats_dict = self.collection.find_one(
                {"coin_type": coin_type},
                sort=[('updated_at', -1)]
            )

            logging.info(f"stats_dict: {stats_dict}")

            if stats_dict:
                return Stats(**stats_dict)
            else:
                # Trả về một đối tượng Stats mặc định nếu không có dữ liệu
                return Stats(
                    coin_type=coin_type,
                    total_wallets=0,
                    total_balance=0.0,
                    wallets_with_balance=0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
        except Exception as e:
            logging.error(f"Lỗi khi lấy thống kê123131248172634871623746: {str(e)}")
            # Trả về một đối tượng Stats mặc định nếu có lỗi
            return Stats(
                coin_type=coin_type,
                total_wallets=0,
                total_balance=0.0,
                wallets_with_balance=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

    def update(self, wallet: Wallet) -> Stats:
        """Update stats when a new wallet is found using MongoDB findOneAndUpdate"""
        current_time = datetime.now()
        
        try:
            # Use findOneAndUpdate for atomic update and return
            result = self.collection.find_one_and_update(
                {"coin_type": wallet.coin_type},
                {
                    "$inc": {
                        "total_wallets": 1,
                        "total_balance": wallet.balance
                    },
                    "$max": {
                        "max_balance": wallet.balance
                    },
                    "$min": {
                        "min_balance": wallet.balance
                    },
                    "$set": {
                        "updated_at": current_time
                    },
                    "$setOnInsert": {
                        "created_at": current_time
                    }
                },
                upsert=True,
                return_document=ReturnDocument.AFTER  # Return the document after update
            )
            
            # Convert to Stats object and return
            if result:
                return Stats(**result)
            else:
                # Trả về một đối tượng Stats mặc định nếu không có kết quả
                return Stats(
                    coin_type=wallet.coin_type,
                    total_wallets=1,
                    total_balance=wallet.balance,
                    max_balance=wallet.balance,
                    min_balance=wallet.balance,
                    created_at=current_time,
                    updated_at=current_time
                )
        except Exception as e:
            logging.error(f"Lỗi khi cập nhật thống kê: {str(e)}")
            # Trả về một đối tượng Stats mặc định nếu có lỗi
            return Stats(
                coin_type=wallet.coin_type,
                total_wallets=1,
                total_balance=wallet.balance,
                max_balance=wallet.balance,
                min_balance=wallet.balance,
                created_at=current_time,
                updated_at=current_time
            )

class WalletRepository:
    """Repository pattern cho thao tác với database"""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.collection = db.get_database().wallets

    def save_wallet(self, wallet: Wallet) -> bool:
        """Lưu thông tin ví mới hoặc cập nhật ví cũ"""
        try:
            # Upsert based on address
            self.collection.insert_one(wallet.to_dict())
            return True
        except Exception as e:
            logging.error(f"Lỗi khi lưu ví: {str(e)}")
            return False

    def get_wallets(self, limit: int = 50) -> List[Wallet]:
        try:            
            # Lấy danh sách ví, sắp xếp theo thời gian tạo giảm dần
            wallets_cursor = self.collection.find({}).sort("created_at", -1).limit(limit)
            wallets_list = list(wallets_cursor)
            
            # Convert MongoDB documents to Wallet objects
            wallets = [
                Wallet(
                    address=w['address'],
                    private_key_hex=w['private_key_hex'],
                    wif_key=w['wif_key'],
                    balance=w['balance'],
                    strategy=w.get('strategy', 'unknown'),
                    api_source=w.get('api_source', 'unknown'),
                    coin_type=w.get('coin_type', 'BTC'),
                    created_at=w['created_at'],
                    updated_at=w['updated_at']
                ) for w in wallets_list
            ]
            
            return wallets
            
        except Exception as e:
            logging.error(f"Lỗi khi lấy danh sách ví: {str(e)}")
            return []

    def get_stats(self) -> Stats:
        # This method is no longer needed
        pass
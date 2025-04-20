from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseConnection:
    """Quản lý kết nối MongoDB"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Khởi tạo kết nối MongoDB"""
        self.client = None
        self.db = None
        self.connect()

    def connect(self):
        """Kết nối đến MongoDB"""
        try:
            # Get MongoDB URI from environment variable
            mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/crypto-lucky")
            
            # Connect to MongoDB
            self.client = MongoClient(mongodb_uri)
            self.db = self.client["crypto-lucky"]
            
            # Kiểm tra kết nối
            self.client.admin.command('ping')
            logging.info("✓ Kết nối MongoDB thành công! Database: crypto-lucky")
            
            # Tạo indexes cho các collection
            self._create_indexes()
            
        except ConnectionFailure as e:
            logging.error(f"Lỗi kết nối MongoDB: {str(e)}")
            self.client = None
            self.db = None

    def _create_indexes(self):
        """Tạo các index cần thiết"""
        try:
            # Index cho collection wallets
            self.db.wallets.create_index([("address", 1)], unique=True)
            self.db.wallets.create_index([("coin_type", 1)])
            self.db.wallets.create_index([("balance", -1)])

            # Index cho collection search_history
            self.db.search_history.create_index([("timestamp", -1)])
            self.db.search_history.create_index([("coin_type", 1)])
            self.db.search_history.create_index([("strategy", 1)])

            # Index cho collection coins
            self.db.coins.create_index([("symbol", 1)], unique=True)
            
            logging.info("✓ Đã tạo indexes thành công!")
            
            # Kiểm tra collections
            collections = self.db.list_collection_names()
            logging.info(f"Collections hiện có: {collections}")
            
        except Exception as e:
            logging.error(f"Lỗi khi tạo indexes: {str(e)}")
            raise e

    def get_database(self):
        """Lấy instance của database"""
        if self.db is None:
            self.connect()
        return self.db

    def close(self):
        """Đóng kết nối"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None 
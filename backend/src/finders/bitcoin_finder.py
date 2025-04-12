import datetime
import time
import logging
import requests
import binascii
from .base_finder import BaseFinder
from .strategies import (
    RandomSearchStrategy,
    BrainWalletStrategy,
    PatternSearchStrategy,
    RangeSearchStrategy,
    LostBitcoinStrategy
)
from database import wallet_repo, stats_repo
from database.models import Wallet

class BitcoinFinder(BaseFinder):
    """Bitcoin address finder with balance checking"""
    
    def __init__(self):
        super().__init__("BTC")
        # API endpoints để check balance
        self.api_endpoints = [
            {
                'name': 'mempool',
                'url': 'https://mempool.space/api/address/{address}',
                'parser': self._parse_mempool_response
            },
            {
                'name': 'blockchain',
                'url': 'https://blockchain.info/balance?active={address}',
                'parser': self._parse_blockchain_response
            },
            {
                'name': 'blockchair',
                'url': 'https://api.blockchair.com/bitcoin/dashboards/address/{address}',
                'parser': self._parse_blockchair_response
            }
        ]
        
        # Khởi tạo các chiến lược tìm kiếm
        self.current_strategy_index = 0
        self.strategies = [
            RandomSearchStrategy(),
            BrainWalletStrategy(),
            PatternSearchStrategy(),
            RangeSearchStrategy(),
            LostBitcoinStrategy()
        ]

    def _search_worker(self):
        """Main search worker"""
        counter = 0
        start_time = time.time()
        
        while self._is_running:
            try:
                # Lấy chiến lược hiện tại và chuyển sang chiến lược tiếp theo
                strategy = self.strategies[self.current_strategy_index]
                self.current_strategy_index = (self.current_strategy_index + 1) % len(self.strategies)
                
                # Generate key pair using strategy
                private_key, wif, address = strategy.generate_key()

                # Check balance
                balance, api_source = self.check_balance(address)
                
                # Lưu tất cả ví tìm được
                wallet = Wallet(
                    address=address,
                    private_key_hex=binascii.hexlify(private_key).decode(),
                    wif_key=wif,
                    balance=balance,
                    coin_type=self.coin_type,
                    api_source=api_source,
                    strategy=strategy.__class__.__name__.replace("Strategy", "").lower(),
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now()
                )
                wallet_repo.save_wallet(wallet)

                # Cập nhật thống kê
                stats = stats_repo.update(wallet)

                # Gọi callback nếu có
                if self.on_wallet_found:
                    self.on_wallet_found(wallet, stats)
                    
                counter += 1
                if counter % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = counter / elapsed
                    logging.info(f"BTC Finder: Checked {counter} addresses at {rate:.2f} addresses/second using {strategy.__class__.__name__}")
                    
                time.sleep(1)
                    
            except Exception as e:
                logging.error(f"Error in BTC search worker: {str(e)}")

    def check_balance(self, address: str):
        """Check BTC balance using multiple APIs"""
        for api in self.api_endpoints:
            try:
                url = api['url'].format(address=address)
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    balance, source = api['parser'](data)
                    if balance is not None:
                        return balance, source
                        
            except Exception as e:
                logging.error(f"Error checking balance with {api['name']}: {str(e)}")
                continue
                
        return 0, None

    def _parse_mempool_response(self, data: dict):
        """Parse response from mempool.space API"""
        try:
            balance = float(data.get("chain_stats", {}).get("funded_txo_sum", 0)) / 100000000
            return balance, "mempool"
        except:
            return None, None

    def _parse_blockchain_response(self, data: dict):
        """Parse response from blockchain.info API"""
        try:
            balance = float(data.get("final_balance", 0)) / 100000000
            return balance, "blockchain"
        except:
            return None, None

    def _parse_blockchair_response(self, data: dict):
        """Parse response from blockchair.com API"""
        try:
            balance = float(data.get("data", {}).get("address", {}).get("balance", 0)) / 100000000
            return balance, "blockchair"
        except:
            return None, None
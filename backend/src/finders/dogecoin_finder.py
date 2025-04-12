import datetime
from .base_finder import BaseFinder
import time
import logging
import requests
from coincurve import PrivateKey
import hashlib
import base58
from database import wallet_repo, stats_repo
from database.models import Wallet
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class DogecoinFinder(BaseFinder):
    """Dogecoin address finder with balance checking"""
    
    def __init__(self):
        super().__init__("DOGE")
        # API endpoints để check balance
        self.api_endpoints = [
            {
                'name': 'dogechain',
                'url': 'https://dogechain.info/api/v1/address/balance/{address}',
                'parser': self._parse_dogechain_response
            },
            {
                'name': 'blockchair',
                'url': 'https://api.blockchair.com/dogecoin/dashboards/address/{address}',
                'parser': self._parse_blockchair_response
            }
        ]

    def _search_worker(self):
        """Main search worker"""
        counter = 0
        start_time = time.time()
        
        while self._is_running:
            try:
                # Generate private key and address
                private_key = PrivateKey()
                address = self._generate_address(private_key)
                
                # Check balance
                balance, api_source = self.check_balance(address)
                
                # Lưu ví và gửi thông báo
                self._save_wallet_and_notify(address, private_key, balance, api_source)
                    
                counter += 1
                if counter % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = counter / elapsed
                    logging.info(f"DOGE Finder: Checked {counter} addresses at {rate:.2f} addresses/second")
                
                time.sleep(1)    
            except Exception as e:
                logging.error(f"Error in DOGE search worker: {str(e)}")
                
    def _generate_address(self, private_key):
        """Generate DOGE address from private key"""
        public_key = private_key.public_key.format(compressed=True)
        sha256_hash = hashlib.sha256(public_key).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
        version = b'\x1e'  # Dogecoin mainnet
        vh160 = version + ripemd160_hash
        double_sha256 = hashlib.sha256(hashlib.sha256(vh160).digest()).digest()
        checksum = double_sha256[:4]
        binary_addr = vh160 + checksum
        return base58.b58encode(binary_addr).decode()
        
    def _save_wallet_and_notify(self, address, private_key, balance, api_source):
        """Save wallet and notify if found"""
        wallet = Wallet(
            address=address,
            private_key_hex=private_key.to_hex(),
            wif_key=None,
            balance=balance,
            coin_type=self.coin_type,
            api_source=api_source,
            strategy="random",
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        )
        wallet_repo.save_wallet(wallet)
        
        # Cập nhật thống kê
        stats = stats_repo.update(wallet)
        
        # Gọi callback nếu có
        if self.on_wallet_found:
            self.on_wallet_found(wallet, stats)

    def check_balance(self, address: str):
        """Check DOGE balance using multiple APIs"""
        for api in self.api_endpoints:
            try:
                url = api['url'].format(address=address)
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    balance = api['parser'](response)
                    if balance is not None:
                        return balance, api['name']
            except Exception as e:
                logging.error(f"Error checking DOGE balance with {api['name']}: {str(e)}")
                continue
        
        return 0, "unknown"
        
    def _parse_dogechain_response(self, response):
        """Parse dogechain.info API response"""
        try:
            data = response.json()
            if data.get("success", 0) == 1:
                return float(data.get("balance", 0))
        except:
            pass
        return None
        
    def _parse_blockchair_response(self, response):
        """Parse Blockchair API response"""
        try:
            data = response.json()
            if 'data' in data:
                address = list(data['data'].keys())[0]
                balance = data['data'][address]['address']['balance']
                return balance
        except:
            pass
        return None

    def _check_balance_blockchair(self, address: str) -> float:
        """Check DOGE balance using Blockchair API"""
        try:
            # Tăng timeout và thêm retry
            session = requests.Session()
            retries = Retry(
                total=3,  # Số lần retry tối đa
                backoff_factor=1,  # Thời gian chờ giữa các lần retry
                status_forcelist=[500, 502, 503, 504]  # Các mã lỗi cần retry
            )
            session.mount('https://', HTTPAdapter(max_retries=retries))
            
            response = session.get(
                f"https://api.blockchair.com/dogecoin/dashboards/address/{address}",
                timeout=30  # Tăng timeout lên 30 giây
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('data', {}).get(address, {}).get('balance'):
                balance = int(data['data'][address]['balance']) / 100000000  # Convert satoshi to DOGE
                return balance
            return 0.0
        except Exception as e:
            logging.error(f"Error checking DOGE balance with blockchair: {str(e)}")
            return 0.0 
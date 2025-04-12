import os
import hashlib
import ecdsa
import base58
import requests
import pandas as pd
from datetime import datetime
import random
import binascii
from typing import Tuple, List, Dict, Optional, Union, Callable
import json
import time
from functools import wraps
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging
from database import wallet_repo, stats_repo
from database.models import Wallet
from database.repository import WalletRepository, StatsRepository
import threading
import asyncio

# Không cần khởi tạo các biến global nữa
# db = DatabaseConnection()
# wallet_repo = WalletRepository(db)
# stats_repo = StatsRepository(db)

def _rate_limit(func):
    """Decorator để giới hạn tốc độ gọi API"""
    @wraps(func)
    def wrapper(self, address: str, api_name: str, headers: dict = None) -> Tuple[float, str]:
        api = self.apis[api_name]
        
        # Kiểm tra rate limit
        current_time = time.time()
        time_since_last_call = current_time - api['last_call']
        
        if time_since_last_call < api['rate_limit']:
            time.sleep(api['rate_limit'] - time_since_last_call)
        
        # Kiểm tra giới hạn gọi mỗi phút
        if current_time - self.minute_start >= 60:
            self.minute_start = current_time
            self.minute_calls = {api: 0 for api in self.apis.keys()}
        
        if self.minute_calls[api_name] >= api['max_calls_per_minute']:
            return None, None  # Báo hiệu vượt quá rate limit
        
        # Cập nhật thông tin gọi API
        api['last_call'] = time.time()
        api['calls'] += 1
        self.minute_calls[api_name] += 1
        
        return func(self, address, api_name, headers)
    return wrapper

class BitcoinSearchStrategy:
    """Interface cho các chiến lược tìm kiếm"""
    def generate_key(self) -> Tuple[bytes, str, str]:
        """Tạo key theo chiến lược cụ thể"""
        raise NotImplementedError

class RandomSearchStrategy(BitcoinSearchStrategy):
    """Chiến lược tìm kiếm ngẫu nhiên hoàn toàn"""
    def generate_key(self) -> Tuple[bytes, str, str]:
        private_key = os.urandom(32)
        wif = private_key_to_wif(private_key)
        address = private_key_to_address(private_key)
        return private_key, wif, address

class BrainWalletStrategy(BitcoinSearchStrategy):
    """Chiến lược tìm kiếm từ passphrase (brain wallet)"""
    def __init__(self, wordlist_file: str = "wordlist.txt"):
        self.words = self._load_wordlist(wordlist_file)
    
    def _load_wordlist(self, filename: str) -> List[str]:
        """Load danh sách từ từ file"""
        try:
            with open(filename, 'r') as f:
                return [line.strip() for line in f]
        except:
            # Nếu không có file, dùng danh sách mặc định
            return ["satoshi", "bitcoin", "blockchain", "crypto", "wallet", 
                   "private", "key", "address", "mining", "block"]
    
    def generate_key(self) -> Tuple[bytes, str, str]:
        # Tạo passphrase ngẫu nhiên từ 3-5 từ
        num_words = random.randint(3, 5)
        passphrase = " ".join(random.choices(self.words, k=num_words))
        
        # SHA256 của passphrase làm private key
        private_key = hashlib.sha256(passphrase.encode()).digest()
        wif = private_key_to_wif(private_key)
        address = private_key_to_address(private_key)
        return private_key, wif, address

class PatternSearchStrategy(BitcoinSearchStrategy):
    """Chiến lược tìm kiếm theo pattern"""
    def __init__(self):
        self.patterns = [
            "000",  # Địa chỉ bắt đầu bằng nhiều số 0
            "777",  # Địa chỉ chứa nhiều số 7
            "123",  # Địa chỉ chứa dãy số liên tiếp
            "aaa"   # Địa chỉ chứa các ký tự giống nhau
        ]
    
    def generate_key(self) -> Tuple[bytes, str, str]:
        while True:
            private_key = os.urandom(32)
            wif = private_key_to_wif(private_key)
            address = private_key_to_address(private_key)
            
            # Kiểm tra nếu địa chỉ match với bất kỳ pattern nào
            if any(pattern in address.lower() for pattern in self.patterns):
                return private_key, wif, address

class RangeSearchStrategy(BitcoinSearchStrategy):
    """Chiến lược tìm kiếm trong một range private key"""
    def __init__(self):
        self.current = 0
        # Bắt đầu từ một số ngẫu nhiên lớn
        self.start = random.randint(2**200, 2**256)
    
    def generate_key(self) -> Tuple[bytes, str, str]:
        # Chuyển số thành private key
        private_key = (self.start + self.current).to_bytes(32, byteorder='big')
        self.current += 1
        
        wif = private_key_to_wif(private_key)
        address = private_key_to_address(private_key)
        return private_key, wif, address

class LostBitcoinStrategy(BitcoinSearchStrategy):
    """Chiến lược tìm kiếm các ví Bitcoin đã mất"""
    def __init__(self):
        # Các pattern thời kỳ đầu (2009-2011)
        self.early_patterns = [
            "1111", # Các địa chỉ thời kỳ đầu thường đơn giản
            "1234",
            "abcd",
            "1A1z", # Pattern của Satoshi
            "1H6Q"  # Pattern phổ biến thời kỳ đầu
        ]
        
        # Danh sách các sàn giao dịch đã sập
        self.dead_exchanges = {
            "mtgox": [
                "1LNWw6yCxkUmkhArb2Nf2MPw6vG7u5WG7q",
                "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF"
            ],
            "quadriga": [
                "1HocPduHmQUJerpdaLG8DnmxvnDCVQwQQU",
                "1JPtxSGoekZfLQeYAWkbhBhkr2VEDUL7Zt"
            ]
        }
        
        # Số lần thử tối đa
        self.max_attempts = 100

    def generate_key(self) -> Tuple[bytes, str, str]:
        """Tạo key theo các pattern của ví đã mất"""
        attempts = 0
        while attempts < self.max_attempts:
            attempts += 1
            private_key = os.urandom(32)
            wif = private_key_to_wif(private_key)
            address = private_key_to_address(private_key)
            
            # Kiểm tra các pattern thời kỳ đầu
            if any(pattern in address for pattern in self.early_patterns):
                return private_key, wif, address
                
            # Kiểm tra địa chỉ của các sàn đã sập
            if any(address in addresses for exchange, addresses in self.dead_exchanges.items()):
                return private_key, wif, address
            
        # Nếu không tìm thấy sau số lần thử tối đa, trả về một địa chỉ ngẫu nhiên
        private_key = os.urandom(32)
        wif = private_key_to_wif(private_key)
        address = private_key_to_address(private_key)
        return private_key, wif, address

class BalanceChecker:
    """Lớp quản lý việc kiểm tra số dư qua nhiều API khác nhau"""
    def __init__(self):
        # Danh sách API theo thứ tự ưu tiên, mempool ở đầu
        self.api_list = [
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
                'name': 'blockcypher',
                'url': 'https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance',
                'parser': self._parse_blockcypher_response
            },
            {
                'name': 'blockchair',
                'url': 'https://api.blockchair.com/bitcoin/dashboards/address/{address}',
                'parser': self._parse_blockchair_response
            }
        ]
        
        # Thông tin rate limit
        self.last_call_time = 0
        self.min_call_interval = 3  # Giây giữa các lần gọi
        self.error_count = 0
        self.max_errors = 5  # Số lần lỗi tối đa trước khi đợi
        self.cooldown_time = 60  # Thời gian đợi sau khi vượt quá số lần lỗi tối đa

    def _parse_mempool_response(self, response: dict) -> Tuple[float, str]:
        """Parse response từ mempool.space API"""
        try:
            chain_stats = response.get('chain_stats', {})
            mempool_stats = response.get('mempool_stats', {})
            
            chain_balance = chain_stats.get('funded_txo_sum', 0)
            mempool_balance = mempool_stats.get('funded_txo_sum', 0)
            
            total_balance = (chain_balance + mempool_balance) / 100000000  # Convert to BTC
            return total_balance, 'mempool'
        except (KeyError, ValueError, TypeError) as e:
            logging.error(f"Lỗi khi parse mempool response: {str(e)}")
            return 0.0, 'mempool'

    def _parse_blockchain_response(self, response: dict) -> Tuple[float, str]:
        """Parse response từ blockchain.info API"""
        try:
            if not response:
                return 0.0, 'blockchain'
                
            address = next(iter(response))
            address_data = response[address]
            
            balance = float(address_data.get('final_balance', 0)) / 100000000  # Convert to BTC
            return balance, 'blockchain'
        except (KeyError, ValueError, TypeError, StopIteration) as e:
            logging.error(f"Lỗi khi parse blockchain response: {str(e)}")
            return 0.0, 'blockchain'

    def _parse_blockcypher_response(self, response: dict) -> Tuple[float, str]:
        """Parse response từ BlockCypher API"""
        try:
            final_balance = float(response.get('final_balance', 0)) / 100000000  # Convert to BTC
            return final_balance, 'blockcypher'
        except (KeyError, ValueError, TypeError) as e:
            logging.error(f"Lỗi khi parse blockcypher response: {str(e)}")
            return 0.0, 'blockcypher'

    def _parse_blockchair_response(self, response: dict) -> Tuple[float, str]:
        """Parse response từ Blockchair API"""
        try:
            context = response.get('context', {})
            if context.get('code', 200) != 200 or response.get('data') is None:
                error_msg = context.get('error', 'Unknown error')
                logging.error(f"Blockchair API error: {error_msg}")
                return 0.0, 'blockchair'
            
            first_address = next(iter(response.get('data', {})))
            address_data = response['data'][first_address]['address']
            
            balance = float(address_data.get('balance', 0)) / 100000000  # Convert to BTC
            return balance, 'blockchair'
        except (KeyError, ValueError, TypeError, StopIteration) as e:
            logging.error(f"Lỗi khi parse blockchair response: {str(e)}")
            return 0.0, 'blockchair'

    def check_balance(self, address: str, headers: dict = None) -> Tuple[float, str]:
        """Kiểm tra số dư của địa chỉ qua nhiều API, luôn ưu tiên mempool"""
        # Kiểm tra xem có cần đợi không
        current_time = time.time()
        if current_time - self.last_call_time < self.min_call_interval:
            time.sleep(self.min_call_interval - (current_time - self.last_call_time))
        
        # Luôn thử mempool trước
        logging.info(f"Đang thử kiểm tra số dư cho {address} bằng mempool API")
        try:
            mempool_api = self.api_list[0]  # mempool luôn là API đầu tiên
            url = mempool_api['url'].format(address=address)
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    balance, source = mempool_api['parser'](json_data)
                    if balance is not None:
                        # Reset lỗi khi thành công
                        self.error_count = 0
                        self.last_call_time = time.time()
                        logging.info(f"Mempool API thành công: {balance} BTC")
                        return balance, source
                    else:
                        logging.warning(f"Mempool API trả về balance là None")
                except (ValueError, KeyError) as e:
                    logging.error(f"Lỗi khi parse response từ mempool: {str(e)}")
            else:
                logging.error(f"Lỗi {response.status_code} từ mempool: {response.text}")
            
        except Exception as e:
            logging.error(f"Lỗi khi gọi mempool: {str(e)}")
        
        # Nếu mempool không khả dụng hoặc lỗi, thử các API khác
        logging.info(f"Mempool không khả dụng, thử các API khác")
        for api in self.api_list[1:]:  # Bỏ qua mempool vì đã thử ở trên
            try:
                logging.info(f"Đang thử {api['name']} API")
                url = api['url'].format(address=address)
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        balance, source = api['parser'](json_data)
                        if balance is not None:
                            # Reset lỗi khi thành công
                            self.error_count = 0
                            self.last_call_time = time.time()
                            logging.info(f"{api['name']} API thành công: {balance} BTC")
                            return balance, source
                        else:
                            logging.warning(f"{api['name']} API trả về balance là None")
                    except (ValueError, KeyError) as e:
                        logging.error(f"Lỗi khi parse response từ {api['name']}: {str(e)}")
                else:
                    logging.error(f"Lỗi {response.status_code} từ {api['name']}: {response.text}")
                
            except Exception as e:
                logging.error(f"Lỗi khi gọi {api['name']}: {str(e)}")
            
            # Tăng số lần lỗi
            self.error_count += 1
            
            # Nếu vượt quá số lần lỗi tối đa, đợi một chút
            if self.error_count >= self.max_errors:
                logging.warning(f"Đã vượt quá số lần lỗi tối đa ({self.max_errors}), đợi {self.cooldown_time} giây")
                time.sleep(self.cooldown_time)
                self.error_count = 0
        
        # Nếu tất cả API đều lỗi
        self.last_call_time = time.time()
        logging.error(f"Tất cả API đều lỗi khi kiểm tra số dư cho {address}")
        return 0.0, "unknown"

# Tạo instance của BalanceChecker
balance_checker = BalanceChecker()

def generate_private_key(strategy: str = "random") -> Tuple[bytes, str, str]:
    """Tạo private key theo chiến lược được chọn"""
    strategies = {
        "random": RandomSearchStrategy(),
        "brain": BrainWalletStrategy(),
        "pattern": PatternSearchStrategy(),
        "range": RangeSearchStrategy(),
        "lost": LostBitcoinStrategy()
    }
    
    if strategy not in strategies:
        strategy = "random"
    
    return strategies[strategy].generate_key()

def private_key_to_wif(private_key: bytes) -> str:
    """Chuyển đổi private key sang định dạng WIF"""
    # Thêm version byte (0x80 cho mainnet)
    extended_key = b'\x80' + private_key
    
    # Double SHA256
    first_sha256 = hashlib.sha256(extended_key).digest()
    second_sha256 = hashlib.sha256(first_sha256).digest()
    
    # Lấy 4 byte đầu làm checksum
    checksum = second_sha256[:4]
    
    # Thêm checksum vào cuối
    final_key = extended_key + checksum
    
    # Encode base58
    wif = base58.b58encode(final_key).decode('utf-8')
    return wif

def private_key_to_public_key(private_key: bytes) -> bytes:
    """Chuyển đổi private key sang public key"""
    signing_key = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
    verifying_key = signing_key.get_verifying_key()
    return b'\x04' + verifying_key.to_string()

def public_key_to_address(public_key: bytes) -> str:
    """Chuyển đổi public key sang địa chỉ Bitcoin"""
    # SHA256
    sha256_hash = hashlib.sha256(public_key).digest()
    
    # RIPEMD160
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(sha256_hash)
    ripemd160_hash = ripemd160.digest()
    
    # Thêm version byte (0x00 cho mainnet)
    version_ripemd160_hash = b'\x00' + ripemd160_hash
    
    # Double SHA256 cho checksum
    first_sha256 = hashlib.sha256(version_ripemd160_hash).digest()
    second_sha256 = hashlib.sha256(first_sha256).digest()
    
    # Lấy 4 byte đầu làm checksum
    checksum = second_sha256[:4]
    
    # Thêm checksum vào cuối
    binary_address = version_ripemd160_hash + checksum
    
    # Encode base58
    address = base58.b58encode(binary_address).decode('utf-8')
    return address

def private_key_to_address(private_key: bytes) -> str:
    """Chuyển đổi private key sang địa chỉ Bitcoin"""
    public_key = private_key_to_public_key(private_key)
    return public_key_to_address(public_key)

def check_balance(address: str) -> Tuple[float, str]:
    """Kiểm tra số dư của địa chỉ Bitcoin sử dụng nhiều API"""
    balance, api_source = balance_checker.check_balance(address)
    return balance, api_source

def search_bitcoin(
    strategy: BitcoinSearchStrategy = None,
    num_threads: int = 4,
    check_interval: int = 100,
    on_wallet_found: Callable = None
) -> None:
    """
    Tìm kiếm ví Bitcoin với số dư
    
    Args:
        strategy: Chiến lược tìm kiếm (mặc định là RandomSearchStrategy)
        num_threads: Số luồng chạy đồng thời
        check_interval: Số ví kiểm tra trước khi lưu vào DB
        on_wallet_found: Callback khi tìm thấy ví
    """
    if strategy is None:
        strategy = RandomSearchStrategy()
    
    # ... existing code ...

class BitcoinFinder:
    """Bitcoin address finder with balance checking"""
    
    def __init__(self):
        self.is_running_flag = False
        self.thread = None
        self.on_wallet_found = None
        self.COIN_TYPE = "BTC"  # Constant for Bitcoin
        self.strategies = [RandomSearchStrategy()]  # Default strategy
        self.current_strategy_index = 0

    def is_running(self) -> bool:
        return self.is_running_flag

    def start(self, on_wallet_found: Callable[[Wallet], None], strategy: str = "random"):
        """Start the search process"""
        if self.is_running():
            return
            
        # Set strategy based on parameter
        self.strategies = []
        
        if strategy == "all":
            # Use all strategies
            self.strategies = [
                RandomSearchStrategy(),
                BrainWalletStrategy(),
                PatternSearchStrategy(),
                RangeSearchStrategy(),
                LostBitcoinStrategy()
            ]
        elif isinstance(strategy, list):
            # Use specified strategies
            for s in strategy:
                if s == "random":
                    self.strategies.append(RandomSearchStrategy())
                elif s == "brain":
                    self.strategies.append(BrainWalletStrategy())
                elif s == "pattern":
                    self.strategies.append(PatternSearchStrategy())
                elif s == "range":
                    self.strategies.append(RangeSearchStrategy())
                elif s == "lost":
                    self.strategies.append(LostBitcoinStrategy())
        else:
            # Single strategy
            if strategy == "random":
                self.strategies = [RandomSearchStrategy()]
            elif strategy == "brain":
                self.strategies = [BrainWalletStrategy()]
            elif strategy == "pattern":
                self.strategies = [PatternSearchStrategy()]
            elif strategy == "range":
                self.strategies = [RangeSearchStrategy()]
            elif strategy == "lost":
                self.strategies = [LostBitcoinStrategy()]
            else:
                self.strategies = [RandomSearchStrategy()]  # Default to random
        
        # If no strategies were added, use random as default
        if not self.strategies:
            self.strategies = [RandomSearchStrategy()]
            
        self.current_strategy_index = 0
        self.is_running_flag = True
        self.on_wallet_found = on_wallet_found
        
        self.thread = threading.Thread(target=self._search_worker)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the search process"""
        self.is_running_flag = False
        if self.thread:
            self.thread.join()
            self.thread = None

    def _search_worker(self):
        """Worker function for searching Bitcoin addresses"""
        counter = 0
        start_time = time.time()
        
        while self.is_running_flag:
            try:
                counter += 1
                current_time = time.time()
                elapsed = current_time - start_time
                rate = counter / elapsed if elapsed > 0 else 0
                
                # Get current strategy and move to next one
                current_strategy = self.strategies[self.current_strategy_index]
                strategy_name = current_strategy.__class__.__name__
                self.current_strategy_index = (self.current_strategy_index + 1) % len(self.strategies)
                
                # Generate key pair using the current strategy
                private_key, wif, address = current_strategy.generate_key()
                
                # Check balance
                balance, api_source = self.check_balance(address)
                
                # Create wallet object
                wallet = Wallet(
                    address=address,
                    private_key_hex=private_key.hex(),
                    wif_key=wif,
                    balance=balance,
                    strategy=strategy_name.replace("Strategy", "").lower(),
                    api_source=api_source,
                    coin_type=self.COIN_TYPE,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                # Save wallet and update stats
                try:
                    self._save_wallet_and_stats(wallet)
                except Exception as e:
                    print(f"[ERROR] Error saving wallet or updating stats: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                
            except Exception as e:
                print(f"[ERROR] Error in search worker: {str(e)}")
                import traceback
                print(traceback.format_exc())
                
            time.sleep(1)

    def _save_wallet_and_stats(self, wallet: Wallet):
        """Save wallet and update stats"""
        # Save wallet
        saved = wallet_repo.save_wallet(wallet)
        logging.info(f"Wallet saved: {saved}")
        if saved:
            # Update stats for BTC
            new_stats = stats_repo.update(wallet)
            # Notify callback with wallet and stats
            if self.on_wallet_found:
                self.on_wallet_found(wallet, new_stats)

    def check_balance(self, address: str) -> Tuple[float, str]:
        """Check balance of a Bitcoin address using multiple APIs"""
        apis = [
            ('mempool.space', f'https://mempool.space/api/address/{address}'),
            ('blockchain.info', f'https://blockchain.info/q/addressbalance/{address}'),
            ('blockchair', f'https://api.blockchair.com/bitcoin/dashboards/address/{address}')
        ]
        
        for api_name, url in apis:
            try:
                print(f"[BALANCE] Trying {api_name} API... for {address}")
                response = requests.get(url)
                if response.status_code == 200:
                    balance = 0.0
                    
                    if api_name == 'mempool.space':
                        data = response.json()
                        # Convert satoshis to BTC
                        balance = float(data.get('chain_stats', {}).get('funded_txo_sum', 0)) / 100000000
                    elif api_name == 'blockchain.info':
                        # Response is already in satoshis
                        balance = float(response.text) / 100000000
                    elif api_name == 'blockchair':
                        data = response.json()
                        # Data is in satoshis
                        balance = float(data.get('data', {}).get(address, {}).get('address', {}).get('balance', 0)) / 100000000
                    
                    return balance, f"API: {api_name}"
                else:
                    print(f"[BALANCE] {api_name} returned status code: {response.status_code}")
                    
            except Exception as e:
                print(f"[ERROR] Error checking balance with {api_name}: {str(e)}")
                import traceback
                print(traceback.format_exc())
                continue
                
        print("[BALANCE] All APIs failed, returning 0 balance")
        return 0.0, "unknown"

    def _generate_key_pair(self) -> Tuple[bytes, str]:
        """Generate a random Bitcoin private key and address"""
        # Generate a random 32-byte private key
        private_key = os.urandom(32)
        
        # Generate the Bitcoin address from the private key
        address = private_key_to_address(private_key)
        
        return private_key, address

    def _to_wif(self, private_key_hex: str) -> str:
        """Convert private key to WIF format"""
        # Your existing WIF conversion logic here
        pass 
import os
import hashlib
import random
import base58
from typing import Tuple
from coincurve import PrivateKey

class BitcoinSearchStrategy:
    """Interface cho các chiến lược tìm kiếm"""
    def generate_key(self) -> Tuple[bytes, str, str]:
        """Tạo key theo chiến lược cụ thể"""
        raise NotImplementedError

    @staticmethod
    def _private_key_to_wif(private_key: bytes) -> str:
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

    @staticmethod
    def _private_key_to_address(private_key: bytes) -> str:
        """Chuyển đổi private key sang địa chỉ Bitcoin"""
        # Tạo public key từ private key
        pk = PrivateKey(private_key)
        public_key = pk.public_key.format(compressed=True)
        
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

class RandomSearchStrategy(BitcoinSearchStrategy):
    """Chiến lược tìm kiếm ngẫu nhiên hoàn toàn"""
    def generate_key(self) -> Tuple[bytes, str, str]:
        private_key = os.urandom(32)
        wif = self._private_key_to_wif(private_key)
        address = self._private_key_to_address(private_key)
        return private_key, wif, address

class BrainWalletStrategy(BitcoinSearchStrategy):
    """Chiến lược tìm kiếm từ passphrase (brain wallet)"""
    def __init__(self):
        self.words = [
            "satoshi", "bitcoin", "blockchain", "crypto", "wallet",
            "private", "key", "address", "mining", "block"
        ]
    
    def generate_key(self) -> Tuple[bytes, str, str]:
        # Tạo passphrase ngẫu nhiên từ 3-5 từ
        num_words = random.randint(3, 5)
        passphrase = " ".join(random.choices(self.words, k=num_words))
        
        # SHA256 của passphrase làm private key
        private_key = hashlib.sha256(passphrase.encode()).digest()
        wif = self._private_key_to_wif(private_key)
        address = self._private_key_to_address(private_key)
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
            wif = self._private_key_to_wif(private_key)
            address = self._private_key_to_address(private_key)
            
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
        
        wif = self._private_key_to_wif(private_key)
        address = self._private_key_to_address(private_key)
        return private_key, wif, address

class LostBitcoinStrategy(BitcoinSearchStrategy):
    """Chiến lược tìm kiếm các ví Bitcoin đã mất"""
    def __init__(self):
        self.early_patterns = [
            "1111", # Các địa chỉ thời kỳ đầu thường đơn giản
            "1234",
            "abcd",
            "1A1z", # Pattern của Satoshi
            "1H6Q"  # Pattern phổ biến thời kỳ đầu
        ]
    
    def generate_key(self) -> Tuple[bytes, str, str]:
        while True:
            private_key = os.urandom(32)
            wif = self._private_key_to_wif(private_key)
            address = self._private_key_to_address(private_key)
            
            if any(pattern in address for pattern in self.early_patterns):
                return private_key, wif, address 
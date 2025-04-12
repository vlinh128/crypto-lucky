import datetime
from .base_finder import BaseFinder
import time
import logging
import requests
import binascii
from eth_account import Account
import secrets
from web3 import Web3
from database import wallet_repo, stats_repo
from database.models import Wallet

class EthereumFinder(BaseFinder):
    """Ethereum address finder with balance checking"""
    
    def __init__(self):
        super().__init__("ETH")
        self.w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
        Account.enable_unaudited_hdwallet_features()
        # API endpoints để check balance
        self.api_endpoints = [
            {
                'name': 'etherscan',
                'url': 'https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest',
                'parser': self._parse_etherscan_response
            },
            {
                'name': 'blockchair',
                'url': 'https://api.blockchair.com/ethereum/dashboards/address/{address}',
                'parser': self._parse_blockchair_response
            }
        ]

    def _search_worker(self):
        """Main search worker"""
        counter = 0
        start_time = time.time()
        
        while self._is_running:
            try:
                # Generate random private key
                private_key = Account.create().key
                
                # Get address from private key
                account = Account.from_key(private_key)
                address = account.address
                
                # Check balance
                balance, api_source = self.check_balance(address)
                
                # Lưu tất cả ví tìm được
                wallet = Wallet(
                    address=address,
                    private_key_hex=binascii.hexlify(private_key).decode(),
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
                    
                counter += 1
                if counter % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = counter / elapsed
                    logging.info(f"ETH Finder: Checked {counter} addresses at {rate:.2f} addresses/second")
                    
                time.sleep(1)
                    
            except Exception as e:
                logging.error(f"Error in ETH search worker: {str(e)}")

    def _parse_etherscan_response(self, response):
        """Parse Etherscan API response"""
        try:
            data = response.json()
            if data['status'] == '1' and data['message'] == 'OK':
                balance = int(data['result']) / 1e18  # Convert from wei to ETH
                return balance
        except:
            pass
        return None

    def _parse_blockchair_response(self, response):
        """Parse Blockchair API response"""
        try:
            data = response.json()
            if 'data' in data:
                address = list(data['data'].keys())[0]
                balance = data['data'][address]['address']['balance'] / 1e18  # Convert from wei to ETH
                return balance
        except:
            pass
        return None

    def check_balance(self, address: str):
        """Check ETH balance using multiple APIs"""
        # Thử với Web3 trước
        try:
            balance_wei = self.w3.eth.get_balance(address)
            balance_eth = self.w3.from_wei(balance_wei, 'ether')
            return float(balance_eth), "web3"
        except Exception as e:
            logging.error(f"Error checking ETH balance with Web3: {str(e)}")
        
        # Thử với các API endpoints khác
        for api in self.api_endpoints:
            try:
                url = api['url'].format(address=address)
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    balance = api['parser'](response)
                    if balance is not None:
                        return balance, api['name']
            except Exception as e:
                logging.error(f"Error checking ETH balance with {api['name']}: {str(e)}")
                continue
        
        # Nếu không có API nào hoạt động, trả về 0
        return 0, "unknown" 
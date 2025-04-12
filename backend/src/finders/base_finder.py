from abc import ABC, abstractmethod
from threading import Thread
import logging
from typing import Callable
from database.models import Wallet, Stats

class BaseFinder(ABC):
    def __init__(self, coin_type: str):
        self._is_running = False
        self._search_thread = None
        self.coin_type = coin_type
        self.on_wallet_found = None

    def start(self, on_wallet_found: Callable[[Wallet, Stats], None] = None):
        """Start the search process with optional callback"""
        if not self._is_running:
            self._is_running = True
            self.on_wallet_found = on_wallet_found
            self._search_thread = Thread(target=self._search_worker)
            self._search_thread.daemon = True
            self._search_thread.start()
            logging.info(f"Đã bắt đầu tìm kiếm {self.coin_type}")

    def is_running(self):
        """Check if search is running"""
        return self._is_running and self._search_thread and self._search_thread.is_alive()

    @abstractmethod
    def _search_worker(self):
        """Main search logic - must be implemented by child classes"""
        pass

    @abstractmethod
    def check_balance(self, address: str):
        """Check balance for an address - must be implemented by child classes"""
        pass 
from .connection import DatabaseConnection
from .repository import WalletRepository, StatsRepository

# Khởi tạo database connection
db = DatabaseConnection()

# Khởi tạo repositories
wallet_repo = WalletRepository(db)
stats_repo = StatsRepository(db)

# Export các repository để các module khác có thể import
__all__ = ['db', 'wallet_repo', 'stats_repo'] 
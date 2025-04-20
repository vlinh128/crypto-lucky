from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import threading
from datetime import datetime, UTC
from database import wallet_repo, stats_repo
from database.models import Wallet, Stats
from finders.bitcoin_finder import BitcoinFinder
from finders.ethereum_finder import EthereumFinder
from finders.dogecoin_finder import DogecoinFinder
import logging
import json
from queue import Queue
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Cấu hình logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Khởi tạo API với Swagger
api = Api(app, version='1.0',
    title='Crypto Finder API',
    description='API để tìm kiếm các loại cryptocurrency',
    doc='/docs'
)

# Tạo các namespace
search_ns = Namespace('search', description='Các API liên quan đến tìm kiếm')
wallet_ns = Namespace('wallets', description='Các API liên quan đến ví')
stats_ns = Namespace('stats', description='Các API liên quan đến thống kê')

api.add_namespace(search_ns, path='/api/search')
api.add_namespace(wallet_ns, path='/api/wallets')
api.add_namespace(stats_ns, path='/api/stats')

# Global queue for clients
clients = []

def send_sse_message(event_type: str, data: dict):
    """Send SSE message to all clients"""
    message = {
        'event': event_type,
        'data': data
    }
    for client in clients[:]:
        try:
            client.put(json.dumps(message))
        except:
            clients.remove(client)

def handle_wallet_found(wallet: Wallet, stats: Stats):
    """Callback khi tìm thấy ví mới"""
    # Gửi thông báo qua SSE
    send_sse_message('wallet_found', wallet.to_dict_str())
    
    # Gửi stats mới
    if stats:
        send_sse_message('stats_update', stats.to_dict_str())

# Khởi tạo và start tất cả finders
finders = [
    BitcoinFinder(),
    EthereumFinder(),
    DogecoinFinder()
]

# Start tất cả finders với callback
for finder in finders:
    finder.start(on_wallet_found=handle_wallet_found)

# Models cho Swagger
wallet_model = api.model('Wallet', {
    'address': fields.String(description='Địa chỉ ví'),
    'balance': fields.Float(description='Số dư'),
    'strategy': fields.String(description='Chiến lược đã sử dụng'),
    'api_source': fields.String(description='API được sử dụng để kiểm tra số dư'),
    'created_at': fields.DateTime(description='Thời gian tạo'),
    'updated_at': fields.DateTime(description='Thời gian cập nhật')
})

# Models cho response
wallet_list_model = api.model('WalletList', {
    'success': fields.Boolean(description='Trạng thái response'),
    'data': fields.Nested(api.model('WalletListData', {
        'wallets': fields.List(fields.Nested(wallet_model), description='Danh sách ví'),
    }))
})

@app.route('/api/stream')
def stream():
    """SSE endpoint for real-time updates"""
    def event_stream():
        client = Queue()
        clients.append(client)
        try:
            while True:
                message = client.get()
                yield f"data: {message}\n\n"
        except GeneratorExit:
            clients.remove(client)
    
    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream'
    )

@stats_ns.route('')
@stats_ns.route('/')
class StatsResource(Resource):
    @stats_ns.doc('get_stats')
    def get(self):
        """Get current statistics"""
        try:
            all_stats = {}
            for finder in finders:
                stats = stats_repo.get_latest(finder.coin_type)
                if stats:
                    all_stats[finder.coin_type] = stats.to_dict_str()
            
            return {
                'success': True,
                'data': all_stats
            }
        except Exception as e:
            logging.error(f"Error getting stats: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }, 500

@wallet_ns.route('')
class WalletList(Resource):
    @wallet_ns.doc('get_wallets')
    @wallet_ns.param('limit', 'Số lượng item (tối đa 50)', type=int, default=20)
    @wallet_ns.response(200, 'Success', wallet_list_model)
    def get(self):
        """Get wallets with pagination"""
        try:
            # Parse arguments
            limit = min(request.args.get('limit', 20, type=int), 50)  # Giới hạn tối đa 50
            
            # Get wallets with pagination
            wallets = wallet_repo.get_wallets(limit=limit)
            
            # Return response
            return {
                'success': True,
                'data': {
                    'wallets': [wallet.to_dict_str() for wallet in wallets],
                }
            }
        except Exception as e:
            logging.error(f"Lỗi khi lấy danh sách ví: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }, 500

if __name__ == '__main__':
    # Get host and port from environment variables
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8888"))
    
    logging.info(f"Starting server on {host}:{port}")
    app.run(host=host, port=port) 
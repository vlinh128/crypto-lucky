from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import threading
from datetime import datetime, UTC
from database import wallet_repo, stats_repo
from database.models import Wallet, Stats
from finders.bitcoin_finder import BitcoinFinder
import logging
import json
from queue import Queue
import asyncio
from typing import List
import inspect

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app)

# Khởi tạo API với Swagger
api = Api(app, version='1.0',
    title='Bitcoin Finder API',
    description='API để tìm kiếm ví Bitcoin',
    doc='/docs'
)

# Tạo các namespace
search_ns = Namespace('search', description='Các API liên quan đến tìm kiếm')
wallet_ns = Namespace('wallets', description='Các API liên quan đến ví')
stats_ns = Namespace('stats', description='Các API liên quan đến thống kê')

api.add_namespace(search_ns, path='/api/search')
api.add_namespace(wallet_ns, path='/api/wallets')
api.add_namespace(stats_ns, path='/api/stats')

def handle_wallet_found(wallet: Wallet, stats: Stats):
    """Handle when a wallet is found"""
    try:
        # Gửi thông báo qua SSE
        send_sse_message("wallet_found", wallet.to_dict_str())
        send_sse_message("stats_update", stats.to_dict_str())
        
    except Exception as e:
        logging.error(f"Error sending SSE message: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Khởi tạo Bitcoin finder và start ngay khi khởi động
bitcoin_finder = BitcoinFinder()
bitcoin_finder.start(on_wallet_found=handle_wallet_found, strategy="all")

# Global queue for clients
clients = []

# Models cho Swagger
strategy_model = api.model('Strategy', {
    'strategies': fields.String(required=True,
        description="Chiến lược tìm kiếm ('all' hoặc list các chiến lược)",
        example="all")
})

wallet_model = api.model('Wallet', {
    'address': fields.String(description='Địa chỉ ví'),
    'private_key_hex': fields.String(description='Private key dạng hex'),
    'wif_key': fields.String(description='WIF key'),
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
        'total': fields.Integer(description='Tổng số ví có số dư'),
        'next_cursor': fields.String(description='Cursor cho lần load tiếp theo')
    }))
})

# Cập nhật pagination parser
pagination_parser = api.parser()
pagination_parser.add_argument('limit', type=int, default=20, help='Số lượng item (tối đa 50)')
pagination_parser.add_argument('cursor', help='Cursor cho load more')

def send_sse_message(event_type: str, data: dict):
    """Helper function to send SSE messages to all clients"""
    message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    for queue in clients:
        queue.put(message)


@search_ns.route('/start')
class SearchStart(Resource):
    @search_ns.expect(strategy_model)
    @search_ns.doc(responses={
        200: 'Bắt đầu tìm kiếm thành công',
        400: 'Đã có một phiên tìm kiếm đang chạy',
        500: 'Lỗi server'
    })
    def post(self):
        """Bắt đầu tìm kiếm Bitcoin"""
        if bitcoin_finder.is_running():
            return {
                'success': False,
                'message': 'Đã có một phiên tìm kiếm đang chạy'
            }, 400
        
        try:
            # Thử lấy dữ liệu JSON từ request
            try:
                data = request.get_json()
                strategies = data.get('strategies', 'all')
            except Exception:
                # Nếu không thể lấy dữ liệu JSON, sử dụng giá trị mặc định
                strategies = 'all'
            
            # Start finder với callback
            bitcoin_finder.start(
                on_wallet_found=handle_wallet_found,
                strategy=strategies
            )
        
            return {
                'success': True,
                'message': 'Đã bắt đầu tìm kiếm Bitcoin'
            }
        except Exception as e:
            logging.error(f"Error starting search: {e}")
            return {
                'success': False,
                'message': f'Lỗi khi bắt đầu tìm kiếm: {str(e)}'
            }, 500

@search_ns.route('/stop')
class SearchStop(Resource):
    @search_ns.doc(responses={
        200: 'Dừng tìm kiếm thành công',
        400: 'Không có phiên tìm kiếm nào đang chạy',
        500: 'Lỗi server'
    })
    def post(self):
        """Dừng tìm kiếm Bitcoin"""
        if not bitcoin_finder.is_running():
            return {
                'success': False,
                'message': 'Không có phiên tìm kiếm nào đang chạy'
            }, 400
        
        try:
            bitcoin_finder.stop()
            # Notify clients about search status
            send_sse_message('search_status', {'is_searching': False})
            
            return {
                'success': True,
                'message': 'Đã dừng tìm kiếm'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi dừng tìm kiếm: {str(e)}'
            }, 500

@app.route('/api/stream')
def stream():
    """SSE endpoint for real-time updates"""
    def generate():
        # Create queue for this client
        queue = Queue()
        clients.append(queue)
        
        try:
            while True:
                message = queue.get()    # This will block until a message is available
                yield message
        finally:
            clients.remove(queue)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )

@app.route('/api/stats')
def get_stats():
    """Get current statistics"""
    try:
        stats = stats_repo.get_latest('BTC')
        return jsonify({
            'success': True,
            'data': stats.to_dict() if stats else {}
        })
    except Exception as e:
        logging.error(f"Error getting stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.get("/api/wallets")
def get_wallets():
    """Get wallets with pagination"""
    try:
        wallets = wallet_repo.get_wallets_paginated()
        return {
            "wallets": [{
                "address": wallet.address,
                "balance": wallet.balance,
                "strategy": wallet.strategy,
                "api_source": wallet.api_source,
                "coin_type": wallet.coin_type,
                "created_at": wallet.created_at.isoformat(),
                "updated_at": wallet.updated_at.isoformat()
            } for wallet in wallets]
        }
    except Exception as e:
        logging.error(f"Lỗi khi lấy danh sách ví: {str(e)}")
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888) 
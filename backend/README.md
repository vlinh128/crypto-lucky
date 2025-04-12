# Crypto Finder Backend

Backend service cho ứng dụng tìm kiếm ví Bitcoin.

## Cài đặt

1. Tạo môi trường ảo:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows
```

2. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

## Chạy server

```bash
python src/web_server.py
```

Server sẽ chạy tại `http://localhost:8888`

## API Endpoints

- `GET /api/stats`: Lấy thống kê tìm kiếm
- `GET /api/addresses`: Lấy danh sách địa chỉ đã tìm kiếm
- `POST /api/search/start`: Bắt đầu tìm kiếm
- `POST /api/search/stop`: Dừng tìm kiếm
- `GET /stream`: Server-Sent Events endpoint cho realtime updates 
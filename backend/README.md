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
make install
```

3. Thiết lập file .env:
```bash
cp .env.example .env
# Chỉnh sửa file .env với thông tin MongoDB của bạn
```

## Chạy server

### Chạy trực tiếp (không dùng Docker)
```bash
make run
```

Server sẽ chạy tại `http://localhost:8888`

### Chạy với Docker
```bash
make up
```

## Quản lý Docker

- Khởi động lại toàn bộ hệ thống: `make restart`
- Khởi động lại với logs: `make restart-logs`
- Khởi động lại backend: `make restart-backend`
- Khởi động lại frontend: `make restart-frontend`
- Xem logs: `make logs`
- Xem trạng thái: `make ps`
- Dừng hệ thống: `make down`
- Xóa tất cả containers và images: `make clean-docker`

## Chạy tests

Chạy tất cả tests:
```bash
make test
```

Chạy một test file cụ thể:
```bash
make test-file file=tests/test_price_predictor.py
```

Chạy tests với báo cáo coverage:
```bash
make test-coverage
```

## Công cụ phát triển

Format code:
```bash
make format
```

Kiểm tra code style:
```bash
make lint
```

Dọn dẹp cache và file tạm:
```bash
make clean
```

## Cấu hình

Các biến môi trường trong file `.env`:

- `MONGODB_URI`: URI kết nối MongoDB (mặc định: mongodb://localhost:27017/crypto-lucky)
- `API_PORT`: Port cho API server (mặc định: 8888)
- `API_HOST`: Host cho API server (mặc định: 0.0.0.0)
- `LOG_LEVEL`: Cấp độ log (mặc định: INFO)
- `SEARCH_INTERVAL`: Khoảng thời gian tìm kiếm (giây) (mặc định: 5)
- `MAX_WALLETS`: Số lượng ví tối đa lưu trữ (mặc định: 1000)
- `PREDICTION_INTERVAL`: Khoảng thời gian dự đoán giá (giây) (mặc định: 3600)
- `MAX_PRICE_HISTORY`: Số lượng điểm dữ liệu giá tối đa (mặc định: 1000)

## API Endpoints

- `GET /api/stats`: Lấy thống kê tìm kiếm
- `GET /api/addresses`: Lấy danh sách địa chỉ đã tìm kiếm
- `POST /api/search/start`: Bắt đầu tìm kiếm
- `POST /api/search/stop`: Dừng tìm kiếm
- `GET /stream`: Server-Sent Events endpoint cho realtime updates 
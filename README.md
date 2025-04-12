# Crypto Lucky - Bitcoin Address Finder

Ứng dụng tìm kiếm địa chỉ Bitcoin có số dư, sử dụng nhiều chiến lược tìm kiếm khác nhau.

## Tính năng

- Tìm kiếm địa chỉ Bitcoin tự động
- Nhiều chiến lược tìm kiếm: random, brain wallet, pattern, range, lost
- Kiểm tra số dư qua nhiều API: mempool.space, blockchain.info, blockchair
- Theo dõi realtime qua Server-Sent Events (SSE)
- Lưu trữ dữ liệu với MongoDB
- Giao diện web hiện đại với React

## Yêu cầu

- Docker và Docker Compose
- MongoDB (chạy locally hoặc MongoDB Atlas)

## Cài đặt và Chạy

1. **Cài đặt MongoDB**
   - Sử dụng MongoDB local (port 27017)
   - Hoặc tạo database trên [MongoDB Atlas](https://www.mongodb.com/atlas/database)

2. **Cấu hình MongoDB URI**
```bash
# Tạo file .env từ template
cp .env.example .env

# Cập nhật MONGODB_URI trong .env
# Nếu dùng MongoDB local:
MONGODB_URI=mongodb://localhost:27017/crypto-lucky
# Hoặc nếu dùng MongoDB Atlas:
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/crypto-lucky
```

3. **Chạy ứng dụng với Docker**
```bash
# Clone repository
git clone <repository-url>
cd crypto-lucky

# Khởi động services
docker-compose up -d

# Xem logs
docker-compose logs -f

# Dừng services
docker-compose down
```

Truy cập ứng dụng tại `http://localhost:5173`

## Cấu trúc Project

```
crypto-lucky/
├── backend/             # Python Flask backend
│   ├── src/
│   │   ├── database/   # Database models và repositories
│   │   ├── finders/    # Bitcoin address finder logic
│   │   └── web_server.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/           # React frontend
│   ├── src/
│   ├── package.json
│   └── Dockerfile
│
└── docker-compose.yml  # Docker Compose configuration
```

## Cài đặt Thủ công

1. **Clone repository**
```bash
git clone <repository-url>
cd crypto-lucky
```

2. **Backend setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Tạo file .env
cp .env.example .env
# Cập nhật các biến môi trường trong .env
```

3. **Frontend setup**
```bash
cd frontend
npm install

# Tạo file .env
cp .env.example .env
# Cập nhật VITE_API_URL trong .env
```

4. **Chạy ứng dụng**

Backend:
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python src/web_server.py
```

Frontend:
```bash
cd frontend
npm run dev
```

## Deploy

### Backend (Render.com)
1. Push code lên GitHub
2. Tạo new Web Service trên Render
3. Connect với GitHub repository
4. Cấu hình:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python src/web_server.py`
   - Environment Variables: Thêm các biến từ .env

### Frontend (Vercel)
1. Push code lên GitHub
2. Import project vào Vercel
3. Cấu hình Environment Variables:
   - `VITE_API_URL`: URL của backend service

## Environment Variables

### Backend (.env)
```
MONGODB_URI=mongodb://localhost:27017/crypto-lucky
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8888
```

## Contributing

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

## License

MIT License - xem [LICENSE](LICENSE) để biết thêm chi tiết. 
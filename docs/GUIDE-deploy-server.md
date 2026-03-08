# 🚀 Deploy Knowledge Search: Mac → Linux Server

> Quy trình deploy đầy đủ từ Mac local lên Linux server văn phòng.
> **Stack:** Docker Compose (pgvector + FastAPI + Next.js)
> **Trung chuyển code:** GitHub | **SSH:** Tailscale

---

## 📋 Kiến trúc tổng quan

```
Mac (code) ──git push──▶ GitHub ──git pull──▶ Linux Server
                                                │
                                          docker compose
                                           ┌────┼────┐
                                           DB  API  Web
                                         :5432 :8000 :3001
                                                │
                                         Tailscale Serve / Nginx
                                                │
                                          Live Link nội bộ
                                    http://<tailscale-ip>:3001
```

---

## PHẦN 1: Setup Linux Server (chỉ làm 1 lần)

### 1.1 Cài Tailscale

```bash
# Ubuntu/Debian
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Sau khi `tailscale up` → đăng nhập tài khoản Tailscale → server xuất hiện trong network.

```bash
# Kiểm tra IP
tailscale ip -4
# Ghi nhớ IP này, VD: 100.x.y.z
```

### 1.2 Cài Docker & Docker Compose

```bash
# Cài Docker (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Cho user hiện tại dùng docker không cần sudo
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### 1.3 Cài Git

```bash
sudo apt-get install -y git
git config --global user.name "Tên bạn"
git config --global user.email "email@domain.com"
```

### 1.4 Clone repo lần đầu

```bash
cd ~
git clone https://github.com/<username>/knowledge-search.git
cd knowledge-search
```

> **Private repo?** Dùng HTTPS + Personal Access Token hoặc SSH key:
> ```bash
> # Option A: HTTPS (mỗi lần nhập token)
> git clone https://github.com/<username>/knowledge-search.git
>
> # Option B: SSH key (setup 1 lần)
> ssh-keygen -t ed25519 -C "server-key"
> cat ~/.ssh/id_ed25519.pub
> # → Copy pubkey → GitHub Settings → SSH Keys → Add
> git clone git@github.com:<username>/knowledge-search.git
> ```

### 1.5 Tạo file .env cho backend

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Nội dung cần sửa:

```env
DATABASE_URL=postgresql+asyncpg://ks_admin:ks_secret_2024@db:5432/knowledge_search
SECRET_KEY=<random-secret-key-dài>
OPENAI_API_KEY=sk-...
DEBUG=false
```

> ⚠️ **Quan trọng:** `DATABASE_URL` phải dùng host `db` (tên service trong Docker Compose), KHÔNG dùng `localhost`.

### 1.6 Build & Khởi chạy lần đầu

```bash
cd ~/knowledge-search
docker compose up -d --build
```

Đợi 1-2 phút để build xong. Kiểm tra:

```bash
# Xem trạng thái
docker compose ps

# Xem logs (Ctrl+C để thoát)
docker compose logs -f

# Test từng service
curl http://localhost:8000/docs    # Backend API docs
curl http://localhost:3001         # Frontend
```

---

## PHẦN 2: Mở Live Link nội bộ

### Option A: Truy cập trực tiếp qua Tailscale IP (đơn giản nhất)

Nếu cả Mac và Linux server đều có Tailscale → bạn đã có thể truy cập ngay:

```
http://<tailscale-ip>:3001    # Frontend
http://<tailscale-ip>:8000    # Backend API
```

Kiểm tra từ Mac:

```bash
# Trên Mac
tailscale status              # Xem IP server
curl http://100.x.y.z:3001   # Test frontend
```

> ⚠️ **Frontend gọi API:** Cần đảm bảo `NEXT_PUBLIC_API_URL` trỏ đúng.
> Trong `docker-compose.yml`, thay `http://localhost:8000` thành `http://<tailscale-ip>:8000`:
>
> ```yaml
> frontend:
>   build:
>     args:
>       NEXT_PUBLIC_API_URL: http://<tailscale-ip>:8000
> ```
>
> Sau đó rebuild: `docker compose up -d --build frontend`

### Option B: Tailscale Serve (HTTPS tự động, domain đẹp)

```bash
# Serve frontend qua port 443 (HTTPS)
sudo tailscale serve --bg 3001

# Kiểm tra status
tailscale serve status
```

Sau khi bật, truy cập: `https://<machine-name>.<tailnet>.ts.net`

Để serve cả backend:

```bash
sudo tailscale serve --bg --set-path /api 8000
```

### Option C: Nginx Reverse Proxy

```bash
sudo apt-get install -y nginx

# Tạo config
sudo tee /etc/nginx/sites-available/knowledge-search << 'EOF'
server {
    listen 80;
    server_name _;

    # Frontend
    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/knowledge-search /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Truy cập: `http://<tailscale-ip>` (port 80, không cần nhập port).

---

## PHẦN 3: Quy trình deploy hàng ngày

### Trên Mac (push code)

```bash
cd ~/99.Code/knowledge-search
git add -A
git commit -m "feat: mô tả thay đổi"
git push origin main
```

### Trên Linux Server (pull & restart)

```bash
ssh <user>@<tailscale-ip>
cd ~/knowledge-search
git pull origin main

# Nếu chỉ thay đổi code (không thay đổi dependency):
docker compose up -d --build

# Nếu thay đổi requirements.txt hoặc package.json:
docker compose down
docker compose up -d --build --no-cache
```

### Script deploy tự động (optional)

Tạo file `deploy.sh` trên server:

```bash
cat > ~/knowledge-search/deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "📥 Pulling latest code..."
cd ~/knowledge-search
git pull origin main

echo "🔨 Rebuilding containers..."
docker compose down
docker compose up -d --build

echo "⏳ Waiting for services..."
sleep 10

echo "✅ Checking services..."
docker compose ps
curl -sf http://localhost:8000/docs > /dev/null && echo "✅ Backend OK" || echo "❌ Backend FAIL"
curl -sf http://localhost:3001 > /dev/null && echo "✅ Frontend OK" || echo "❌ Frontend FAIL"

echo "🎉 Deploy complete!"
EOF

chmod +x ~/knowledge-search/deploy.sh
```

Sau đó mỗi lần deploy chỉ cần:

```bash
ssh <user>@<tailscale-ip>
./knowledge-search/deploy.sh
```

---

## PHẦN 4: Giữ app chạy ổn định

### Docker Compose `restart: unless-stopped`

Đã có sẵn trong `docker-compose.yml` → container tự restart khi crash hoặc server reboot.

### Bật Docker auto-start khi boot

```bash
sudo systemctl enable docker
```

### Kiểm tra app đang chạy

```bash
docker compose ps                    # Trạng thái container
docker compose logs --tail=50 -f     # Xem 50 dòng log cuối
docker stats --no-stream             # RAM/CPU usage
```

### Restart từng service

```bash
docker compose restart backend       # Chỉ restart backend
docker compose restart frontend      # Chỉ restart frontend
docker compose restart db            # Chỉ restart database
```

---

## PHẦN 5: Troubleshooting

### ❌ App chỉ chạy trên localhost, không truy cập từ máy khác

**Nguyên nhân:** App bind `127.0.0.1` thay vì `0.0.0.0`.

**Giải pháp:** Đã xử lý sẵn — Dockerfile dùng `--host 0.0.0.0`. Kiểm tra:

```bash
docker compose exec backend ss -tlnp | grep 8000
# Phải thấy 0.0.0.0:8000
```

### ❌ Pull xong nhưng không truy cập được

```bash
# 1. Kiểm tra container có chạy không
docker compose ps

# 2. Xem logs lỗi
docker compose logs backend --tail=30
docker compose logs frontend --tail=30

# 3. Rebuild hoàn toàn
docker compose down
docker compose up -d --build --no-cache
```

### ❌ Port chưa mở / bị chặn

```bash
# Kiểm tra port đang listen
sudo ss -tlnp | grep -E '3001|8000|5432'

# Nếu dùng UFW firewall
sudo ufw allow 3001
sudo ufw allow 8000
sudo ufw status
```

> **Lưu ý:** Nếu dùng Tailscale, traffic đi qua Tailscale tunnel → firewall thường không chặn. Chỉ cần mở port nếu truy cập qua LAN thông thường.

### ❌ Container bị tắt / crash loop

```bash
# Xem container nào đang restart
docker compose ps

# Xem logs của container lỗi
docker compose logs <service-name> --tail=50

# Nguyên nhân phổ biến:
# - DB: .env sai password → kiểm tra POSTGRES_PASSWORD
# - Backend: thiếu .env → cp .env.example .env
# - Frontend: NEXT_PUBLIC_API_URL sai → rebuild frontend
```

### ❌ Database mất data sau deploy

Data PostgreSQL được lưu trong Docker volume `pgdata` → **không mất khi rebuild**.

```bash
# Kiểm tra volume
docker volume ls | grep pgdata

# ⚠️ CẢNH BÁO: Lệnh này XÓA TOÀN BỘ data
# docker compose down -v   ← KHÔNG dùng -v trừ khi muốn xóa DB
```

### ❌ Frontend gọi API bị lỗi CORS / sai URL

```bash
# Kiểm tra NEXT_PUBLIC_API_URL hiện tại
docker compose exec frontend printenv | grep API

# Nếu sai → sửa docker-compose.yml → rebuild
docker compose up -d --build frontend
```

### ❌ Tailscale SSH bị timeout

```bash
# Trên Mac - kiểm tra Tailscale status
tailscale status

# Trên server - kiểm tra Tailscale đang chạy
sudo systemctl status tailscaled
sudo tailscale up   # Nếu bị disconnect
```

### ❌ Hết dung lượng disk

```bash
# Kiểm tra disk
df -h

# Dọn Docker images/containers cũ
docker system prune -a --volumes
# ⚠️ Lệnh trên xóa TẤT CẢ images không sử dụng
```

---

## 📌 Tóm tắt lệnh hay dùng

| Tác vụ | Lệnh |
|--------|-------|
| Push code (Mac) | `git add -A && git commit -m "msg" && git push` |
| SSH vào server | `ssh user@<tailscale-ip>` |
| Pull code (Server) | `cd ~/knowledge-search && git pull` |
| Deploy | `docker compose down && docker compose up -d --build` |
| Xem logs | `docker compose logs -f` |
| Xem trạng thái | `docker compose ps` |
| Restart 1 service | `docker compose restart <service>` |
| Dọn Docker | `docker system prune -a` |

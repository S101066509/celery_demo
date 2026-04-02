# Celery 技能展示 Demo

本專案是用於展示 Celery 實作能力的 Demo。透過多資訊來源以展示非同步任務、排程、錯誤追蹤、快取整合等能力。

---

## 快速開始（Docker 部署）

本專案已使用 Docker 打包，使用前請先依 backend/.env.example 建立 backend/.env，再執行 docker-compose up --build 啟動專案。

### 1. 準備環境檔
請先完成 `.env` 設定（可參考 `.env.example`）：
```bash
cd backend
cp .env.example .env
```

### 2. 一鍵啟動（Docker Compose）
在 `backend` 目錄下執行：
```bash
docker-compose up --build
```
啟動完成後，請前往：[http://localhost:8080](http://localhost:8080)

---

## 使用技術

*   後端：Django 5.2（SSR / DRF API）
*   非同步任務：Celery + Redis（訊息代理）
*   資料庫：PostgreSQL 15
*   基礎架構：Nginx（反向代理）、Docker & Docker Compose
*   排程：django-celery-beat（DB 動態排程）
*   前端：Vanilla JS + Phosphor Icons + Bootstrap 5（玻璃擬態風格）

---

## 展示重點（技能面）

*   任務排程：使用 django-celery-beat 管理 DB 動態排程。
*   非同步任務：透過 Celery Worker 執行耗時資料抓取。
*   分散式鎖：用 Redis Cache 防止相同任務重複並發。
*   系統健康檢查：Dashboard 會檢查 DB / Redis / Celery 狀態。
*   錯誤追蹤：任務失敗會集中寫入 ErrorLog，支援 UI 檢視。
*   快取整合：股票搜尋與目錄同步皆透過 Redis 快取加速。
*   前端展示：以簡單 UI 呈現任務管理、圖表與錯誤記錄。

---

## 容器架構

啟動後會產生以下服務容器：
1.  crawler-nginx：入口網關（Port 8080），轉發請求並處理靜態檔案。
2.  crawler-django：核心業務邏輯，執行 Gunicorn WSGI 伺服器。
3.  crawler-postgres：資料庫容器，具備資料持久化掛載。
4.  crawler-redis：快取與 Celery 訊息交換中心。
5.  crawler-worker：負責實際執行股價資料抓取的非同步進程。
6.  crawler-beat：以 DB 為基礎的排程器，負責定時派發任務。

---

## 開發常用指令

### 初始化股票清單
如果你發現搜尋不到股票，請進入容器手動執行強制初始化：
```bash
docker exec -it crawler-django python force_seed.py
```

### 手動啟動（非 Docker 環境）
若不使用 Docker 啟動服務，請自行建立並啟動 PostgreSQL 與 Redis，再於本機直接執行：
```bash
# 啟動 Django 伺服器
python manage.py runserver 8000

# 啟動 Celery Worker
celery -A config worker -l info --pool=solo

# 啟動 Celery Beat
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## 授權說明
本專案僅供開發展示與學習參考使用。資料對接請遵守各交易所 API 的使用條款。

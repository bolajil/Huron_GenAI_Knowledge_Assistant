# P0 Critical Fixes - Setup Guide

## Quick Start (5 Minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements-p0-fixes.txt
```

### Step 2: Install & Start Redis

**Option A: Windows (Chocolatey)**
```bash
choco install redis-64
redis-server
```

**Option B: Windows (WSL2)**
```bash
wsl --install
wsl
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
```

**Option C: Docker**
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

### Step 3: Verify Redis
```bash
redis-cli ping
# Should return: PONG
```

### Step 4: Start Celery Worker
```bash
# Windows
start_celery_worker.bat

# Linux/Mac
celery -A celery_worker worker --loglevel=info
```

### Step 5: Start Streamlit App
```bash
streamlit run genai_dashboard_modular.py
```

---

## Detailed Setup Instructions

### 1. Redis Installation

#### Windows - Method 1: Chocolatey (Recommended)
```powershell
# Install Chocolatey if not installed
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Redis
choco install redis-64 -y

# Start Redis
redis-server
```

#### Windows - Method 2: Manual Download
1. Download from: https://github.com/microsoftarchive/redis/releases
2. Download `Redis-x64-3.0.504.msi`
3. Install and run `redis-server.exe`

#### Windows - Method 3: WSL2
```bash
# Install WSL2
wsl --install

# Inside WSL
sudo apt-get update
sudo apt-get install redis-server -y

# Start Redis
sudo service redis-server start

# Verify
redis-cli ping
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install redis-server -y
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### macOS
```bash
brew install redis
brew services start redis
```

### 2. Python Dependencies

```bash
# Install P0 fixes requirements
pip install -r requirements-p0-fixes.txt

# Verify installation
python -c "import celery, redis; print('✅ Dependencies installed')"
```

### 3. Environment Variables (Optional)

Create `.env` file in project root:
```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Validation Settings
ENABLE_VALIDATION=true
ENABLE_DUPLICATE_CHECK=true

# Async Processing
USE_ASYNC_INGESTION=true
```

### 4. Directory Structure

Ensure these directories exist:
```
project_root/
├── logs/                    # Celery worker logs
├── data/
│   ├── faiss_index/        # FAISS indexes
│   └── backups/            # Document backups (future)
├── utils/
│   ├── ingestion_validator.py
│   └── ingestion_queue.py
├── celery_worker.py
└── start_celery_worker.bat
```

Create logs directory:
```bash
mkdir logs
```

---

## Testing the Setup

### Test 1: Redis Connection
```bash
python -c "from redis import Redis; r = Redis(); r.ping(); print('✅ Redis OK')"
```

### Test 2: Celery Worker
```bash
# Terminal 1: Start worker
celery -A celery_worker worker --loglevel=info --pool=solo

# Terminal 2: Test task
python -c "from utils.ingestion_queue import health_check; result = health_check.delay(); print(result.get())"
```

### Test 3: Validation
```bash
python -c "from utils.ingestion_validator import get_ingestion_validator; v = get_ingestion_validator(); print('✅ Validator OK')"
```

### Test 4: Full Integration
1. Start Redis: `redis-server`
2. Start Celery: `start_celery_worker.bat`
3. Start Streamlit: `streamlit run genai_dashboard_modular.py`
4. Upload a test document
5. Verify async processing works

---

## Troubleshooting

### Issue: Redis Connection Failed

**Error**: `redis.exceptions.ConnectionError: Error connecting to Redis`

**Solutions**:
1. Check if Redis is running: `redis-cli ping`
2. Check Redis port: `netstat -an | findstr 6379`
3. Restart Redis: `redis-server`
4. Check firewall settings

### Issue: Celery Worker Won't Start

**Error**: `ImportError: No module named celery`

**Solutions**:
1. Install dependencies: `pip install -r requirements-p0-fixes.txt`
2. Check Python path: `python -c "import sys; print(sys.path)"`
3. Use virtual environment

### Issue: "pool=solo" Error on Linux

**Error**: `celery.exceptions.ImproperlyConfigured: solo pool requires Windows`

**Solution**:
Use different pool on Linux/Mac:
```bash
celery -A celery_worker worker --loglevel=info --concurrency=4
```

### Issue: Validation Fails for Valid Files

**Error**: `Validation failed: Unsupported file extension`

**Solutions**:
1. Check file extension is in allowed list
2. Verify file is not corrupted
3. Check file size limits
4. Review validation logs

### Issue: Task Stuck in PENDING

**Error**: Task never starts processing

**Solutions**:
1. Check Celery worker is running
2. Verify Redis connection
3. Check worker logs: `logs/celery_worker.log`
4. Restart Celery worker

---

## Performance Tuning

### Redis Configuration

Edit `redis.conf`:
```conf
# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Performance
tcp-backlog 511
timeout 0
tcp-keepalive 300
```

### Celery Worker Configuration

For high-throughput:
```bash
celery -A celery_worker worker \
    --loglevel=info \
    --concurrency=8 \
    --max-tasks-per-child=100 \
    --time-limit=3600 \
    --soft-time-limit=3300
```

### Monitoring

View Celery events:
```bash
celery -A celery_worker events
```

View Flower dashboard:
```bash
pip install flower
celery -A celery_worker flower
# Open http://localhost:5555
```

---

## Production Deployment

### 1. Use Supervisor (Linux)

Create `/etc/supervisor/conf.d/celery.conf`:
```ini
[program:celery]
command=celery -A celery_worker worker --loglevel=info
directory=/path/to/project
user=www-data
numprocs=1
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
```

### 2. Use systemd (Linux)

Create `/etc/systemd/system/celery.service`:
```ini
[Unit]
Description=Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/celery -A celery_worker worker --loglevel=info --detach
ExecStop=/path/to/venv/bin/celery -A celery_worker control shutdown
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Use Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  celery:
    build: .
    command: celery -A celery_worker worker --loglevel=info
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - .:/app

volumes:
  redis_data:
```

---

## Next Steps

After successful setup:

1. ✅ Test with small documents first
2. ✅ Monitor Celery worker logs
3. ✅ Check Redis memory usage
4. ✅ Implement Phase 2 fixes (Streaming Batch Ingestion)
5. ✅ Add observability dashboard
6. ✅ Set up monitoring alerts

---

## Support

For issues:
1. Check logs: `logs/celery_worker.log`
2. Review Redis logs
3. Test individual components
4. Refer to INGESTION_TAB_REVIEW.md for detailed recommendations

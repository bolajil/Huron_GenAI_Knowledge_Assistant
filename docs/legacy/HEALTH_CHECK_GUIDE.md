# System Health Check Guide

## Understanding Health Status

### ✅ HEALTHY
Component is fully operational and working as expected.

### ⚠️ DEGRADED
Component has issues but system can still function. Often means optional services are not running.

### ❌ UNHEALTHY
Critical component failure that may impact core functionality.

---

## Component Status Explained

### Weaviate (Vector Database)
- **HEALTHY**: Connected to Weaviate, collections accessible
- **UNHEALTHY**: Cannot connect to Weaviate instance
- **Fix**: Check `WEAVIATE_URL` and `WEAVIATE_API_KEY` in `.env`

### FAISS (Local Vector Store)
- **HEALTHY**: FAISS indexes found and accessible
- **DEGRADED**: No FAISS indexes found (using Weaviate instead)
- **UNHEALTHY**: FAISS directory missing or corrupted
- **Fix**: Indexes are in `data/faiss_index/` directory

### Redis (Cache & Queue)
- **HEALTHY**: Redis server running and accessible
- **DEGRADED**: Redis not available (OPTIONAL - system works without it)
- **Fix**: Install and start Redis:
  ```bash
  # Windows: Download from https://github.com/microsoftarchive/redis/releases
  # Linux: sudo apt-get install redis-server
  # Mac: brew install redis
  redis-server
  ```

### Celery (Background Tasks)
- **HEALTHY**: Celery workers are running
- **DEGRADED**: No workers running (OPTIONAL - for async tasks only)
- **Fix**: Start Celery worker:
  ```bash
  python celery_worker.py
  ```

### Disk Space
- **HEALTHY**: >20% free space
- **DEGRADED**: 10-20% free space (warning)
- **UNHEALTHY**: <10% free space (critical)
- **Fix**: Free up disk space

### Memory
- **HEALTHY**: >20% available memory
- **DEGRADED**: 10-20% available (warning)
- **UNHEALTHY**: <10% available (critical)
- **Fix**: Close unused applications or add more RAM

---

## Current System Status

Based on your screenshot:

### ❌ Issues Found:
1. **Weaviate**: Connection error - needs configuration
2. **Redis**: Not running (optional, but recommended)

### ⚠️ Warnings:
1. **Celery**: No workers (optional, only needed for background tasks)
2. **Memory**: Low available memory

### ✅ Working:
1. **FAISS**: Indexes available
2. **Disk Space**: Adequate space

---

## Quick Fixes

### Priority 1: Fix Weaviate (if using cloud)
```bash
# Edit .env file
WEAVIATE_URL=https://your-cluster.weaviate.cloud
WEAVIATE_API_KEY=your-api-key
```

### Priority 2: Install Redis (optional but recommended)
```bash
# Windows
# Download from: https://github.com/microsoftarchive/redis/releases
# Extract and run: redis-server.exe

# Linux
sudo apt-get install redis-server
sudo systemctl start redis

# Mac
brew install redis
brew services start redis
```

### Priority 3: Start Celery Worker (optional)
```bash
# Only if you need background document processing
python celery_worker.py
```

---

## When to Worry

### ❌ Critical (Fix Immediately):
- Weaviate UNHEALTHY (if you're using Weaviate)
- Disk Space < 10%
- Memory < 10%

### ⚠️ Warning (Fix When Convenient):
- Redis DEGRADED (limits caching and background tasks)
- Celery DEGRADED (limits async document processing)
- Disk Space 10-20%
- Memory 10-20%

### ✅ OK (No Action Needed):
- FAISS DEGRADED (if using Weaviate instead)
- Redis DEGRADED (if not using background tasks)
- Celery DEGRADED (if not using async processing)

---

## System Requirements

### Minimum (Basic Functionality):
- ✅ FAISS or Weaviate (at least one)
- ✅ 4GB RAM
- ✅ 10GB free disk space

### Recommended (Full Features):
- ✅ Weaviate (cloud or local)
- ✅ Redis (for caching)
- ✅ Celery workers (for background tasks)
- ✅ 8GB RAM
- ✅ 20GB free disk space

### Optimal (Production):
- ✅ Weaviate cloud cluster
- ✅ Redis cluster
- ✅ Multiple Celery workers
- ✅ 16GB+ RAM
- ✅ 50GB+ free disk space
- ✅ Monitoring and alerting enabled

---

## Troubleshooting

### "System is unhealthy" message
1. Check which components are unhealthy
2. Focus on critical components (Weaviate if using it)
3. Optional components (Redis, Celery) can be degraded without issues

### Weaviate connection errors
```bash
# Test connection
curl https://your-cluster.weaviate.cloud/v1/meta

# Check environment variables
echo $WEAVIATE_URL
echo $WEAVIATE_API_KEY
```

### Redis connection errors
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running, start it
redis-server
```

### Memory warnings
```bash
# Check memory usage
# Windows: Task Manager
# Linux/Mac: top or htop
```

---

## Getting Help

If issues persist:
1. Check logs: `logs/automation.log`
2. Review `IMPLEMENTATION_COMPLETE.md`
3. Contact: bolafiz2001@gmail.com

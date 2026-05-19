# Quick Start: VaultMind Automation Setup

## 🚀 Get Started in 30 Minutes

This guide helps you implement the most critical automation features immediately.

---

## Step 1: Enable CI/CD (5 minutes)

### GitHub Actions Setup

1. **Push to GitHub** (if not already done):
```bash
git add .github/workflows/ci.yml
git commit -m "Add CI/CD pipeline"
git push origin main
```

2. **Configure Secrets** in GitHub:
   - Go to: Settings → Secrets and variables → Actions
   - Add secrets:
     - `DOCKER_USERNAME`
     - `DOCKER_PASSWORD`
     - `CODECOV_TOKEN` (optional)

3. **Verify**: Check Actions tab in GitHub - CI should run automatically

---

## Step 2: Add Monitoring (10 minutes)

### Install Dependencies
```bash
pip install prometheus-client grafana-api
```

### Start Metrics Collection

Add to your `genai_dashboard_modular.py`:
```python
from utils.monitoring.metrics import metrics

# At startup
metrics.start_metrics_server(port=8000)
metrics.set_system_info(version="1.0.0", environment="production")

# In your code
metrics.record_query('semantic_search', 'success')
metrics.record_query_duration(1.5, 'semantic_search')
```

### View Metrics
```bash
# Access metrics endpoint
curl http://localhost:8000/metrics
```

---

## Step 3: Setup Automated Backups (10 minutes)

### Install Dependencies
```bash
pip install schedule boto3
```

### Create Backup Script

**File: `run_backups.py`**
```python
import schedule
import time
from utils.backup.backup_manager import BackupManager

config = {
    'backup_dir': 'backups',
    'use_s3': False,  # Set True for S3 backups
    's3_bucket': 'vaultmind-backups'
}

manager = BackupManager(config)

# Schedule backups
schedule.every().day.at("02:00").do(manager.backup_vector_stores)
schedule.every().hour.do(manager.backup_database)
schedule.every().week.do(lambda: manager.cleanup_old_backups(30))

print("Backup scheduler started...")
while True:
    schedule.run_pending()
    time.sleep(60)
```

### Run Backup Service
```bash
# Windows
start python run_backups.py

# Linux/Mac
nohup python run_backups.py &
```

---

## Step 4: Enable Health Monitoring (5 minutes)

### Add Health Check Endpoint

Add to `genai_dashboard_modular.py`:
```python
import streamlit as st
from utils.monitoring.metrics import metrics

# Add to sidebar
with st.sidebar:
    st.subheader("System Health")
    
    # Check vector stores
    weaviate_healthy = check_weaviate_connection()
    metrics.update_vector_store_health('weaviate', weaviate_healthy)
    
    st.metric("Weaviate", "✅ Healthy" if weaviate_healthy else "❌ Down")
    
    # Check Redis
    redis_healthy = check_redis_connection()
    st.metric("Redis", "✅ Healthy" if redis_healthy else "❌ Down")
    
    # Active users
    metrics.update_active_users(len(st.session_state.get('users', [])))
```

---

## Step 5: Quick Wins - Immediate Improvements

### 1. Add Error Tracking
```python
from utils.monitoring.metrics import track_errors

@track_errors(component='ingestion')
def ingest_document(file):
    # Your ingestion code
    pass
```

### 2. Add Performance Tracking
```python
from utils.monitoring.metrics import track_duration

@track_duration('query', query_type='semantic')
def search_documents(query):
    # Your search code
    pass
```

### 3. Add Logging
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/vaultmind.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("System started")
```

---

## Verification Checklist

After setup, verify everything works:

- [ ] GitHub Actions runs on commits
- [ ] Metrics endpoint accessible at http://localhost:8000/metrics
- [ ] Backups created in `backups/` directory
- [ ] Health checks visible in sidebar
- [ ] Logs written to `logs/vaultmind.log`

---

## Next Steps

### Week 1: Monitoring Dashboard
1. Install Grafana: `docker run -d -p 3000:3000 grafana/grafana`
2. Add Prometheus data source
3. Import VaultMind dashboard

### Week 2: AI Agents
1. Review `AUTOMATION_ROADMAP.md`
2. Implement Document Management Agent
3. Enable auto-ingestion from SharePoint/S3

### Week 3: Advanced Features
1. Setup alerting (Slack/Email)
2. Implement auto-scaling
3. Add A/B testing for queries

---

## Troubleshooting

### Metrics Server Won't Start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Use different port
metrics.start_metrics_server(port=8001)
```

### Backups Failing
```bash
# Check permissions
ls -la backups/

# Create directory
mkdir -p backups
chmod 755 backups
```

### CI/CD Not Running
1. Check `.github/workflows/ci.yml` exists
2. Verify GitHub Actions enabled in repo settings
3. Check Actions tab for error messages

---

## Cost Estimate

### Free Tier (Recommended for Start)
- GitHub Actions: 2,000 minutes/month (free)
- Prometheus: Self-hosted (free)
- Grafana: Self-hosted (free)
- **Total: $0/month**

### Production Tier
- GitHub Actions: $0.008/minute (after free tier)
- Grafana Cloud: $49/month
- S3 Backups: ~$5/month (100GB)
- **Total: ~$60-100/month**

---

## Support

Need help? Check:
- `AUTOMATION_ROADMAP.md` - Full implementation plan
- `TESTING_GUIDE.md` - Testing documentation
- `PRODUCTION_DEPLOYMENT_GUIDE.md` - Production setup

Questions? Contact: bolafiz2001@gmail.com

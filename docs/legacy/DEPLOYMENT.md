# VaultMind Deployment Guide

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Python 3.9-3.11
- pip or conda
- OpenAI API key (or other LLM provider)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/vaultmind-genai-assistant
cd vaultmind-genai-assistant

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements-complete.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your API keys

# 5. Launch
streamlit run genai_dashboard_modular.py
```

### First-Time Setup

1. **Access the app:** http://localhost:8501
2. **Login:** Default credentials in `.env` or create new user
3. **Ingest a document:**
   - Go to "📄 Ingest Document" tab
   - Upload a PDF
   - Wait for processing
4. **Test query:**
   - Go to "🔍 Query Assistant" tab
   - Ask a question about your document

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional: Vector Database
WEAVIATE_URL=https://your-instance.weaviate.cloud
WEAVIATE_API_KEY=your-weaviate-key

# Optional: Alternative LLMs
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
MISTRAL_API_KEY=...

# Optional: Settings
LLM_PROVIDER=openai  # openai, anthropic, groq, mistral, ollama
VECTOR_BACKEND=faiss  # faiss, weaviate
COMPLEXITY_THRESHOLD=50.0  # For hybrid routing
```

### Configuration Files

**`config/weaviate.env`** - Weaviate-specific settings
```bash
WEAVIATE_URL=https://...
WEAVIATE_API_KEY=...
WEAVIATE_FORCE_API_VERSION=v1
```

**`config/storage.env`** - Storage backend settings
```bash
FAISS_INDEX_ROOT=data/faiss_index
TEXT_INDEX_ROOT=data/indexes
```

---

## 🏢 Deployment Options

### Option 1: Local Development

**Best for:** Testing, development, small teams

```bash
# Run locally
streamlit run genai_dashboard_modular.py

# Access at http://localhost:8501
```

**Pros:**
- No cloud costs
- Full control
- Fast iteration

**Cons:**
- Single user
- No persistence across restarts
- Manual scaling

---

### Option 2: Streamlit Community Cloud

**Best for:** Demos, small teams, public showcases

#### Setup Steps

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/vaultmind
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud:**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Select your repository
   - Main file: `genai_dashboard_modular.py`
   - Python version: 3.11

3. **Add Secrets:**
   - In Streamlit Cloud dashboard → Settings → Secrets
   - Add your `.env` variables:
   ```toml
   OPENAI_API_KEY = "sk-..."
   WEAVIATE_URL = "https://..."
   WEAVIATE_API_KEY = "..."
   ```

4. **Deploy!**

**Pros:**
- Free tier available
- Auto-scaling
- HTTPS included
- Easy updates (git push)

**Cons:**
- Public by default
- Resource limits on free tier
- Cold starts

---

### Option 3: Docker Deployment

**Best for:** Production, on-premise, custom infrastructure

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-complete.txt .
RUN pip install --no-cache-dir -r requirements-complete.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run
CMD ["streamlit", "run", "genai_dashboard_modular.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  vaultmind:
    build: .
    ports:
      - "8501:8501"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - WEAVIATE_URL=${WEAVIATE_URL}
      - WEAVIATE_API_KEY=${WEAVIATE_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

#### Deploy

```bash
# Build
docker-compose build

# Run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

**Pros:**
- Consistent environment
- Easy scaling
- Portable
- Production-ready

**Cons:**
- Requires Docker knowledge
- More complex setup

---

### Option 4: Cloud Platforms (AWS, Azure, GCP)

**Best for:** Enterprise, high-scale, compliance requirements

#### AWS (ECS/Fargate)

```bash
# 1. Build and push to ECR
aws ecr create-repository --repository-name vaultmind
docker build -t vaultmind .
docker tag vaultmind:latest <account-id>.dkr.ecr.<region>.amazonaws.com/vaultmind:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/vaultmind:latest

# 2. Create ECS task definition
# 3. Create ECS service
# 4. Configure load balancer
```

#### Azure (Container Apps)

```bash
# 1. Create container registry
az acr create --resource-group myResourceGroup --name vaultmindacr --sku Basic

# 2. Build and push
az acr build --registry vaultmindacr --image vaultmind:latest .

# 3. Deploy to Container Apps
az containerapp create \
  --name vaultmind \
  --resource-group myResourceGroup \
  --image vaultmindacr.azurecr.io/vaultmind:latest \
  --target-port 8501 \
  --ingress external
```

#### GCP (Cloud Run)

```bash
# 1. Build and push to Artifact Registry
gcloud builds submit --tag gcr.io/PROJECT-ID/vaultmind

# 2. Deploy to Cloud Run
gcloud run deploy vaultmind \
  --image gcr.io/PROJECT-ID/vaultmind \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 🔐 Security Best Practices

### Production Checklist

- [ ] **Environment Variables:** Never commit `.env` to git
- [ ] **API Keys:** Rotate regularly, use secrets manager
- [ ] **Authentication:** Enable MFA for admin users
- [ ] **HTTPS:** Always use SSL/TLS in production
- [ ] **Rate Limiting:** Configure in `utils/security.py`
- [ ] **Logging:** Enable audit logs for compliance
- [ ] **Backups:** Regular backups of indexes and databases
- [ ] **Updates:** Keep dependencies updated

### Secrets Management

**AWS Secrets Manager:**
```python
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='vaultmind/openai-key')
os.environ['OPENAI_API_KEY'] = secret['SecretString']
```

**Azure Key Vault:**
```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

client = SecretClient(vault_url="https://myvault.vault.azure.net/", credential=DefaultAzureCredential())
secret = client.get_secret("openai-api-key")
os.environ['OPENAI_API_KEY'] = secret.value
```

---

## 📊 Monitoring & Observability

### Health Checks

```bash
# Application health
curl http://localhost:8501/_stcore/health

# Vector store health
python -c "from utils.simple_vector_manager import get_simple_vector_status; print(get_simple_vector_status())"

# Weaviate health
curl https://your-instance.weaviate.cloud/v1/.well-known/ready
```

### Logging

Configure in `logging.conf`:
```ini
[loggers]
keys=root,vaultmind

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=detailed

[logger_vaultmind]
level=INFO
handlers=consoleHandler,fileHandler
qualname=vaultmind
propagate=0

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=detailed
args=('logs/vaultmind.log', 'a')
```

### Metrics

Key metrics to track:
- Query response time (p50, p95, p99)
- Ingestion throughput (docs/min)
- Error rates
- LLM API costs
- Vector store latency
- User activity

---

## 🔄 Updates & Maintenance

### Updating VaultMind

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements-complete.txt --upgrade

# Restart application
# (Streamlit auto-reloads in development)
```

### Database Migrations

```bash
# Backup existing data
cp -r data/faiss_index data/faiss_index.backup

# Run migration
python scripts/migrate_indexes.py

# Verify
python check_indexes.py
```

### Scaling Considerations

**Horizontal Scaling:**
- Use load balancer (nginx, AWS ALB)
- Shared vector store (Weaviate cloud)
- Stateless application design

**Vertical Scaling:**
- Increase memory for large indexes
- GPU for faster embeddings
- SSD for FAISS performance

---

## 🆘 Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
pip install -r requirements-complete.txt
```

**"OpenAI API key not found":**
```bash
# Check .env file
cat .env | grep OPENAI_API_KEY

# Or set directly
export OPENAI_API_KEY=sk-...
```

**"Weaviate connection failed":**
```bash
# Test connection
curl https://your-instance.weaviate.cloud/v1/.well-known/ready

# Check credentials
python check_config.py
```

**"No indexes found":**
```bash
# List indexes
python check_indexes.py

# Create sample index
python scripts/create_demo_index.py
```

### Debug Mode

```bash
# Run with debug logging
streamlit run genai_dashboard_modular.py --logger.level=debug

# Check logs
tail -f logs/vaultmind.log
```

---

## 📞 Support

- **Documentation:** https://github.com/yourusername/vaultmind/wiki
- **Issues:** https://github.com/yourusername/vaultmind/issues
- **Email:** support@vaultmind.ai
- **Slack:** vaultmind-community.slack.com

---

## 📝 License

[Your License Here - e.g., MIT, Apache 2.0]

---

**Ready to deploy? Run the pre-flight check:**
```bash
python scripts/deployment_preflight_check.py
```

This validates:
- ✅ All dependencies installed
- ✅ Configuration files present
- ✅ API keys valid
- ✅ Vector stores accessible
- ✅ Application starts successfully

**Happy deploying! 🚀**

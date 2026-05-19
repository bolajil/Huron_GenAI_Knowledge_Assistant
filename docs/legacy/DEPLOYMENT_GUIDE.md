# VaultMind Enterprise Deployment Guide

## 🚀 Production Deployment

### Prerequisites
- Python 3.8+
- PostgreSQL or SQLite database
- Redis (optional, for session caching)
- SSL certificates for HTTPS
- Domain name and DNS configuration

### 1. Server Setup

#### Recommended Specifications
```
Minimum:
- 4 CPU cores
- 8GB RAM
- 100GB SSD storage
- 100 Mbps network

Production:
- 8+ CPU cores
- 16GB+ RAM
- 500GB+ SSD storage
- 1 Gbps network
```

#### Operating System
- Ubuntu 20.04 LTS or newer
- CentOS 8+ / RHEL 8+
- Amazon Linux 2
- Windows Server 2019+

### 2. Environment Configuration

#### Create Environment File
```bash
# Create .env file
cat > .env << EOF
# Application Settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_ENABLE_CORS=false
STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true

# Security
VAULTMIND_MASTER_KEY=your-secure-256-bit-key-here
SECRET_KEY=your-django-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database
DATABASE_URL=postgresql://vaultmind:password@localhost:5432/vaultmind
REDIS_URL=redis://localhost:6379/0

# OpenAI (if using AI features)
OPENAI_API_KEY=your-openai-api-key

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@your-domain.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true

# Active Directory (if using)
AD_SERVER=your-ad-server.company.com
AD_PORT=636
AD_DOMAIN=company.com
AD_BASE_DN=DC=company,DC=com
AD_SERVICE_USER=vaultmind-service@company.com
AD_SERVICE_PASSWORD=service-account-password

# Okta SSO (if using)
OKTA_DOMAIN=your-company.okta.com
OKTA_CLIENT_ID=your-okta-client-id
OKTA_CLIENT_SECRET=your-okta-client-secret
OKTA_REDIRECT_URI=https://your-domain.com/auth/callback

# MFA Providers
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890

AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
EOF
```

### 3. Database Setup

#### PostgreSQL Installation
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo dnf install postgresql postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

#### Database Configuration
```sql
-- Connect as postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE vaultmind;
CREATE USER vaultmind WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE vaultmind TO vaultmind;
ALTER USER vaultmind CREATEDB;
\q
```

### 4. Application Deployment

#### Clone Repository
```bash
git clone https://github.com/your-org/vaultmind-genai.git
cd vaultmind-genai
```

#### Python Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-enterprise.txt

# Install additional production dependencies
pip install gunicorn psycopg2-binary redis
```

#### Initialize Database
```bash
# Run database migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 5. Web Server Configuration

#### Nginx Configuration
```nginx
# /etc/nginx/sites-available/vaultmind
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    location /static/ {
        alias /path/to/vaultmind/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### Enable Nginx Site
```bash
sudo ln -s /etc/nginx/sites-available/vaultmind /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Process Management

#### Systemd Service
```ini
# /etc/systemd/system/vaultmind.service
[Unit]
Description=VaultMind GenAI Knowledge Assistant
After=network.target

[Service]
Type=simple
User=vaultmind
Group=vaultmind
WorkingDirectory=/opt/vaultmind
Environment=PATH=/opt/vaultmind/venv/bin
EnvironmentFile=/opt/vaultmind/.env
ExecStart=/opt/vaultmind/venv/bin/streamlit run genai_dashboard_modular.py --server.port=8501 --server.address=127.0.0.1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable vaultmind
sudo systemctl start vaultmind
sudo systemctl status vaultmind
```

### 7. SSL Certificate Setup

#### Let's Encrypt (Certbot)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 8. Monitoring & Logging

#### Log Configuration
```bash
# Create log directory
sudo mkdir -p /var/log/vaultmind
sudo chown vaultmind:vaultmind /var/log/vaultmind

# Logrotate configuration
sudo tee /etc/logrotate.d/vaultmind << EOF
/var/log/vaultmind/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 vaultmind vaultmind
}
EOF
```

#### Health Check Script
```bash
#!/bin/bash
# /opt/vaultmind/health_check.sh

HEALTH_URL="https://your-domain.com/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "VaultMind is healthy"
    exit 0
else
    echo "VaultMind health check failed: $RESPONSE"
    systemctl restart vaultmind
    exit 1
fi
```

### 9. Backup Strategy

#### Database Backup
```bash
#!/bin/bash
# /opt/vaultmind/backup_db.sh

BACKUP_DIR="/opt/backups/vaultmind"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/vaultmind_$DATE.sql"

mkdir -p $BACKUP_DIR

pg_dump -h localhost -U vaultmind vaultmind > $BACKUP_FILE
gzip $BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Database backup completed: $BACKUP_FILE.gz"
```

#### Configuration Backup
```bash
#!/bin/bash
# /opt/vaultmind/backup_config.sh

BACKUP_DIR="/opt/backups/vaultmind/config"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration files
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" \
    /opt/vaultmind/.env \
    /opt/vaultmind/data/security_config.json \
    /etc/nginx/sites-available/vaultmind \
    /etc/systemd/system/vaultmind.service

echo "Configuration backup completed: config_$DATE.tar.gz"
```

### 10. Security Hardening

#### Firewall Configuration
```bash
# UFW (Ubuntu)
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Fail2ban for SSH protection
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

#### File Permissions
```bash
# Set secure permissions
sudo chown -R vaultmind:vaultmind /opt/vaultmind
sudo chmod 600 /opt/vaultmind/.env
sudo chmod 600 /opt/vaultmind/data/security_config.json
sudo chmod +x /opt/vaultmind/health_check.sh
sudo chmod +x /opt/vaultmind/backup_*.sh
```

### 11. Performance Optimization

#### Redis Configuration
```bash
# Install Redis
sudo apt install redis-server

# Configure Redis
sudo tee -a /etc/redis/redis.conf << EOF
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
EOF

sudo systemctl restart redis-server
```

#### Database Optimization
```sql
-- PostgreSQL performance tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
SELECT pg_reload_conf();
```

### 12. Monitoring Setup

#### Prometheus & Grafana (Optional)
```bash
# Install Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
sudo mv prometheus-2.40.0.linux-amd64 /opt/prometheus

# Install Grafana
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install grafana
```

### 13. Troubleshooting

#### Common Issues

**Application Won't Start**
```bash
# Check logs
sudo journalctl -u vaultmind -f

# Check configuration
sudo -u vaultmind /opt/vaultmind/venv/bin/python -c "import os; print(os.environ.get('VAULTMIND_MASTER_KEY'))"
```

**Database Connection Issues**
```bash
# Test database connection
sudo -u vaultmind psql -h localhost -U vaultmind -d vaultmind -c "SELECT 1;"
```

**SSL Certificate Problems**
```bash
# Check certificate validity
sudo certbot certificates
openssl x509 -in /path/to/certificate.crt -text -noout
```

### 14. Maintenance Tasks

#### Weekly Tasks
- Review application logs
- Check disk space usage
- Verify backup completion
- Update security patches

#### Monthly Tasks
- Review user access logs
- Update dependencies
- Performance monitoring review
- Security configuration audit

#### Quarterly Tasks
- Full security assessment
- Disaster recovery testing
- Capacity planning review
- Documentation updates

---

**Production Deployment Complete** - Your VaultMind enterprise installation is ready for production use with enterprise-grade security, monitoring, and backup systems.

# PharmaGEN - Web Deployment Guide

## 📋 Table of Contents
- [Python Version Recommendation](#python-version-recommendation)
- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
- [Configuration](#configuration)
- [Production Deployment](#production-deployment)
- [Monitoring & Maintenance](#monitoring--maintenance)

## 🐍 Python Version Recommendation

**Recommended: Python 3.11.x**

### Why Python 3.11?
- **Performance**: 10-60% faster than Python 3.10
- **Better error messages**: Improved debugging experience
- **Stability**: Production-ready and well-tested
- **Compatibility**: Full support for all dependencies (Gradio, Google Generative AI, FPDF)
- **Long-term support**: Security updates until October 2027

### Alternative Versions
- **Minimum**: Python 3.9
- **Also supported**: Python 3.10, 3.12
- **Not recommended**: Python 3.8 (end of life October 2024)

### Check Your Python Version
```bash
python --version
# or
python3 --version
```

### Install Python 3.11
**Windows:**
```powershell
# Download from python.org
# Or use winget
winget install Python.Python.3.11
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

**macOS:**
```bash
brew install python@3.11
```

---

## 🚀 Quick Start

### 1. Clone and Setup
```bash
cd PharmaGEN
python3.11 -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your-api-key-here
```

### 3. Run the Application

**Development Mode:**
```bash
python app_production.py
```

**Original Version (without production features):**
```bash
python app.py
```

Access at: `http://localhost:7860`

---

## 🌐 Deployment Options

### Option 1: Docker Deployment (Recommended for Production)

**Prerequisites:**
- Docker 20.10+
- Docker Compose 2.0+

**Steps:**

1. **Build and Run with Docker Compose:**
```bash
# Set your API key in .env file first
docker-compose up -d
```

2. **Check Status:**
```bash
docker-compose ps
docker-compose logs -f pharmagen
```

3. **Stop Services:**
```bash
docker-compose down
```

**Advantages:**
- Isolated environment
- Easy scaling
- Consistent deployment
- Built-in Redis for caching

---

### Option 2: Cloud Platform Deployment

#### A. Hugging Face Spaces (Easiest)

1. Create account at [huggingface.co](https://huggingface.co)
2. Create new Space with Gradio SDK
3. Upload files:
   - `app_production.py` (rename to `app.py`)
   - `requirements.txt`
   - `config.py`
4. Add Secret: `GEMINI_API_KEY`
5. Space will auto-deploy

**Pros:** Free tier, automatic HTTPS, easy setup
**Cons:** Limited resources on free tier

---

#### B. Google Cloud Run

1. **Install Google Cloud SDK:**
```bash
gcloud init
```

2. **Build and Deploy:**
```bash
# Set project
gcloud config set project YOUR_PROJECT_ID

# Build container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/pharmagen

# Deploy
gcloud run deploy pharmagen \
  --image gcr.io/YOUR_PROJECT_ID/pharmagen \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your-key-here
```

**Pros:** Auto-scaling, pay-per-use, managed infrastructure
**Cons:** Requires Google Cloud account, costs after free tier

---

#### C. AWS (Amazon Web Services)

**Using AWS Elastic Beanstalk:**

1. **Install EB CLI:**
```bash
pip install awsebcli
```

2. **Initialize and Deploy:**
```bash
eb init -p python-3.11 pharmagen
eb create pharmagen-env
eb setenv GEMINI_API_KEY=your-key-here
eb open
```

**Using AWS ECS (Docker):**
```bash
# Push to ECR
aws ecr create-repository --repository-name pharmagen
docker build -t pharmagen .
docker tag pharmagen:latest YOUR_ACCOUNT.dkr.ecr.REGION.amazonaws.com/pharmagen:latest
docker push YOUR_ACCOUNT.dkr.ecr.REGION.amazonaws.com/pharmagen:latest

# Deploy to ECS (use AWS Console or CLI)
```

---

#### D. Heroku

1. **Install Heroku CLI:**
```bash
# Download from heroku.com/cli
```

2. **Create Procfile:**
```bash
echo "web: python app_production.py" > Procfile
```

3. **Deploy:**
```bash
heroku login
heroku create pharmagen-app
heroku config:set GEMINI_API_KEY=your-key-here
git push heroku main
heroku open
```

---

#### E. DigitalOcean App Platform

1. Connect GitHub repository
2. Select Python as runtime
3. Set build command: `pip install -r requirements.txt`
4. Set run command: `python app_production.py`
5. Add environment variable: `GEMINI_API_KEY`
6. Deploy

---

#### F. Railway.app

1. Connect GitHub repository
2. Add environment variable: `GEMINI_API_KEY`
3. Railway auto-detects Python and deploys
4. Get public URL

**Pros:** Simple, generous free tier
**Cons:** Limited customization

---

### Option 3: VPS Deployment (Full Control)

**For: DigitalOcean, Linode, AWS EC2, Azure VM, etc.**

1. **Setup Server (Ubuntu 22.04 example):**
```bash
# SSH into server
ssh user@your-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev nginx -y

# Install Redis (optional but recommended)
sudo apt install redis-server -y
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

2. **Deploy Application:**
```bash
# Clone repository
git clone https://github.com/yourusername/PharmaGEN.git
cd PharmaGEN

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your API key
```

3. **Setup Systemd Service:**
```bash
sudo nano /etc/systemd/system/pharmagen.service
```

Add:
```ini
[Unit]
Description=PharmaGEN Medical Assistant
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/PharmaGEN
Environment="PATH=/path/to/PharmaGEN/venv/bin"
ExecStart=/path/to/PharmaGEN/venv/bin/python app_production.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

4. **Start Service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable pharmagen
sudo systemctl start pharmagen
sudo systemctl status pharmagen
```

5. **Setup Nginx Reverse Proxy:**
```bash
sudo nano /etc/nginx/sites-available/pharmagen
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for Gradio
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

6. **Enable Site and SSL:**
```bash
sudo ln -s /etc/nginx/sites-available/pharmagen /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Install Certbot for SSL
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with these settings:

```bash
# Required
GEMINI_API_KEY=your-gemini-api-key-here

# Optional - API Configuration
GEMINI_MODEL_NAME=gemini-1.5-flash-latest

# Optional - Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100

# Optional - Redis (for production)
REDIS_ENABLED=False
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional - Server
SERVER_HOST=0.0.0.0
SERVER_PORT=7860
DEBUG_MODE=False

# Optional - Security
MAX_MESSAGE_LENGTH=2000
ALLOWED_ORIGINS=*

# Optional - Logging
LOG_LEVEL=INFO
LOG_FILE=pharmagen.log
```

### Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key and add to `.env` file

---

## 🔒 Production Best Practices

### 1. Security

```bash
# Use environment variables, never hardcode API keys
# Enable HTTPS (use Nginx with Let's Encrypt)
# Set proper CORS origins
ALLOWED_ORIGINS=https://yourdomain.com

# Limit message length
MAX_MESSAGE_LENGTH=2000

# Use strong rate limiting
RATE_LIMIT_PER_MINUTE=5
RATE_LIMIT_PER_HOUR=50
```

### 2. Performance

```bash
# Enable Redis for caching
REDIS_ENABLED=True
CACHE_ENABLED=True
CACHE_TTL=3600

# Use production-grade model
GEMINI_MODEL_NAME=gemini-1.5-flash-latest
```

### 3. Monitoring

```bash
# Enable detailed logging
LOG_LEVEL=INFO

# Monitor logs
tail -f pharmagen.log

# Docker logs
docker-compose logs -f pharmagen
```

### 4. Backup

```bash
# Backup reports directory
tar -czf reports-backup-$(date +%Y%m%d).tar.gz reports/

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

---

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# Check if app is running
curl http://localhost:7860

# Check Redis (if enabled)
redis-cli ping

# Check Docker containers
docker-compose ps
```

### View Logs

```bash
# Application logs
tail -f pharmagen.log

# Docker logs
docker-compose logs -f

# System service logs
sudo journalctl -u pharmagen -f
```

### Update Application

```bash
# Pull latest changes
git pull origin main

# Restart service
sudo systemctl restart pharmagen

# Or with Docker
docker-compose down
docker-compose up -d --build
```

---

## 🐛 Troubleshooting

### Issue: API Key Error
```bash
# Check if API key is set
echo $GEMINI_API_KEY

# Verify in .env file
cat .env | grep GEMINI_API_KEY
```

### Issue: Port Already in Use
```bash
# Find process using port 7860
# Windows
netstat -ano | findstr :7860

# Linux/Mac
lsof -i :7860

# Change port in .env
SERVER_PORT=8080
```

### Issue: Redis Connection Failed
```bash
# Check Redis status
redis-cli ping

# Disable Redis if not needed
REDIS_ENABLED=False
```

### Issue: Out of Memory
```bash
# Increase Docker memory limit
# Edit docker-compose.yml, add under pharmagen service:
    deploy:
      resources:
        limits:
          memory: 2G
```

---

## 📈 Scaling

### Horizontal Scaling (Multiple Instances)

1. **Use Load Balancer** (Nginx, HAProxy, AWS ALB)
2. **Enable Redis** for shared caching
3. **Use external database** for session storage

### Vertical Scaling (More Resources)

```yaml
# docker-compose.yml
services:
  pharmagen:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## 💰 Cost Estimation

### Free Tier Options:
- **Hugging Face Spaces**: Free (limited resources)
- **Railway.app**: $5 credit/month free
- **Google Cloud Run**: 2M requests/month free
- **Heroku**: Free tier discontinued (paid plans start at $7/month)

### Paid Options:
- **DigitalOcean Droplet**: $6-12/month
- **AWS EC2 t3.small**: ~$15/month
- **Google Cloud Run**: Pay per use (~$5-20/month for moderate traffic)

### API Costs:
- **Gemini API**: Check [Google AI pricing](https://ai.google.dev/pricing)
- Free tier available with limits

---

## 📞 Support

For issues or questions:
1. Check logs: `tail -f pharmagen.log`
2. Review [GitHub Issues](https://github.com/yourusername/PharmaGEN/issues)
3. Consult deployment platform documentation

---

## ✅ Deployment Checklist

- [ ] Python 3.11 installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with API key
- [ ] Application runs locally
- [ ] Deployment platform selected
- [ ] Environment variables set on platform
- [ ] Application deployed and accessible
- [ ] HTTPS/SSL configured (for production)
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Monitoring setup
- [ ] Backup strategy in place

---

**Good luck with your deployment! 🚀**

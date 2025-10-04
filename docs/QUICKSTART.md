# PharmaGEN - Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Step 1: Check Python Version (REQUIRED)

**Recommended: Python 3.11.x**

```bash
python --version
```

If you don't have Python 3.11, download it from:
- **Windows**: https://www.python.org/downloads/
- **Mac**: `brew install python@3.11`
- **Linux**: `sudo apt install python3.11`

---

### Step 2: Install Dependencies

```bash
# Navigate to project directory
cd PharmaGEN

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

---

### Step 3: Get Gemini API Key

1. Go to: https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key

---

### Step 4: Configure Environment

```bash
# Copy example file
cp .env.example .env

# Windows:
copy .env.example .env
```

Edit `.env` file and add your API key:
```bash
GEMINI_API_KEY=your-api-key-here
```

---

### Step 5: Run the Application

**Option A: Production Version (Recommended)**
```bash
python app_production.py
```

**Option B: Original Version**
```bash
python app.py
```

**Option C: Using Docker**
```bash
docker-compose up
```

---

### Step 6: Access the Application

Open your browser and go to:
```
http://localhost:7860
```

---

## 🎯 First Time Usage

1. **Select Language**: Type your preferred language (e.g., "English", "Hindi", "Spanish")
2. **Describe Symptoms**: Enter your symptoms when prompted
3. **Mention Allergies**: Provide any allergies or type "None"
4. **View Results**: Get AI-generated diagnosis and drug concept
5. **Ask Questions**: Continue conversation for more details
6. **Download Report**: Click "Download PDF Report" button

---

## 🐛 Troubleshooting

### Issue: "Module not found"
```bash
# Make sure virtual environment is activated
# Then reinstall:
pip install -r requirements.txt
```

### Issue: "API Key Error"
```bash
# Check your .env file has the correct key
cat .env | grep GEMINI_API_KEY

# Make sure no extra spaces or quotes
```

### Issue: "Port 7860 already in use"
```bash
# Change port in .env file:
SERVER_PORT=8080

# Or kill the process using the port
# Windows:
netstat -ano | findstr :7860
taskkill /PID <PID> /F

# Mac/Linux:
lsof -i :7860
kill -9 <PID>
```

### Issue: "Redis connection failed"
```bash
# Disable Redis in .env:
REDIS_ENABLED=False
```

---

## 📦 What's Included

### Files Overview

| File | Purpose |
|------|---------|
| `app.py` | Original application |
| `app_production.py` | Enhanced production version |
| `config.py` | Configuration management |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment template |
| `Dockerfile` | Container configuration |
| `docker-compose.yml` | Multi-container setup |
| `DEPLOYMENT.md` | Full deployment guide |
| `IMPROVEMENTS.md` | What's new and improved |

---

## 🔄 Switching Between Versions

### Original Version (app.py)
- Simple setup
- No extra dependencies
- Good for testing

```bash
python app.py
```

### Production Version (app_production.py)
- Rate limiting
- Caching
- Better error handling
- Logging
- Production-ready

```bash
python app_production.py
```

---

## 🌐 Deploy to Cloud (Easy Options)

### Hugging Face Spaces (Easiest - Free)
1. Create account at huggingface.co
2. Create new Space (Gradio)
3. Upload files
4. Add secret: `GEMINI_API_KEY`
5. Done! Auto-deployed

### Railway.app (Very Easy - Free Tier)
1. Connect GitHub repo
2. Add env var: `GEMINI_API_KEY`
3. Deploy automatically

### Google Cloud Run (Scalable)
```bash
gcloud run deploy pharmagen \
  --source . \
  --set-env-vars GEMINI_API_KEY=your-key
```

See `DEPLOYMENT.md` for detailed instructions.

---

## 📊 Features

### Core Features
- ✅ 20+ language support
- ✅ AI-powered diagnosis
- ✅ Hypothetical drug generation
- ✅ PDF report generation
- ✅ Follow-up Q&A

### Production Features (app_production.py)
- ✅ Rate limiting (10 req/min)
- ✅ Translation caching
- ✅ Error handling
- ✅ Logging
- ✅ Session management
- ✅ Redis support (optional)

---

## 🔐 Security Notes

⚠️ **Important:**
- Never commit `.env` file to Git
- Keep API key secret
- Use rate limiting in production
- Enable HTTPS for public deployment

---

## 💡 Tips

1. **First run**: Use original `app.py` to test quickly
2. **Production**: Switch to `app_production.py` for deployment
3. **Development**: Keep `DEBUG_MODE=True` in `.env`
4. **Production**: Set `DEBUG_MODE=False` and enable rate limiting
5. **Caching**: Enable Redis for better performance with multiple users

---

## 📞 Need Help?

1. Check `DEPLOYMENT.md` for detailed guides
2. Check `IMPROVEMENTS.md` for what's new
3. Review logs: `tail -f pharmagen.log`
4. Open issue on GitHub

---

## ⚠️ Medical Disclaimer

This application is for **educational and conceptual purposes only**:
- AI-generated diagnoses may not be accurate
- Hypothetical drugs are NOT real medications
- Always consult qualified medical professionals
- Do not use for actual medical decisions

---

## ✅ Quick Checklist

- [ ] Python 3.11 installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Virtual environment activated
- [ ] `.env` file created with API key
- [ ] Application running (`python app_production.py`)
- [ ] Accessible at http://localhost:7860
- [ ] Tested with sample symptoms

---

**You're all set! Start using PharmaGEN! 🎉**

For detailed deployment options, see `DEPLOYMENT.md`

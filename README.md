# Luminaris TechWorks - Backend API

FastAPI backend for Luminaris TechWorks website, handling contact form submissions with Gmail SMTP integration and rate limiting.

## 🚀 Tech Stack

- **Framework:** FastAPI
- **Language:** Python 3.10+
- **ASGI Server:** Uvicorn (with uvloop)
- **Email:** Gmail SMTP (TLS)
- **Rate Limiting:** slowapi (in-memory, future: Redis)
- **Validation:** Pydantic v2
- **Deployment:** Self-hosted on LXC container (lxc-fastapi)

## 📁 Project Structure

```
ltw-backend/
├── main.py                  # FastAPI application entry point
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (NOT committed)
├── brand_identity_guidelines.md
├── business_details.md
└── README.md
```

## 🛠️ Development Setup

### Prerequisites
- Python 3.10 or higher
- Git
- Gmail account with App Password enabled

### Local Development

```bash
# Clone repository
git clone https://github.com/Swartdraak/ltw-backend.git
cd ltw-backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate          # Linux/Mac
# .\venv\Scripts\activate         # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env with your configuration (see below)

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at [http://localhost:8000](http://localhost:8000)  
Interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs)

## 🔐 Environment Variables

Create a `.env` file in the root directory:

```env
# Frontend CORS origin
FRONTEND_ORIGIN=http://localhost:3000

# Gmail SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password    # Gmail App Password (NOT account password)
CONTACT_EMAIL=contact@yourdomain.com

# Optional: Database (future)
# DB_HOST=192.168.40.118
# DB_NAME=luminaris
# DB_USER=luminaris_app
# DB_PASSWORD=your-db-password
```

### Gmail App Password Setup

1. Enable 2FA on your Gmail account
2. Go to [Google Account App Passwords](https://myaccount.google.com/apppasswords)
3. Generate an app password for "Mail"
4. Use the 16-character password (with spaces) in `SMTP_PASSWORD`

**Important:** Never use your actual Gmail password - always use App Passwords!

## 🌐 API Endpoints

### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "ok"
}
```

### Contact Form Submission
```http
POST /contact
Content-Type: application/json
```

Request Body:
```json
{
  "name": "John Doe",           // Required, 1-100 chars
  "email": "john@example.com",  // Required, valid email
  "company": "Acme Corp",       // Optional, max 200 chars
  "role": "IT Manager",         // Optional, max 100 chars
  "interest": "cybersecurity",  // Optional, max 100 chars
  "message": "Need help...",    // Optional, max 5000 chars
  "deadline": "ASAP"            // Optional, max 100 chars
}
```

Response (Success):
```json
{
  "status": "success",
  "message": "Thank you for contacting us. We'll respond within 24 hours."
}
```

Response (Error):
```json
{
  "detail": "Failed to send email. Please try again later or email us directly."
}
```

**Rate Limit:** 5 requests per minute per IP address

## 🔒 Security Features

### Rate Limiting
- **Implementation:** slowapi (in-memory)
- **Limit:** 5 requests/minute per IP on `/contact` endpoint
- **Future:** Migrate to Redis for multi-instance support

### CORS Configuration
- **Allowed Origins:** Restricted to `FRONTEND_ORIGIN` environment variable
- **Allowed Methods:** `GET`, `POST` only
- **Credentials:** Enabled

### Input Validation
- **Framework:** Pydantic Field validators
- **Email:** Uses `EmailStr` type (validates format)
- **Length Limits:** All fields have min/max constraints
- **SQL Injection:** Pydantic validation prevents injection attacks

## 📧 Email System

### SMTP Configuration
- **Provider:** Gmail SMTP (`smtp.gmail.com:587`)
- **Security:** STARTTLS encryption
- **Authentication:** Gmail App Password
- **Rate Limit:** 500 emails/day (free tier)

### Email Features
- **Plain Text + HTML:** Multi-part MIME messages
- **Reply-To:** Set to sender's email for easy replies
- **Branding:** HTML emails use Luminaris brand colors
- **Logging:** Detailed `[SMTP]` logs at each step

### Sample Email Output

```
Subject: New Contact Request from John Doe
From: admin@luminaristechworks.ai
To: admin@luminaristechworks.ai
Reply-To: john@example.com

[Styled HTML with brand colors showing all form fields]
```

## 🚢 Deployment

### Production Server (LXC)

The API is deployed on `lxc-fastapi` (192.168.40.121):

```bash
# SSH to server
ssh lxc-fastapi

# Navigate to deployment directory
cd /opt/LTW

# Pull latest changes
git pull

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Restart systemd service
sudo systemctl restart luminaris-backend.service

# Check status
sudo systemctl status luminaris-backend.service
sudo journalctl -u luminaris-backend.service -f
```

### Systemd Service Configuration

Location: `/etc/systemd/system/luminaris-backend.service`

```ini
[Unit]
Description=Luminaris TechWorks FastAPI Backend
After=network.target

[Service]
User=swartdraak
Group=swartdraak
WorkingDirectory=/opt/LTW
Environment=FRONTEND_ORIGIN=https://luminaristechworks.ai
EnvironmentFile=/opt/LTW/.env
ExecStart=/opt/LTW/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Traefik Routing

Backend is routed through Traefik reverse proxy on `lxc-traefik` (192.168.40.102):
- Domain: `api.luminaristechworks.ai`
- HTTPS certificates managed by Traefik
- Routes to `lxc-fastapi:8000`

## 🧪 Testing

### Manual API Testing

```bash
# Health check
curl https://api.luminaristechworks.ai/health

# Contact form submission
curl -X POST https://api.luminaristechworks.ai/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "message": "Test message"
  }'
```

### Test SMTP Connection

```bash
cd /opt/LTW
source venv/bin/activate
python3 -c "
from dotenv import load_dotenv
import os, smtplib
load_dotenv()
print(f'SMTP_USER: {os.getenv(\"SMTP_USER\")}')
with smtplib.SMTP('smtp.gmail.com', 587) as server:
    server.starttls()
    print('✅ TLS OK')
    server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
    print('✅ Login OK')
"
```

### Check Logs

```bash
# Watch live logs
sudo journalctl -u luminaris-backend.service -f

# Filter for contact/SMTP logs
sudo journalctl -u luminaris-backend.service -n 100 --no-pager | grep -E "\[CONTACT\]|\[SMTP\]"

# Check for errors
sudo journalctl -u luminaris-backend.service -n 50 --no-pager | grep -i error
```

## 🐛 Troubleshooting

### No Emails Sending

1. **Check environment variables loaded:**
   ```bash
   sudo systemctl cat luminaris-backend.service | grep EnvironmentFile
   cat /opt/LTW/.env | grep SMTP
   ```

2. **Verify SMTP credentials:**
   ```bash
   source venv/bin/activate
   python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('SMTP_USER'))"
   ```

3. **Test SMTP manually** (see Testing section above)

4. **Check logs for `[SMTP]` errors:**
   ```bash
   sudo journalctl -u luminaris-backend.service | grep "\[SMTP\]"
   ```

### Rate Limit Issues

Currently using in-memory rate limiting. If service restarts, rate limit counters reset.

**Future:** Migrate to Redis for persistent rate limiting:
```bash
# Install Redis on lxc-redis (192.168.40.119)
# Update main.py to use Redis backend
```

### CORS Errors

Ensure `FRONTEND_ORIGIN` matches the exact frontend URL (including protocol and no trailing slash):
```env
FRONTEND_ORIGIN=https://luminaristechworks.ai  # Correct
# NOT: http://luminaristechworks.ai           # Wrong protocol
# NOT: https://luminaristechworks.ai/         # Wrong trailing slash
```

## 📊 Monitoring

### Log Prefixes
- `[CONTACT]` - Contact form processing
- `[SMTP]` - Email sending operations
- `INFO` - Uvicorn server logs

### Key Metrics to Monitor
- Request rate to `/contact` endpoint
- SMTP success/failure rate
- Response times
- Error frequency

## 🔮 Future Enhancements

### Planned Features
- **Redis Rate Limiting:** Persistent rate limits across restarts
- **Async Email Queue:** Use Celery/RQ for non-blocking email sending
- **PostgreSQL Integration:** Store contact submissions (lxc-postgresql)
- **Marketplace API:** Product catalog endpoints (future digital products)
- **Authentication:** JWT tokens for protected endpoints
- **Webhook Support:** Integrate with CRM systems

### Database Integration (Planned)

```python
# PostgreSQL connection via asyncpg
from databases import Database

database = Database(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)
```

## 📚 Documentation

- [Brand Identity Guidelines](brand_identity_guidelines.md) - Visual design reference
- [Business Details](business_details.md) - Company information
- [FastAPI Docs](https://fastapi.tiangolo.com/) - Framework documentation

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 🤝 Related Repositories

- **Frontend:** [ltw-frontend](https://github.com/Swartdraak/ltw-frontend)

---

**Luminaris TechWorks LLC** | Cybersecurity Consulting & Automation  
API: [api.luminaristechworks.ai](https://api.luminaristechworks.ai)  
Contact: admin@luminaristechworks.ai

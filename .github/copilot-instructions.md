# Luminaris TechWorks - Backend - AI Agent Instructions

## Project Overview

**Luminaris TechWorks Backend** is a FastAPI application handling contact form submissions with Gmail SMTP integration. This is the **backend-only repository** - the frontend is in a separate repository: [ltw-frontend](https://github.com/Swartdraak/ltw-frontend).

## Backend Architecture

**Framework:** FastAPI with Python 3.10+
**ASGI Server:** Uvicorn with uvloop
**Email:** Gmail SMTP (TLS)
**Rate Limiting:** slowapi (in-memory)
**Validation:** Pydantic v2

### Key Features
- **Rate Limiting:** 5 requests/minute per IP using `slowapi` (applied to `/contact`)
- **CORS:** Restricts origin to `FRONTEND_ORIGIN` env var
- **Validation:** Pydantic models with field length limits (name ≤100, message ≤5000)
- **Email:** Uses `EmailStr` type from `pydantic[email]`
- **SMTP Logging:** Detailed `[SMTP]` and `[CONTACT]` debug logs

### API Endpoints
- `GET /health` - Health check (no rate limit)
- `POST /contact` - Contact form submission (rate limited, validated)

### Development Commands
```bash
python -m venv venv
source venv/bin/activate          # Linux/Mac
# .\venv\Scripts\activate         # Windows PowerShell
pip install -r requirements.txt
uvicorn main:app --reload         # Development server (localhost:8000)
```

## Environment Variables

**Critical:** This application requires environment variables loaded via `python-dotenv`. The `.env` file must exist in the working directory.

### Required `.env` Configuration
```bash
FRONTEND_ORIGIN=http://localhost:3000
# Gmail SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=admin@luminaristechworks.ai
SMTP_PASSWORD=xxxx xxxx xxxx xxxx    # Gmail App Password (16 chars with spaces)
CONTACT_EMAIL=admin@luminaristechworks.ai
```

### Gmail App Password Setup
1. Enable 2FA on Gmail account
2. Generate App Password at https://myaccount.google.com/apppasswords
3. Use the 16-character password (with spaces) in `SMTP_PASSWORD`
4. **Never use actual Gmail password** - always use App Passwords

### Environment Loading
The application uses `python-dotenv` to load `.env` file:

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Must be called at startup

# Access variables
smtp_user = os.getenv('SMTP_USER')
smtp_password = os.getenv('SMTP_PASSWORD')
```

## Code Patterns

### Email Sending
- Use `send_contact_email(contact_data: ContactRequest)` function
- Logs at each SMTP step with `[SMTP]` prefix
- Try/except blocks catch `SMTPException` separately from generic `Exception`
- Email includes plain text + HTML versions (MIMEMultipart)

### Error Handling
- Raise `HTTPException` for API errors
- Log errors with descriptive prefixes: `[SMTP] ❌ Error: ...`
- Return user-friendly error messages (don't expose internal details)

### Validation
- Use Pydantic `Field()` for min/max constraints
- Prefer `model_dump_json()` over deprecated `.json()` method
- EmailStr automatically validates email format

### Rate Limiting
- Apply `@limiter.limit("5/minute")` decorator to sensitive endpoints
- Current implementation is in-memory (resets on restart)
- Future: Migrate to Redis for persistence

## Deployment Architecture

### Self-Hosted Infrastructure
- **lxc-traefik** (192.168.40.102): Traefik reverse proxy handling HTTPS/routing
  - Routes: `api.luminaristechworks.ai` → backend
- **lxc-fastapi** (192.168.40.121): FastAPI backend (Python/uvicorn)
- **lxc-postgresql** (192.168.40.118): PostgreSQL database (future)
- **lxc-redis** (192.168.40.119): Redis cache (future - rate limiting, queue)

### Deployment Process

```bash
# SSH to backend server
ssh lxc-fastapi

# Navigate to deployment directory
cd /opt/LTW

# Pull latest changes
git pull

# Activate virtual environment
source venv/bin/activate

# Install dependencies (if requirements.txt changed)
pip install -r requirements.txt

# Restart systemd service
sudo systemctl restart luminaris-backend.service

# Check status
sudo systemctl status luminaris-backend.service
sudo journalctl -u luminaris-backend.service -f
```

### Systemd Service Configuration

Location: `/etc/systemd/system/luminaris-backend.service`

**Critical:** Must include `EnvironmentFile=/opt/LTW/.env` to load environment variables into the systemd process.

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

## Frontend Integration

The backend is consumed by the frontend via API calls:

```typescript
// Frontend code example
const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/contact`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(contactData)
});
```

**Frontend Repository:** https://github.com/Swartdraak/ltw-frontend

### CORS Configuration
- `FRONTEND_ORIGIN` must match frontend URL exactly
- Include protocol: `https://luminaristechworks.ai` (not `http://`)
- No trailing slash
- CORS allows: `GET`, `POST` methods only
- Credentials enabled for future cookie-based auth

## Testing & Debugging

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
sudo journalctl -u luminaris-backend.service -n 100 | grep -E "\[CONTACT\]|\[SMTP\]"

# Check POST requests
sudo journalctl -u luminaris-backend.service -n 50 | grep "POST /contact"
```

### Verify Environment Variables Loaded
```bash
# Check systemd service configuration
sudo systemctl cat luminaris-backend.service | grep EnvironmentFile

# Check .env file exists and has SMTP credentials
cat /opt/LTW/.env | grep SMTP
```

## Common Issues & Solutions

### No Emails Sending (No Logs)
**Cause:** Environment variables not loaded into Python process
**Solution:** 
1. Verify `from dotenv import load_dotenv` and `load_dotenv()` in main.py
2. Check `EnvironmentFile=/opt/LTW/.env` in systemd service
3. Restart service: `sudo systemctl restart luminaris-backend.service`

### SMTP Authentication Failed
**Cause:** Using account password instead of App Password
**Solution:** Generate Gmail App Password and use in `SMTP_PASSWORD`

### CORS Errors from Frontend
**Cause:** `FRONTEND_ORIGIN` mismatch or protocol difference
**Solution:** Ensure exact match including `https://` and no trailing slash

### Rate Limit Not Persisting
**Cause:** In-memory rate limiting resets on service restart
**Solution:** Future enhancement - migrate to Redis backend

## Future Enhancements

### Planned Features
- **Redis Rate Limiting:** Persistent rate limits across restarts
- **Async Email Queue:** Use Celery/RQ for non-blocking email sending
- **PostgreSQL Integration:** Store contact submissions
- **Marketplace API:** Product catalog endpoints
- **Authentication:** JWT tokens for protected endpoints

### Database Integration (Planned)
```python
from databases import Database

database = Database(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
)
```

## Business Context (`business_details.md`)

**Company:** Luminaris TechWorks LLC (Florida single-member LLC)
**Services:** Cybersecurity assessments, PowerShell/Python automation, M365/cloud config, network optimization, AI-driven workflows
**Target Audience:** Small businesses, freelancers, technical teams seeking secure, automated infrastructure

## Documentation References

- **README:** Project overview, setup, deployment
- **Brand Guidelines:** `brand_identity_guidelines.md` - Visual identity reference
- **Business Details:** `business_details.md` - Company info and services

## Security Considerations

- All inputs validated with Pydantic Field constraints
- Rate limiting prevents abuse (5/min - adjust if needed)
- CORS restricted to specific origin and methods
- Never log sensitive data (passwords, tokens)
- Gmail rate limit: 500 emails/day (free tier)

---

*Last updated: December 4, 2025*
*This is the backend-only repository. Frontend: [ltw-frontend](https://github.com/Swartdraak/ltw-frontend)*

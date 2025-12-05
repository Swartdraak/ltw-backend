from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Luminaris TechWorks API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://192.168.40.117:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    company: str | None = Field(None, max_length=200)
    role: str | None = Field(None, max_length=100)
    interest: str | None = Field(None, max_length=100)
    message: str | None = Field(None, max_length=5000)
    deadline: str | None = Field(None, max_length=100)


@app.get("/health")
async def health():
    return {"status": "ok"}


def send_contact_email(contact_data: ContactRequest):
    """Send contact form submission via Gmail SMTP"""
    try:
        print(f"[SMTP] Starting email send for {contact_data.name} ({contact_data.email})")
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"New Contact Request from {contact_data.name}"
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = os.getenv('CONTACT_EMAIL')
        msg['Reply-To'] = contact_data.email
        
        print(f"[SMTP] Email headers set - From: {os.getenv('SMTP_USER')}, To: {os.getenv('CONTACT_EMAIL')}")
        
        # Plain text version
        text = f"""
New contact form submission from Luminaris TechWorks website

Name: {contact_data.name}
Email: {contact_data.email}
Company: {contact_data.company or 'N/A'}
Role: {contact_data.role or 'N/A'}
Interest: {contact_data.interest or 'N/A'}
Deadline: {contact_data.deadline or 'N/A'}

Message:
{contact_data.message or 'No message provided'}

Submitted: {datetime.utcnow().isoformat()}
"""
        
        # HTML version
        html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #0A192F; color: #00D4FF; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="margin: 0;">🔔 New Contact Request</h2>
        <p style="color: #C0C0C8; margin: 5px 0 0 0;">Luminaris TechWorks Website</p>
    </div>
    <div style="background: #f4f4f4; padding: 20px; border-radius: 0 0 8px 8px;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px; font-weight: bold; width: 120px;">Name:</td>
                <td style="padding: 8px;">{contact_data.name}</td>
            </tr>
            <tr style="background: white;">
                <td style="padding: 8px; font-weight: bold;">Email:</td>
                <td style="padding: 8px;"><a href="mailto:{contact_data.email}">{contact_data.email}</a></td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Company:</td>
                <td style="padding: 8px;">{contact_data.company or 'N/A'}</td>
            </tr>
            <tr style="background: white;">
                <td style="padding: 8px; font-weight: bold;">Role:</td>
                <td style="padding: 8px;">{contact_data.role or 'N/A'}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Interest:</td>
                <td style="padding: 8px;">{contact_data.interest or 'N/A'}</td>
            </tr>
            <tr style="background: white;">
                <td style="padding: 8px; font-weight: bold;">Deadline:</td>
                <td style="padding: 8px;">{contact_data.deadline or 'N/A'}</td>
            </tr>
        </table>
        <div style="margin-top: 20px; padding: 15px; background: white; border-radius: 4px;">
            <p style="margin: 0 0 10px 0; font-weight: bold;">Message:</p>
            <p style="margin: 0; white-space: pre-wrap;">{contact_data.message or 'No message provided'}</p>
        </div>
        <p style="color: #666; font-size: 12px; margin-top: 15px;">
            Submitted: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        </p>
    </div>
</body>
</html>
"""
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        # Send email
        print(f"[SMTP] Connecting to {os.getenv('SMTP_HOST')}:{os.getenv('SMTP_PORT')}")
        with smtplib.SMTP(os.getenv('SMTP_HOST'), int(os.getenv('SMTP_PORT'))) as server:
            print("[SMTP] Connected to SMTP server")
            server.starttls()
            print("[SMTP] STARTTLS completed")
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASSWORD'))
            print(f"[SMTP] Logged in as {os.getenv('SMTP_USER')}")
            server.send_message(msg)
            print(f"[SMTP] ✅ Email sent successfully to {os.getenv('CONTACT_EMAIL')}")
    
    except smtplib.SMTPException as e:
        print(f"[SMTP] ❌ SMTP Error: {str(e)}")
        raise
    except Exception as e:
        print(f"[SMTP] ❌ Unexpected error: {str(e)}")
        raise

@app.post("/contact")
@limiter.limit("5/minute")
async def contact(request: Request, contact_request: ContactRequest):
    """Handle contact form submissions and send email notification"""
    print(f"\n{'='*60}")
    print(f"[CONTACT] Received contact form submission")
    print(f"[CONTACT] Name: {contact_request.name}")
    print(f"[CONTACT] Email: {contact_request.email}")
    print(f"{'='*60}\n")
    
    try:
        send_contact_email(contact_request)
        print(f"[CONTACT] ✅ Successfully processed contact from {contact_request.name}")
        return {
            "status": "success",
            "message": "Thank you for contacting us. We'll respond within 24 hours."
        }
    except smtplib.SMTPException as e:
        print(f"[CONTACT] ❌ SMTP Error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to send email. Please try again later or email us directly."
        )
    except Exception as e:
        print(f"[CONTACT] ❌ Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process request")

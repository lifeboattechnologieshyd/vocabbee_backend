from django.core.mail import send_mail
from django.conf import settings



import requests

# ishvaa api will be used here.
def send_otp_email(otp, email='padidalaranjith@gmail.com'):
    url = 'https://api.ishaa.eshily.com/api/v1/email/send'
    headers = {
        'X-API-Key': settings.ISHVAA_EMAIL_ID,
        'Content-Type': 'application/json'
    }
    payload = {
        "from_name": "VocabBee",
        "from": "noreply@vocabbee.com",
        "to": [
            email
        ],
        "subject": f"Your Vocabbee Verification Code: {otp}",
        "html": f"<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;background:#f5f5f5;padding:40px;'><div style='max-width:600px;margin:auto;background:#ffffff;border-radius:10px;padding:40px;box-shadow:0 2px 10px rgba(0,0,0,0.1);'><h1 style='color:#f59e0b;margin-bottom:8px;'>Vocabbee</h1><h2 style='color:#1e293b;margin-top:0;'>Verify Your Email Address</h2><p style='color:#475569;font-size:15px;line-height:1.5;'>Hello,</p><p style='color:#475569;font-size:15px;line-height:1.5;'>Thank you for joining <strong>Vocabbee</strong>! Use the verification code below to complete your registration and start expanding your vocabulary.</p><div style='margin:30px 0;text-align:center;background:#fffbeb;border:2px dashed #f59e0b;border-radius:8px;padding:20px;'><span style='font-size:32px;font-weight:bold;letter-spacing:8px;color:#d97706;'>{otp}</span></div><p style='color:#64748b;font-size:13px;line-height:1.5;'>This code is valid for <strong>10 minutes</strong>. If you did not request this code, please ignore this email.</p><hr style='margin:30px 0;border:none;border-top:1px solid #e2e8f0;'><div style='padding:15px;background:#f8fafc;border-left:4px solid #f59e0b;border-radius:4px;'><strong style='color:#334155;'>Pro Tip for New Learners:</strong><br><span style='color:#64748b;font-size:13px;'>Set up your daily 5-minute vocabulary habit right after signing in to keep your streak going!</span></div><p style='margin-top:40px;color:#475569;font-size:14px;'>Happy Learning<br><strong>Team Vocabbee</strong></p></div></body></html>"
    }
    response = requests.post(url, headers=headers, json=payload)
    print("Mail status:", response.json())
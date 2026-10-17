"""Delivery of one-time codes.

Email:  RESEND_API_KEY (+ MAIL_FROM)  or  SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS (+ MAIL_FROM)
SMS:    MSG91_AUTH_KEY + MSG91_TEMPLATE_ID (India, DLT-approved OTP template with ##OTP##)  or
        TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_FROM
OTP_DEMO=1 returns the code in the API response instead of sending it: for testing only, never in production.
"""
from __future__ import annotations

import base64
import json
import os
import smtplib
import ssl
import urllib.parse
import urllib.request
from email.message import EmailMessage

APP = "TheHealthTracker"


def email_ready() -> bool:
    return bool(os.getenv("RESEND_API_KEY") or os.getenv("SMTP_HOST"))


def sms_ready() -> bool:
    return bool((os.getenv("MSG91_AUTH_KEY") and os.getenv("MSG91_TEMPLATE_ID")) or (os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN")))


def demo() -> bool:
    return os.getenv("OTP_DEMO", "0") == "1"


def _html(code: str, purpose: str) -> str:
    what = {"signup": "finish creating your account", "reset": "reset your password", "step": "finish signing in", "verify": "verify this address"}.get(purpose, "sign in")
    return f"""<div style="font-family:Inter,Segoe UI,Arial,sans-serif;max-width:460px;margin:auto;padding:28px;color:#14151b">
<p style="font-weight:700;font-size:18px;margin:0 0 18px">the<span style="color:#2F5BFF">health</span>tracker</p>
<p style="margin:0 0 10px">Use this code to {what}:</p>
<p style="font:700 34px/1 ui-monospace,Menlo,monospace;letter-spacing:.18em;margin:0 0 16px;color:#2F5BFF">{code}</p>
<p style="color:#5f6577;font-size:13px;margin:0">It expires in 10 minutes. If you did not ask for it, ignore this email — nobody can sign in without the code.
Our team will never ask you for this code.</p></div>"""


def send_email(to: str, code: str, purpose: str) -> None:
    sender = os.getenv("MAIL_FROM", f"{APP} <no-reply@thehealthtracker.com>")
    subject = f"{code} is your {APP} code"
    text = f"Your {APP} code is {code}. It expires in 10 minutes. Never share it with anyone."
    if os.getenv("RESEND_API_KEY"):
        req = urllib.request.Request("https://api.resend.com/emails", method="POST",
                                     data=json.dumps({"from": sender, "to": [to], "subject": subject, "text": text, "html": _html(code, purpose)}).encode(),
                                     headers={"Authorization": "Bearer " + os.getenv("RESEND_API_KEY"), "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()
        return
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = sender, to, subject
    m.set_content(text)
    m.add_alternative(_html(code, purpose), subtype="html")
    host, port = os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "587"))
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=10) as s:
            s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
            s.send_message(m)
    else:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls(context=ssl.create_default_context())
            if os.getenv("SMTP_USER"):
                s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
            s.send_message(m)


def send_sms(to: str, code: str) -> None:
    if os.getenv("MSG91_AUTH_KEY") and os.getenv("MSG91_TEMPLATE_ID"):
        q = urllib.parse.urlencode({"template_id": os.getenv("MSG91_TEMPLATE_ID"), "mobile": to.lstrip("+"), "otp": code, "otp_expiry": 10})
        req = urllib.request.Request("https://control.msg91.com/api/v5/otp?" + q, method="POST", data=b"{}",
                                     headers={"authkey": os.getenv("MSG91_AUTH_KEY"), "Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()
        return
    sid, tok = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
    body = urllib.parse.urlencode({"To": to, "From": os.getenv("TWILIO_FROM", ""), "Body": f"{code} is your {APP} code. It expires in 10 min. Do not share it."}).encode()
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=body, method="POST",
                                 headers={"Authorization": "Basic " + base64.b64encode(f"{sid}:{tok}".encode()).decode()})
    urllib.request.urlopen(req, timeout=10).read()

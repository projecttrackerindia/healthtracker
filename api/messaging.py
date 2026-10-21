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
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage

APP = "Urban Health"
UA = f"{APP}/1.0 (+https://urbanhealth.in)"  # a default urllib User-Agent gets blocked by some providers' bot protection (e.g. Cloudflare)


def email_ready() -> bool:
    return bool(os.getenv("RESEND_API_KEY") or os.getenv("SMTP_HOST"))


def _use_resend() -> bool:
    """MAIL_TRANSPORT=smtp forces SMTP (e.g. Google Workspace) even when a Resend key is still set; resend forces Resend; auto = Resend when its key exists."""
    t = (os.getenv("MAIL_TRANSPORT") or "auto").strip().lower()
    if t == "smtp":
        return False
    if t == "resend":
        return bool(os.getenv("RESEND_API_KEY"))
    return bool(os.getenv("RESEND_API_KEY"))


def sms_mode() -> str:
    """Who delivers mobile codes: msg91 / twilio send our own 6-digit code; firebase = Firebase Phone Authentication sends and
    checks the SMS itself (Google handles the Indian DLT registration) and the browser hands us an ID token to verify."""
    if os.getenv("MSG91_AUTH_KEY") and os.getenv("MSG91_TEMPLATE_ID"):
        return "msg91"
    if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"):
        return "twilio"
    if os.getenv("FIREBASE_WEB_API_KEY"):
        return "firebase"
    return ""


def sms_ready() -> bool:
    return bool(sms_mode())


def firebase_web_config() -> dict | None:
    """What the browser needs to start a phone verification; empty unless Firebase is the SMS channel."""
    if sms_mode() != "firebase":
        return None
    return {"apiKey": os.getenv("FIREBASE_WEB_API_KEY"), "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN") or f"{os.getenv('FIREBASE_PROJECT_ID', '')}.firebaseapp.com",
            "projectId": os.getenv("FIREBASE_PROJECT_ID", ""), "appId": os.getenv("FIREBASE_APP_ID", "")}


def firebase_phone(id_token: str) -> str:
    """Verify a Firebase ID token with Google and return the phone number it certifies (E.164), or '' when it is not valid.
    accounts:lookup checks signature, expiry and project server-side, so no key material lives here."""
    if not id_token or sms_mode() != "firebase":
        return ""
    body = json.dumps({"idToken": id_token}).encode()
    req = urllib.request.Request("https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=" + urllib.parse.quote(os.getenv("FIREBASE_WEB_API_KEY", "")),
                                 data=body, headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            j = json.loads(r.read().decode())
    except Exception as e:
        print("[auth] firebase lookup failed:", str(e)[:160], flush=True)
        return ""
    users = j.get("users") or []
    return str(users[0].get("phoneNumber") or "") if users else ""


def demo() -> bool:
    """One-time codes shown on screen instead of sent: local development and staging only, never in production."""
    return os.getenv("OTP_DEMO", "0") == "1" and os.getenv("APP_ENV", "production") != "production"


def _html(code: str, purpose: str) -> str:
    what = {"signup": "finish creating your account", "reset": "reset your password", "step": "finish signing in", "verify": "verify this address"}.get(purpose, "sign in")
    return f"""<div style="font-family:Inter,Segoe UI,Arial,sans-serif;max-width:460px;margin:auto;padding:28px;color:#14151b">
<p style="font-weight:700;font-size:18px;margin:0 0 18px">Urban <span style="color:#2F5BFF">Health</span></p>
<p style="margin:0 0 10px">Use this code to {what}:</p>
<p style="font:700 34px/1 ui-monospace,Menlo,monospace;letter-spacing:.18em;margin:0 0 16px;color:#2F5BFF">{code}</p>
<p style="color:#5f6577;font-size:13px;margin:0">It expires in 10 minutes. If you did not ask for it, ignore this email — nobody can sign in without the code.
Our team will never ask you for this code.</p></div>"""


def send_email(to: str, code: str, purpose: str) -> None:
    sender = os.getenv("MAIL_FROM", f"{APP} <no-reply@urbanhealth.in>")
    subject = f"{code} is your {APP} code"
    text = f"Your {APP} code is {code}. It expires in 10 minutes. Never share it with anyone."
    if _use_resend():
        req = urllib.request.Request("https://api.resend.com/emails", method="POST",
                                     data=json.dumps({"from": sender, "to": [to], "subject": subject, "text": text, "html": _html(code, purpose)}).encode(),
                                     headers={"Authorization": "Bearer " + os.getenv("RESEND_API_KEY"), "Content-Type": "application/json", "User-Agent": UA})
        try:
            body = urllib.request.urlopen(req, timeout=10).read()
            print(f"[messaging] Resend accepted, from={sender!r} to={to!r}: {body.decode('utf-8', 'ignore')[:200]}", flush=True)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Resend {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}") from e
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


def send_mail_attachment(to: str, subject: str, text: str, filename: str, data: bytes, mime: str = "application/zip") -> None:
    """A transactional email with one attachment (monthly backup). SMTP transport; with Resend the attachment goes base64 in the payload."""
    sender = os.getenv("MAIL_FROM", f"{APP} <no-reply@urbanhealth.in>")
    if _use_resend():
        payload = {"from": sender, "to": [to], "subject": subject, "text": text, "attachments": [{"filename": filename, "content": base64.b64encode(data).decode()}]}
        req = urllib.request.Request("https://api.resend.com/emails", method="POST", data=json.dumps(payload).encode(),
                                     headers={"Authorization": "Bearer " + os.getenv("RESEND_API_KEY"), "Content-Type": "application/json", "User-Agent": UA})
        try:
            urllib.request.urlopen(req, timeout=20).read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Resend {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}") from e
        return
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = sender, to, subject
    m.set_content(text)
    main, _, sub = mime.partition("/")
    m.add_attachment(data, maintype=main or "application", subtype=sub or "octet-stream", filename=filename)
    host, port = os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "587"))
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as s:
            s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
            s.send_message(m)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ssl.create_default_context())
            if os.getenv("SMTP_USER"):
                s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", ""))
            s.send_message(m)


def alert_sms_ready() -> bool:
    """A channel that can carry free text, not only an OTP: Twilio, or an MSG91 flow registered for alerts (Firebase sends OTPs only)."""
    return bool((os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN")) or (os.getenv("MSG91_AUTH_KEY") and os.getenv("MSG91_SOS_FLOW_ID")))


def send_flow_sms(to: str, flow_id: str, variables: dict) -> bool:
    """MSG91 Flow API: a DLT-registered transactional template with variables (##name##, ##link##). India's way to send an alert
    SMS without Twilio: register the template once in MSG91 → DLT, then set MSG91_SOS_FLOW_ID."""
    key = os.getenv("MSG91_AUTH_KEY")
    if not (key and flow_id):
        return False
    body = json.dumps({"template_id": flow_id, "short_url": "0", "recipients": [{"mobiles": to.lstrip("+"), **{k: str(v)[:160] for k, v in variables.items()}}]}).encode()
    req = urllib.request.Request("https://control.msg91.com/api/v5/flow/", method="POST", data=body,
                                 headers={"authkey": key, "Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA})
    urllib.request.urlopen(req, timeout=10).read()
    return True


def send_text_sms(to: str, text: str, flow_vars: dict | None = None) -> bool:
    """Free-text SMS through Twilio; or, when flow_vars is given and MSG91_SOS_FLOW_ID is set, the MSG91 alert template. False when
    no such channel exists (MSG91 OTP templates cannot carry arbitrary text)."""
    sid, tok = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
    if not (sid and tok):
        if flow_vars is not None and os.getenv("MSG91_SOS_FLOW_ID"):
            return send_flow_sms(to, os.getenv("MSG91_SOS_FLOW_ID", ""), flow_vars)
        return False
    body = urllib.parse.urlencode({"To": to, "From": os.getenv("TWILIO_FROM", ""), "Body": text[:1500]}).encode()
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", method="POST", data=body,
                                 headers={"Authorization": "Basic " + base64.b64encode(f"{sid}:{tok}".encode()).decode(), "Content-Type": "application/x-www-form-urlencoded", "User-Agent": UA})
    urllib.request.urlopen(req, timeout=10).read()
    return True


def send_sms(to: str, code: str) -> None:
    if os.getenv("MSG91_AUTH_KEY") and os.getenv("MSG91_TEMPLATE_ID"):
        q = urllib.parse.urlencode({"template_id": os.getenv("MSG91_TEMPLATE_ID"), "mobile": to.lstrip("+"), "otp": code, "otp_expiry": 10})
        req = urllib.request.Request("https://control.msg91.com/api/v5/otp?" + q, method="POST", data=b"{}",
                                     headers={"authkey": os.getenv("MSG91_AUTH_KEY"), "Content-Type": "application/json", "User-Agent": UA})
        urllib.request.urlopen(req, timeout=10).read()
        return
    sid, tok = os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
    body = urllib.parse.urlencode({"To": to, "From": os.getenv("TWILIO_FROM", ""), "Body": f"{code} is your {APP} code. It expires in 10 min. Do not share it."}).encode()
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=body, method="POST",
                                 headers={"Authorization": "Basic " + base64.b64encode(f"{sid}:{tok}".encode()).decode(), "User-Agent": UA})
    urllib.request.urlopen(req, timeout=10).read()


def send_invite_email(to: str, by: str, name: str, link: str) -> None:
    """Invitation to create an account for an existing family profile (email only; SMS in India needs a DLT template)."""
    sender = os.getenv("MAIL_FROM", f"{APP} <no-reply@urbanhealth.in>")
    subject = f"{by} added you to the family on {APP}"
    text = (f"{by} has set up a profile for {name or 'you'} on {APP}, the family health app.\n\n"
            f"Create your account with this link to see your own records and your family's: {link}\n\n"
            f"The link works for 7 days. If you were not expecting this, you can ignore it.")
    html = f"""<div style="font-family:Inter,Arial,sans-serif;max-width:520px;margin:auto;padding:24px;color:#0f1220">
<p style="font-size:18px;margin:0 0 12px"><b>{by}</b> added you to the family on {APP}</p>
<p>A profile for <b>{name or 'you'}</b> is ready. Create your account to see your own records and your family's, on your own phone.</p>
<p style="margin:20px 0"><a href="{link}" style="background:#2F5BFF;color:#fff;text-decoration:none;padding:12px 20px;border-radius:12px;font-weight:600">Create my account</a></p>
<p style="color:#5f6577;font-size:13px">The link works for 7 days. If you were not expecting this, ignore this email.</p></div>"""
    if _use_resend():
        req = urllib.request.Request("https://api.resend.com/emails", method="POST",
                                     data=json.dumps({"from": sender, "to": [to], "subject": subject, "text": text, "html": html}).encode(),
                                     headers={"Authorization": "Bearer " + os.getenv("RESEND_API_KEY"), "Content-Type": "application/json", "User-Agent": UA})
        try:
            urllib.request.urlopen(req, timeout=10).read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Resend {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}") from e
        return
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = sender, to, subject
    m.set_content(text)
    m.add_alternative(html, subtype="html")
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


def send_mail(to: str, subject: str, text: str, html: str = "") -> None:
    """Any transactional email (partner alerts, welcome mails, admin attention). Same transport as the codes."""
    sender = os.getenv("MAIL_FROM", f"{APP} <no-reply@urbanhealth.in>")
    html = html or "<div style=\"font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;padding:24px;color:#0f1220;white-space:pre-line\">" + text.replace("&", "&amp;").replace("<", "&lt;") + "</div>"
    if _use_resend():
        req = urllib.request.Request("https://api.resend.com/emails", method="POST",
                                     data=json.dumps({"from": sender, "to": [to], "subject": subject, "text": text, "html": html}).encode(),
                                     headers={"Authorization": "Bearer " + os.getenv("RESEND_API_KEY"), "Content-Type": "application/json", "User-Agent": UA})
        try:
            urllib.request.urlopen(req, timeout=10).read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Resend {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}") from e
        return
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = sender, to, subject
    m.set_content(text)
    m.add_alternative(html, subtype="html")
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


SENT_LOG: list[dict] = []   # tests and the admin page look here when no transport is configured


def mail(to: str, subject: str, text: str, html: str = "") -> bool:
    """Best effort: never breaks the request that triggered it; returns whether it was handed to a transport."""
    if not to or "@" not in to:
        return False
    SENT_LOG.append({"to": to, "subject": subject, "t": int(time.time())})
    del SENT_LOG[:-200]
    if not email_ready():
        return False
    try:
        send_mail(to, subject, text, html)
        return True
    except Exception as e:
        print("[messaging] mail failed:", type(e).__name__, str(e)[:200], flush=True)
        return False

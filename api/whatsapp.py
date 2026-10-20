"""WhatsApp as the second channel (Meta Cloud API). On in India, read far more than push or email.

Set WA_TOKEN (permanent system-user token), WA_PHONE_ID (the sender's phone-number id) and, for the first message to a
person who has not written to us in 24 h, approved template names: WA_TEMPLATE_NOTICE (one body variable: the text).
Without a template only free-form text is sent, which Meta delivers inside a 24-hour customer-service window.
Everything is best effort: a failed send never breaks the request that triggered it. Phones must be E.164 (+91…).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SENT: list[dict] = []
KINDS = {"order", "lab_result", "appointment", "consult", "prescription", "payment", "blood", "message", "plan"}


def ready() -> bool:
    return bool(os.getenv("WA_TOKEN") and os.getenv("WA_PHONE_ID"))


def _post(payload: dict) -> dict:
    req = urllib.request.Request(f"https://graph.facebook.com/v20.0/{os.getenv('WA_PHONE_ID')}/messages", method="POST", data=json.dumps(payload).encode(),
                                 headers={"Authorization": "Bearer " + os.getenv("WA_TOKEN", ""), "Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"WhatsApp {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}") from e


def send(phone: str, text: str, template: bool = True) -> bool:
    phone = (phone or "").strip()
    if not phone.startswith("+") or len(phone) < 11:
        return False
    SENT.append({"to": phone, "text": text[:120]})
    del SENT[:-200]
    if not ready():
        return False
    to = phone.lstrip("+")
    try:
        tpl = os.getenv("WA_TEMPLATE_NOTICE")
        if template and tpl:
            _post({"messaging_product": "whatsapp", "to": to, "type": "template",
                   "template": {"name": tpl, "language": {"code": os.getenv("WA_TEMPLATE_LANG", "en")}, "components": [{"type": "body", "parameters": [{"type": "text", "text": text[:1000]}]}]}})
        else:
            _post({"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"preview_url": False, "body": text[:4000]}})
        return True
    except Exception as e:
        print("[whatsapp] send failed:", str(e)[:200], flush=True)
        return False


def send_sos(phone: str, name: str, link: str, text: str) -> bool:
    """The emergency message: the WA_TEMPLATE_SOS template (two body variables: name, live link) when approved, else the notice
    template / free text through send()."""
    phone = (phone or "").strip()
    if not phone.startswith("+"):
        phone = "+91" + phone.lstrip("0") if len(phone.lstrip("0")) == 10 else phone
    tpl = os.getenv("WA_TEMPLATE_SOS")
    if not (ready() and tpl):
        return send(phone, text)
    try:
        _post({"messaging_product": "whatsapp", "to": phone.lstrip("+"), "type": "template",
               "template": {"name": tpl, "language": {"code": os.getenv("WA_TEMPLATE_LANG", "en")},
                            "components": [{"type": "body", "parameters": [{"type": "text", "text": name[:60]}, {"type": "text", "text": link[:200]}]}]}})
        return True
    except Exception as e:
        print("[whatsapp] sos failed:", str(e)[:200], flush=True)
        return send(phone, text)

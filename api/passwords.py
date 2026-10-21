"""Password policy (same rules as the sign-up form shows), hashing (scrypt) and an optional breach check.

Rules: 12–128 characters; upper case, lower case, a number and a symbol; no 3 identical characters in a row; no 4-character
runs like 1234/abcd/qwer; must not contain the name, email or phone; must not be a common password; and (online) must not
appear in known breaches (Have I Been Pwned, k-anonymity: only the first 5 characters of the SHA-1 leave the server).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import urllib.request

COMMON = set("""password passw0rd password1 password12 password123 password@123 p@ssw0rd p@ssword 123456 1234567 12345678 123456789
1234567890 123123 111111 000000 654321 666666 121212 112233 qwerty qwerty123 qwertyuiop asdfgh asdfghjkl zxcvbnm iloveyou
admin admin123 administrator welcome welcome1 welcome123 letmein monkey dragon master sunshine princess football cricket
baseball superman batman trustno1 abc123 abcd1234 aa123456 india india123 india@123 bharat hyderabad bangalore mumbai delhi
chennai krishna sairam omsairam ganesh lakshmi jaishriram jaihind mother father family health healthy doctor hospital
changeme secret login default guest test test123 demo demo123 user user123 root toor pass pass123 pass@123 hello hello123
whatever freedom computer internet google facebook instagram samsung iphone apple microsoft windows linux urbanhealth
healthtracker tracker dokko dokko123 qwerty@123 admin@123 welcome@123 india@1234 password@1 Password@123 Password@1234
""".lower().split())
SEQS = ["abcdefghijklmnopqrstuvwxyz", "0123456789", "qwertyuiop", "asdfghjkl", "zxcvbnm"]


def check(pw: str, name: str = "", email: str = "", phone: str = "") -> list[str]:
    """Return a list of unmet rules (empty = acceptable)."""
    out = []
    if len(pw) < 12:
        out.append("Use at least 12 characters")
    if len(pw) > 128:
        out.append("Use at most 128 characters")
    if not re.search(r"[A-Z]", pw):
        out.append("Add an upper-case letter")
    if not re.search(r"[a-z]", pw):
        out.append("Add a lower-case letter")
    if not re.search(r"\d", pw):
        out.append("Add a number")
    if not re.search(r"[^A-Za-z0-9]", pw):
        out.append("Add a symbol such as ! @ # $ %")
    if re.search(r"(.)\1\1", pw):
        out.append("Avoid three identical characters in a row")
    low = pw.lower()
    for s in SEQS:
        for i in range(len(s) - 3):
            if s[i:i + 4] in low or s[i:i + 4][::-1] in low:
                out.append("Avoid runs like 1234, abcd or qwer")
                break
        else:
            continue
        break
    bits = [p for p in re.split(r"[\s@._+-]+", (name + " " + email.split("@")[0]).lower()) if len(p) >= 3]
    digits = re.sub(r"\D", "", phone)
    if any(b in low for b in bits) or (len(digits) >= 6 and digits[-6:] in pw):
        out.append("Do not use your name, email or phone number")
    core = re.sub(r"[^a-z0-9@]", "", low)
    if low in COMMON or core in COMMON or re.sub(r"[\d!@#$%^&*]+$", "", low) in COMMON:
        out.append("This password is too common")
    return out


def pwned(pw: str) -> int:
    """Times the password appears in known breaches (0 if not found or the service is unreachable)."""
    if os.getenv("PWNED_CHECK", "1") == "0":
        return 0
    h = hashlib.sha1(pw.encode()).hexdigest().upper()
    try:
        req = urllib.request.Request(f"https://api.pwnedpasswords.com/range/{h[:5]}", headers={"Add-Padding": "true", "User-Agent": "Urban Health"})
        with urllib.request.urlopen(req, timeout=3) as r:
            for line in r.read().decode().splitlines():
                suf, _, n = line.partition(":")
                if suf == h[5:]:
                    return int(n or 0)
    except Exception:
        return 0
    return 0


def hash_pw(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)
    return "scrypt$15$8$1$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_pw(pw: str, stored: str) -> bool:
    try:
        alg, ln, r, p, s, d = stored.split("$")
        if alg != "scrypt":
            return False
        dk = hashlib.scrypt(pw.encode(), salt=base64.b64decode(s), n=2 ** int(ln), r=int(r), p=int(p), maxmem=64 * 1024 * 1024, dklen=32)
        return hmac.compare_digest(dk, base64.b64decode(d))
    except Exception:
        return False

"""Round 1 landing-page fixes for site/index.html: accurate claims, no technical internals, privacy/terms links,
mobile number required at sign-up. Run once from the repository root: python tools/live/p0_site.py"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
F = ROOT / "site" / "index.html"
s = F.read_text(encoding="utf-8")
if "<!--live-p0-->" in s:
    sys.exit("already applied")

R = [
    ('<span class="pill rv"><b>NEW</b> AI reads your lab reports and prescriptions</span>',
     '<span class="pill rv"><b>NEW</b> A health card for every family member</span>'),
    ("A 3D body that shows your reports, medicines and reminders. Nearby pharmacies and labs compared on price. Pregnancy week by week. And one-tap SOS when it matters.",
     "A health card for everyone you care for, a 3D body that shows your reports, medicine reminders, pregnancy week by week, and one-tap SOS when it matters."),
    ('<a class="btn s" href="/app">Try the demo</a>', '<a class="btn s" href="/app">Try it without an account</a>'),
    ("<b>HbA1c + Lipid at home</b><small>Nearest lab ₹1,120 · tomorrow 7 AM</small>", "<b>Doses on time</b><small>Reminders for the whole family</small>"),
    ('<span class="ic" style="background:color-mix(in srgb,var(--teal) 14%,transparent)">🧪</span>', '<span class="ic" style="background:color-mix(in srgb,var(--teal) 14%,transparent)">💊</span>'),
    ("<div><b>40+</b><span>lab tests priced at nearby labs</span></div>", "<div><b>1 tap</b><span>SOS to 112 with your location</span></div>"),
    ("A prescription becomes a medicine list and an order in one tap.", "A prescription becomes a medicine list with reminders."),
    ('<span class="tag">Medicines</span><h3>Compare pharmacies before you order</h3><p>Nearby stores side by side on price, discount, delivery time and rating, with prescriptions checked by a pharmacist. Track the order and rate the delivery.</p><div class="shot"><img src="/s/img/cart.webp" width="900" height="1389" alt="Basket comparing nearby pharmacies by price and delivery" loading="lazy"></div>',
     '<span class="tag">Medicines · Coming soon</span><h3>Order from licensed pharmacies near you</h3><p>Compare nearby pharmacies on price and delivery time, with every prescription checked by a registered pharmacist. Opening city by city. Until then: dose reminders, stock alerts and allergy checks for every medicine.</p>'),
    ('<span class="tag">Labs</span><h3>Know the price before the needle</h3><p>Estimates for each test at labs near you, fasting needs, report time, NABL accreditation and home-collection slots.</p><div class="shot"><img src="/s/img/labs.webp" width="900" height="1389" alt="Nearby labs with price estimates and home collection" loading="lazy"></div>',
     '<span class="tag">Labs · Coming soon</span><h3>Know the price before the needle</h3><p>Accredited labs near you with test prices, fasting needs, report times and home sample collection. Opening city by city.</p>'),
    ('<i style="background:#2F5BFF">PR</i><i style="background:#E0457F">AN</i><i style="background:#D98A00">RA</i><i style="background:#0B8A7C">LA</i><i style="background:#7A5CFF">AR</i>',
     '<i style="background:#2F5BFF">👩</i><i style="background:#E0457F">👨</i><i style="background:#D98A00">👧</i><i style="background:#0B8A7C">👵</i><i style="background:#7A5CFF">👴</i>'),
    ("<h3>Create your account</h3><p>Email or mobile, a strong password, a one-time code — then a passkey so you never type the password again.</p>",
     "<h3>Create your account and health card</h3><p>Your name, mobile number and a strong password, then your health card: date of birth, sex and blood group. Add a passkey so you never type the password again.</p>"),
    ("<h3>Let it work for you</h3><p>Dose reminders, results explained, prices compared, seasonal health alerts for your city and SOS one tap away.</p>",
     "<h3>Let it work for you</h3><p>Dose reminders, results explained in plain words, seasonal health alerts for your city and SOS one tap away.</p>"),
    ("<summary>Which pharmacies and labs are listed?</summary><p>Partners are verified by our team before they appear, with their licence or NABL number. Prices come from their own price lists and are confirmed when you order or book.</p>",
     "<summary>Can I order medicines or book lab tests?</summary><p>Ordering and lab booking are opening city by city. Every pharmacy and lab is checked by our team, with its licence or NABL number, before it appears. Prices come from their own lists and are confirmed when you order or book.</p>"),
    ('<a href="/app">Demo</a>', '<a href="/app">Open the app</a>'),
    ('<div><b>Emergency</b><a href="tel:112">Call 112</a><a href="tel:108">Ambulance 108</a></div>',
     '<div><b>Legal</b><a href="/privacy">Privacy policy</a><a href="/terms">Terms of use</a></div>\n    <div><b>Emergency</b><a href="tel:112">Call 112</a><a href="tel:108">Ambulance 108</a></div>'),
    ("I agree to the Terms and Privacy Policy, and I understand Urban Health gives information, not a diagnosis.",
     'I agree to the <a href="/terms" target="_blank" rel="noopener">Terms</a> and <a href="/privacy" target="_blank" rel="noopener">Privacy Policy</a>, and I understand Urban Health gives information, not a diagnosis.'),
    ('<label for="up">Mobile <span style="font-weight:400;color:var(--mute)">optional</span></label>', '<label for="up">Mobile number</label>'),
    ("if(!B.email&&!B.phone){say('Enter an email address or a mobile number.');$('#ue').focus();return}",
     "if(!/^\\+91[6-9]\\d{9}$|^\\+(?!91)\\d{10,15}$/.test(B.phone)){say('Please enter a valid mobile number.');$('#up').focus();return}"),
]
for old, new in R:
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1, found {n}: {old[:80]!r}")
    s = s.replace(old, new)

# "Explore the demo" (final call to action)
s = s.replace(">Explore the demo<", ">Try it without an account<")

# Security section: plain language, no implementation details
i = s.index('<section class="band" id="security"')
j = s.index("</section>", i) + len("</section>")
sec = s[i:j]
icons = re.findall(r"<svg[\s\S]*?</svg>", sec[sec.index('<div class="sgrid">'):])
items = [
    ("Sign in without a password", "Use your fingerprint, face or screen lock with a passkey. There is nothing to steal or phish."),
    ("Codes that expire", "One-time codes by SMS or email work for a few minutes and only a few tries."),
    ("Strong passwords only", "If you use a password, it must be strong and is checked against known data breaches."),
    ("Records stay with you", "Reports, results and your health card live on your device. You choose what leaves it."),
    ("Consent you can see", "Every share, with a doctor, a pharmacy or an AI reading, is switched on by you and kept in a history."),
    ("Your account, protected", "Repeated wrong attempts pause sign-in, and you can sign out of every device at any time."),
]
grid = '<div class="sgrid">' + "".join(f"\n    <div>{icons[k] if k < len(icons) else ''}<b>{t}</b><p>{p}</p></div>" for k, (t, p) in enumerate(items)) + "\n  </div>"
new_sec = ('<section class="band" id="security" style="padding-top:20px"><div class="wrap"><div class="sec rv">\n'
           '  <span class="eyebrow" style="color:#8FA6FF">Security &amp; privacy</span>\n'
           '  <h2 style="margin-top:14px">Your family\'s health data, protected like it should be.</h2>\n'
           '  <p class="lead">Encrypted connections, sign-in with your fingerprint or face, and records that stay on your own device. '
           'Read exactly what we collect and why in our <a href="/privacy" style="color:#8FA6FF">privacy policy</a>.</p>\n  ' + grid + "\n</div></div></section>")
s = s[:i] + new_sec + s[j:]

s = s.replace("</body>", "<!--live-p0-->\n</body>", 1)
F.write_text(s, encoding="utf-8")
print("landing patched")
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)

"""Build site/privacy.html and site/terms.html (run: python tools/live/legal.py).

The pages contain {{ENTITY}}, {{ADDRESS}}, {{GRIEVANCE_NAME}}, {{GRIEVANCE_EMAIL}}, {{SUPPORT_EMAIL}} and {{UPDATED}}.
server.py fills them from environment variables at request time (see RAILWAY.md), so legal details are changed in
Railway, not in code. Have a lawyer review both texts before relying on them.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
LOGO = (Path(__file__).resolve().parent / "logo.svg").read_text(encoding="utf-8") if (Path(__file__).resolve().parent / "logo.svg").exists() else "TheHealthTracker"

CSS = """
@font-face{font-family:Geist;src:url(/s/fonts/geist.woff2) format("woff2");font-weight:100 900;font-display:swap}
:root{--bg:#F4F5F8;--card:#fff;--ink:#0F1220;--ink2:#2B2F3D;--mute:#646B7E;--line:rgba(15,18,32,.09);--blue:#2F5BFF;--teal:#0B8A7C;--red:#EF3B4F;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#0A0C12;--card:#141824;--ink:#EEF1FA;--ink2:#C9CFDE;--mute:#8A92A8;--line:rgba(255,255,255,.09);--blue:#7B95FF;color-scheme:dark}.logo svg path[transform]{fill:#E8EDFF}}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink2);font:16px/1.65 Geist,Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--blue)}header{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.bar{max-width:1080px;margin:auto;padding:14px 20px;display:flex;justify-content:space-between;align-items:center;gap:16px}.logo svg{height:26px;width:auto;display:block}
.bar nav{display:flex;gap:18px;font-size:14px}.bar nav a{color:var(--mute);text-decoration:none}.bar nav a:hover,.bar nav a[aria-current]{color:var(--ink)}
.hero{max-width:1080px;margin:auto;padding:56px 20px 10px}.eyebrow{font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--blue)}
h1{font-size:clamp(34px,5vw,52px);line-height:1.05;letter-spacing:-.03em;color:var(--ink);margin:12px 0 14px}.lead{font-size:18px;color:var(--mute);max-width:720px;margin:0}
.meta{font-size:13px;color:var(--mute);margin-top:14px}
.grid{max-width:1080px;margin:auto;padding:30px 20px 80px;display:grid;grid-template-columns:240px minmax(0,1fr);gap:40px}
.toc{position:sticky;top:84px;align-self:start;font-size:14px;display:grid;gap:6px}.toc a{color:var(--mute);text-decoration:none;padding:4px 10px;border-left:2px solid var(--line)}.toc a:hover{color:var(--ink);border-color:var(--blue)}
.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:0 0 34px}
.cards div{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px 18px}.cards b{display:block;color:var(--ink);font-size:15px;margin:8px 0 4px}.cards p{margin:0;font-size:14px;color:var(--mute);line-height:1.5}
.cards i{font-style:normal;display:grid;place-items:center;width:36px;height:36px;border-radius:11px;background:color-mix(in srgb,var(--blue) 12%,transparent);font-size:18px}
article section{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:26px 28px;margin-bottom:14px;scroll-margin-top:90px}
article h2{font-size:21px;letter-spacing:-.01em;color:var(--ink);margin:0 0 10px}article h3{font-size:16px;color:var(--ink);margin:18px 0 6px}
article p,article li{max-width:76ch}article ul{padding-left:20px;margin:8px 0}article li{margin:4px 0}
table{width:100%;border-collapse:collapse;font-size:14.5px;margin:10px 0}th,td{text-align:left;padding:10px 12px;border-top:1px solid var(--line);vertical-align:top}th{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);border-top:0}
.note{border-left:3px solid var(--teal);background:color-mix(in srgb,var(--teal) 8%,transparent);padding:12px 16px;border-radius:0 12px 12px 0;margin:12px 0}
.warn{border-left-color:var(--red);background:color-mix(in srgb,var(--red) 8%,transparent)}
footer{border-top:1px solid var(--line);padding:26px 20px;text-align:center;font-size:13px;color:var(--mute)}
@media (max-width:860px){.grid{grid-template-columns:1fr}.toc{display:none}.cards{grid-template-columns:1fr}article section{padding:20px}.bar nav a.hide-s{display:none}}
"""


def page(title, desc, eyebrow, h1, lead, cards, sections, current):
    toc = "".join(f'<a href="#{sid}">{t}</a>' for sid, t, _ in sections)
    body = "".join(f'<section id="{sid}"><h2>{t}</h2>{html}</section>' for sid, t, html in sections)
    cards_html = "".join(f"<div><i>{ic}</i><b>{t}</b><p>{p}</p></div>" for ic, t, p in cards)
    nav = "".join(f'<a href="{h}"{" aria-current=page" if h == current else ""}{c}>{t}</a>' for h, t, c in
                  (("/", "Home", ' class="hide-s"'), ("/privacy", "Privacy", ""), ("/terms", "Terms", ""), ("/app", "Open the app", "")))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title} · TheHealthTracker</title><meta name="description" content="{desc}"><link rel="icon" href="/icon.svg">
<style>{CSS}</style></head><body>
<header><div class="bar"><a class="logo" href="/" aria-label="TheHealthTracker home">{LOGO}</a><nav>{nav}</nav></div></header>
<div class="hero"><span class="eyebrow">{eyebrow}</span><h1>{h1}</h1><p class="lead">{lead}</p><p class="meta">Last updated: {{{{UPDATED}}}} · Provided by {{{{ENTITY}}}}</p></div>
<div class="grid"><nav class="toc" aria-label="On this page">{toc}</nav><article><div class="cards">{cards_html}</div>{body}</article></div>
<footer>© 2026 {{{{ENTITY}}}} · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a> · In an emergency call <a href="tel:112">112</a> or <a href="tel:108">108</a></footer>
</body></html>"""


PRIVACY = [
    ("summary", "In short", """
<p>TheHealthTracker helps you keep your family's health information in one place. We built it so that <b>your health records stay on your own device</b> and leave it only when you choose to share them.</p>
<ul><li>Your health card, family profiles, reports, results, medicines, readings, pregnancy logs and Medical ID are stored in your browser on your device. We cannot see them.</li>
<li>Our servers keep what is needed to run your account: your name, email, mobile number, sign-in details, plan and payments, and orders when ordering is available in your area.</li>
<li>A report or prescription is read by our servers only when you tap <b>Analyse</b> and agree. It is processed for that one reading and not stored by us.</li>
<li>We do not sell your data, we do not show ads, and we do not use your health information for marketing.</li></ul>
<p class="note">This policy explains how we handle personal data under India's Digital Personal Data Protection Act, 2023 (DPDP Act) and the Information Technology Act, 2000.</p>"""),
    ("device", "What stays on your device", """
<p>The app saves these in your browser's private storage on the device you use:</p>
<ul><li>Health card: name, date of birth, sex, blood group and mobile number for you and each family member you add.</li>
<li>Reports, prescriptions, scans and photos you upload to the Vault, and the results read from them.</li>
<li>Medicines, dose history, readings (heart rate, blood pressure, sugar, weight), visits, emergency contacts, Medical ID, consent history and pregnancy logs.</li></ul>
<p>Because they are stored on your device, they are not copied to other devices, and clearing your browser's site data removes them. Use <b>Family &amp; Privacy → My data</b> to download a copy or delete everything.</p>"""),
    ("server", "What our servers keep", """
<table><thead><tr><th>Data</th><th>Why</th><th>How long</th></tr></thead><tbody>
<tr><td>Name, email, mobile number and whether each is verified</td><td>To create and secure your account and to send sign-in codes</td><td>Until you delete your account</td></tr>
<tr><td>Password (stored only as a one-way hash), passkeys (public keys only)</td><td>To sign you in safely</td><td>Until you change them or delete your account</td></tr>
<tr><td>Sign-in sessions: device and browser type, IP address, times</td><td>To protect your account and let you sign out other devices</td><td>Up to 30 days per session</td></tr>
<tr><td>One-time codes</td><td>To verify your email or mobile</td><td>Expire after 10 minutes</td></tr>
<tr><td>An anonymous household key, the first name shown in the app, number of profiles, and the area you choose to share</td><td>To keep your plan and orders together and show services near you</td><td>Until you delete your account</td></tr>
<tr><td>Plan, invoices and payment references</td><td>To provide paid plans and meet tax law</td><td>As long as tax law requires (usually 8 years)</td></tr>
<tr><td>Orders and ratings, with the prescription you attach</td><td>To fulfil the order through the pharmacy you choose</td><td>As long as pharmacy and tax law require</td></tr>
</tbody></table>
<p>We never store your card, UPI or bank details. Payments are handled by our payment partner.</p>"""),
    ("ai", "Reading reports with AI", """
<p>When you tap <b>Analyse</b> on a document and agree, the document and the details needed to explain it (first name, age, sex, pregnancy status, allergies, conditions, current medicines, height and weight) are sent securely to our server and to our AI processing partner for that one reading.</p>
<ul><li>The result comes back to your device. We do not keep the document or the result on our servers; we keep only a count of readings for your plan.</li>
<li>Our AI processing partner acts only on our instructions. Under its commercial terms it does not use this data to train its models and deletes it after a short period kept for abuse monitoring.</li>
<li>You can switch AI reading off at any time in <b>Family &amp; Privacy → Consent</b>.</li></ul>
<p class="note warn">AI reading explains results in plain language. It is not a diagnosis. Always discuss results with your doctor.</p>"""),
    ("sharing", "Who we share data with", """
<p>We share personal data only with service providers that help us run TheHealthTracker, under contracts that require them to protect it and use it only for us:</p>
<table><thead><tr><th>Provider type</th><th>What they receive</th></tr></thead><tbody>
<tr><td>Cloud hosting and database</td><td>Account and order data described above</td></tr>
<tr><td>Email and SMS delivery</td><td>Your email or mobile number and the one-time code</td></tr>
<tr><td>Payment processing (Razorpay)</td><td>Amount, plan and the payment details you enter on their page</td></tr>
<tr><td>AI document reading (Anthropic)</td><td>Only the document you choose to analyse and the details listed above</td></tr>
<tr><td>Video playback (YouTube, privacy-enhanced mode)</td><td>Standard web request data when you play a first-aid video</td></tr>
<tr><td>Pharmacies and labs (when available in your area)</td><td>Only what an order or booking you place needs</td></tr></tbody></table>
<p>Some providers process data outside India. We use them only where the law allows and with safeguards in place. We disclose data to authorities only when the law requires it.</p>"""),
    ("sos", "Emergencies (SOS)", """
<p>SOS opens your phone's own dialer for 112 or 108 and prepares a message to your emergency contacts with your location and Medical ID. The message is sent from your phone, by you. Your location is read only when you press SOS or tap <b>Use my location</b>.</p>"""),
    ("rights", "Your rights and choices", """
<p>Under the DPDP Act you can:</p>
<ul><li><b>See</b> the personal data we hold about you and how we use it.</li>
<li><b>Correct or update</b> it. Most details can be changed in the app.</li>
<li><b>Delete</b> it. Delete on-device data in <b>Family &amp; Privacy → My data</b>, and your account in <b>Settings → Account &amp; security → Delete account</b>.</li>
<li><b>Withdraw consent</b> at any time, for example for AI reading or sharing with a doctor. Withdrawal does not affect what was done before.</li>
<li><b>Nominate</b> someone to exercise these rights if you are unable to.</li>
<li><b>Raise a grievance</b> with us, and if you are not satisfied, with the Data Protection Board of India.</li></ul>"""),
    ("children", "Children and family members", """
<p>You must be 18 or older to create an account. A parent or legal guardian may add children and manage their records, and by doing so confirms they have the authority to do so. We do not knowingly track children or use their data for advertising. Add an adult family member's details only with their permission.</p>"""),
    ("security", "How we protect data", """
<ul><li>All traffic is encrypted with HTTPS, and browsers are told to always use it.</li>
<li>Passkeys let you sign in with your fingerprint, face or screen lock, so there is no password to steal.</li>
<li>Passwords must be strong and are checked against known data breaches before they are accepted; we store only a one-way hash.</li>
<li>Repeated wrong attempts lock sign-in for a while, and you can sign out of all devices at any time.</li>
<li>We limit access to production systems to the people who need it to run the service.</li></ul>
<p>If a personal data breach affects you, we will inform you and the Data Protection Board as the law requires.</p>"""),
    ("changes", "Changes to this policy", """
<p>If we change this policy in a way that matters, we will tell you in the app before the change applies. The date at the top shows the latest version.</p>"""),
    ("contact", "Contact and grievance officer", """
<p>{{ENTITY}}<br>{{ADDRESS}}</p>
<p><b>Grievance Officer:</b> {{GRIEVANCE_NAME}}<br>Email: <a href="mailto:{{GRIEVANCE_EMAIL}}">{{GRIEVANCE_EMAIL}}</a></p>
<p>We acknowledge every request promptly and respond within the time the law requires.</p>"""),
]

TERMS = [
    ("service", "The service", """
<p>TheHealthTracker is a family health companion: a health card, records kept on your device, medicine reminders, a 3D body for understanding results, pregnancy information, first-aid guidance and an SOS shortcut. By creating an account or using the app you agree to these terms and to our <a href="/privacy">Privacy Policy</a>.</p>"""),
    ("medical", "Not medical advice", """
<p class="note warn"><b>TheHealthTracker gives general health information. It is not a medical device and does not diagnose, treat or prevent any condition.</b> Explanations, suggested checks and AI readings are for discussion with a qualified doctor. Never ignore or delay medical advice because of something in the app. In an emergency call 112 or 108 immediately.</p>"""),
    ("account", "Your account", """
<ul><li>You must be 18 or older. A parent or guardian may manage records for children.</li>
<li>Give accurate details, keep your sign-in methods safe, and tell us if you think someone else has used your account.</li>
<li>Records stored on your device are your responsibility to back up; use <b>My data → Download</b>.</li></ul>"""),
    ("use", "Acceptable use", """
<p>Do not misuse the service: no unlawful use, no adding someone's data without their permission, no attempts to break, overload or reverse-engineer the service, and no uploading of content you have no right to share.</p>"""),
    ("partners", "Pharmacies, labs and doctors", """
<p>Where pharmacies, labs or doctors are available through the app, they are independent providers responsible for their own products and services. Prescription medicines are supplied only against a valid prescription checked by a registered pharmacist. Prices shown are estimates until the provider confirms them.</p>"""),
    ("plans", "Plans and payments", """
<ul><li>The Free plan costs nothing. Paid plans are billed monthly or yearly in Indian rupees, including GST, through our payment partner.</li>
<li>You can cancel at any time; paid features continue until the end of the period you paid for. Refunds follow applicable law.</li>
<li>We will tell you in advance before changing the price of your plan.</li></ul>"""),
    ("ip", "Content and licences", """
<p>The app, its design and text belong to {{ENTITY}}. The 3D anatomy is built on open datasets (Z-Anatomy, CC BY-SA 4.0, based on BodyParts3D © DBCLS, and the HuBMAP Human Reference Atlas, CC BY 4.0) and is shared under those licences. First-aid videos belong to their publishers.</p>"""),
    ("liability", "Liability", """
<p>We work hard to keep the service accurate and available, but we provide it "as is" and cannot promise it will always be error-free or uninterrupted. To the extent the law allows, we are not liable for indirect losses, or for decisions made using the app instead of professional medical advice. Nothing in these terms limits rights you have under Indian consumer law.</p>"""),
    ("law", "Governing law", """
<p>These terms are governed by the laws of India. Courts in Hyderabad, Telangana have jurisdiction, subject to your rights as a consumer.</p>"""),
    ("contact", "Contact", """
<p>{{ENTITY}}, {{ADDRESS}} · <a href="mailto:{{SUPPORT_EMAIL}}">{{SUPPORT_EMAIL}}</a></p>"""),
]

(SITE / "privacy.html").write_text(page(
    "Privacy Policy", "How TheHealthTracker protects your family's health information.", "Privacy Policy",
    "Your health data stays yours.", "What we collect, what stays on your device, who we share with, and the rights you have under India's data protection law.",
    [("📱", "Records on your device", "Reports, results and your health card are stored in your browser, not on our servers."),
     ("✋", "You choose what leaves", "Nothing is shared with a doctor, pharmacy or AI reading unless you switch it on."),
     ("🚫", "Never sold", "No ads, no selling of data, no marketing from your health information.")],
    PRIVACY, "/privacy"), encoding="utf-8")
(SITE / "terms.html").write_text(page(
    "Terms of Use", "The terms for using TheHealthTracker.", "Terms of Use",
    "Terms of use", "The rules for using TheHealthTracker, written to be read.",
    [("ℹ️", "Information, not diagnosis", "Use the app to understand and organise. Decide with your doctor."),
     ("🆘", "Emergencies first", "Call 112 or 108. SOS helps you call and alert your family."),
     ("👪", "Your family, your consent", "Add people's details only with their permission.")],
    TERMS, "/terms"), encoding="utf-8")
print("wrote site/privacy.html and site/terms.html")

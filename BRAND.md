# Urban Health · brand and logo

## The mark
A place mark with a medical cross punched out of it: *health* (the cross), *here* (the pin). The cross is a real hole — one
path with `fill-rule="evenodd"` — so the same glyph works on a coloured tile (the hole shows the tile) and bare on any
background (the hole shows the page). There is no second colour to pass around and nothing to get wrong in dark mode.
Built on a 64-unit grid inside a rounded tile (radius 16); the cross sits at y≈25.6, above the geometric centre, because the
point below pulls the visual weight down.

The wordmark is **Urban Health** — "Urban" in Regular, "Health" in Bold — set in Inter Display and converted to outlines, so
it looks the same everywhere and needs no font file. Do not re-type it in another face, and do not letterspace it.

## One colour per audience
| Audience | Colour | Files | Where it is used |
| --- | --- | --- | --- |
| **Users** (people and families) | Signal Blue `#2F5BFF` | `user-*` | App, app icon, store listings, social, consumer marketing |
| **Partners** (doctors, hospitals, pharmacies, labs, insurers) | Care Teal `#0B8A7C` | `partner-*` | Partner onboarding, "verified partner" badges, partner documents and shop stickers |
| **Admin** (internal) | Graphite `#1C1E26` | `admin-*` | Admin console, internal tools, invoices |
| Print / fax / stamps | Black or white | `mono-*` | One-colour printing, embossing, dark photos |

Each logo uses a single colour: the tile and wordmark in the audience colour and the glyph knocked out in white (or the reverse
on a coloured background: `*-logo-white`). Never mix two audience colours in one logo.

## Files (`web/brand/`, also served at `https://urbanhealth.in/brand/…`)
* `svg/{user,partner,admin}-icon.svg` – app icon tile · `*-icon-maskable.svg` – Android adaptive icon (full bleed, safe zone)
* `svg/*-mark.svg` – the glyph alone · `svg/*-logo.svg` – horizontal lock-up · `svg/*-logo-white.svg` – for coloured/dark backgrounds
* `svg/user-logo-stacked.svg` – square layouts (splash, social avatar, posters)
* `png/*-icon-{1024,512,192,180,32}.png`, `png/*-logo*.png` – raster exports (transparent background)
* `brand-sheet.png` – overview

## Rules
* Clear space around the logo: at least half the tile height on every side. Minimum size: icon 16 px, lock-up 96 px wide.
* Do not stretch, rotate, outline, add shadows or gradients, recolour outside the palette, or re-type the wordmark in another font.
* Partners may show the partner logo only while they are verified in the admin panel.

## Protecting it (India) — practical steps
*General information, not legal advice; a registered trademark agent or IP lawyer should file and check the details.*

1. **Clear it first.** Search the Trade Marks Registry public search (ipindia.gov.in → Trade Marks → Public Search) for
   "urban health", "urbanhealth" and for device marks of a pin containing a cross in the classes below. Pin-and-cross
   logos are common in health and maps; a professional search reduces the risk of an objection or a dispute. Also check
   app stores and the .com/.in domains. Search the former name ("health tracker", "healthtracker") too — anything filed
   against it still matters while the old name is in the app stores and in users' hands.
2. **File trademarks (the main protection for a logo and a name).** E-file Form **TM-A** on the IP India portal. Government fee
   is **₹4,500 per class** for an individual, startup (DPIIT-recognised) or MSME, **₹9,000 per class** for others.
   Suggested classes:
   * **9** – downloadable mobile and web application software
   * **42** – software as a service / platform (the web app)
   * **44** – medical and health information services
   * **35** – online retail/marketplace for pharmacy and lab products, advertising for partners (if you sell or list)
   * **36** – only if you broker insurance yourself (that also needs an IRDAI licence)
   File the **composite logo** (mark + wordmark) as a device mark. "Urban Health" on its own is largely descriptive, so a plain
   word mark may draw an objection under s.9; the composite logo, used consistently, is the stronger filing. File the word
   mark as well if the agent thinks it is worth the fee — a refusal costs the class fee and nothing else. Use **™** now; use **®** only after
   registration (using ® before is an offence).
3. **Copyright (optional, extra evidence).** A logo is an artistic work. Copyright exists automatically, and you can register
   it on copyright.gov.in with **Form XIV**. For artwork used on goods or services the Copyright Office asks for a statement
   from the Trade Marks Registry that no identical/similar mark exists (a search certificate), so do it after the trademark
   search. Note: copyright protects human authorship; this logo was produced with AI assistance from your brief, so the
   trademark route above is the reliable protection. If you want a stronger copyright position, have a designer refine it
   and sign an assignment of copyright to your company.
4. **Own the assets.** Register urbanhealth.in and .in, the social handles, and the app-store developer name in the
   company's name. Keep dated copies of the files (these SVGs) as proof of first use.
5. **Timeline.** Examination report typically in 1–3 months; publication in the Trade Marks Journal; registration often
   within 6–18 months if not opposed. Protection runs for 10 years from filing and is renewable.

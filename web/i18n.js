/* Urban Health — app languages (English, Tamil, Telugu, Hindi).
   The app is written in English. In another language this file swaps the visible words for their translation
   as pages render, so every screen follows without its own copy of the strings. Medicine names, people's names,
   numbers and anything a person typed are never in the table, so they always stay exactly as entered.
   Every Tamil, Telugu and Hindi line must be checked by a native speaker before each release. */
(function () {
  'use strict';
  var KEY = 'uh-lang', CHOSEN = 'uh-lang-chosen';
  var NAMES = { en: 'English', ta: 'தமிழ்', te: 'తెలుగు', hi: 'हिन्दी' };
  var BCP = { en: 'en-IN', ta: 'ta-IN', te: 'te-IN', hi: 'hi-IN' };

  var TA = {
    'Summary': 'சுருக்கம்', 'Records': 'அறிக்கைகள்', 'Medicines': 'மருந்துகள்', 'Insurance': 'காப்பீடு', 'Family': 'குடும்பம்',
    'Settings': 'அமைப்புகள்', 'Save': 'சேமி', 'Saved': 'சேமிக்கப்பட்டது', 'Cancel': 'ரத்து', 'Change': 'மாற்று', 'Add': 'சேர்',
    'Total': 'மொத்தம்', 'Only': 'மட்டும்', 'Update': 'புதுப்பி', 'Not now': 'இப்போது வேண்டாம்', 'Continue': 'தொடரவும்',
    'Yes': 'ஆம்', 'No': 'இல்லை', 'Call': 'அழை', 'Delete': 'நீக்கு', 'Remove': 'அகற்று', 'Confirm': 'உறுதிசெய்', 'Send': 'அனுப்பு',
    'Skip': 'தவிர்', 'Skip for now': 'இப்போதைக்குத் தவிர்', 'Choose': 'தேர்ந்தெடு', 'Check': 'சரிபார்', 'Thanks': 'நன்றி',
    'Copied': 'நகலெடுக்கப்பட்டது', 'Free': 'இலவசம்', 'Other': 'மற்றவை', 'Work': 'வேலை', 'Not sure': 'தெரியவில்லை', 'Age': 'வயது',
    'State': 'மாநிலம்', 'Plan': 'திட்டம்', 'Merge': 'இணை', 'Keep both': 'இரண்டையும் வை', 'Stop': 'நிறுத்து', 'Verify': 'சரிபார்',
    'Emergency contacts': 'அவசரத் தொடர்புகள்', 'Medical ID': 'மருத்துவ அடையாளம்', 'Health profile': 'சுகாதார விவரம்',
    'My doctors': 'என் மருத்துவர்கள்', 'Share with a doctor': 'மருத்துவருடன் பகிர்', 'Doctor visit summary (PDF)': 'மருத்துவர் சந்திப்புச் சுருக்கம் (PDF)',
    'Who can see my health': 'என் ஆரோக்கியத்தை யார் பார்க்கலாம்', 'Notifications': 'அறிவிப்புகள்', 'Notification settings': 'அறிவிப்பு அமைப்புகள்',
    'Bookings and orders': 'முன்பதிவுகள் மற்றும் ஆர்டர்கள்', 'Addresses': 'முகவரிகள்', 'Who opened my records': 'என் அறிக்கைகளை யார் திறந்தார்கள்',
    'Sign-in and security': 'உள்நுழைவு மற்றும் பாதுகாப்பு', 'Your data': 'உங்கள் தரவு', 'Export, delete': 'பதிவிறக்கு, நீக்கு',
    'Sign out': 'வெளியேறு', 'Sign out everywhere': 'எல்லா இடங்களிலும் வெளியேறு', 'Privacy': 'தனியுரிமை', 'Terms': 'விதிமுறைகள்',
    'Privacy Policy': 'தனியுரிமைக் கொள்கை', 'Language': 'மொழி', 'On': 'இயக்கத்தில்', 'Off': 'அணைப்பில்', 'Private': 'தனிப்பட்டது',
    'Cycle': 'மாதவிடாய்ச் சுழற்சி', 'Pregnancy': 'கர்ப்பம்', "Women's health": 'பெண்கள் ஆரோக்கியம்',
    'Cycle, pregnancy and kick counts': 'சுழற்சி, கர்ப்பம், குழந்தை அசைவுகள்', 'Kick counter': 'குழந்தை அசைவு எண்ணி',
    'Book a home test': 'வீட்டில் பரிசோதனை பதிவு', 'Home test': 'வீட்டுப் பரிசோதனை', 'Sample collected at home': 'மாதிரி வீட்டிலேயே எடுக்கப்படும்',
    'My bookings': 'என் முன்பதிவுகள்', 'Tests and orders': 'பரிசோதனைகள் மற்றும் ஆர்டர்கள்', 'More results': 'மேலும் முடிவுகள்',
    'Search tests, doctors, labs, medicines': 'பரிசோதனை, மருத்துவர், ஆய்வகம், மருந்து தேடுக',
    'Try a test name, a doctor, a lab or a medicine.': 'பரிசோதனை, மருத்துவர், ஆய்வகம் அல்லது மருந்தின் பெயரைத் தேடுங்கள்.',
    'Not a diagnosis. Discuss with your doctor.': 'இது நோயறிதல் அல்ல. உங்கள் மருத்துவரிடம் பேசுங்கள்.',
    'Send invite': 'அழைப்பு அனுப்பு', 'Change history': 'மாற்ற வரலாறு', 'For': 'யாருக்கு', 'Add a new address': 'புதிய முகவரி சேர்',
    'Remove card': 'அட்டையை அகற்று', 'Cancelled': 'ரத்துசெய்யப்பட்டது', 'Enter a 10-digit mobile number': '10 இலக்க மொபைல் எண்ணை உள்ளிடுங்கள்',
    'Card saved': 'அட்டை சேமிக்கப்பட்டது', 'Send now': 'இப்போது அனுப்பு', 'From their own Settings': 'அவர்களின் அமைப்புகளிலிருந்து',
    'Taken': 'எடுத்தாயிற்று', 'Tap to see what it means': 'இதன் பொருளைக் காணத் தட்டுங்கள்', 'Recheck': 'மறுபரிசோதனை',
    'Conditions': 'நோய் நிலைகள்', 'None added': 'எதுவும் சேர்க்கப்படவில்லை', 'Blood': 'இரத்த வகை', 'Allergies': 'ஒவ்வாமைகள்',
    'Full Medical ID and conditions': 'முழு மருத்துவ அடையாளம் மற்றும் நோய் நிலைகள்', 'Share card with a doctor': 'அட்டையை மருத்துவருடன் பகிர்',
    'Due date': 'பிரசவ தேதி', 'Add your first report': 'உங்கள் முதல் அறிக்கையைச் சேர்க்கவும்', 'See what changed': 'என்ன மாறியது என்று பார்',
    'Highlights': 'முக்கியக் குறிப்புகள்', 'No medicines': 'மருந்துகள் இல்லை', 'Add them by hand or scan a prescription.': 'கையால் சேர்க்கவும் அல்லது மருந்துச் சீட்டை ஸ்கேன் செய்யவும்.',
    'Stopped': 'நிறுத்தப்பட்டது', 'Order from a nearby pharmacy': 'அருகிலுள்ள மருந்தகத்தில் ஆர்டர் செய்',
    'Invite': 'அழை', 'Invite by mobile or email': 'மொபைல் அல்லது மின்னஞ்சல் மூலம் அழை', "Sharing and women's health": 'பகிர்வு மற்றும் பெண்கள் ஆரோக்கியம்',
    'Leave this family': 'இந்தக் குடும்பத்திலிருந்து விலகு', 'Prescription medicine': 'மருந்துச் சீட்டு மருந்து', 'Save schedule': 'அட்டவணையைச் சேமி',
    'Looks right': 'சரியாக உள்ளது', "We couldn't read this clearly": 'இதைத் தெளிவாகப் படிக்க முடியவில்லை', 'Retake or upload again': 'மீண்டும் எடுக்கவும் அல்லது பதிவேற்றவும்',
    'No values were read from this file.': 'இந்தக் கோப்பிலிருந்து எந்த மதிப்பும் படிக்கப்படவில்லை.', 'Book a recheck at home': 'வீட்டில் மறுபரிசோதனை பதிவு',
    'View file': 'கோப்பைப் பார்', 'Add a doctor': 'மருத்துவரைச் சேர்', 'Send my health summary to a doctor': 'என் சுகாதாரச் சுருக்கத்தை மருத்துவருக்கு அனுப்பு',
    'Include medicines': 'மருந்துகளையும் சேர்', 'Create link': 'இணைப்பை உருவாக்கு', 'Copy link': 'இணைப்பை நகலெடு',
    'Tablets left': 'மீதமுள்ள மாத்திரைகள்', 'Remind me to refill': 'மீண்டும் வாங்க நினைவூட்டு', 'You can see': 'நீங்கள் பார்க்கலாம்',
    'Shared with you': 'உங்களுடன் பகிரப்பட்டது', 'Add another guardian': 'மற்றொரு பாதுகாவலரைச் சேர்', 'Remove from family': 'குடும்பத்திலிருந்து அகற்று',
    "Yes, that's right": 'ஆம், சரிதான்', 'Save relation': 'உறவைச் சேமி', 'Choose a guardian': 'பாதுகாவலரைத் தேர்ந்தெடு', 'Cancel invite': 'அழைப்பை ரத்துசெய்',
    'You invited': 'நீங்கள் அழைத்தவர்', 'Resend invite': 'மீண்டும் அழைப்பு அனுப்பு', 'Invite to your family': 'உங்கள் குடும்பத்திற்கு அழை',
    'Yes, open their profile': 'ஆம், அவர்களின் விவரத்தைத் திற', 'Edit details': 'விவரங்களைத் திருத்து', 'No contacts yet': 'இன்னும் தொடர்புகள் இல்லை',
    'Add a contact': 'தொடர்பைச் சேர்', 'Send family invite': 'குடும்ப அழைப்பு அனுப்பு', 'Guardian': 'பாதுகாவலர்',
    'Nobody else is in your family yet.': 'உங்கள் குடும்பத்தில் இன்னும் வேறு யாரும் இல்லை.', 'Invite someone': 'ஒருவரை அழை',
    'Nobody has opened your records.': 'உங்கள் அறிக்கைகளை யாரும் திறக்கவில்லை.', 'No duplicates': 'நகல்கள் இல்லை',
    'People, invites and medicines are all unique.': 'நபர்கள், அழைப்புகள், மருந்துகள் அனைத்தும் தனித்தவை.',
    'Download everything I can see': 'நான் பார்க்கக்கூடிய அனைத்தையும் பதிவிறக்கு', 'Find duplicates': 'நகல்களைக் கண்டுபிடி',
    'Ask for a copy of my data': 'என் தரவின் நகலைக் கேள்', 'Ask to correct my details': 'என் விவரங்களைத் திருத்தக் கேள்',
    'Ask to delete my data': 'என் தரவை நீக்கக் கேள்', 'Join with a company code': 'நிறுவனக் குறியீட்டுடன் சேர்',
    'Delete my account and data': 'என் கணக்கையும் தரவையும் நீக்கு', 'No partner labs near you yet': 'உங்கள் அருகில் இன்னும் கூட்டாளி ஆய்வகங்கள் இல்லை',
    'Add a report from any lab': 'எந்த ஆய்வகத்தின் அறிக்கையையும் சேர்க்கவும்', 'Labs near me': 'எனக்கு அருகிலுள்ள ஆய்வகங்கள்', 'Home visit': 'வீட்டு வருகை',
    'Fasting needed': 'உண்ணாவிரதம் தேவை', 'Pay the technician (cash or UPI)': 'தொழில்நுட்பரிடம் செலுத்துங்கள் (பணம் அல்லது UPI)',
    'Nothing booked yet': 'இன்னும் எதுவும் பதிவு செய்யப்படவில்லை', 'Report a problem': 'பிரச்சனையைத் தெரிவி', 'What went wrong?': 'என்ன தவறு நடந்தது?',
    'Mark all read': 'அனைத்தையும் படித்ததாகக் குறி', 'Clear all': 'அனைத்தையும் அழி', "You're all caught up": 'புதிதாக எதுவும் இல்லை',
    "Don't allow": 'அனுமதிக்காதே', 'Clear all notifications': 'அனைத்து அறிவிப்புகளையும் அழி', 'Turn on': 'இயக்கு',
    'Send a test notification': 'சோதனை அறிவிப்பு அனுப்பு', 'Quantity is strips or packs.': 'அளவு என்பது ஸ்ட்ரிப்கள் அல்லது பேக்குகள்.',
    'Compare pharmacies': 'மருந்தகங்களை ஒப்பிடு', 'No partner pharmacy has these yet': 'இவை இன்னும் எந்தக் கூட்டாளி மருந்தகத்திலும் இல்லை',
    'We are adding pharmacies area by area.': 'பகுதி பகுதியாக மருந்தகங்களைச் சேர்த்து வருகிறோம்.', 'Pharmacies near me': 'எனக்கு அருகிலுள்ள மருந்தகங்கள்',
    'My medicines': 'என் மருந்துகள்', 'Delivery': 'டெலிவரி', 'No prescription on file': 'மருந்துச் சீட்டு இல்லை', 'Cash on delivery': 'டெலிவரியின் போது பணம்',
    'UPI on delivery': 'டெலிவரியின் போது UPI', 'Order medicines': 'மருந்துகளை ஆர்டர் செய்', 'Choose at least one medicine': 'குறைந்தது ஒரு மருந்தைத் தேர்ந்தெடுக்கவும்',
    'Choose a pharmacy': 'மருந்தகத்தைத் தேர்ந்தெடு', 'Confirm order': 'ஆர்டரை உறுதிசெய்', 'Order placed. The pharmacist is checking it.': 'ஆர்டர் செய்யப்பட்டது. மருந்தாளர் சரிபார்க்கிறார்.',
    'Blood pressure': 'இரத்த அழுத்தம்', 'Alerting your contacts': 'உங்கள் தொடர்புகளுக்குத் தெரிவிக்கிறோம்', 'Share on WhatsApp': 'WhatsApp-இல் பகிர்',
    'Private for each person': 'ஒவ்வொருவருக்கும் தனிப்பட்டது', 'SOS to your family': 'உங்கள் குடும்பத்திற்கு SOS', 'Sign in': 'உள்நுழை',
    'Create account': 'கணக்கை உருவாக்கு', 'Sign in with a passkey': 'பாஸ்கீ மூலம் உள்நுழை', 'Verify the mobile later': 'மொபைலைப் பிறகு சரிபார்',
    'Use a different number or email': 'வேறு எண் அல்லது மின்னஞ்சலைப் பயன்படுத்து', 'Send a new code': 'புதிய குறியீடு அனுப்பு', 'About you': 'உங்களைப் பற்றி',
    'Add your family': 'உங்கள் குடும்பத்தைச் சேர்', 'Invited': 'அழைக்கப்பட்டது', 'Invite adult': 'பெரியவரை அழை', 'Add dependent': 'சார்ந்தவரைச் சேர்',
    'Add Urban Health to your home screen': 'Urban Health-ஐ முகப்புத் திரையில் சேர்க்கவும்', 'Install app': 'ஆப்பை நிறுவு',
    'Choose date': 'தேதியைத் தேர்ந்தெடு', 'Choose relationship': 'உறவைத் தேர்ந்தெடு', 'Relationship': 'உறவு', 'Save address': 'முகவரியைச் சேமி',
    'Remove address': 'முகவரியை அகற்று', 'Visit the lab instead': 'பதிலாக ஆய்வகத்திற்குச் செல்', 'Use current location': 'தற்போதைய இருப்பிடத்தைப் பயன்படுத்து',
    'Resend code': 'குறியீட்டை மீண்டும் அனுப்பு', 'Free government cover': 'இலவச அரசுக் காப்பீடு', 'Check eligibility': 'தகுதியைச் சரிபார்',
    'Your family': 'உங்கள் குடும்பம்', 'Quotes from a licensed partner': 'உரிமம் பெற்ற கூட்டாளியிடமிருந்து விலைகள்', 'Notify me': 'எனக்குத் தெரிவி',
    'No cover saved yet': 'இன்னும் காப்பீடு சேமிக்கப்படவில்லை', 'Am I eligible?': 'எனக்குத் தகுதி உள்ளதா?', 'Add a card': 'அட்டையைச் சேர்',
    'TPA helpline': 'TPA உதவி எண்', 'Valid till': 'செல்லுபடி வரை', 'Edit card': 'அட்டையைத் திருத்து', 'Change the time': 'நேரத்தை மாற்று',
    'GST invoice': 'GST விலைப்பட்டியல்', 'Central govt': 'மத்திய அரசு', 'Ex-service': 'முன்னாள் படைவீரர்', 'ESI worker': 'ESI தொழிலாளர்',
    'Official site': 'அதிகாரப்பூர்வ தளம்', 'Valid until (optional)': 'செல்லுபடி வரை (விருப்பம்)', 'Files up to 15 MB': '15 MB வரையிலான கோப்புகள்',
    'Your medicine schedule': 'உங்கள் மருந்து அட்டவணை', 'Profile updated': 'விவரம் புதுப்பிக்கப்பட்டது', 'Link copied': 'இணைப்பு நகலெடுக்கப்பட்டது',
    'Enter the medicine name': 'மருந்தின் பெயரை உள்ளிடுங்கள்', 'Pick at least one time': 'குறைந்தது ஒரு நேரத்தைத் தேர்ந்தெடுக்கவும்',
    'Choose a relation': 'உறவைத் தேர்ந்தெடு', 'Guardian added': 'பாதுகாவலர் சேர்க்கப்பட்டார்', 'You left the family': 'நீங்கள் குடும்பத்திலிருந்து விலகினீர்கள்',
    'Invite link copied': 'அழைப்பு இணைப்பு நகலெடுக்கப்பட்டது', 'Invite cancelled': 'அழைப்பு ரத்துசெய்யப்பட்டது', 'Invite sent': 'அழைப்பு அனுப்பப்பட்டது',
    'Add someone without a phone': 'போன் இல்லாதவரைச் சேர்', 'Keep at least one emergency contact': 'குறைந்தது ஒரு அவசரத் தொடர்பை வைத்திருங்கள்',
    'Passkey added': 'பாஸ்கீ சேர்க்கப்பட்டது', 'Duplicates': 'நகல்கள்', 'Merged': 'இணைக்கப்பட்டது', 'Joined': 'சேர்ந்தீர்கள்',
    'Request sent. We will tell you when it’s done.': 'கோரிக்கை அனுப்பப்பட்டது. முடிந்ததும் தெரிவிப்போம்.',
    'Notifications are on. A test is on its way.': 'அறிவிப்புகள் இயக்கத்தில் உள்ளன. சோதனை அறிவிப்பு வருகிறது.',
    'Choose a lab': 'ஆய்வகத்தைத் தேர்ந்தெடு', 'Confirm booking': 'முன்பதிவை உறுதிசெய்', 'Choose a time': 'நேரத்தைத் தேர்ந்தெடு',
    'Booked. The lab will confirm shortly.': 'பதிவு செய்யப்பட்டது. ஆய்வகம் விரைவில் உறுதிசெய்யும்.', 'Cleared': 'அழிக்கப்பட்டது',
    'Tell us a little more, in a sentence.': 'இன்னும் கொஞ்சம் சொல்லுங்கள், ஒரு வரியில்.', 'Sent. We will reply in your inbox.': 'அனுப்பப்பட்டது. உங்கள் இன்பாக்ஸில் பதில் தருவோம்.',
    'Add a reading': 'அளவீட்டைச் சேர்', 'Enter at least one reading': 'குறைந்தது ஒரு அளவீட்டை உள்ளிடுங்கள்', 'Enter all 6 digits': '6 இலக்கங்களையும் உள்ளிடுங்கள்',
    'You joined the family': 'நீங்கள் குடும்பத்தில் சேர்ந்தீர்கள்', 'Could not load the map. Check your internet.': 'வரைபடத்தை ஏற்ற முடியவில்லை. இணையத்தைச் சரிபாருங்கள்.',
    'Address saved': 'முகவரி சேமிக்கப்பட்டது', 'New code sent': 'புதிய குறியீடு அனுப்பப்பட்டது', 'That code is not right': 'அந்தக் குறியீடு சரியல்ல',
    'Time changed': 'நேரம் மாற்றப்பட்டது', 'Government health cover': 'அரசு சுகாதாரக் காப்பீடு', 'My cover': 'என் காப்பீடு', 'Government': 'அரசு',
    'Compare plans': 'திட்டங்களை ஒப்பிடு', 'Show card': 'அட்டையைக் காட்டு', 'Add PDF': 'PDF சேர்', 'Call helpline': 'உதவி எண்ணை அழை', 'Renewal': 'புதுப்பித்தல்',
    'After food': 'உணவுக்குப் பின்', 'Before food': 'உணவுக்கு முன்', 'With food': 'உணவுடன்', 'Empty stomach': 'வெறும் வயிற்றில்',
    '1 tablet': '1 மாத்திரை', '½ tablet': '½ மாத்திரை', '2 tablets': '2 மாத்திரைகள்', '1 capsule': '1 கேப்சூல்', '1 puff': '1 இன்ஹேலர் அழுத்தம்', '1 drop': '1 சொட்டு',
    'Add medicine': 'மருந்தைச் சேர்', 'HOW': 'எப்படி', 'WHEN': 'எப்போது', 'NAME AND STRENGTH': 'பெயர் மற்றும் அளவு', '+ Custom': '+ வேறு நேரம்',
    'Your time': 'உங்கள் நேரம்', 'Today': 'இன்று', 'Yesterday': 'நேற்று', 'Tomorrow': 'நாளை', 'Done': 'முடிந்தது', 'Back': 'பின்',
    'Search family and records': 'குடும்பம் மற்றும் அறிக்கைகளைத் தேடு', 'Your health': 'உங்கள் ஆரோக்கியம்', 'You': 'நீங்கள்',
    'Dependent': 'சார்ந்தவர்', 'You look after them': 'நீங்கள் கவனித்துக்கொள்கிறீர்கள்', 'Own login': 'சொந்த உள்நுழைவு',
    'Everything': 'அனைத்தும்', 'Medicine name and strength': 'மருந்தின் பெயர் மற்றும் அளவு', 'Name': 'பெயர்',
    'Start typing — e.g. Metformin 500': 'தட்டச்சு செய்யத் தொடங்குங்கள் — எ.கா. Metformin 500',
    'Choose your language': 'உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்', 'App language': 'ஆப் மொழி', 'For each family member': 'ஒவ்வொரு குடும்ப உறுப்பினருக்கும்',
    'Read reminders aloud': 'நினைவூட்டல்களை உரக்கப் படி', 'Helps elders who prefer listening': 'கேட்க விரும்பும் பெரியவர்களுக்கு உதவும்',
    'Voice': 'குரல்', 'Preview': 'முன்னோட்டம்', 'Play a sample': 'மாதிரியைக் கேள்',
    'Reminders in': 'நினைவூட்டல் மொழி:', 'read aloud': 'உரக்கப் படிக்கப்படும்', 'English': 'ஆங்கிலம்', 'Tamil': 'தமிழ்', 'Telugu': 'தெலுங்கு',
    'This phone may not have a voice for this language': 'இந்த போனில் இந்த மொழிக்கான குரல் இல்லாமல் இருக்கலாம்',
    'Medicine names stay as printed on the strip.': 'மருந்துகளின் பெயர்கள் அட்டையில் அச்சிடப்பட்டபடியே இருக்கும்.',
    'Reminders sent to this account arrive in this language.': 'இந்தக் கணக்கிற்கான நினைவூட்டல்கள் இந்த மொழியில் வரும்.',
    'Step 1 of 3': 'படி 1 / 3', 'Step 2 of 3': 'படி 2 / 3', 'Step 3 of 3': 'படி 3 / 3',
    'This builds your health card, Medical ID and 3D body.': 'இது உங்கள் சுகாதார அட்டை, மருத்துவ அடையாளம், 3D உடல் படத்தை உருவாக்கும்.',
    'Date of birth': 'பிறந்த தேதி', 'Sex': 'பாலினம்', 'Blood group': 'இரத்த வகை', 'Last blood donation': 'கடைசி இரத்த தானம்', 'Height (cm)': 'உயரம் (செ.மீ)',
    'Weight (kg)': 'எடை (கி.கி)', 'Full name as on Aadhaar': 'ஆதாரில் உள்ளபடி முழுப் பெயர்', 'None, or e.g. Penicillin': 'இல்லை, அல்லது எ.கா. Penicillin',
    'None, or e.g. Type 2 diabetes': 'இல்லை, அல்லது எ.கா. டைப் 2 நீரிழிவு', 'Male': 'ஆண்', 'Female': 'பெண்',
    'Add your address': 'உங்கள் முகவரியைச் சேர்க்கவும்', 'All medicines': 'அனைத்து மருந்துகள்', 'All': 'அனைத்தும்',
    'Add a report and it will appear on the body.': 'அறிக்கையைச் சேர்த்தால் அது உடல் படத்தில் தோன்றும்.',
    'Adults sign in with their own account and choose what you can see. Children and elders without a phone are added as dependents you look after.': 'பெரியவர்கள் தங்கள் சொந்தக் கணக்கில் உள்நுழைந்து நீங்கள் எதைப் பார்க்கலாம் என்பதைத் தேர்வு செய்வார்கள். போன் இல்லாத குழந்தைகளும் பெரியவர்களும் நீங்கள் கவனிக்கும் சார்ந்தவர்களாகச் சேர்க்கப்படுவார்கள்.',
    'Confirm location': 'இருப்பிடத்தை உறுதிசெய்', 'Explore body in 3D ›': '3D உடலைப் பாருங்கள் ›', 'Find doctors who accept it': 'இதை ஏற்கும் மருத்துவர்களைக் கண்டறியுங்கள்',
    'How it helps': 'இது எப்படி உதவும்', 'Keep the card here': 'அட்டையை இங்கே வையுங்கள்',
    "Keep your PM-JAY, state or CGHS card here so it's ready at the hospital — or check what you may be eligible for.": 'PM-JAY, மாநில அல்லது CGHS அட்டையை இங்கே வையுங்கள்; மருத்துவமனையில் உடனே காட்டலாம் — அல்லது உங்களுக்கு எது தகுதி என்று பாருங்கள்.',
    'Labs': 'ஆய்வகங்கள்', 'Scans': 'ஸ்கேன்கள்', 'Scan Rx': 'மருந்துச் சீட்டை ஸ்கேன் செய்', 'Search medicines': 'மருந்துகளைத் தேடு', 'No records yet': 'இன்னும் அறிக்கைகள் இல்லை',
    'Matched to your own reports — heart, diabetes, kidney care.': 'உங்கள் அறிக்கைகளுக்குப் பொருந்துபவர்கள் — இதயம், நீரிழிவு, சிறுநீரகம்.',
    'Move the map to your exact door': 'வரைபடத்தை உங்கள் வாசல் வரை நகர்த்துங்கள்',
    'PDF or photo. It is read for you and shown on the body.': 'PDF அல்லது புகைப்படம். அது படிக்கப்பட்டு உடல் படத்தில் காட்டப்படும்.',
    'Search area, street, building…': 'பகுதி, தெரு, கட்டடம் தேடுக…', 'Schemes most families check': 'பெரும்பாலான குடும்பங்கள் பார்க்கும் திட்டங்கள்',
    'See what it can pay for': 'இது எதற்குச் செலுத்தும் என்று பாருங்கள்', 'Shown at the hospital desk in one tap, even offline.': 'இணையம் இல்லாவிட்டாலும் மருத்துவமனையில் ஒரே தட்டலில் காட்டலாம்.',
    'The technician will come here': 'தொழில்நுட்பர் இங்கு வருவார்', 'Verified doctors at partner hospitals near you.': 'உங்கள் அருகிலுள்ள கூட்டாளி மருத்துவமனைகளின் சரிபார்க்கப்பட்ட மருத்துவர்கள்.',
    '— you can still save it': '— இருந்தாலும் சேமிக்கலாம்', 'Use current location': 'தற்போதைய இருப்பிடத்தைப் பயன்படுத்து', 'Not served here yet': 'இங்கு இன்னும் சேவை இல்லை',
    'Next dose': 'அடுத்த டோஸ்', 'Wife': 'மனைவி', 'Husband': 'கணவர்', 'Mother': 'அம்மா', 'Father': 'அப்பா', 'Son': 'மகன்', 'Daughter': 'மகள்', 'Brother': 'சகோதரர்', 'Sister': 'சகோதரி',
    'emergency contact, not in family yet': 'அவசரத் தொடர்பு, இன்னும் குடும்பத்தில் இல்லை', 'emergency contact': 'அவசரத் தொடர்பு',
    'Open in 3D': '3D-யில் திற',
    'High': 'அதிகம்',
    'Low': 'குறைவு',
    'Set up your family': 'உங்கள் குடும்பத்தை அமைக்கவும்',
    'Passkey on this phone': 'இந்த ஃபோனில் பாஸ்கீ',
    'Your profile': 'உங்கள் சுயவிவரம்',
    'First report or medicine': 'முதல் அறிக்கை அல்லது மருந்து',
    'Heart': 'இதயம்',
    'Liver': 'கல்லீரல்',
    'Kidney': 'சிறுநீரகம்',
    'Up next': 'அடுத்து',
    'Open': 'திற',
    'Home': 'முகப்பு',
    'Lab': 'ஆய்வகம்',
    'Medicine': 'மருந்து',
    'Visits': 'வருகைகள்',
    'Hold for 1 second': '1 வினாடி அழுத்திப் பிடிக்கவும்',
    'My reports': 'என் அறிக்கைகள்',
    'Book a test': 'பரிசோதனை பதிவு செய்',
    'Add reports': 'அறிக்கைகளைச் சேர்',
    'See cover': 'காப்பீட்டைப் பார்',
    'Mine': 'என்னுடையவை',
    'Order': 'ஆர்டர் செய்',
    'Orders': 'ஆர்டர்கள்',
    'Reminder on your phone': 'உங்கள் ஃபோனில் நினைவூட்டல்',
    'tablet': 'மாத்திரை',
    'capsule': 'கேப்ஸ்யூல்',
    'Reorder': 'மீண்டும் ஆர்டர்',
    'Claims': 'கோரிக்கைகள்',
    'You may qualify for free cover': 'உங்களுக்கு இலவச காப்பீடு கிடைக்கலாம்',
    'Keep your card ready': 'உங்கள் அட்டையைத் தயாராக வைத்திருங்கள்',
    'What cover can pay for': 'காப்பீடு எதற்குச் செலுத்தும்',
    'Your cover': 'உங்கள் காப்பீடு',
    'Cards, claims, schemes': 'அட்டைகள், கோரிக்கைகள், திட்டங்கள்',
    'Book': 'பதிவு செய்',
    'History': 'வரலாறு',
    'No appointments yet': 'இன்னும் சந்திப்புகள் இல்லை',
    'Book a visit': 'வருகையைப் பதிவு செய்',
    'Overdue': 'தாமதம்',
    'Prepare for your next visit': 'அடுத்த வருகைக்குத் தயாராகுங்கள்',
    'One page for the doctor: medicines, recent results and your questions': 'மருத்துவருக்கு ஒரு பக்கம்: மருந்துகள், சமீபத்திய முடிவுகள், உங்கள் கேள்விகள்',
    'No visits booked': 'வருகைகள் பதிவு செய்யப்படவில்லை',
    'Tap to book': 'பதிவு செய்ய தட்டவும்',
    'Permissions': 'அனுமதிகள்',
    'Download my data': 'என் தரவைப் பதிவிறக்கு',
    'Simple mode for elders': 'மூத்தவர்களுக்கான எளிய முறை',
    'Made in India · Your data stays in India': 'இந்தியாவில் உருவானது · உங்கள் தரவு இந்தியாவிலேயே இருக்கும்',
    'Shown on the lock screen and sent with SOS.': 'பூட்டுத் திரையில் காட்டப்படும், SOS உடன் அனுப்பப்படும்.',
    'Called first': 'முதலில் அழைக்கப்படுவார்',
    'On my lock screen': 'என் பூட்டுத் திரையில்',
    'Responders see it without unlocking': 'உதவுபவர்கள் திறக்காமலே பார்க்கலாம்',
    'Blood donor': 'இரத்த தானம் செய்பவர்',
    'Help someone nearby, only when you can': 'அருகில் உள்ளவருக்கு உதவுங்கள், முடியும்போது மட்டும்',
    'Be there for someone nearby': 'அருகில் உள்ள ஒருவருக்கு துணையாக இருங்கள்',
    'When a hospital near you needs your group, you get one quiet note. You decide each time.': 'அருகிலுள்ள மருத்துவமனைக்கு உங்கள் வகை தேவைப்படும்போது ஒரு அமைதியான செய்தி வரும். ஒவ்வொரு முறையும் நீங்களே முடிவு செய்யலாம்.',
    'You get a note': 'உங்களுக்கு ஒரு செய்தி வரும்',
    'Only when your group matches and you are rested.': 'உங்கள் வகை பொருந்தி, நீங்கள் ஓய்வெடுத்திருக்கும்போது மட்டும்.',
    'You choose': 'நீங்களே தேர்வு செய்கிறீர்கள்',
    'Tap I can give, or simply ignore it. Nobody is told you said no.': '"நான் தருகிறேன்" என்பதைத் தட்டவும், அல்லது விட்டுவிடவும். நீங்கள் மறுத்தது யாருக்கும் தெரிவிக்கப்படாது.',
    'Your details stay private': 'உங்கள் விவரங்கள் தனிப்பட்டவையாக இருக்கும்',
    'The hospital sees your first name and phone only after it accepts your offer.': 'உங்கள் முன்வரவை மருத்துவமனை ஏற்ற பிறகே உங்கள் முதல் பெயரும் ஃபோனும் தெரியும்.',
    'A technician collects at home. Reports come back on your body.': 'தொழில்நுட்பர் வீட்டிலேயே மாதிரி எடுப்பார். அறிக்கைகள் உங்கள் உடலில் காட்டப்படும்.',
    'Due for you': 'உங்களுக்கு நேரமாகிவிட்டது',
    'Packages': 'தொகுப்புகள்',
    'Fasting': 'வெறும் வயிற்றில்',
    'Choose tests': 'பரிசோதனைகளைத் தேர்வு செய்',
    'Home collection': 'வீட்டில் மாதிரி சேகரிப்பு',
    'SOS calls the first contact and sends your location and Medical ID to all of them.': 'SOS முதல் தொடர்பை அழைத்து, அனைவருக்கும் உங்கள் இருப்பிடத்தையும் மருத்துவ அடையாளத்தையும் அனுப்பும்.',
    'Mobile you sign in with': 'நீங்கள் உள்நுழையும் மொபைல்',
    'Add a backup mobile': 'மாற்று மொபைலைச் சேர்',
    'If you change your SIM, codes come here': 'SIM மாற்றினால் குறியீடுகள் இங்கே வரும்',
    'Add a passkey (face or fingerprint)': 'பாஸ்கீ சேர் (முகம் அல்லது கைரேகை)',
    'Use an authenticator app': 'அங்கீகரிப்பு ஆப்பைப் பயன்படுத்து',
    'This device': 'இந்தச் சாதனம்',
    'You are signed out automatically after 10 minutes without use.': '10 நிமிடம் பயன்படுத்தாவிட்டால் தானாக வெளியேற்றப்படுவீர்கள்.',
    'This builds your Medical ID and the 3D body.': 'இது உங்கள் மருத்துவ அடையாளத்தையும் 3D உடலையும் உருவாக்கும்.',
    'Used on reports, prescriptions and insurance. Changes once a week with an email code.': 'அறிக்கைகள், மருந்துச் சீட்டுகள், காப்பீட்டில் பயன்படும். வாரத்துக்கு ஒருமுறை மின்னஞ்சல் குறியீட்டுடன் மாற்றலாம்.',
    'Hindi': 'இந்தி',
    'Doctor visit': 'மருத்துவர் வருகை',
    'Eye check (retina)': 'கண் பரிசோதனை (விழித்திரை)',
    'Every year with diabetes': 'நீரிழிவு இருந்தால் ஆண்டுதோறும்',
    'No reports yet': 'இன்னும் அறிக்கைகள் இல்லை',
    'Your cover may pay for heart care': 'உங்கள் காப்பீடு இதய சிகிச்சைக்குச் செலுத்தலாம்',
    'Matched to these reports. See what your policy or a government scheme includes.': 'இந்த அறிக்கைகளுடன் பொருத்தப்பட்டது. உங்கள் பாலிசி அல்லது அரசுத் திட்டத்தில் என்ன உள்ளது எனப் பாருங்கள்.',
    'Verified · can also get sign-in codes': 'சரிபார்க்கப்பட்டது · உள்நுழைவுக் குறியீடுகளும் வரும்',
    'Google Authenticator or Microsoft Authenticator, after your password': 'கடவுச்சொல்லுக்குப் பிறகு Google Authenticator அல்லது Microsoft Authenticator',
    'How it works': 'இது எப்படிச் செயல்படுகிறது',
    'Please give only when you feel well: at least 18, about 50 kg or more, and no fever or new medicine this week. Men can give every 3 months, women every 4.': 'நீங்கள் நலமாக இருக்கும்போது மட்டும் தாருங்கள்: குறைந்தது 18 வயது, சுமார் 50 kg அல்லது அதற்கு மேல், இந்த வாரம் காய்ச்சலோ புதிய மருந்தோ இல்லாமல். ஆண்கள் 3 மாதத்திற்கு ஒருமுறை, பெண்கள் 4 மாதத்திற்கு ஒருமுறை தரலாம்.',
    'Asked near you': 'உங்கள் அருகில் கேட்கப்பட்டது',
    'Donation camps near you': 'உங்கள் அருகில் இரத்த தான முகாம்கள்',
    'I can give': 'நான் தருகிறேன்',
    'Withdraw': 'திரும்பப் பெறு',
    'Booked': 'பதிவு செய்யப்பட்டது',
    'Read it in your language': 'உங்கள் மொழியில் படியுங்கள்',
    'Book home collection': 'வீட்டில் மாதிரி சேகரிப்பைப் பதிவு செய்',
    'Prescription': 'மருந்துச் சீட்டு',
    'Read it in': 'இந்த மொழியில் படி',
    'Signed prescription': 'கையொப்பமிட்ட மருந்துச் சீட்டு'
  };

  var TE = {
    'Summary': 'సారాంశం', 'Records': 'రికార్డులు', 'Medicines': 'మందులు', 'Insurance': 'బీమా', 'Family': 'కుటుంబం', 'Settings': 'సెట్టింగ్‌లు',
    'Save': 'సేవ్ చేయి', 'Saved': 'సేవ్ అయింది', 'Cancel': 'రద్దు', 'Change': 'మార్చు', 'Add': 'జోడించు', 'Continue': 'కొనసాగించు', 'Yes': 'అవును', 'No': 'కాదు',
    'Call': 'కాల్ చేయి', 'Delete': 'తొలగించు', 'Remove': 'తీసివేయి', 'Confirm': 'నిర్ధారించు', 'Send': 'పంపు', 'Skip': 'దాటవేయి', 'Not now': 'ఇప్పుడు కాదు',
    'Emergency contacts': 'అత్యవసర పరిచయాలు', 'Medical ID': 'మెడికల్ ఐడీ', 'My doctors': 'నా డాక్టర్లు', 'Share with a doctor': 'డాక్టర్‌తో పంచుకోండి',
    'Notifications': 'నోటిఫికేషన్‌లు', 'Bookings and orders': 'బుకింగ్‌లు, ఆర్డర్‌లు', 'Addresses': 'చిరునామాలు', 'Sign-in and security': 'సైన్-ఇన్, భద్రత',
    'Your data': 'మీ డేటా', 'Sign out': 'సైన్ అవుట్', 'Privacy': 'గోప్యత', 'Terms': 'నిబంధనలు', 'Language': 'భాష', 'On': 'ఆన్', 'Off': 'ఆఫ్',
    'Taken': 'వేసుకున్నారు', 'Allergies': 'అలర్జీలు', 'Blood': 'రక్త వర్గం', 'Conditions': 'ఆరోగ్య సమస్యలు', 'Order medicines': 'మందులు ఆర్డర్ చేయండి',
    'Order from a nearby pharmacy': 'దగ్గరి ఫార్మసీ నుండి ఆర్డర్ చేయండి', 'Book a home test': 'ఇంటి వద్ద పరీక్ష బుక్ చేయండి', 'My medicines': 'నా మందులు',
    'Add medicine': 'మందు జోడించండి', 'After food': 'భోజనం తర్వాత', 'Before food': 'భోజనానికి ముందు', 'With food': 'భోజనంతో', 'Empty stomach': 'ఖాళీ కడుపుతో',
    'HOW': 'ఎలా', 'WHEN': 'ఎప్పుడు', 'Today': 'ఈరోజు', 'Done': 'పూర్తి', 'Back': 'వెనుకకు', 'You': 'మీరు', 'Your health': 'మీ ఆరోగ్యం',
    'Invite': 'ఆహ్వానించు', 'Invite by mobile or email': 'మొబైల్ లేదా ఇమెయిల్‌తో ఆహ్వానించండి', 'Sign in': 'సైన్ ఇన్', 'Create account': 'ఖాతా సృష్టించండి',
    'My cover': 'నా బీమా', 'Government': 'ప్రభుత్వం', 'Compare plans': 'ప్లాన్‌లు పోల్చండి', 'Add a card': 'కార్డ్ జోడించండి',
    'Choose your language': 'మీ భాషను ఎంచుకోండి', 'App language': 'యాప్ భాష', 'For each family member': 'ప్రతి కుటుంబ సభ్యునికి',
    'Read reminders aloud': 'రిమైండర్‌లను బిగ్గరగా చదవండి', 'Helps elders who prefer listening': 'వినడానికి ఇష్టపడే పెద్దలకు సహాయం', 'Voice': 'వాయిస్',
    'Preview': 'ముందస్తు చూపు', 'Play a sample': 'నమూనా వినండి',
    'Reminders in': 'రిమైండర్ భాష:', 'read aloud': 'బిగ్గరగా చదువుతుంది', 'English': 'ఇంగ్లీష్', 'Tamil': 'తమిళం', 'Telugu': 'తెలుగు',
    'This phone may not have a voice for this language': 'ఈ ఫోన్‌లో ఈ భాషకు వాయిస్ లేకపోవచ్చు',
    'Medicine names stay as printed on the strip.': 'మందుల పేర్లు స్ట్రిప్‌పై ముద్రించినట్లే ఉంటాయి.',
    'Reminders sent to this account arrive in this language.': 'ఈ ఖాతాకు రిమైండర్‌లు ఈ భాషలో వస్తాయి.',
    'Open in 3D': '3Dలో తెరవండి',
    'High': 'ఎక్కువ',
    'Low': 'తక్కువ',
    'Set up your family': 'మీ కుటుంబాన్ని సెటప్ చేయండి',
    'Passkey on this phone': 'ఈ ఫోన్‌లో పాస్‌కీ',
    'Your profile': 'మీ ప్రొఫైల్',
    'First report or medicine': 'మొదటి రిపోర్ట్ లేదా మందు',
    'Heart': 'గుండె',
    'Liver': 'కాలేయం',
    'Kidney': 'కిడ్నీ',
    'Up next': 'తర్వాత',
    'Open': 'తెరవండి',
    'Home': 'హోమ్',
    'Lab': 'ల్యాబ్',
    'Medicine': 'మందు',
    'Visits': 'విజిట్‌లు',
    'Hold for 1 second': '1 సెకను నొక్కి ఉంచండి',
    'My reports': 'నా రిపోర్టులు',
    'Book a test': 'టెస్ట్ బుక్ చేయండి',
    'Add reports': 'రిపోర్టులు జోడించండి',
    'See cover': 'కవర్ చూడండి',
    'Mine': 'నావి',
    'Order': 'ఆర్డర్ చేయండి',
    'Orders': 'ఆర్డర్లు',
    'Reminder on your phone': 'మీ ఫోన్‌లో రిమైండర్',
    'tablet': 'మాత్ర',
    'capsule': 'క్యాప్సూల్',
    'Reorder': 'మళ్ళీ ఆర్డర్',
    'Claims': 'క్లెయిమ్‌లు',
    'You may qualify for free cover': 'మీకు ఉచిత కవర్ రావచ్చు',
    'Keep your card ready': 'మీ కార్డ్ సిద్ధంగా ఉంచుకోండి',
    'What cover can pay for': 'కవర్ దేనికి చెల్లిస్తుంది',
    'Your cover': 'మీ కవర్',
    'Cards, claims, schemes': 'కార్డులు, క్లెయిమ్‌లు, పథకాలు',
    'Book': 'బుక్ చేయండి',
    'History': 'చరిత్ర',
    'No appointments yet': 'ఇంకా అపాయింట్‌మెంట్లు లేవు',
    'Book a visit': 'విజిట్ బుక్ చేయండి',
    'Overdue': 'ఆలస్యమైంది',
    'Prepare for your next visit': 'తదుపరి విజిట్‌కు సిద్ధం కండి',
    'One page for the doctor: medicines, recent results and your questions': 'డాక్టర్ కోసం ఒక పేజీ: మందులు, ఇటీవలి ఫలితాలు, మీ ప్రశ్నలు',
    'No visits booked': 'విజిట్‌లు బుక్ కాలేదు',
    'Tap to book': 'బుక్ చేయడానికి నొక్కండి',
    'Permissions': 'అనుమతులు',
    'Download my data': 'నా డేటా డౌన్‌లోడ్ చేయండి',
    'Simple mode for elders': 'పెద్దల కోసం సులభ మోడ్',
    'Made in India · Your data stays in India': 'భారతదేశంలో తయారైంది · మీ డేటా భారతదేశంలోనే ఉంటుంది',
    'Shown on the lock screen and sent with SOS.': 'లాక్ స్క్రీన్‌పై కనిపిస్తుంది, SOSతో పంపబడుతుంది.',
    'Called first': 'ముందుగా కాల్',
    'On my lock screen': 'నా లాక్ స్క్రీన్‌పై',
    'Responders see it without unlocking': 'సహాయకులు అన్‌లాక్ చేయకుండానే చూడగలరు',
    'Blood donor': 'రక్తదాత',
    'Help someone nearby, only when you can': 'దగ్గర్లో ఎవరికైనా సహాయం చేయండి, మీకు వీలైనప్పుడు మాత్రమే',
    'Be there for someone nearby': 'దగ్గర్లో ఉన్నవారికి అండగా ఉండండి',
    'When a hospital near you needs your group, you get one quiet note. You decide each time.': 'దగ్గర్లోని ఆసుపత్రికి మీ గ్రూప్ అవసరమైనప్పుడు మీకు ఒక సందేశం వస్తుంది. ప్రతిసారీ నిర్ణయం మీదే.',
    'You get a note': 'మీకు ఒక సందేశం వస్తుంది',
    'Only when your group matches and you are rested.': 'మీ గ్రూప్ సరిపోయి, మీరు విశ్రాంతి తీసుకున్నప్పుడు మాత్రమే.',
    'You choose': 'మీరే ఎంచుకుంటారు',
    'Tap I can give, or simply ignore it. Nobody is told you said no.': '"నేను ఇవ్వగలను" నొక్కండి, లేదా వదిలేయండి. మీరు కాదన్నట్టు ఎవరికీ చెప్పరు.',
    'Your details stay private': 'మీ వివరాలు గోప్యంగా ఉంటాయి',
    'The hospital sees your first name and phone only after it accepts your offer.': 'మీ ఆఫర్‌ను ఆసుపత్రి అంగీకరించిన తర్వాతే మీ మొదటి పేరు, ఫోన్ కనిపిస్తాయి.',
    'A technician collects at home. Reports come back on your body.': 'టెక్నీషియన్ ఇంటి వద్దే శాంపిల్ తీసుకుంటారు. రిపోర్టులు మీ శరీరంపై కనిపిస్తాయి.',
    'Due for you': 'మీకు సమయం అయింది',
    'Packages': 'ప్యాకేజీలు',
    'Fasting': 'ఖాళీ కడుపుతో',
    'Choose tests': 'టెస్టులు ఎంచుకోండి',
    'Home collection': 'ఇంటి వద్ద శాంపిల్',
    'SOS calls the first contact and sends your location and Medical ID to all of them.': 'SOS మొదటి కాంటాక్ట్‌కు కాల్ చేసి, అందరికీ మీ లొకేషన్, మెడికల్ IDని పంపుతుంది.',
    'Mobile you sign in with': 'మీరు సైన్ ఇన్ చేసే మొబైల్',
    'Add a backup mobile': 'బ్యాకప్ మొబైల్ జోడించండి',
    'If you change your SIM, codes come here': 'SIM మారిస్తే కోడ్‌లు ఇక్కడికి వస్తాయి',
    'Add a passkey (face or fingerprint)': 'పాస్‌కీ జోడించండి (ముఖం లేదా వేలిముద్ర)',
    'Use an authenticator app': 'ఆథెంటికేటర్ యాప్ వాడండి',
    'This device': 'ఈ పరికరం',
    'You are signed out automatically after 10 minutes without use.': '10 నిమిషాలు వాడకపోతే మీరు ఆటోమేటిక్‌గా సైన్ అవుట్ అవుతారు.',
    'This builds your Medical ID and the 3D body.': 'దీనితో మీ మెడికల్ ID, 3D శరీరం తయారవుతాయి.',
    'Used on reports, prescriptions and insurance. Changes once a week with an email code.': 'రిపోర్టులు, ప్రిస్క్రిప్షన్లు, బీమాలో వాడుతారు. వారానికి ఒకసారి ఈమెయిల్ కోడ్‌తో మార్చవచ్చు.',
    'Hindi': 'హిందీ',
    'Doctor visit': 'డాక్టర్ విజిట్',
    'Eye check (retina)': 'కంటి పరీక్ష (రెటీనా)',
    'Every year with diabetes': 'మధుమేహం ఉంటే ప్రతి సంవత్సరం',
    'No reports yet': 'ఇంకా రిపోర్టులు లేవు',
    'Your cover may pay for heart care': 'మీ కవర్ గుండె చికిత్సకు చెల్లించవచ్చు',
    'Matched to these reports. See what your policy or a government scheme includes.': 'ఈ రిపోర్టులతో సరిపోల్చాం. మీ పాలసీ లేదా ప్రభుత్వ పథకంలో ఏముందో చూడండి.',
    'Verified · can also get sign-in codes': 'ధృవీకరించారు · సైన్-ఇన్ కోడ్‌లు కూడా వస్తాయి',
    'Google Authenticator or Microsoft Authenticator, after your password': 'పాస్‌వర్డ్ తర్వాత Google Authenticator లేదా Microsoft Authenticator',
    'How it works': 'ఇది ఎలా పనిచేస్తుంది',
    'Please give only when you feel well: at least 18, about 50 kg or more, and no fever or new medicine this week. Men can give every 3 months, women every 4.': 'మీరు ఆరోగ్యంగా ఉన్నప్పుడే ఇవ్వండి: కనీసం 18 ఏళ్లు, దాదాపు 50 kg లేదా అంతకంటే ఎక్కువ, ఈ వారం జ్వరం గానీ కొత్త మందు గానీ లేకుండా. పురుషులు ప్రతి 3 నెలలకు, మహిళలు ప్రతి 4 నెలలకు ఇవ్వవచ్చు.',
    'Asked near you': 'మీ దగ్గర అడిగారు',
    'Donation camps near you': 'మీ దగ్గర రక్తదాన శిబిరాలు',
    'I can give': 'నేను ఇవ్వగలను',
    'Withdraw': 'వెనక్కి తీసుకోండి',
    'Booked': 'బుక్ అయింది',
    'Read it in your language': 'మీ భాషలో చదవండి',
    'Book home collection': 'ఇంటి వద్ద శాంపిల్ బుక్ చేయండి',
    'Prescription': 'ప్రిస్క్రిప్షన్',
    'Read it in': 'ఈ భాషలో చదవండి',
    'Signed prescription': 'సంతకం చేసిన ప్రిస్క్రిప్షన్'
  };


  var HI = {
    'Summary': 'सारांश',
    'Records': 'रिकॉर्ड',
    'Medicines': 'दवाइयाँ',
    'Insurance': 'बीमा',
    'Family': 'परिवार',
    'Settings': 'सेटिंग्स',
    'Save': 'सेव करें',
    'Saved': 'सेव हो गया',
    'Cancel': 'रद्द करें',
    'Change': 'बदलें',
    'Add': 'जोड़ें',
    'Total': 'कुल',
    'Only': 'सिर्फ़',
    'Update': 'अपडेट करें',
    'Not now': 'अभी नहीं',
    'Continue': 'आगे बढ़ें',
    'Yes': 'हाँ',
    'No': 'नहीं',
    'Call': 'कॉल करें',
    'Delete': 'हटाएँ',
    'Remove': 'हटाएँ',
    'Confirm': 'पक्का करें',
    'Send': 'भेजें',
    'Skip': 'छोड़ें',
    'Skip for now': 'अभी छोड़ें',
    'Choose': 'चुनें',
    'Check': 'जाँचें',
    'Thanks': 'धन्यवाद',
    'Copied': 'कॉपी हो गया',
    'Free': 'मुफ़्त',
    'Other': 'अन्य',
    'Work': 'दफ़्तर',
    'Not sure': 'पक्का नहीं',
    'Age': 'उम्र',
    'State': 'राज्य',
    'Plan': 'प्लान',
    'Merge': 'मिलाएँ',
    'Keep both': 'दोनों रखें',
    'Stop': 'रोकें',
    'Verify': 'पुष्टि करें',
    'Emergency contacts': 'आपातकालीन संपर्क',
    'Medical ID': 'मेडिकल आईडी',
    'Health profile': 'स्वास्थ्य प्रोफ़ाइल',
    'My doctors': 'मेरे डॉक्टर',
    'Share with a doctor': 'डॉक्टर के साथ साझा करें',
    'Doctor visit summary (PDF)': 'डॉक्टर विज़िट सारांश (PDF)',
    'Who can see my health': 'मेरा स्वास्थ्य कौन देख सकता है',
    'Notifications': 'सूचनाएँ',
    'Notification settings': 'सूचना सेटिंग्स',
    'Bookings and orders': 'बुकिंग और ऑर्डर',
    'Addresses': 'पते',
    'Who opened my records': 'मेरे रिकॉर्ड किसने खोले',
    'Sign-in and security': 'साइन-इन और सुरक्षा',
    'Your data': 'आपका डेटा',
    'Export, delete': 'एक्सपोर्ट, हटाएँ',
    'Sign out': 'साइन आउट',
    'Sign out everywhere': 'हर जगह से साइन आउट',
    'Privacy': 'गोपनीयता',
    'Terms': 'शर्तें',
    'Privacy Policy': 'गोपनीयता नीति',
    'Language': 'भाषा',
    'On': 'चालू',
    'Off': 'बंद',
    'Private': 'निजी',
    'Cycle': 'मासिक चक्र',
    'Pregnancy': 'गर्भावस्था',
    'Cycle, pregnancy and kick counts': 'मासिक चक्र, गर्भावस्था और बच्चे की हलचल',
    'Kick counter': 'हलचल गिनें',
    'Book a home test': 'घर पर टेस्ट बुक करें',
    'Home test': 'घर पर टेस्ट',
    'Sample collected at home': 'घर से लिया गया सैंपल',
    'My bookings': 'मेरी बुकिंग',
    'Tests and orders': 'टेस्ट और ऑर्डर',
    'More results': 'और नतीजे',
    'Search tests, doctors, labs, medicines': 'टेस्ट, डॉक्टर, लैब, दवाइयाँ खोजें',
    'Try a test name, a doctor, a lab or a medicine.': 'किसी टेस्ट, डॉक्टर, लैब या दवा का नाम लिखें।',
    'Not a diagnosis. Discuss with your doctor.': 'यह निदान नहीं है। अपने डॉक्टर से बात करें।',
    'Send invite': 'न्योता भेजें',
    'Change history': 'बदलाव का इतिहास',
    'For': 'किसके लिए',
    'Add a new address': 'नया पता जोड़ें',
    'Remove card': 'कार्ड हटाएँ',
    'Cancelled': 'रद्द हो गया',
    'Enter a 10-digit mobile number': '10 अंकों का मोबाइल नंबर डालें',
    'Card saved': 'कार्ड सेव हो गया',
    'Send now': 'अभी भेजें',
    'From their own Settings': 'उनकी अपनी सेटिंग्स से',
    'Taken': 'ली गई',
    'Tap to see what it means': 'मतलब जानने के लिए टैप करें',
    'Recheck': 'दोबारा जाँच',
    'Conditions': 'बीमारियाँ',
    'None added': 'कुछ नहीं जोड़ा',
    'Blood': 'ब्लड',
    'Allergies': 'एलर्जी',
    'Full Medical ID and conditions': 'पूरी मेडिकल आईडी और बीमारियाँ',
    'Share card with a doctor': 'कार्ड डॉक्टर के साथ साझा करें',
    'Due date': 'डिलीवरी की तारीख़',
    'Add your first report': 'अपनी पहली रिपोर्ट जोड़ें',
    'See what changed': 'देखें क्या बदला',
    'Highlights': 'मुख्य बातें',
    'No medicines': 'कोई दवा नहीं',
    'Add them by hand or scan a prescription.': 'हाथ से जोड़ें या पर्चा स्कैन करें।',
    'Stopped': 'बंद की गई',
    'Order from a nearby pharmacy': 'पास की फ़ार्मेसी से मँगाएँ',
    'Invite': 'न्योता',
    'Invite by mobile or email': 'मोबाइल या ईमेल से न्योता दें',
    'Leave this family': 'यह परिवार छोड़ें',
    'Prescription medicine': 'पर्चे वाली दवा',
    'Save schedule': 'समय-सारणी सेव करें',
    'Looks right': 'सही है',
    'Retake or upload again': 'दोबारा फ़ोटो लें या फिर से अपलोड करें',
    'No values were read from this file.': 'इस फ़ाइल से कोई वैल्यू नहीं पढ़ी जा सकी।',
    'Book a recheck at home': 'घर पर दोबारा जाँच बुक करें',
    'View file': 'फ़ाइल देखें',
    'Add a doctor': 'डॉक्टर जोड़ें',
    'Send my health summary to a doctor': 'मेरा स्वास्थ्य सारांश डॉक्टर को भेजें',
    'Include medicines': 'दवाइयाँ शामिल करें',
    'Create link': 'लिंक बनाएँ',
    'Copy link': 'लिंक कॉपी करें',
    'Tablets left': 'बची हुई गोलियाँ',
    'Remind me to refill': 'दवा ख़त्म होने से पहले याद दिलाएँ',
    'You can see': 'आप देख सकते हैं',
    'Shared with you': 'आपके साथ साझा किया गया',
    'Add another guardian': 'एक और अभिभावक जोड़ें',
    'Remove from family': 'परिवार से हटाएँ',
    'Save relation': 'रिश्ता सेव करें',
    'Choose a guardian': 'अभिभावक चुनें',
    'Cancel invite': 'न्योता रद्द करें',
    'You invited': 'आपने न्योता भेजा',
    'Resend invite': 'न्योता फिर से भेजें',
    'Invite to your family': 'अपने परिवार में न्योता दें',
    'Yes, open their profile': 'हाँ, उनकी प्रोफ़ाइल खोलें',
    'Edit details': 'जानकारी बदलें',
    'No contacts yet': 'अभी कोई संपर्क नहीं',
    'Add a contact': 'संपर्क जोड़ें',
    'Send family invite': 'परिवार का न्योता भेजें',
    'Guardian': 'अभिभावक',
    'Nobody else is in your family yet.': 'अभी आपके परिवार में कोई और नहीं है।',
    'Invite someone': 'किसी को न्योता दें',
    'Nobody has opened your records.': 'किसी ने आपके रिकॉर्ड नहीं खोले।',
    'No duplicates': 'कोई दोहराव नहीं',
    'People, invites and medicines are all unique.': 'लोग, न्योते और दवाइयाँ सब अलग-अलग हैं।',
    'Download everything I can see': 'जो कुछ मैं देख सकता हूँ, सब डाउनलोड करें',
    'Find duplicates': 'दोहराव खोजें',
    'Ask for a copy of my data': 'मेरे डेटा की कॉपी माँगें',
    'Ask to correct my details': 'मेरी जानकारी ठीक करवाएँ',
    'Ask to delete my data': 'मेरा डेटा हटाने को कहें',
    'Join with a company code': 'कंपनी कोड से जुड़ें',
    'Delete my account and data': 'मेरा खाता और डेटा हटाएँ',
    'No partner labs near you yet': 'अभी आपके पास कोई पार्टनर लैब नहीं है',
    'Add a report from any lab': 'किसी भी लैब की रिपोर्ट जोड़ें',
    'Labs near me': 'मेरे पास की लैब',
    'Home visit': 'घर पर विज़िट',
    'Fasting needed': 'ख़ाली पेट आना है',
    'Pay the technician (cash or UPI)': 'टेक्नीशियन को भुगतान करें (नकद या UPI)',
    'Nothing booked yet': 'अभी कुछ बुक नहीं हुआ',
    'Report a problem': 'समस्या बताएँ',
    'What went wrong?': 'क्या गड़बड़ हुई?',
    'Mark all read': 'सब पढ़ा हुआ करें',
    'Clear all': 'सब हटाएँ',
    'Clear all notifications': 'सारी सूचनाएँ हटाएँ',
    'Turn on': 'चालू करें',
    'Send a test notification': 'एक टेस्ट सूचना भेजें',
    'Quantity is strips or packs.': 'मात्रा पत्तों या पैक में है।',
    'Compare pharmacies': 'फ़ार्मेसी की तुलना करें',
    'No partner pharmacy has these yet': 'किसी पार्टनर फ़ार्मेसी के पास अभी ये नहीं हैं',
    'We are adding pharmacies area by area.': 'हम इलाक़े-इलाक़े में फ़ार्मेसी जोड़ रहे हैं।',
    'Pharmacies near me': 'मेरे पास की फ़ार्मेसी',
    'My medicines': 'मेरी दवाइयाँ',
    'Delivery': 'डिलीवरी',
    'No prescription on file': 'कोई पर्चा नहीं है',
    'Cash on delivery': 'डिलीवरी पर नकद',
    'UPI on delivery': 'डिलीवरी पर UPI',
    'Order medicines': 'दवाइयाँ मँगाएँ',
    'Choose at least one medicine': 'कम से कम एक दवा चुनें',
    'Choose a pharmacy': 'फ़ार्मेसी चुनें',
    'Confirm order': 'ऑर्डर पक्का करें',
    'Order placed. The pharmacist is checking it.': 'ऑर्डर हो गया। फ़ार्मासिस्ट इसे जाँच रहे हैं।',
    'Blood pressure': 'ब्लड प्रेशर',
    'Alerting your contacts': 'आपके संपर्कों को ख़बर दी जा रही है',
    'Share on WhatsApp': 'WhatsApp पर भेजें',
    'Private for each person': 'हर व्यक्ति के लिए निजी',
    'SOS to your family': 'परिवार को SOS',
    'Sign in': 'साइन इन करें',
    'Create account': 'खाता बनाएँ',
    'Sign in with a passkey': 'पासकी से साइन इन करें',
    'Verify the mobile later': 'मोबाइल बाद में पक्का करें',
    'Use a different number or email': 'कोई और नंबर या ईमेल इस्तेमाल करें',
    'Send a new code': 'नया कोड भेजें',
    'About you': 'आपके बारे में',
    'Add your family': 'अपना परिवार जोड़ें',
    'Invited': 'न्योता भेजा',
    'Invite adult': 'बड़े सदस्य को न्योता दें',
    'Add dependent': 'आश्रित जोड़ें',
    'Add Urban Health to your home screen': 'Urban Health को होम स्क्रीन पर जोड़ें',
    'Install app': 'ऐप इंस्टॉल करें',
    'Choose date': 'तारीख़ चुनें',
    'Choose relationship': 'रिश्ता चुनें',
    'Relationship': 'रिश्ता',
    'Save address': 'पता सेव करें',
    'Remove address': 'पता हटाएँ',
    'Visit the lab instead': 'इसके बजाय लैब जाएँ',
    'Use current location': 'अभी की जगह इस्तेमाल करें',
    'Resend code': 'कोड फिर से भेजें',
    'Free government cover': 'मुफ़्त सरकारी बीमा',
    'Check eligibility': 'पात्रता जाँचें',
    'Your family': 'आपका परिवार',
    'Quotes from a licensed partner': 'लाइसेंस वाले पार्टनर से कोटेशन',
    'Notify me': 'मुझे बताएँ',
    'No cover saved yet': 'अभी कोई बीमा सेव नहीं',
    'Am I eligible?': 'क्या मैं पात्र हूँ?',
    'Add a card': 'कार्ड जोड़ें',
    'TPA helpline': 'TPA हेल्पलाइन',
    'Valid till': 'कब तक मान्य',
    'Edit card': 'कार्ड बदलें',
    'Change the time': 'समय बदलें',
    'GST invoice': 'GST बिल',
    'Central govt': 'केंद्र सरकार',
    'Ex-service': 'पूर्व सैनिक',
    'ESI worker': 'ESI कर्मचारी',
    'Official site': 'आधिकारिक साइट',
    'Valid until (optional)': 'कब तक मान्य (वैकल्पिक)',
    'Files up to 15 MB': '15 MB तक की फ़ाइलें',
    'Your medicine schedule': 'आपकी दवा की समय-सारणी',
    'Profile updated': 'प्रोफ़ाइल अपडेट हो गई',
    'Link copied': 'लिंक कॉपी हो गया',
    'Enter the medicine name': 'दवा का नाम लिखें',
    'Pick at least one time': 'कम से कम एक समय चुनें',
    'Choose a relation': 'रिश्ता चुनें',
    'Guardian added': 'अभिभावक जोड़ दिए गए',
    'You left the family': 'आपने परिवार छोड़ दिया',
    'Invite link copied': 'न्योते का लिंक कॉपी हो गया',
    'Invite cancelled': 'न्योता रद्द हो गया',
    'Invite sent': 'न्योता भेज दिया',
    'Add someone without a phone': 'बिना फ़ोन वाले किसी व्यक्ति को जोड़ें',
    'Keep at least one emergency contact': 'कम से कम एक आपातकालीन संपर्क रखें',
    'Passkey added': 'पासकी जुड़ गई',
    'Duplicates': 'दोहराव',
    'Merged': 'जोड़ दिए गए',
    'Joined': 'जुड़ गए',
    'Request sent. We will tell you when it’s done.': 'अनुरोध भेज दिया। पूरा होने पर हम आपको बताएँगे।',
    'Notifications are on. A test is on its way.': 'सूचनाएँ चालू हैं। एक टेस्ट सूचना आ रही है।',
    'Choose a lab': 'लैब चुनें',
    'Confirm booking': 'बुकिंग पक्की करें',
    'Choose a time': 'समय चुनें',
    'Booked. The lab will confirm shortly.': 'बुक हो गया। लैब जल्द ही पक्का करेगी।',
    'Cleared': 'हटा दिया गया',
    'Tell us a little more, in a sentence.': 'थोड़ा और बताइए, एक वाक्य में।',
    'Sent. We will reply in your inbox.': 'भेज दिया। हम आपके इनबॉक्स में जवाब देंगे।',
    'Add a reading': 'रीडिंग जोड़ें',
    'Enter at least one reading': 'कम से कम एक रीडिंग डालें',
    'Enter all 6 digits': 'सभी 6 अंक डालें',
    'You joined the family': 'आप परिवार में जुड़ गए',
    'Could not load the map. Check your internet.': 'नक्शा नहीं खुल सका। अपना इंटरनेट जाँचें।',
    'Address saved': 'पता सेव हो गया',
    'New code sent': 'नया कोड भेज दिया',
    'That code is not right': 'यह कोड सही नहीं है',
    'Time changed': 'समय बदल गया',
    'Government health cover': 'सरकारी स्वास्थ्य बीमा',
    'My cover': 'मेरा बीमा',
    'Government': 'सरकारी',
    'Compare plans': 'प्लान की तुलना करें',
    'Show card': 'कार्ड दिखाएँ',
    'Add PDF': 'PDF जोड़ें',
    'Call helpline': 'हेल्पलाइन पर कॉल करें',
    'Renewal': 'रिन्यूअल',
    'After food': 'खाने के बाद',
    'Before food': 'खाने से पहले',
    'With food': 'खाने के साथ',
    'Empty stomach': 'ख़ाली पेट',
    '1 tablet': '1 गोली',
    '½ tablet': '½ गोली',
    '2 tablets': '2 गोलियाँ',
    '1 capsule': '1 कैप्सूल',
    '1 puff': '1 पफ़',
    '1 drop': '1 बूँद',
    'Add medicine': 'दवा जोड़ें',
    'HOW': 'कैसे',
    'WHEN': 'कब',
    'NAME AND STRENGTH': 'नाम और ताक़त',
    '+ Custom': '+ अपना समय',
    'Your time': 'आपका समय',
    'Today': 'आज',
    'Yesterday': 'बीता कल',
    'Tomorrow': 'आने वाला कल',
    'Done': 'हो गया',
    'Back': 'वापस',
    'Search family and records': 'परिवार और रिकॉर्ड खोजें',
    'Your health': 'आपका स्वास्थ्य',
    'You': 'आप',
    'Dependent': 'आश्रित',
    'You look after them': 'आप इनकी देखभाल करते हैं',
    'Own login': 'अपना लॉगिन',
    'Everything': 'सब कुछ',
    'Medicine name and strength': 'दवा का नाम और ताक़त',
    'Name': 'नाम',
    'Start typing — e.g. Metformin 500': 'लिखना शुरू करें — जैसे Metformin 500',
    'Choose your language': 'अपनी भाषा चुनें',
    'App language': 'ऐप की भाषा',
    'For each family member': 'परिवार के हर सदस्य के लिए',
    'Read reminders aloud': 'रिमाइंडर पढ़कर सुनाएँ',
    'Helps elders who prefer listening': 'सुनना पसंद करने वाले बुज़ुर्गों के लिए मददगार',
    'Voice': 'आवाज़',
    'Preview': 'झलक',
    'Play a sample': 'नमूना सुनें',
    'Reminders in': 'रिमाइंडर इस भाषा में',
    'read aloud': 'पढ़कर सुनाया जाएगा',
    'English': 'अंग्रेज़ी',
    'Tamil': 'तमिल',
    'Telugu': 'तेलुगु',
    'This phone may not have a voice for this language': 'इस फ़ोन में शायद इस भाषा की आवाज़ नहीं है',
    'Medicine names stay as printed on the strip.': 'दवाओं के नाम वैसे ही रहते हैं जैसे पत्ते पर छपे हैं।',
    'Reminders sent to this account arrive in this language.': 'इस खाते पर भेजे गए रिमाइंडर इसी भाषा में आते हैं।',
    'Step 1 of 3': 'चरण 1 / 3',
    'Step 2 of 3': 'चरण 2 / 3',
    'Step 3 of 3': 'चरण 3 / 3',
    'This builds your health card, Medical ID and 3D body.': 'इससे आपका हेल्थ कार्ड, मेडिकल आईडी और 3D शरीर बनता है।',
    'Date of birth': 'जन्म तिथि',
    'Sex': 'लिंग',
    'Blood group': 'ब्लड ग्रुप',
    'Last blood donation': 'पिछला रक्तदान',
    'Height (cm)': 'लंबाई (cm)',
    'Weight (kg)': 'वज़न (kg)',
    'Full name as on Aadhaar': 'पूरा नाम, आधार के अनुसार',
    'None, or e.g. Penicillin': 'कुछ नहीं, या जैसे Penicillin',
    'None, or e.g. Type 2 diabetes': 'कुछ नहीं, या जैसे टाइप 2 डायबिटीज़',
    'Male': 'पुरुष',
    'Female': 'महिला',
    'Add your address': 'अपना पता जोड़ें',
    'All medicines': 'सभी दवाइयाँ',
    'All': 'सभी',
    'Add a report and it will appear on the body.': 'रिपोर्ट जोड़ें, वह शरीर पर दिखेगी।',
    'Adults sign in with their own account and choose what you can see. Children and elders without a phone are added as dependents you look after.': 'बड़े अपने खाते से साइन इन करते हैं और चुनते हैं कि आप क्या देख सकते हैं। बिना फ़ोन वाले बच्चे और बुज़ुर्ग आश्रित के रूप में जोड़े जाते हैं, जिनकी देखभाल आप करते हैं।',
    'Confirm location': 'जगह पक्की करें',
    'Explore body in 3D ›': 'शरीर को 3D में देखें ›',
    'Find doctors who accept it': 'इसे मानने वाले डॉक्टर खोजें',
    'How it helps': 'यह कैसे मदद करता है',
    'Keep the card here': 'कार्ड यहाँ रखें',
    'Labs': 'लैब',
    'Scans': 'स्कैन',
    'Scan Rx': 'पर्चा स्कैन करें',
    'Search medicines': 'दवाइयाँ खोजें',
    'No records yet': 'अभी कोई रिकॉर्ड नहीं',
    'Matched to your own reports — heart, diabetes, kidney care.': 'आपकी अपनी रिपोर्टों से मिलाया गया — दिल, डायबिटीज़, किडनी की देखभाल।',
    'Move the map to your exact door': 'नक्शे को अपने दरवाज़े तक खिसकाएँ',
    'PDF or photo. It is read for you and shown on the body.': 'PDF या फ़ोटो। इसे आपके लिए पढ़कर शरीर पर दिखाया जाता है।',
    'Search area, street, building…': 'इलाक़ा, गली, बिल्डिंग खोजें…',
    'Schemes most families check': 'योजनाएँ जिन्हें ज़्यादातर परिवार देखते हैं',
    'See what it can pay for': 'देखें यह किसका ख़र्च उठा सकता है',
    'Shown at the hospital desk in one tap, even offline.': 'अस्पताल के काउंटर पर एक टैप में दिखता है, बिना इंटरनेट के भी।',
    'The technician will come here': 'टेक्नीशियन यहाँ आएँगे',
    'Verified doctors at partner hospitals near you.': 'आपके पास के पार्टनर अस्पतालों के जाँचे-परखे डॉक्टर।',
    '— you can still save it': '— फिर भी आप इसे सेव कर सकते हैं',
    'Use current location': 'अभी की जगह इस्तेमाल करें',
    'Not served here yet': 'यहाँ अभी सेवा नहीं है',
    'Next dose': 'अगली ख़ुराक',
    'Wife': 'पत्नी',
    'Husband': 'पति',
    'Mother': 'माँ',
    'Father': 'पिता',
    'Son': 'बेटा',
    'Daughter': 'बेटी',
    'Brother': 'भाई',
    'Sister': 'बहन',
    'emergency contact, not in family yet': 'आपातकालीन संपर्क, अभी परिवार में नहीं',
    'emergency contact': 'आपातकालीन संपर्क',
    'Open in 3D': '3D में खोलें',
    'High': 'ज़्यादा',
    'Low': 'कम',
    'Set up your family': 'अपना परिवार सेट करें',
    'Passkey on this phone': 'इस फ़ोन पर पासकी',
    'Your profile': 'आपकी प्रोफ़ाइल',
    'First report or medicine': 'पहली रिपोर्ट या दवा',
    'Heart': 'दिल',
    'Liver': 'लिवर',
    'Kidney': 'किडनी',
    'Up next': 'आगे',
    'Open': 'खोलें',
    'Home': 'होम',
    'Lab': 'लैब',
    'Medicine': 'दवा',
    'Visits': 'विज़िट',
    'Hold for 1 second': '1 सेकंड दबाए रखें',
    'My reports': 'मेरी रिपोर्ट',
    'Book a test': 'टेस्ट बुक करें',
    'Add reports': 'रिपोर्ट जोड़ें',
    'See cover': 'बीमा देखें',
    'Mine': 'मेरी',
    'Order': 'मँगाएँ',
    'Orders': 'ऑर्डर',
    'Reminder on your phone': 'आपके फ़ोन पर रिमाइंडर',
    'tablet': 'गोली',
    'capsule': 'कैप्सूल',
    'Reorder': 'फिर से मँगाएँ',
    'Claims': 'क्लेम',
    'You may qualify for free cover': 'आपको मुफ़्त बीमा मिल सकता है',
    'Keep your card ready': 'अपना कार्ड तैयार रखें',
    'What cover can pay for': 'बीमा किसका ख़र्च उठा सकता है',
    'Your cover': 'आपका बीमा',
    'Cards, claims, schemes': 'कार्ड, क्लेम, योजनाएँ',
    'Book': 'बुक करें',
    'History': 'इतिहास',
    'No appointments yet': 'अभी कोई अपॉइंटमेंट नहीं',
    'Book a visit': 'विज़िट बुक करें',
    'Overdue': 'देर हो गई',
    'Prepare for your next visit': 'अगली विज़िट की तैयारी करें',
    'One page for the doctor: medicines, recent results and your questions': 'डॉक्टर के लिए एक पन्ना: दवाइयाँ, हाल के नतीजे और आपके सवाल',
    'No visits booked': 'कोई विज़िट बुक नहीं',
    'Tap to book': 'बुक करने के लिए टैप करें',
    'Permissions': 'अनुमतियाँ',
    'Download my data': 'मेरा डेटा डाउनलोड करें',
    'Simple mode for elders': 'बुज़ुर्गों के लिए आसान मोड',
    'Made in India · Your data stays in India': 'भारत में बना · आपका डेटा भारत में ही रहता है',
    'Shown on the lock screen and sent with SOS.': 'लॉक स्क्रीन पर दिखता है और SOS के साथ भेजा जाता है।',
    'Called first': 'सबसे पहले कॉल',
    'On my lock screen': 'मेरी लॉक स्क्रीन पर',
    'Responders see it without unlocking': 'मदद करने वाले बिना अनलॉक किए देख सकते हैं',
    'Blood donor': 'रक्तदाता',
    'Help someone nearby, only when you can': 'पास में किसी की मदद करें, सिर्फ़ जब आप कर सकें',
    'Be there for someone nearby': 'पास में किसी के काम आएँ',
    'When a hospital near you needs your group, you get one quiet note. You decide each time.': 'जब पास के किसी अस्पताल को आपके ग्रुप की ज़रूरत हो, तो आपको एक सूचना मिलती है। हर बार फ़ैसला आपका।',
    'You get a note': 'आपको सूचना मिलती है',
    'Only when your group matches and you are rested.': 'सिर्फ़ जब आपका ग्रुप मिले और आपने आराम किया हो।',
    'You choose': 'आप चुनते हैं',
    'Tap I can give, or simply ignore it. Nobody is told you said no.': '"मैं दे सकता हूँ" दबाएँ, या बस छोड़ दें। किसी को नहीं बताया जाता कि आपने मना किया।',
    'Your details stay private': 'आपकी जानकारी निजी रहती है',
    'The hospital sees your first name and phone only after it accepts your offer.': 'अस्पताल आपका पहला नाम और फ़ोन तभी देखता है जब वह आपकी पेशकश स्वीकार करे।',
    'A technician collects at home. Reports come back on your body.': 'टेक्नीशियन घर से सैंपल लेते हैं। रिपोर्ट आपके शरीर पर दिखती है।',
    'Due for you': 'आपके लिए ज़रूरी',
    'Packages': 'पैकेज',
    'Fasting': 'ख़ाली पेट',
    'Choose tests': 'टेस्ट चुनें',
    'Home collection': 'घर से सैंपल',
    'SOS calls the first contact and sends your location and Medical ID to all of them.': 'SOS पहले संपर्क को कॉल करता है और सभी को आपकी जगह और मेडिकल आईडी भेजता है।',
    'Mobile you sign in with': 'जिस मोबाइल से आप साइन इन करते हैं',
    'Add a backup mobile': 'एक और मोबाइल जोड़ें',
    'If you change your SIM, codes come here': 'अगर आप SIM बदलें, तो कोड यहाँ आएँगे',
    'Add a passkey (face or fingerprint)': 'पासकी जोड़ें (चेहरा या फ़िंगरप्रिंट)',
    'Use an authenticator app': 'ऑथेंटिकेटर ऐप इस्तेमाल करें',
    'This device': 'यह डिवाइस',
    'You are signed out automatically after 10 minutes without use.': '10 मिनट तक इस्तेमाल न होने पर आप अपने-आप साइन आउट हो जाते हैं।',
    'This builds your Medical ID and the 3D body.': 'इससे आपकी मेडिकल आईडी और 3D शरीर बनता है।',
    'Used on reports, prescriptions and insurance. Changes once a week with an email code.': 'रिपोर्ट, पर्चे और बीमा पर इस्तेमाल होता है। हफ़्ते में एक बार ईमेल कोड से बदलता है।',
    'Hindi': 'हिन्दी',
    'Doctor visit': 'डॉक्टर विज़िट',
    'Eye check (retina)': 'आँखों की जाँच (रेटिना)',
    'Every year with diabetes': 'डायबिटीज़ में हर साल',
    'No reports yet': 'अभी कोई रिपोर्ट नहीं',
    'Your cover may pay for heart care': 'आपका बीमा दिल के इलाज का ख़र्च उठा सकता है',
    'Matched to these reports. See what your policy or a government scheme includes.': 'इन रिपोर्टों से मिलाया गया। देखें आपकी पॉलिसी या सरकारी योजना में क्या शामिल है।',
    'Verified · can also get sign-in codes': 'पक्का किया गया · साइन-इन कोड भी पा सकता है',
    'Google Authenticator or Microsoft Authenticator, after your password': 'पासवर्ड के बाद Google Authenticator या Microsoft Authenticator',
    'How it works': 'यह कैसे काम करता है',
    'Please give only when you feel well: at least 18, about 50 kg or more, and no fever or new medicine this week. Men can give every 3 months, women every 4.': 'कृपया तभी दें जब आप ठीक महसूस करें: कम से कम 18 साल, लगभग 50 kg या उससे ज़्यादा, और इस हफ़्ते न बुख़ार हो, न कोई नई दवा। पुरुष हर 3 महीने में और महिलाएँ हर 4 महीने में दे सकती हैं।',
    'Asked near you': 'आपके पास माँगा गया',
    'Donation camps near you': 'आपके पास रक्तदान शिविर',
    'I can give': 'मैं दे सकता हूँ',
    'Withdraw': 'वापस लें',
    'Booked': 'बुक हो गया',
    'Read it in your language': 'अपनी भाषा में पढ़ें',
    'Book home collection': 'घर से सैंपल बुक करें',
    'Prescription': 'पर्चा',
    'Read it in': 'इस भाषा में पढ़ें',
    'Signed prescription': 'हस्ताक्षर वाला पर्चा'
  };

  // Words with a number or a name inside them.
  var RULES = {
    ta: [
      [/^Runs out Sunday$/, 'ஞாயிறு அன்று தீரும்'], [/^Runs out Monday$/, 'திங்கள் அன்று தீரும்'], [/^Runs out Tuesday$/, 'செவ்வாய் அன்று தீரும்'], [/^Runs out Wednesday$/, 'புதன் அன்று தீரும்'], [/^Runs out Thursday$/, 'வியாழன் அன்று தீரும்'], [/^Runs out Friday$/, 'வெள்ளி அன்று தீரும்'], [/^Runs out Saturday$/, 'சனி அன்று தீரும்'], [/^Good morning, (.+)$/i, 'காலை வணக்கம், $1'], [/^Good afternoon, (.+)$/i, 'மதிய வணக்கம், $1'], [/^Good evening, (.+)$/i, 'மாலை வணக்கம், $1'], [/^(\d+) on$/, '$1 இயக்கத்தில்'],
      [/^Morning (\d{1,2}:\d{2})$/, 'காலை $1'], [/^Afternoon (\d{1,2}:\d{2})$/, 'மதியம் $1'], [/^Evening (\d{1,2}:\d{2})$/, 'மாலை $1'],
      [/^Night (\d{1,2}:\d{2})$/, 'இரவு $1'], [/^Week (\d+)$/, 'வாரம் $1'], [/^Welcome, (.+)$/, 'வரவேற்கிறோம், $1'],
      [/^Invite sent to (.+)$/, '$1-க்கு அழைப்பு அனுப்பப்பட்டது'], [/^Sending a code to (.+)$/, '$1-க்குக் குறியீடு அனுப்புகிறோம்'],
      [/^Renews in (\d+) days$/, '$1 நாட்களில் புதுப்பிக்க வேண்டும்'], [/^(\d+) left$/, '$1 மீதம்'],
      [/^(\d+) left today$/, 'இன்று $1 மீதம்'], [/^(.+) \(you\)$/, '$1 (நீங்கள்)'], [/^Step (\d) of (\d)$/i, 'படி $1 / $2'],
      [/^Up to ₹(.+) a family a year$/, 'ஒரு குடும்பத்திற்கு ஆண்டுக்கு ₹$1 வரை'], [/^₹(.+) a family a year$/, 'ஒரு குடும்பத்திற்கு ஆண்டுக்கு ₹$1'],
      [/^₹(.+) a year for the senior, on top of family cover$/, 'மூத்தவருக்கு ஆண்டுக்கு ₹$1, குடும்பக் காப்பீட்டுக்கு மேல்'],
      [/^Lab reports, prescriptions and scans for (.+) appear here, newest first\.$/, '$1-இன் ஆய்வக அறிக்கைகள், மருந்துச் சீட்டுகள், ஸ்கேன்கள் இங்கே, புதியவை முதலில்.'],
      [/^(\d+) of (\d+) doses taken$/, '$2 இல் $1 அளவுகள் எடுக்கப்பட்டன'], [/^Started (.+)$/, '$1 தொடங்கப்பட்டது'], [/^See all (\d+)$/, 'அனைத்து $1-ஐயும் பார்'], [/^(\d+) in range$/, '$1 இயல்பு'], [/^(\d+) results in range$/, '$1 முடிவுகள் இயல்பு'], [/^(\d+) to look at$/, '$1 கவனிக்க வேண்டியவை'], [/^For ([A-Z][A-Za-z]{1,20})$/, '$1-க்கு'], [/^Week (\d+) of pregnancy$/, 'கர்ப்பத்தின் $1-வது வாரம்'], [/^Browse all (\d+) tests$/, 'அனைத்து $1 பரிசோதனைகளையும் பார்'], [/^Next: (.+) at (.+)$/, 'அடுத்து: $1, $2'], [/^Next: (.+)$/, 'அடுத்து: $1'], [/^([A-Za-z0-9 ]{2,30}) is high$/, '$1 அதிகமாக உள்ளது'], [/^([A-Za-z0-9 ]{2,24}) high$/, '$1 அதிகம்'],
      [/^Time to recheck (.+)\?$/, '$1 மீண்டும் பரிசோதிக்க நேரமா?'], [/^It was a little high in the report of (.+)$/, '$1 அறிக்கையில் சற்று அதிகமாக இருந்தது'], [/^Runs out (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|today|tomorrow)$/, '$1 அன்று தீரும்']
    ],
    te: [
      [/^Runs out Sunday$/, 'ఆదివారం అయిపోతుంది'], [/^Runs out Monday$/, 'సోమవారం అయిపోతుంది'], [/^Runs out Tuesday$/, 'మంగళవారం అయిపోతుంది'], [/^Runs out Wednesday$/, 'బుధవారం అయిపోతుంది'], [/^Runs out Thursday$/, 'గురువారం అయిపోతుంది'], [/^Runs out Friday$/, 'శుక్రవారం అయిపోతుంది'], [/^Runs out Saturday$/, 'శనివారం అయిపోతుంది'], [/^Good morning, (.+)$/i, 'శుభోదయం, $1'], [/^Good afternoon, (.+)$/i, 'నమస్కారం, $1'], [/^Good evening, (.+)$/i, 'శుభ సాయంత్రం, $1'], [/^(\d+) on$/, '$1 ఆన్'],
      [/^Morning (\d{1,2}:\d{2})$/, 'ఉదయం $1'], [/^Afternoon (\d{1,2}:\d{2})$/, 'మధ్యాహ్నం $1'], [/^Evening (\d{1,2}:\d{2})$/, 'సాయంత్రం $1'],
      [/^Night (\d{1,2}:\d{2})$/, 'రాత్రి $1'], [/^Week (\d+)$/, 'వారం $1'],
      [/^(\d+) of (\d+) doses taken$/, '$2లో $1 డోసులు తీసుకున్నారు'], [/^Started (.+)$/, '$1 మొదలుపెట్టారు'], [/^See all (\d+)$/, 'మొత్తం $1 చూడండి'], [/^(\d+) in range$/, '$1 సాధారణం'], [/^(\d+) results in range$/, '$1 ఫలితాలు సాధారణం'], [/^(\d+) to look at$/, '$1 గమనించాలి'], [/^For ([A-Z][A-Za-z]{1,20})$/, '$1 కోసం'], [/^Week (\d+) of pregnancy$/, 'గర్భం $1వ వారం'], [/^Browse all (\d+) tests$/, 'మొత్తం $1 టెస్టులు చూడండి'], [/^Next: (.+) at (.+)$/, 'తర్వాత: $1, $2'], [/^Next: (.+)$/, 'తర్వాత: $1'], [/^([A-Za-z0-9 ]{2,30}) is high$/, '$1 ఎక్కువగా ఉంది'], [/^([A-Za-z0-9 ]{2,24}) high$/, '$1 ఎక్కువ'],
      [/^Time to recheck (.+)\?$/, '$1 మళ్ళీ పరీక్షించే సమయమా?'], [/^It was a little high in the report of (.+)$/, '$1 రిపోర్టులో ఇది కొంచెం ఎక్కువగా ఉంది'], [/^Runs out (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|today|tomorrow)$/, '$1 అయిపోతుంది']
    ],
    hi: [
      [/^Runs out Sunday$/, 'रविवार को ख़त्म होगी'], [/^Runs out Monday$/, 'सोमवार को ख़त्म होगी'], [/^Runs out Tuesday$/, 'मंगलवार को ख़त्म होगी'], [/^Runs out Wednesday$/, 'बुधवार को ख़त्म होगी'], [/^Runs out Thursday$/, 'गुरुवार को ख़त्म होगी'], [/^Runs out Friday$/, 'शुक्रवार को ख़त्म होगी'], [/^Runs out Saturday$/, 'शनिवार को ख़त्म होगी'], [/^Good morning, (.+)$/i, 'सुप्रभात, $1'], [/^Good afternoon, (.+)$/i, 'नमस्ते, $1'], [/^Good evening, (.+)$/i, 'शुभ संध्या, $1'], [/^(\d+) on$/, '$1 चालू'],
      [/^Morning (\d{1,2}:\d{2})$/, 'सुबह $1'], [/^Afternoon (\d{1,2}:\d{2})$/, 'दोपहर $1'], [/^Evening (\d{1,2}:\d{2})$/, 'शाम $1'],
      [/^Night (\d{1,2}:\d{2})$/, 'रात $1'], [/^Week (\d+)$/, 'हफ़्ता $1'], [/^Welcome, (.+)$/, 'स्वागत है, $1'],
      [/^Invite sent to (.+)$/, '$1 को न्योता भेज दिया'], [/^Sending a code to (.+)$/, '$1 पर कोड भेज रहे हैं'],
      [/^Renews in (\d+) days$/, '$1 दिन में रिन्यू करना है'], [/^(\d+) left$/, '$1 बचे'],
      [/^(\d+) left today$/, 'आज $1 बचे'], [/^(.+) \(you\)$/, '$1 (आप)'], [/^Step (\d) of (\d)$/i, 'चरण $1 / $2'],
      [/^Up to ₹(.+) a family a year$/, 'हर परिवार को साल में ₹$1 तक'], [/^₹(.+) a family a year$/, 'हर परिवार को साल में ₹$1'],
      [/^₹(.+) a year for the senior, on top of family cover$/, 'बुज़ुर्ग के लिए साल में ₹$1, परिवार के बीमे के ऊपर'],
      [/^Lab reports, prescriptions and scans for (.+) appear here, newest first\.$/, '$1 की लैब रिपोर्ट, पर्चे और स्कैन यहाँ दिखते हैं, नए सबसे ऊपर।'],
      [/^(\d+) of (\d+) doses taken$/, '$2 में से $1 ख़ुराक ली गई'], [/^Started (.+)$/, '$1 शुरू की'], [/^See all (\d+)$/, 'सभी $1 देखें'], [/^(\d+) in range$/, '$1 सामान्य'], [/^(\d+) results in range$/, '$1 नतीजे सामान्य'], [/^(\d+) to look at$/, '$1 पर ध्यान दें'], [/^For ([A-Z][A-Za-z]{1,20})$/, '$1 के लिए'], [/^Week (\d+) of pregnancy$/, 'गर्भावस्था का हफ़्ता $1'], [/^Browse all (\d+) tests$/, 'सभी $1 टेस्ट देखें'], [/^Next: (.+) at (.+)$/, 'अगली: $1, $2 बजे'], [/^Next: (.+)$/, 'अगली: $1'], [/^([A-Za-z0-9 ]{2,30}) is high$/, '$1 ज़्यादा है'], [/^([A-Za-z0-9 ]{2,24}) high$/, '$1 ज़्यादा'],
      [/^Time to recheck (.+)\?$/, '$1 की दोबारा जाँच का समय?'], [/^It was a little high in the report of (.+)$/, '$1 की रिपोर्ट में यह थोड़ा ज़्यादा था'], [/^Runs out (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|today|tomorrow)$/, '$1 को ख़त्म होगी']
    ]
  };
  // First aid and insulin sites (Nov 2026): added only where the table has no line of its own yet.
  (function (add) { add(TA, {"First aid": "முதலுதவி", "Calm, simple steps until help arrives.": "உதவி வரும் வரை அமைதியான, எளிய படிகள்.", "Serious? Call 108 first": "தீவிரமா? முதலில் 108-ஐ அழையுங்கள்", "Then follow the steps below": "பிறகு கீழே உள்ள படிகளைப் பின்பற்றுங்கள்", "Call 108": "108-ஐ அழை", "Call 108 ambulance": "108 ஆம்புலன்ஸை அழை", "Throat": "தொண்டை", "Centre of chest": "மார்பின் நடுவில்", "MORE": "மேலும்", "DO THIS": "இதைச் செய்யுங்கள்", "DO NOT": "செய்யக்கூடாதவை", "Standard first-aid steps for adults. They don’t replace trained help: always call 108 for an emergency.": "பெரியவர்களுக்கான வழக்கமான முதலுதவிப் படிகள். இவை பயிற்சி பெற்றவர்களின் உதவிக்கு மாற்று அல்ல: அவசர நிலையில் எப்போதும் 108-ஐ அழையுங்கள்.", "General first aid. A doctor or the 108 call-taker may tell you something different for this person; follow them.": "பொதுவான முதலுதவி. இந்த நபருக்கு மருத்துவர் அல்லது 108 அழைப்பாளர் வேறு ஏதாவது சொல்லலாம்; அவர்களைப் பின்பற்றுங்கள்.", "First aid steps": "முதலுதவிப் படிகள்", "CPR, choking, recovery position, bleeding": "CPR, மூச்சுத் திணறல், மீட்பு நிலை, இரத்தப்போக்கு", "CPR and step-by-step help": "CPR மற்றும் படிப்படியான உதவி", "Shown on the body: CPR, choking, recovery position, bleeding": "உடலில் காட்டப்படும்: CPR, மூச்சுத் திணறல், மீட்பு நிலை, இரத்தப்போக்கு", "Start the beat": "தாளத்தைத் தொடங்கு", "Stop the beat": "தாளத்தை நிறுத்து", "Read aloud": "சத்தமாகப் படி", "Reading aloud": "சத்தமாகப் படிக்கிறது", "Next": "அடுத்து", "Back": "பின்", "Done": "முடிந்தது", "Back to first aid": "முதலுதவிக்குத் திரும்பு", "Snake bite": "பாம்புக் கடி", "Keep still, go to hospital": "அசையாமல் இருங்கள், மருத்துவமனைக்குச் செல்லுங்கள்", "Call 108 or 112. Go to the nearest hospital that has anti-snake venom. Most government hospitals do.": "108 அல்லது 112-ஐ அழையுங்கள். பாம்பு விஷ முறிவு மருந்து உள்ள அருகிலுள்ள மருத்துவமனைக்குச் செல்லுங்கள். பெரும்பாலான அரசு மருத்துவமனைகளில் உள்ளது.", "Keep the person calm and still. Movement spreads venom faster.": "அவரை அமைதியாகவும் அசையாமலும் வைத்திருங்கள். அசைவு விஷத்தை வேகமாகப் பரப்பும்.", "Keep the bitten arm or leg still and at heart level. Remove rings, watches and tight clothes near the bite.": "கடித்த கை அல்லது காலை அசையாமல் இதய உயரத்தில் வையுங்கள். கடியின் அருகில் உள்ள மோதிரம், கடிகாரம், இறுக்கமான உடைகளை அகற்றுங்கள்.", "Note the time of the bite. A photo of the snake helps, but do not try to catch it.": "கடித்த நேரத்தைக் குறித்துக் கொள்ளுங்கள். பாம்பின் புகைப்படம் உதவும், ஆனால் அதைப் பிடிக்க முயற்சிக்காதீர்கள்.", "Do not cut the wound, suck it, or put ice or chemicals on it.": "காயத்தை வெட்டவோ, உறிஞ்சவோ, அதன் மீது பனிக்கட்டி அல்லது ரசாயனம் வைக்கவோ வேண்டாம்.", "Do not tie a tight tourniquet.": "இறுக்கமாகக் கட்டுப் போட வேண்டாம்.", "Do not give alcohol, painkillers or herbal remedies. Do not wait to see if symptoms come.": "மது, வலி நிவாரணி அல்லது மூலிகை மருந்துகள் கொடுக்க வேண்டாம். அறிகுறிகள் வருகிறதா என்று காத்திருக்க வேண்டாம்.", "Poisoning": "விஷம்", "Medicines, pesticide, kerosene": "மருந்துகள், பூச்சிக்கொல்லி, மண்ணெண்ணெய்", "Call 108 or 112 now. Say what was taken, how much and when, if you know.": "இப்போதே 108 அல்லது 112-ஐ அழையுங்கள். என்ன, எவ்வளவு, எப்போது உட்கொண்டார் என்று தெரிந்தால் சொல்லுங்கள்.", "Take the bottle, packet or strip with you to the hospital.": "பாட்டில், பாக்கெட் அல்லது மாத்திரை அட்டையை மருத்துவமனைக்கு எடுத்துச் செல்லுங்கள்.", "If it is on the skin or clothes (pesticide), remove the clothes and wash the skin with plenty of water.": "தோலில் அல்லது உடையில் பட்டிருந்தால் (பூச்சிக்கொல்லி), உடையை அகற்றி நிறைய தண்ணீரில் தோலைக் கழுவுங்கள்.", "If it got in the eyes, rinse with clean running water for 15 minutes.": "கண்ணில் பட்டிருந்தால், 15 நிமிடம் சுத்தமான ஓடும் நீரில் கழுவுங்கள்.", "If they are unconscious but breathing, lay them on their side.": "சுயநினைவு இல்லாமல் மூச்சு விட்டால், பக்கவாட்டில் படுக்க வையுங்கள்.", "Do not make them vomit, unless a doctor tells you to.": "மருத்துவர் சொன்னால் தவிர வாந்தி எடுக்க வைக்க வேண்டாம்.", "Do not give milk, salt water or oil.": "பால், உப்புத் தண்ணீர் அல்லது எண்ணெய் கொடுக்க வேண்டாம்.", "Kerosene, petrol or acid: never make them vomit.": "மண்ணெண்ணெய், பெட்ரோல் அல்லது அமிலம்: ஒருபோதும் வாந்தி எடுக்க வைக்க வேண்டாம்.", "Burns": "தீக்காயம்", "Cool water for 20 minutes": "20 நிமிடம் குளிர்ந்த நீர்", "Cool the burn under cool running water for 20 minutes.": "காயத்தை 20 நிமிடம் குளிர்ந்த ஓடும் நீரில் குளிர வையுங்கள்.", "Remove rings and tight clothes near the burn, unless stuck to the skin.": "தோலில் ஒட்டியிருந்தால் தவிர, காயத்தின் அருகே உள்ள மோதிரம், இறுக்கமான உடைகளை அகற்றுங்கள்.", "Cover loosely with cling film or a clean cloth.": "கிளிங் ஃபிலிம் அல்லது சுத்தமான துணியால் தளர்வாக மூடுங்கள்.", "Call 108 for large burns, burns on the face, hands or private parts, or any burn on a child.": "பெரிய தீக்காயம், முகம், கை அல்லது அந்தரங்கப் பகுதிகளில் காயம், அல்லது குழந்தைக்கு எந்தக் காயமாக இருந்தாலும் 108-ஐ அழையுங்கள்.", "Do not put ice, toothpaste, oil or butter on it.": "பனிக்கட்டி, பற்பசை, எண்ணெய் அல்லது வெண்ணெய் தடவ வேண்டாம்.", "Do not burst blisters.": "கொப்புளங்களை உடைக்க வேண்டாம்.", "Choking": "மூச்சுத் திணறல்", "Adult, child or baby": "பெரியவர், குழந்தை அல்லது கைக்குழந்தை", "If they can cough, let them keep coughing.": "இருமல் முடிந்தால், இருமிக் கொண்டே இருக்கட்டும்.", "Adult or child: give up to 5 firm back blows between the shoulder blades, then up to 5 abdominal thrusts. Repeat.": "பெரியவர் அல்லது குழந்தை: தோள்பட்டைகளுக்கு இடையில் 5 முறை வரை உறுதியாகத் தட்டுங்கள், பிறகு 5 முறை வரை வயிற்றில் அழுத்துங்கள். மீண்டும் செய்யுங்கள்.", "Baby under 1: lay face down along your forearm, give 5 back blows, then turn over and give 5 chest thrusts with two fingers. Repeat.": "1 வயதுக்குட்பட்ட குழந்தை: உங்கள் முன்கையில் முகம் கீழே படுக்க வைத்து முதுகில் 5 முறை தட்டுங்கள், பிறகு திருப்பி இரண்டு விரல்களால் மார்பில் 5 முறை அழுத்துங்கள். மீண்டும் செய்யுங்கள்.", "If they stop responding, call 108 or 112 and start CPR.": "பதில் தரவில்லை என்றால், 108 அல்லது 112-ஐ அழைத்து CPR தொடங்குங்கள்.", "Do not put your fingers in the mouth to search for the object.": "பொருளைத் தேட வாய்க்குள் விரலை விட வேண்டாம்.", "Fits (seizure)": "வலிப்பு", "Keep them safe, time it": "பாதுகாப்பாக வையுங்கள், நேரத்தைக் கணியுங்கள்", "Move hard or sharp things away. Put something soft under the head.": "கடினமான அல்லது கூர்மையான பொருட்களை அகற்றுங்கள். தலைக்குக் கீழ் மென்மையான ஒன்றை வையுங்கள்.", "Time the fit. Call 108 if it lasts more than 5 minutes, or if it is their first fit.": "வலிப்பின் நேரத்தைக் கணியுங்கள். 5 நிமிடத்திற்கு மேல் நீடித்தால், அல்லது முதல் முறை என்றால் 108-ஐ அழையுங்கள்.", "When it stops, turn them on their side and stay with them.": "நின்ற பிறகு, பக்கவாட்டில் திருப்பி அவருடன் இருங்கள்.", "Do not hold them down.": "அவரை அழுத்திப் பிடிக்க வேண்டாம்.", "Do not put anything in the mouth.": "வாயில் எதையும் வைக்க வேண்டாம்.", "CPR": "CPR", "Not breathing, not responding": "மூச்சு இல்லை, பதில் இல்லை", "Heel of your hand": "உங்கள் உள்ளங்கையின் அடிப்பகுதி", "Lower half of the breastbone": "மார்பெலும்பின் கீழ்ப் பாதி", "Check and call": "சரிபார்த்து அழையுங்கள்", "Tap their shoulders and shout. If they don’t respond and aren’t breathing normally, call 108 and put the phone on speaker.": "தோள்களைத் தட்டி சத்தமாகக் கூப்பிடுங்கள். பதில் இல்லாமல், சாதாரணமாக மூச்சு விடவில்லை என்றால், 108-ஐ அழைத்து ஃபோனை ஸ்பீக்கரில் வையுங்கள்.", "Push hard and fast": "வலுவாகவும் வேகமாகவும் அழுத்துங்கள்", "One hand on top of the other, arms straight, on the red spot. Press down about 5–6 cm, then let the chest rise fully. 100–120 pushes a minute: follow the beat.": "ஒரு கையின் மேல் மற்றொரு கை, கைகள் நேராக, சிவப்புப் புள்ளியில். சுமார் 5–6 செ.மீ கீழே அழுத்தி, பிறகு மார்பு முழுமையாக மேலே வரட்டும். நிமிடத்திற்கு 100–120 அழுத்தங்கள்: தாளத்தைப் பின்பற்றுங்கள்.", "Keep going": "தொடர்ந்து செய்யுங்கள்", "Don’t stop. If someone can take over, swap every 2 minutes. If you’re trained, give 2 breaths after every 30 pushes; if not, keep pushing.": "நிறுத்த வேண்டாம். வேறொருவர் உதவ முடிந்தால், 2 நிமிடத்திற்கு ஒருமுறை மாறிக்கொள்ளுங்கள். பயிற்சி இருந்தால், 30 அழுத்தங்களுக்குப் பிறகு 2 மூச்சு கொடுங்கள்; இல்லையென்றால், அழுத்திக் கொண்டே இருங்கள்.", "Until help arrives": "உதவி வரும் வரை", "Carry on until they breathe normally, the ambulance team takes over, or you can’t continue. If they start breathing, use the recovery position.": "அவர் சாதாரணமாக மூச்சு விடும் வரை, ஆம்புலன்ஸ் குழு பொறுப்பேற்கும் வரை, அல்லது உங்களால் தொடர முடியாத வரை செய்யுங்கள். மூச்சு வந்தால், மீட்பு நிலையில் வையுங்கள்.", "Can’t speak, cough or breathe": "பேச, இருமல், மூச்சு விட முடியவில்லை", "Fist goes here": "முஷ்டி இங்கே", "Just above the navel": "தொப்புளுக்குச் சற்று மேலே", "Ask: are you choking?": "கேளுங்கள்: மூச்சுத் திணறுகிறதா?", "If they can cough, let them keep coughing. Stay with them.": "இருமல் முடிந்தால், இருமிக் கொண்டே இருக்கட்டும். அவருடன் இருங்கள்.", "5 back blows": "முதுகில் 5 தட்டுகள்", "Help them lean forward. Give up to 5 firm blows between the shoulder blades with the heel of your hand.": "முன்னோக்கிச் சாய உதவுங்கள். உள்ளங்கையின் அடிப்பகுதியால் தோள்பட்டைகளுக்கு இடையில் 5 முறை வரை உறுதியாகத் தட்டுங்கள்.", "5 tummy thrusts": "வயிற்றில் 5 அழுத்தங்கள்", "Stand behind them. Make a fist just above the navel, hold it with your other hand and pull sharply inwards and upwards. For a pregnant woman, put your hands on the lower chest instead.": "அவருக்குப் பின்னால் நில்லுங்கள். தொப்புளுக்குச் சற்று மேலே முஷ்டி வைத்து, மற்றொரு கையால் பிடித்து உள்ளேயும் மேலேயும் வேகமாக இழுங்கள். கர்ப்பிணிப் பெண் என்றால், மார்பின் கீழ்ப் பகுதியில் கைகளை வையுங்கள்.", "Repeat until it clears": "வெளியே வரும் வரை மீண்டும் செய்யுங்கள்", "Keep swapping 5 back blows and 5 thrusts. If they stop responding, call 108 and start CPR.": "5 முதுகுத் தட்டுகளையும் 5 அழுத்தங்களையும் மாறி மாறிச் செய்யுங்கள். பதில் தரவில்லை என்றால், 108-ஐ அழைத்து CPR தொடங்குங்கள்.", "Baby under 1: lay face down along your forearm, give 5 back blows, then turn over and give 5 chest thrusts with two fingers. Repeat. Never put your fingers in the mouth to search for the object.": "1 வயதுக்குட்பட்ட குழந்தை: உங்கள் முன்கையில் முகம் கீழே படுக்க வைத்து முதுகில் 5 முறை தட்டுங்கள், பிறகு திருப்பி இரண்டு விரல்களால் மார்பில் 5 முறை அழுத்துங்கள். மீண்டும் செய்யுங்கள். பொருளைத் தேட வாய்க்குள் ஒருபோதும் விரலை விட வேண்டாம்.", "Recovery position": "மீட்பு நிலை", "Breathing but not awake": "மூச்சு உள்ளது, சுயநினைவு இல்லை", "Keep the airway open": "மூச்சுப் பாதையைத் திறந்து வையுங்கள்", "Head tilted back": "தலை பின்னால் சாய்ந்து", "Check breathing": "மூச்சைச் சரிபாருங்கள்", "Kneel beside them. Look, listen and feel for normal breathing. Not breathing? Start CPR instead.": "அவர் அருகில் மண்டியிடுங்கள். சாதாரண மூச்சைப் பாருங்கள், கேளுங்கள், உணருங்கள். மூச்சு இல்லையா? அதற்குப் பதிலாக CPR தொடங்குங்கள்.", "Arms": "கைகள்", "Put the arm nearest you at a right angle. Bring the far arm across the chest, back of the hand against their near cheek.": "உங்களுக்கு அருகில் உள்ள கையை செங்கோணத்தில் வையுங்கள். தொலைவில் உள்ள கையை மார்பின் குறுக்கே கொண்டு வந்து, புறங்கையை அருகிலுள்ள கன்னத்தில் வையுங்கள்.", "Roll": "திருப்புங்கள்", "Bend the far knee up, then pull it towards you so they roll onto their side.": "தொலைவில் உள்ள முழங்காலை மடக்கி, உங்களை நோக்கி இழுத்து பக்கவாட்டில் திருப்புங்கள்.", "Stay with them": "அவருடன் இருங்கள்", "Tilt the head back so the airway stays open. Keep checking their breathing until help arrives.": "மூச்சுப் பாதை திறந்திருக்கத் தலையைப் பின்னால் சாய்யுங்கள். உதவி வரும் வரை மூச்சைச் சரிபார்த்துக் கொண்டே இருங்கள்.", "Heavy bleeding": "அதிக இரத்தப்போக்கு", "Press firmly, keep pressing": "உறுதியாக அழுத்துங்கள், அழுத்திக் கொண்டே இருங்கள்", "Press on the wound": "காயத்தின் மீது அழுத்துங்கள்", "With a clean cloth": "சுத்தமான துணியால்", "For heavy bleeding, call first, then press.": "அதிக இரத்தப்போக்கு என்றால், முதலில் அழைத்து, பிறகு அழுத்துங்கள்.", "Press firmly": "உறுதியாக அழுத்துங்கள்", "Press on the wound with a clean cloth, or your hand if there’s nothing else.": "சுத்தமான துணியால், அல்லது வேறு எதுவும் இல்லையென்றால் உங்கள் கையால் காயத்தின் மீது அழுத்துங்கள்.", "Keep pressing": "அழுத்திக் கொண்டே இருங்கள்", "Press for at least 10 minutes without lifting to check. If blood soaks through, add more cloth on top.": "சரிபார்க்கத் தூக்காமல் குறைந்தது 10 நிமிடம் அழுத்துங்கள். இரத்தம் ஊறி வந்தால், மேலே இன்னும் துணி வையுங்கள்.", "Keep them still": "அசையாமல் வையுங்கள்", "Raise the injured part if you can. Keep them lying down and warm until help arrives.": "முடிந்தால் காயமடைந்த பகுதியை உயர்த்துங்கள். உதவி வரும் வரை படுக்க வைத்து கதகதப்பாக வையுங்கள்.", "Insulin": "இன்சுலின்", "Insulin sites": "இன்சுலின் ஊசி இடங்கள்", "Next:": "அடுத்து:", "Used": "பயன்படுத்தியது", "Where next": "அடுத்து எங்கே", "Belly, right side": "வயிறு, வலது பக்கம்", "Belly, left side": "வயிறு, இடது பக்கம்", "Right thigh": "வலது தொடை", "Left thigh": "இடது தொடை", "Right upper arm": "வலது மேல் கை", "Left upper arm": "இடது மேல் கை", "outer front": "வெளிப்புற முன்பகுதி", "back of the arm": "கையின் பின்பகுதி", "in the last 2 days": "கடந்த 2 நாட்களில்", "Used recently": "சமீபத்தில் பயன்படுத்தியது", "Suggested": "பரிந்துரை", "Rested": "ஓய்வில்", "All insulin doses logged today": "இன்றைய இன்சுலின் அளவுகள் அனைத்தும் பதிவாகின", "Dose as prescribed": "மருந்துச்சீட்டின்படி அளவு", "Log dose": "அளவைப் பதிவு செய்", "Log a dose": "அளவைப் பதிவு செய்யுங்கள்", "Use a new spot about a finger’s width from the last one.": "கடைசி இடத்திலிருந்து ஒரு விரல் அகல தூரத்தில் புதிய இடத்தைப் பயன்படுத்துங்கள்.", "Keep about 5 cm away from the navel.": "தொப்புளிலிருந்து சுமார் 5 செ.மீ தள்ளி இருங்கள்.", "Skip any lumps, bruises or scars.": "கட்டிகள், சிராய்ப்புகள், தழும்புகள் உள்ள இடங்களைத் தவிருங்கள்.", "LAST DOSES": "கடைசி அளவுகள்", "General guidance on rotating sites. Your doctor or diabetes educator may advise differently: follow them.": "இடங்களை மாற்றுவது பற்றிய பொதுவான வழிகாட்டுதல். உங்கள் மருத்துவர் அல்லது நீரிழிவுக் கல்வியாளர் வேறு விதமாக அறிவுறுத்தலாம்: அவர்களைப் பின்பற்றுங்கள்.", "Tap the spot you used. The suggested one is already chosen.": "நீங்கள் பயன்படுத்திய இடத்தைத் தட்டுங்கள். பரிந்துரைத்த இடம் ஏற்கனவே தேர்வாகியுள்ளது.", "Belly": "வயிறு", "Thighs": "தொடைகள்", "Their right": "அவரின் வலது", "Their left": "அவரின் இடது", "Spot": "இடம்", "Time": "நேரம்", "Now": "இப்போது", "Tap a spot": "ஒரு இடத்தைத் தட்டுங்கள்", "Save dose": "அளவைச் சேமி", "Body with injection areas": "ஊசி போடும் பகுதிகளுடன் உடல்"}); add(TE, {"First aid": "ప్రథమ చికిత్స", "Calm, simple steps until help arrives.": "సహాయం వచ్చే వరకు ప్రశాంతమైన, సులభమైన దశలు.", "Serious? Call 108 first": "తీవ్రంగా ఉందా? ముందు 108కి కాల్ చేయండి", "Then follow the steps below": "తర్వాత కింది దశలను పాటించండి", "Call 108": "108కి కాల్ చేయండి", "Call 108 ambulance": "108 అంబులెన్స్‌కి కాల్ చేయండి", "Throat": "గొంతు", "Centre of chest": "ఛాతీ మధ్యలో", "MORE": "మరిన్ని", "DO THIS": "ఇలా చేయండి", "DO NOT": "ఇలా చేయకండి", "Standard first-aid steps for adults. They don’t replace trained help: always call 108 for an emergency.": "పెద్దలకు సాధారణ ప్రథమ చికిత్స దశలు. ఇవి శిక్షణ పొందినవారి సహాయానికి బదులు కావు: అత్యవసరంలో ఎప్పుడూ 108కి కాల్ చేయండి.", "General first aid. A doctor or the 108 call-taker may tell you something different for this person; follow them.": "సాధారణ ప్రథమ చికిత్స. ఈ వ్యక్తి కోసం డాక్టర్ లేదా 108 సిబ్బంది వేరేలా చెప్పవచ్చు; వారిని పాటించండి.", "First aid steps": "ప్రథమ చికిత్స దశలు", "CPR, choking, recovery position, bleeding": "CPR, గొంతులో ఇరుక్కోవడం, రికవరీ పొజిషన్, రక్తస్రావం", "CPR and step-by-step help": "CPR మరియు దశలవారీ సహాయం", "Shown on the body: CPR, choking, recovery position, bleeding": "శరీరంపై చూపిస్తాం: CPR, గొంతులో ఇరుక్కోవడం, రికవరీ పొజిషన్, రక్తస్రావం", "Start the beat": "బీట్ ప్రారంభించండి", "Stop the beat": "బీట్ ఆపండి", "Read aloud": "బిగ్గరగా చదవండి", "Reading aloud": "బిగ్గరగా చదువుతోంది", "Next": "తర్వాత", "Back": "వెనుకకు", "Done": "పూర్తి", "Back to first aid": "ప్రథమ చికిత్సకు తిరిగి", "Snake bite": "పాము కాటు", "Keep still, go to hospital": "కదలకుండా ఉంచి, ఆసుపత్రికి వెళ్లండి", "Call 108 or 112. Go to the nearest hospital that has anti-snake venom. Most government hospitals do.": "108 లేదా 112కి కాల్ చేయండి. పాము విష విరుగుడు ఉన్న దగ్గరి ఆసుపత్రికి వెళ్లండి. చాలా ప్రభుత్వ ఆసుపత్రుల్లో ఉంటుంది.", "Keep the person calm and still. Movement spreads venom faster.": "వ్యక్తిని ప్రశాంతంగా, కదలకుండా ఉంచండి. కదిలితే విషం త్వరగా వ్యాపిస్తుంది.", "Keep the bitten arm or leg still and at heart level. Remove rings, watches and tight clothes near the bite.": "కాటు పడిన చేయి లేదా కాలిని కదలకుండా గుండె ఎత్తులో ఉంచండి. కాటు దగ్గర ఉంగరాలు, వాచీలు, బిగుతు బట్టలు తీసేయండి.", "Note the time of the bite. A photo of the snake helps, but do not try to catch it.": "కాటు వేసిన సమయాన్ని గుర్తుంచుకోండి. పాము ఫోటో ఉపయోగపడుతుంది, కానీ దాన్ని పట్టుకోడానికి ప్రయత్నించకండి.", "Do not cut the wound, suck it, or put ice or chemicals on it.": "గాయాన్ని కోయవద్దు, పీల్చవద్దు, దానిపై మంచు లేదా రసాయనాలు పెట్టవద్దు.", "Do not tie a tight tourniquet.": "బిగుతుగా కట్టు కట్టవద్దు.", "Do not give alcohol, painkillers or herbal remedies. Do not wait to see if symptoms come.": "మద్యం, నొప్పి మాత్రలు లేదా మూలికా మందులు ఇవ్వవద్దు. లక్షణాలు వస్తాయేమో అని ఎదురుచూడవద్దు.", "Poisoning": "విషప్రయోగం", "Medicines, pesticide, kerosene": "మందులు, పురుగుమందు, కిరోసిన్", "Call 108 or 112 now. Say what was taken, how much and when, if you know.": "ఇప్పుడే 108 లేదా 112కి కాల్ చేయండి. ఏమి, ఎంత, ఎప్పుడు తీసుకున్నారో తెలిస్తే చెప్పండి.", "Take the bottle, packet or strip with you to the hospital.": "సీసా, ప్యాకెట్ లేదా స్ట్రిప్‌ను ఆసుపత్రికి తీసుకెళ్లండి.", "If it is on the skin or clothes (pesticide), remove the clothes and wash the skin with plenty of water.": "చర్మం లేదా బట్టలపై పడితే (పురుగుమందు), బట్టలు తీసి చర్మాన్ని ఎక్కువ నీటితో కడగండి.", "If it got in the eyes, rinse with clean running water for 15 minutes.": "కళ్లలో పడితే, 15 నిమిషాలు శుభ్రమైన పారే నీటితో కడగండి.", "If they are unconscious but breathing, lay them on their side.": "స్పృహ లేకుండా శ్వాస తీసుకుంటుంటే, పక్కకు పడుకోబెట్టండి.", "Do not make them vomit, unless a doctor tells you to.": "డాక్టర్ చెబితే తప్ప వాంతి చేయించవద్దు.", "Do not give milk, salt water or oil.": "పాలు, ఉప్పు నీరు లేదా నూనె ఇవ్వవద్దు.", "Kerosene, petrol or acid: never make them vomit.": "కిరోసిన్, పెట్రోల్ లేదా యాసిడ్: ఎప్పుడూ వాంతి చేయించవద్దు.", "Burns": "కాలిన గాయాలు", "Cool water for 20 minutes": "20 నిమిషాలు చల్లని నీరు", "Cool the burn under cool running water for 20 minutes.": "కాలిన చోటును 20 నిమిషాలు చల్లని పారే నీటి కింద ఉంచండి.", "Remove rings and tight clothes near the burn, unless stuck to the skin.": "చర్మానికి అంటుకోకపోతే, కాలిన చోటు దగ్గర ఉంగరాలు, బిగుతు బట్టలు తీసేయండి.", "Cover loosely with cling film or a clean cloth.": "క్లింగ్ ఫిల్మ్ లేదా శుభ్రమైన గుడ్డతో వదులుగా కప్పండి.", "Call 108 for large burns, burns on the face, hands or private parts, or any burn on a child.": "పెద్ద కాలిన గాయాలు, ముఖం, చేతులు లేదా గోప్య భాగాలపై గాయాలు, లేదా పిల్లలకు ఏ కాలిన గాయమైనా 108కి కాల్ చేయండి.", "Do not put ice, toothpaste, oil or butter on it.": "మంచు, టూత్‌పేస్ట్, నూనె లేదా వెన్న రాయవద్దు.", "Do not burst blisters.": "బొబ్బలను పగలగొట్టవద్దు.", "Choking": "గొంతులో ఇరుక్కోవడం", "Adult, child or baby": "పెద్దవారు, పిల్లలు లేదా పసిపిల్లలు", "If they can cough, let them keep coughing.": "దగ్గగలిగితే, దగ్గుతూనే ఉండనివ్వండి.", "Adult or child: give up to 5 firm back blows between the shoulder blades, then up to 5 abdominal thrusts. Repeat.": "పెద్దవారు లేదా పిల్లలు: భుజాల మధ్య 5 సార్ల వరకు గట్టిగా కొట్టండి, తర్వాత 5 సార్ల వరకు పొట్టపై నొక్కండి. మళ్లీ చేయండి.", "Baby under 1: lay face down along your forearm, give 5 back blows, then turn over and give 5 chest thrusts with two fingers. Repeat.": "1 ఏళ్లలోపు పసిపిల్లలు: మీ ముంజేతిపై బోర్లా పడుకోబెట్టి వీపుపై 5 సార్లు కొట్టండి, తర్వాత తిప్పి రెండు వేళ్లతో ఛాతీపై 5 సార్లు నొక్కండి. మళ్లీ చేయండి.", "If they stop responding, call 108 or 112 and start CPR.": "స్పందించకపోతే, 108 లేదా 112కి కాల్ చేసి CPR ప్రారంభించండి.", "Do not put your fingers in the mouth to search for the object.": "వస్తువును వెతకడానికి నోటిలో వేళ్లు పెట్టవద్దు.", "Fits (seizure)": "మూర్ఛ (ఫిట్స్)", "Keep them safe, time it": "సురక్షితంగా ఉంచండి, సమయం చూడండి", "Move hard or sharp things away. Put something soft under the head.": "గట్టి లేదా పదునైన వస్తువులను దూరంగా జరపండి. తల కింద మెత్తనిది పెట్టండి.", "Time the fit. Call 108 if it lasts more than 5 minutes, or if it is their first fit.": "మూర్ఛ ఎంతసేపు ఉందో చూడండి. 5 నిమిషాలకు మించితే, లేదా ఇది మొదటిసారి అయితే 108కి కాల్ చేయండి.", "When it stops, turn them on their side and stay with them.": "ఆగిన తర్వాత, పక్కకు తిప్పి వారి దగ్గరే ఉండండి.", "Do not hold them down.": "వారిని గట్టిగా పట్టుకోవద్దు.", "Do not put anything in the mouth.": "నోటిలో ఏమీ పెట్టవద్దు.", "CPR": "CPR", "Not breathing, not responding": "శ్వాస లేదు, స్పందన లేదు", "Heel of your hand": "మీ అరచేతి కింది భాగం", "Lower half of the breastbone": "ఛాతీ ఎముక కింది సగం", "Check and call": "చూసి కాల్ చేయండి", "Tap their shoulders and shout. If they don’t respond and aren’t breathing normally, call 108 and put the phone on speaker.": "భుజాలు తట్టి గట్టిగా పిలవండి. స్పందించకపోతే, సాధారణంగా శ్వాస తీసుకోకపోతే, 108కి కాల్ చేసి ఫోన్‌ను స్పీకర్‌లో పెట్టండి.", "Push hard and fast": "గట్టిగా, వేగంగా నొక్కండి", "One hand on top of the other, arms straight, on the red spot. Press down about 5–6 cm, then let the chest rise fully. 100–120 pushes a minute: follow the beat.": "ఒక చేయి మీద మరో చేయి, చేతులు నిటారుగా, ఎర్రని చుక్క మీద. సుమారు 5–6 సెం.మీ. కిందకు నొక్కి, తర్వాత ఛాతీ పూర్తిగా పైకి రానివ్వండి. నిమిషానికి 100–120 సార్లు: బీట్‌ను అనుసరించండి.", "Keep going": "ఆపకుండా కొనసాగించండి", "Don’t stop. If someone can take over, swap every 2 minutes. If you’re trained, give 2 breaths after every 30 pushes; if not, keep pushing.": "ఆపకండి. ఎవరైనా సహాయం చేయగలిగితే, ప్రతి 2 నిమిషాలకు మారండి. శిక్షణ ఉంటే, ప్రతి 30 సార్లు నొక్కిన తర్వాత 2 శ్వాసలు ఇవ్వండి; లేకపోతే నొక్కుతూనే ఉండండి.", "Until help arrives": "సహాయం వచ్చే వరకు", "Carry on until they breathe normally, the ambulance team takes over, or you can’t continue. If they start breathing, use the recovery position.": "వారు సాధారణంగా శ్వాస తీసుకునే వరకు, అంబులెన్స్ సిబ్బంది తీసుకునే వరకు, లేదా మీరు చేయలేనంత వరకు కొనసాగించండి. శ్వాస మొదలైతే, రికవరీ పొజిషన్‌లో ఉంచండి.", "Can’t speak, cough or breathe": "మాట్లాడలేరు, దగ్గలేరు, శ్వాస తీసుకోలేరు", "Fist goes here": "పిడికిలి ఇక్కడ", "Just above the navel": "బొడ్డుకు కొంచెం పైన", "Ask: are you choking?": "అడగండి: గొంతులో ఇరుక్కుందా?", "If they can cough, let them keep coughing. Stay with them.": "దగ్గగలిగితే, దగ్గుతూనే ఉండనివ్వండి. వారి దగ్గరే ఉండండి.", "5 back blows": "వీపుపై 5 దెబ్బలు", "Help them lean forward. Give up to 5 firm blows between the shoulder blades with the heel of your hand.": "ముందుకు వంగేలా సహాయం చేయండి. అరచేతి కింది భాగంతో భుజాల మధ్య 5 సార్ల వరకు గట్టిగా కొట్టండి.", "5 tummy thrusts": "పొట్టపై 5 నొక్కులు", "Stand behind them. Make a fist just above the navel, hold it with your other hand and pull sharply inwards and upwards. For a pregnant woman, put your hands on the lower chest instead.": "వారి వెనుక నిలబడండి. బొడ్డుకు కొంచెం పైన పిడికిలి పెట్టి, మరో చేత్తో పట్టుకుని లోపలికి, పైకి వేగంగా లాగండి. గర్భిణి అయితే, బదులుగా ఛాతీ కింది భాగంపై చేతులు పెట్టండి.", "Repeat until it clears": "బయటకు వచ్చే వరకు మళ్లీ చేయండి", "Keep swapping 5 back blows and 5 thrusts. If they stop responding, call 108 and start CPR.": "5 వీపు దెబ్బలు, 5 నొక్కులు మార్చి మార్చి చేయండి. స్పందించకపోతే, 108కి కాల్ చేసి CPR ప్రారంభించండి.", "Baby under 1: lay face down along your forearm, give 5 back blows, then turn over and give 5 chest thrusts with two fingers. Repeat. Never put your fingers in the mouth to search for the object.": "1 ఏళ్లలోపు పసిపిల్లలు: మీ ముంజేతిపై బోర్లా పడుకోబెట్టి వీపుపై 5 సార్లు కొట్టండి, తర్వాత తిప్పి రెండు వేళ్లతో ఛాతీపై 5 సార్లు నొక్కండి. మళ్లీ చేయండి. వస్తువును వెతకడానికి నోటిలో ఎప్పుడూ వేళ్లు పెట్టవద్దు.", "Recovery position": "రికవరీ పొజిషన్", "Breathing but not awake": "శ్వాస ఉంది, స్పృహ లేదు", "Keep the airway open": "శ్వాస మార్గం తెరిచి ఉంచండి", "Head tilted back": "తల వెనక్కి వంచి", "Check breathing": "శ్వాస చూడండి", "Kneel beside them. Look, listen and feel for normal breathing. Not breathing? Start CPR instead.": "వారి పక్కన మోకాళ్లపై కూర్చోండి. సాధారణ శ్వాస కోసం చూడండి, వినండి, తెలుసుకోండి. శ్వాస లేదా? బదులుగా CPR ప్రారంభించండి.", "Arms": "చేతులు", "Put the arm nearest you at a right angle. Bring the far arm across the chest, back of the hand against their near cheek.": "మీకు దగ్గరగా ఉన్న చేయిని లంబకోణంలో పెట్టండి. దూరపు చేయిని ఛాతీ మీదుగా తెచ్చి, చేతి వెనుక భాగాన్ని దగ్గరి చెంపకు ఆనించండి.", "Roll": "తిప్పండి", "Bend the far knee up, then pull it towards you so they roll onto their side.": "దూరపు మోకాలును పైకి వంచి, మీ వైపు లాగి వారు పక్కకు తిరిగేలా చేయండి.", "Stay with them": "వారి దగ్గరే ఉండండి", "Tilt the head back so the airway stays open. Keep checking their breathing until help arrives.": "శ్వాస మార్గం తెరిచి ఉండేలా తలను వెనక్కి వంచండి. సహాయం వచ్చే వరకు శ్వాసను చూస్తూనే ఉండండి.", "Heavy bleeding": "ఎక్కువ రక్తస్రావం", "Press firmly, keep pressing": "గట్టిగా నొక్కండి, నొక్కుతూనే ఉండండి", "Press on the wound": "గాయంపై నొక్కండి", "With a clean cloth": "శుభ్రమైన గుడ్డతో", "For heavy bleeding, call first, then press.": "ఎక్కువ రక్తస్రావం అయితే, ముందు కాల్ చేసి, తర్వాత నొక్కండి.", "Press firmly": "గట్టిగా నొక్కండి", "Press on the wound with a clean cloth, or your hand if there’s nothing else.": "శుభ్రమైన గుడ్డతో, లేదా ఏమీ లేకపోతే మీ చేత్తో గాయంపై నొక్కండి.", "Keep pressing": "నొక్కుతూనే ఉండండి", "Press for at least 10 minutes without lifting to check. If blood soaks through, add more cloth on top.": "చూడటానికి ఎత్తకుండా కనీసం 10 నిమిషాలు నొక్కండి. రక్తం తడిపేస్తే, పైన ఇంకా గుడ్డ పెట్టండి.", "Keep them still": "కదలకుండా ఉంచండి", "Raise the injured part if you can. Keep them lying down and warm until help arrives.": "వీలైతే గాయపడిన భాగాన్ని పైకి ఎత్తండి. సహాయం వచ్చే వరకు పడుకోబెట్టి వెచ్చగా ఉంచండి.", "Insulin": "ఇన్సులిన్", "Insulin sites": "ఇన్సులిన్ ఇంజెక్షన్ స్థలాలు", "Next:": "తర్వాత:", "Used": "వాడినది", "Where next": "తర్వాత ఎక్కడ", "Belly, right side": "పొట్ట, కుడి వైపు", "Belly, left side": "పొట్ట, ఎడమ వైపు", "Right thigh": "కుడి తొడ", "Left thigh": "ఎడమ తొడ", "Right upper arm": "కుడి పై చేయి", "Left upper arm": "ఎడమ పై చేయి", "outer front": "బయటి ముందు భాగం", "back of the arm": "చేయి వెనుక భాగం", "in the last 2 days": "గత 2 రోజుల్లో", "Used recently": "ఇటీవల వాడినది", "Suggested": "సూచించినది", "Rested": "విశ్రాంతిలో", "All insulin doses logged today": "ఈరోజు ఇన్సులిన్ డోసులన్నీ నమోదయ్యాయి", "Dose as prescribed": "ప్రిస్క్రిప్షన్ ప్రకారం డోసు", "Log dose": "డోసు నమోదు చేయండి", "Log a dose": "డోసు నమోదు చేయండి", "Use a new spot about a finger’s width from the last one.": "చివరి స్థలానికి ఒక వేలి వెడల్పు దూరంలో కొత్త స్థలాన్ని వాడండి.", "Keep about 5 cm away from the navel.": "బొడ్డు నుండి సుమారు 5 సెం.మీ. దూరంగా ఉంచండి.", "Skip any lumps, bruises or scars.": "గడ్డలు, కమిలిన చోట్లు, మచ్చలను వదిలేయండి.", "LAST DOSES": "చివరి డోసులు", "General guidance on rotating sites. Your doctor or diabetes educator may advise differently: follow them.": "స్థలాలు మార్చడంపై సాధారణ సూచన. మీ డాక్టర్ లేదా డయాబెటిస్ ఎడ్యుకేటర్ వేరేలా చెప్పవచ్చు: వారిని పాటించండి.", "Tap the spot you used. The suggested one is already chosen.": "మీరు వాడిన స్థలాన్ని తాకండి. సూచించినది ఇప్పటికే ఎంచుకోబడింది.", "Belly": "పొట్ట", "Thighs": "తొడలు", "Their right": "వారి కుడి", "Their left": "వారి ఎడమ", "Spot": "స్థలం", "Time": "సమయం", "Now": "ఇప్పుడు", "Tap a spot": "ఒక స్థలాన్ని తాకండి", "Save dose": "డోసు సేవ్ చేయండి", "Body with injection areas": "ఇంజెక్షన్ ప్రాంతాలతో శరీరం"}); add(HI, {"First aid": "प्राथमिक उपचार", "Calm, simple steps until help arrives.": "मदद आने तक शांत, आसान कदम।", "Serious? Call 108 first": "गंभीर है? पहले 108 पर कॉल करें", "Then follow the steps below": "फिर नीचे दिए कदम अपनाएँ", "Call 108": "108 पर कॉल करें", "Call 108 ambulance": "108 एम्बुलेंस को कॉल करें", "Throat": "गला", "Centre of chest": "छाती के बीच में", "MORE": "और", "DO THIS": "यह करें", "DO NOT": "यह न करें", "Standard first-aid steps for adults. They don’t replace trained help: always call 108 for an emergency.": "बड़ों के लिए सामान्य प्राथमिक उपचार के कदम। ये प्रशिक्षित मदद की जगह नहीं लेते: आपात स्थिति में हमेशा 108 पर कॉल करें।", "General first aid. A doctor or the 108 call-taker may tell you something different for this person; follow them.": "सामान्य प्राथमिक उपचार। इस व्यक्ति के लिए डॉक्टर या 108 पर बात करने वाले कुछ और बता सकते हैं; उनकी बात मानें।", "First aid steps": "प्राथमिक उपचार के कदम", "CPR, choking, recovery position, bleeding": "CPR, गले में अटकना, रिकवरी पोज़िशन, खून बहना", "CPR and step-by-step help": "CPR और कदम-दर-कदम मदद", "Shown on the body: CPR, choking, recovery position, bleeding": "शरीर पर दिखाया गया: CPR, गले में अटकना, रिकवरी पोज़िशन, खून बहना", "Start the beat": "बीट शुरू करें", "Stop the beat": "बीट रोकें", "Read aloud": "पढ़कर सुनाएँ", "Reading aloud": "पढ़कर सुना रहे हैं", "Next": "आगे", "Back": "वापस", "Done": "हो गया", "Back to first aid": "प्राथमिक उपचार पर वापस", "Snake bite": "साँप का काटना", "Keep still, go to hospital": "हिलें नहीं, अस्पताल जाएँ", "Call 108 or 112. Go to the nearest hospital that has anti-snake venom. Most government hospitals do.": "108 या 112 पर कॉल करें। सबसे नज़दीकी अस्पताल जाएँ जहाँ साँप के ज़हर की दवा हो। ज़्यादातर सरकारी अस्पतालों में होती है।", "Keep the person calm and still. Movement spreads venom faster.": "व्यक्ति को शांत और स्थिर रखें। हिलने से ज़हर तेज़ी से फैलता है।", "Keep the bitten arm or leg still and at heart level. Remove rings, watches and tight clothes near the bite.": "काटे गए हाथ या पैर को स्थिर और दिल की ऊँचाई पर रखें। काटे वाली जगह के पास अँगूठी, घड़ी और तंग कपड़े हटा दें।", "Note the time of the bite. A photo of the snake helps, but do not try to catch it.": "काटने का समय नोट करें। साँप की फ़ोटो काम आती है, पर उसे पकड़ने की कोशिश न करें।", "Do not cut the wound, suck it, or put ice or chemicals on it.": "घाव को न काटें, न चूसें, न उस पर बर्फ़ या कोई केमिकल लगाएँ।", "Do not tie a tight tourniquet.": "कसकर पट्टी न बाँधें।", "Do not give alcohol, painkillers or herbal remedies. Do not wait to see if symptoms come.": "शराब, दर्द की दवा या जड़ी-बूटी न दें। लक्षण आने का इंतज़ार न करें।", "Poisoning": "ज़हर", "Medicines, pesticide, kerosene": "दवाइयाँ, कीटनाशक, मिट्टी का तेल", "Call 108 or 112 now. Say what was taken, how much and when, if you know.": "अभी 108 या 112 पर कॉल करें। पता हो तो बताएँ क्या लिया, कितना और कब।", "Take the bottle, packet or strip with you to the hospital.": "बोतल, पैकेट या पत्ता अपने साथ अस्पताल ले जाएँ।", "If it is on the skin or clothes (pesticide), remove the clothes and wash the skin with plenty of water.": "अगर त्वचा या कपड़ों पर लगा है (कीटनाशक), तो कपड़े उतारें और त्वचा को खूब पानी से धोएँ।", "If it got in the eyes, rinse with clean running water for 15 minutes.": "आँखों में गया हो तो 15 मिनट तक साफ़ बहते पानी से धोएँ।", "If they are unconscious but breathing, lay them on their side.": "बेहोश हों पर साँस ले रहे हों, तो करवट लिटा दें।", "Do not make them vomit, unless a doctor tells you to.": "डॉक्टर न कहें तो उल्टी न करवाएँ।", "Do not give milk, salt water or oil.": "दूध, नमक का पानी या तेल न दें।", "Kerosene, petrol or acid: never make them vomit.": "मिट्टी का तेल, पेट्रोल या एसिड: कभी उल्टी न करवाएँ।", "Burns": "जलना", "Cool water for 20 minutes": "20 मिनट ठंडा पानी", "Cool the burn under cool running water for 20 minutes.": "जली जगह को 20 मिनट तक ठंडे बहते पानी के नीचे रखें।", "Remove rings and tight clothes near the burn, unless stuck to the skin.": "त्वचा से चिपके न हों तो जली जगह के पास अँगूठी और तंग कपड़े हटा दें।", "Cover loosely with cling film or a clean cloth.": "क्लिंग फ़िल्म या साफ़ कपड़े से ढीला ढक दें।", "Call 108 for large burns, burns on the face, hands or private parts, or any burn on a child.": "बड़ा जला हो, चेहरा, हाथ या गुप्तांग जले हों, या बच्चा कहीं भी जला हो, तो 108 पर कॉल करें।", "Do not put ice, toothpaste, oil or butter on it.": "बर्फ़, टूथपेस्ट, तेल या मक्खन न लगाएँ।", "Do not burst blisters.": "छाले न फोड़ें।", "Choking": "गले में अटकना", "Adult, child or baby": "बड़े, बच्चे या शिशु", "If they can cough, let them keep coughing.": "खाँस पा रहे हों तो खाँसते रहने दें।", "Adult or child: give up to 5 firm back blows between the shoulder blades, then up to 5 abdominal thrusts. Repeat.": "बड़े या बच्चे: कंधों के बीच 5 बार तक ज़ोर से थपथपाएँ, फिर 5 बार तक पेट पर दबाव दें। दोहराएँ।", "Baby under 1: lay face down along your forearm, give 5 back blows, then turn over and give 5 chest thrusts with two fingers. Repeat.": "1 साल से छोटा शिशु: अपनी बाँह पर पेट के बल लिटाकर पीठ पर 5 बार थपथपाएँ, फिर पलटकर दो उँगलियों से छाती पर 5 बार दबाएँ। दोहराएँ।", "If they stop responding, call 108 or 112 and start CPR.": "जवाब देना बंद कर दें तो 108 या 112 पर कॉल करें और CPR शुरू करें।", "Do not put your fingers in the mouth to search for the object.": "चीज़ ढूँढने के लिए मुँह में उँगली न डालें।", "Fits (seizure)": "दौरा (मिर्गी)", "Keep them safe, time it": "सुरक्षित रखें, समय देखें", "Move hard or sharp things away. Put something soft under the head.": "सख़्त या नुकीली चीज़ें हटा दें। सिर के नीचे कुछ नरम रखें।", "Time the fit. Call 108 if it lasts more than 5 minutes, or if it is their first fit.": "दौरे का समय देखें। 5 मिनट से ज़्यादा चले, या पहली बार हो, तो 108 पर कॉल करें।", "When it stops, turn them on their side and stay with them.": "रुकने पर करवट लिटाएँ और उनके पास रहें।", "Do not hold them down.": "उन्हें दबाकर न पकड़ें।", "Do not put anything in the mouth.": "मुँह में कुछ न डालें।", "CPR": "CPR", "Not breathing, not responding": "साँस नहीं, जवाब नहीं", "Heel of your hand": "हथेली का निचला हिस्सा", "Lower half of the breastbone": "छाती की हड्डी का निचला आधा हिस्सा", "Check and call": "जाँचें और कॉल करें", "Tap their shoulders and shout. If they don’t respond and aren’t breathing normally, call 108 and put the phone on speaker.": "कंधे थपथपाएँ और ज़ोर से पुकारें। जवाब न दें और ठीक से साँस न ले रहे हों, तो 108 पर कॉल करें और फ़ोन स्पीकर पर रखें।", "Push hard and fast": "ज़ोर से और तेज़ दबाएँ", "One hand on top of the other, arms straight, on the red spot. Press down about 5–6 cm, then let the chest rise fully. 100–120 pushes a minute: follow the beat.": "एक हाथ के ऊपर दूसरा हाथ, बाँहें सीधी, लाल निशान पर। लगभग 5–6 सेमी नीचे दबाएँ, फिर छाती को पूरा ऊपर आने दें। एक मिनट में 100–120 बार: बीट के साथ चलें।", "Keep going": "करते रहें", "Don’t stop. If someone can take over, swap every 2 minutes. If you’re trained, give 2 breaths after every 30 pushes; if not, keep pushing.": "रुकें नहीं। कोई और मदद कर सके तो हर 2 मिनट में बदल लें। प्रशिक्षित हों तो हर 30 बार दबाने के बाद 2 साँस दें; नहीं तो दबाते रहें।", "Until help arrives": "मदद आने तक", "Carry on until they breathe normally, the ambulance team takes over, or you can’t continue. If they start breathing, use the recovery position.": "तब तक करते रहें जब तक वे ठीक से साँस न लें, एम्बुलेंस टीम सँभाल न ले, या आप आगे न कर सकें। साँस लेने लगें तो रिकवरी पोज़िशन में लिटाएँ।", "Can’t speak, cough or breathe": "बोल, खाँस या साँस नहीं ले पा रहे", "Fist goes here": "मुट्ठी यहाँ", "Just above the navel": "नाभि के ठीक ऊपर", "Ask: are you choking?": "पूछें: क्या गले में कुछ अटका है?", "If they can cough, let them keep coughing. Stay with them.": "खाँस पा रहे हों तो खाँसते रहने दें। उनके पास रहें।", "5 back blows": "पीठ पर 5 थपकी", "Help them lean forward. Give up to 5 firm blows between the shoulder blades with the heel of your hand.": "आगे झुकने में मदद करें। हथेली के निचले हिस्से से कंधों के बीच 5 बार तक ज़ोर से थपथपाएँ।", "5 tummy thrusts": "पेट पर 5 दबाव", "Stand behind them. Make a fist just above the navel, hold it with your other hand and pull sharply inwards and upwards. For a pregnant woman, put your hands on the lower chest instead.": "उनके पीछे खड़े हों। नाभि के ठीक ऊपर मुट्ठी रखें, दूसरे हाथ से पकड़ें और अंदर व ऊपर की ओर झटके से खींचें। गर्भवती महिला हो तो हाथ छाती के निचले हिस्से पर रखें।", "Repeat until it clears": "निकलने तक दोहराएँ", "Keep swapping 5 back blows and 5 thrusts. If they stop responding, call 108 and start CPR.": "5 थपकी और 5 दबाव बारी-बारी से देते रहें। जवाब देना बंद कर दें तो 108 पर कॉल करें और CPR शुरू करें।", "Baby under 1: lay face down along your forearm, give 5 back blows, then turn over and give 5 chest thrusts with two fingers. Repeat. Never put your fingers in the mouth to search for the object.": "1 साल से छोटा शिशु: अपनी बाँह पर पेट के बल लिटाकर पीठ पर 5 बार थपथपाएँ, फिर पलटकर दो उँगलियों से छाती पर 5 बार दबाएँ। दोहराएँ। चीज़ ढूँढने के लिए कभी मुँह में उँगली न डालें।", "Recovery position": "रिकवरी पोज़िशन", "Breathing but not awake": "साँस ले रहे हैं, पर होश नहीं", "Keep the airway open": "साँस का रास्ता खुला रखें", "Head tilted back": "सिर पीछे झुका हुआ", "Check breathing": "साँस जाँचें", "Kneel beside them. Look, listen and feel for normal breathing. Not breathing? Start CPR instead.": "उनके पास घुटनों के बल बैठें। ठीक से साँस ले रहे हैं, यह देखें, सुनें और महसूस करें। साँस नहीं? तो CPR शुरू करें।", "Arms": "बाँहें", "Put the arm nearest you at a right angle. Bring the far arm across the chest, back of the hand against their near cheek.": "आपके पास वाली बाँह को समकोण पर रखें। दूर वाली बाँह को छाती पर से लाकर हाथ का पिछला हिस्सा पास वाले गाल से लगाएँ।", "Roll": "करवट दिलाएँ", "Bend the far knee up, then pull it towards you so they roll onto their side.": "दूर वाला घुटना ऊपर मोड़ें, फिर अपनी ओर खींचें ताकि वे करवट पर आ जाएँ।", "Stay with them": "उनके पास रहें", "Tilt the head back so the airway stays open. Keep checking their breathing until help arrives.": "सिर पीछे झुकाएँ ताकि साँस का रास्ता खुला रहे। मदद आने तक साँस जाँचते रहें।", "Heavy bleeding": "ज़्यादा खून बहना", "Press firmly, keep pressing": "ज़ोर से दबाएँ, दबाते रहें", "Press on the wound": "घाव पर दबाएँ", "With a clean cloth": "साफ़ कपड़े से", "For heavy bleeding, call first, then press.": "ज़्यादा खून बह रहा हो तो पहले कॉल करें, फिर दबाएँ।", "Press firmly": "ज़ोर से दबाएँ", "Press on the wound with a clean cloth, or your hand if there’s nothing else.": "साफ़ कपड़े से घाव पर दबाएँ, कुछ न हो तो हाथ से।", "Keep pressing": "दबाते रहें", "Press for at least 10 minutes without lifting to check. If blood soaks through, add more cloth on top.": "देखने के लिए उठाए बिना कम से कम 10 मिनट दबाएँ। खून कपड़े से रिसे तो ऊपर और कपड़ा रख दें।", "Keep them still": "उन्हें स्थिर रखें", "Raise the injured part if you can. Keep them lying down and warm until help arrives.": "हो सके तो चोट वाला हिस्सा ऊपर उठाएँ। मदद आने तक लिटाकर गर्म रखें।", "Insulin": "इंसुलिन", "Insulin sites": "इंसुलिन लगाने की जगहें", "Next:": "अगली:", "Used": "इस्तेमाल हुई", "Where next": "अगली बार कहाँ", "Belly, right side": "पेट, दाईं ओर", "Belly, left side": "पेट, बाईं ओर", "Right thigh": "दाईं जाँघ", "Left thigh": "बाईं जाँघ", "Right upper arm": "दाईं ऊपरी बाँह", "Left upper arm": "बाईं ऊपरी बाँह", "outer front": "बाहरी सामने का हिस्सा", "back of the arm": "बाँह का पिछला हिस्सा", "in the last 2 days": "पिछले 2 दिनों में", "Used recently": "हाल में इस्तेमाल", "Suggested": "सुझाई गई", "Rested": "आराम में", "All insulin doses logged today": "आज की सभी इंसुलिन खुराकें दर्ज हैं", "Dose as prescribed": "पर्चे के अनुसार खुराक", "Log dose": "खुराक दर्ज करें", "Log a dose": "खुराक दर्ज करें", "Use a new spot about a finger’s width from the last one.": "पिछली जगह से लगभग एक उँगली की चौड़ाई दूर नई जगह लें।", "Keep about 5 cm away from the navel.": "नाभि से लगभग 5 सेमी दूर रखें।", "Skip any lumps, bruises or scars.": "गाँठ, नील या निशान वाली जगह छोड़ दें।", "LAST DOSES": "पिछली खुराकें", "General guidance on rotating sites. Your doctor or diabetes educator may advise differently: follow them.": "जगह बदलने पर सामान्य जानकारी। आपके डॉक्टर या डायबिटीज़ एजुकेटर कुछ और बता सकते हैं: उनकी बात मानें।", "Tap the spot you used. The suggested one is already chosen.": "जहाँ लगाया, उस जगह पर टैप करें। सुझाई गई जगह पहले से चुनी है।", "Belly": "पेट", "Thighs": "जाँघें", "Their right": "उनका दायाँ", "Their left": "उनका बायाँ", "Spot": "जगह", "Time": "समय", "Now": "अभी", "Tap a spot": "एक जगह पर टैप करें", "Save dose": "खुराक सेव करें", "Body with injection areas": "इंजेक्शन की जगहों के साथ शरीर"}); })(function (d, a) { for (var k in a) if (!Object.prototype.hasOwnProperty.call(d, k)) d[k] = a[k]; });
  RULES.ta.push([/^STEP (\d+) OF (\d+)$/, 'படி $1 / $2']); RULES.te.push([/^STEP (\d+) OF (\d+)$/, 'దశ $1 / $2']); RULES.hi.push([/^STEP (\d+) OF (\d+)$/, 'कदम $1 / $2']);
  (function (add) { add(TA, {"Tap and shout": "தட்டி அழையுங்கள்", "Both shoulders": "இரு தோள்களிலும்", "Often holding the throat": "பெரும்பாலும் தொண்டையைப் பிடித்திருப்பார்", "On their back": "அவரின் முதுகில்", "Between the shoulder blades": "தோள்பட்டைகளுக்கு இடையில்", "Mouth and chest": "வாய் மற்றும் மார்பு", "Look, listen, feel": "பாருங்கள், கேளுங்கள், உணருங்கள்", "Near arm": "அருகிலுள்ள கை", "At a right angle": "செங்கோணத்தில்", "Far knee": "தொலைவில் உள்ள முழங்கால்", "Bend it, then pull": "மடக்கி, பிறகு இழுங்கள்"}); add(TE, {"Tap and shout": "తట్టి పిలవండి", "Both shoulders": "రెండు భుజాలు", "Often holding the throat": "తరచూ గొంతు పట్టుకుంటారు", "On their back": "వారి వీపుపై", "Between the shoulder blades": "భుజాల మధ్య", "Mouth and chest": "నోరు మరియు ఛాతీ", "Look, listen, feel": "చూడండి, వినండి, తెలుసుకోండి", "Near arm": "దగ్గరి చేయి", "At a right angle": "లంబకోణంలో", "Far knee": "దూరపు మోకాలు", "Bend it, then pull": "వంచి, తర్వాత లాగండి"}); add(HI, {"Tap and shout": "थपथपाएँ और पुकारें", "Both shoulders": "दोनों कंधे", "Often holding the throat": "अक्सर गला पकड़ते हैं", "On their back": "उनकी पीठ पर", "Between the shoulder blades": "कंधों के बीच", "Mouth and chest": "मुँह और छाती", "Look, listen, feel": "देखें, सुनें, महसूस करें", "Near arm": "पास वाली बाँह", "At a right angle": "समकोण पर", "Far knee": "दूर वाला घुटना", "Bend it, then pull": "मोड़ें, फिर खींचें"}); })(function (d, a) { for (var k in a) if (!Object.prototype.hasOwnProperty.call(d, k)) d[k] = a[k]; });
  var DICT = { ta: TA, te: TE, hi: HI };

  /* Getting Better theme phrases (23 Nov 2026). DRAFT translations: every line here must be checked by a native
     speaker before release, like the rest of this file. Headlines are built from a subject ("Your heart",
     "Kabir’s health") and a predicate ("needs a recheck"); each half is translated on its own. */
  (function () {
    var X = {"ta": {"needs a recheck": "மீண்டும் பரிசோதிக்க வேண்டும்", "need a recheck": "மீண்டும் பரிசோதிக்க வேண்டும்", "is getting better": "மேம்பட்டு வருகிறது", "are getting better": "மேம்பட்டு வருகின்றன", "are all in range": "அனைத்தும் சீரான அளவில் உள்ளன", "Add a report": "அறிக்கையைச் சேர்க்கவும்", "to see your body": "உங்கள் உடலைப் பார்க்க", "to see the body": "உடலைப் பார்க்க", "to get started": "தொடங்க", "to recheck": "மீண்டும் பரிசோதிக்க", "No medicines": "மருந்துகள் இல்லை", "added yet": "இன்னும் சேர்க்கவில்லை", "all taken": "அனைத்தும் எடுக்கப்பட்டன", "Today’s doses": "இன்றைய மருந்துகள்", "Your family is": "உங்கள் குடும்பம்", "covered": "காப்பீட்டில் உள்ளது", "Add your cover": "உங்கள் காப்பீட்டைச் சேர்க்கவும்", "in a minute": "ஒரு நிமிடத்தில்", "coming up": "வரவிருக்கின்றன", "No visit": "வருகை இல்லை", "booked yet": "இன்னும் பதிவு செய்யவில்லை", "Your family": "உங்கள் குடும்பம்", "at a glance": "ஒரே பார்வையில்", "due any day now": "எந்த நாளும் பிரசவம்", "Week": "வாரம்", "under 1": "1 வயதுக்குக் கீழ்", "Care plan": "பராமரிப்புத் திட்டம்", "See all": "அனைத்தையும் பார்", "In range": "சீரான அளவில்", "A little high": "சற்று அதிகம்", "A little low": "சற்று குறைவு", "Worth a recheck": "மீண்டும் பரிசோதிப்பது நல்லது", "Heartbeat": "இதயத் துடிப்பு", "Pressure": "இரத்த அழுத்தம்", "Kids mode": "குழந்தைகள் முறை", "Height": "உயரம்", "Weight": "எடை", "Vaccines": "தடுப்பூசிகள்", "At birth": "பிறக்கும்போது", "After each check-up": "ஒவ்வொரு பரிசோதனைக்குப் பிறகும்", "All up to date": "அனைத்தும் சரியான நேரத்தில்", "Your order": "உங்கள் ஆர்டர்", "ready to send": "அனுப்பத் தயார்", "To pay": "செலுத்த வேண்டியது", "Deliver to": "டெலிவரி முகவரி", "Safety": "பாதுகாப்பு", "Ready before you need it": "தேவைப்படும் முன்பே தயார்", "SOS calls them first, with your location": "SOS முதலில் இவர்களை உங்கள் இருப்பிடத்துடன் அழைக்கும்", "Add a contact": "தொடர்பைச் சேர்க்கவும்", "Two is safer than one": "ஒருவரை விட இருவர் பாதுகாப்பானது", "SOS has nobody to call yet": "SOS அழைக்க இன்னும் யாரும் இல்லை", "Called first": "முதலில் அழைக்கப்படுவார்", "What this device lets Urban Health use": "இந்தச் சாதனம் Urban Health-க்கு அனுமதிப்பவை", "Medicine times and results": "மருந்து நேரங்களும் முடிவுகளும்", "Location": "இருப்பிடம்", "Sent with SOS and for home collection": "SOS-உடனும் வீட்டு மாதிரி சேகரிப்புக்கும் அனுப்பப்படும்", "Camera": "கேமரா", "Photos of reports and prescriptions": "அறிக்கைகள், மருந்துச்சீட்டுகளின் புகைப்படங்கள்", "Emergency setup": "அவசரகால அமைப்பு", "Contacts, Medical ID and lock screen": "தொடர்புகள், மருத்துவ அடையாளம், பூட்டுத் திரை", "First aid": "முதலுதவி", "CPR, choking, bleeding": "CPR, மூச்சுத் திணறல், இரத்தப்போக்கு", "works offline": "இணையம் இல்லாமலும் இயங்கும்", "On my lock screen": "என் பூட்டுத் திரையில்", "Responders see it without unlocking": "திறக்காமலேயே உதவுபவர்கள் பார்க்கலாம்", "Let’s make your": "உங்கள்", "health card": "சுகாதார அட்டையை உருவாக்குவோம்", "This builds your Medical ID and 3D body.": "இது உங்கள் மருத்துவ அடையாளத்தையும் 3D உடலையும் உருவாக்கும்.", "Start with a": "ஒரு", "photo": "புகைப்படத்துடன் தொடங்குங்கள்", "Inside you": "உங்களுக்குள்", "Your body": "உங்கள் உடல்", "Care": "பராமரிப்பு", "Coming up": "வரவிருப்பவை", "This week": "இந்த வாரம்"}, "te": {"needs a recheck": "మళ్లీ పరీక్షించాలి", "need a recheck": "మళ్లీ పరీక్షించాలి", "is getting better": "మెరుగవుతోంది", "are getting better": "మెరుగవుతున్నాయి", "are all in range": "అన్నీ సరైన పరిధిలో ఉన్నాయి", "Add a report": "రిపోర్ట్ జోడించండి", "to see your body": "మీ శరీరాన్ని చూడటానికి", "to see the body": "శరీరాన్ని చూడటానికి", "to get started": "ప్రారంభించడానికి", "to recheck": "మళ్లీ పరీక్షించాలి", "No medicines": "మందులు లేవు", "added yet": "ఇంకా జోడించలేదు", "all taken": "అన్నీ వేసుకున్నారు", "Today’s doses": "ఈరోజు డోసులు", "Your family is": "మీ కుటుంబానికి", "covered": "కవరేజ్ ఉంది", "Add your cover": "మీ కవర్ జోడించండి", "in a minute": "ఒక్క నిమిషంలో", "coming up": "రాబోతున్నాయి", "No visit": "విజిట్ లేదు", "booked yet": "ఇంకా బుక్ చేయలేదు", "Your family": "మీ కుటుంబం", "at a glance": "ఒక్క చూపులో", "due any day now": "ఏ రోజైనా ప్రసవం", "Week": "వారం", "under 1": "1 ఏళ్ల లోపు", "Care plan": "సంరక్షణ ప్రణాళిక", "See all": "అన్నీ చూడండి", "In range": "సరైన పరిధిలో", "A little high": "కొంచెం ఎక్కువ", "A little low": "కొంచెం తక్కువ", "Worth a recheck": "మళ్లీ పరీక్షించడం మంచిది", "Heartbeat": "గుండె చప్పుడు", "Pressure": "రక్తపోటు", "Kids mode": "పిల్లల మోడ్", "Height": "ఎత్తు", "Weight": "బరువు", "Vaccines": "టీకాలు", "At birth": "పుట్టినప్పుడు", "After each check-up": "ప్రతి చెకప్ తర్వాత", "All up to date": "అన్నీ సమయానికి", "Your order": "మీ ఆర్డర్", "ready to send": "పంపడానికి సిద్ధం", "To pay": "చెల్లించాల్సింది", "Deliver to": "డెలివరీ చిరునామా", "Safety": "భద్రత", "Ready before you need it": "అవసరం రాకముందే సిద్ధం", "SOS calls them first, with your location": "SOS ముందుగా వీరికి మీ లొకేషన్‌తో కాల్ చేస్తుంది", "Add a contact": "కాంటాక్ట్ జోడించండి", "Two is safer than one": "ఒకరి కంటే ఇద్దరు సురక్షితం", "SOS has nobody to call yet": "SOS కాల్ చేయడానికి ఇంకా ఎవరూ లేరు", "Called first": "ముందుగా కాల్ వెళ్తుంది", "What this device lets Urban Health use": "ఈ పరికరం Urban Health‌కి అనుమతించేవి", "Medicine times and results": "మందుల సమయాలు, ఫలితాలు", "Location": "లొకేషన్", "Sent with SOS and for home collection": "SOS‌తో, ఇంటి వద్ద శాంపిల్ కోసం పంపబడుతుంది", "Camera": "కెమెరా", "Photos of reports and prescriptions": "రిపోర్టులు, ప్రిస్క్రిప్షన్ల ఫోటోలు", "Emergency setup": "అత్యవసర సెటప్", "Contacts, Medical ID and lock screen": "కాంటాక్ట్‌లు, మెడికల్ ఐడీ, లాక్ స్క్రీన్", "First aid": "ప్రథమ చికిత్స", "CPR, choking, bleeding": "CPR, ఊపిరాడకపోవడం, రక్తస్రావం", "works offline": "ఇంటర్నెట్ లేకుండా పనిచేస్తుంది", "On my lock screen": "నా లాక్ స్క్రీన్‌పై", "Responders see it without unlocking": "అన్‌లాక్ చేయకుండానే సహాయకులు చూడవచ్చు", "Let’s make your": "మీ", "health card": "హెల్త్ కార్డ్ తయారు చేద్దాం", "This builds your Medical ID and 3D body.": "ఇది మీ మెడికల్ ఐడీ, 3D శరీరాన్ని తయారు చేస్తుంది.", "Start with a": "ఒక", "photo": "ఫోటోతో ప్రారంభించండి", "Inside you": "మీ లోపల", "Your body": "మీ శరీరం", "Care": "సంరక్షణ", "Coming up": "రాబోయేవి", "This week": "ఈ వారం"}, "hi": {"needs a recheck": "दोबारा जाँच करानी है", "need a recheck": "दोबारा जाँच करानी है", "is getting better": "बेहतर हो रहा है", "are getting better": "बेहतर हो रहे हैं", "are all in range": "सब सामान्य सीमा में हैं", "Add a report": "रिपोर्ट जोड़ें", "to see your body": "अपना शरीर देखने के लिए", "to see the body": "शरीर देखने के लिए", "to get started": "शुरू करने के लिए", "to recheck": "दोबारा जाँच के लिए", "No medicines": "कोई दवा नहीं", "added yet": "अभी जोड़ी नहीं गई", "all taken": "सब ले ली गईं", "Today’s doses": "आज की खुराकें", "Your family is": "आपका परिवार", "covered": "कवर है", "Add your cover": "अपना कवर जोड़ें", "in a minute": "एक मिनट में", "coming up": "आने वाली हैं", "No visit": "कोई विज़िट नहीं", "booked yet": "अभी बुक नहीं हुई", "Your family": "आपका परिवार", "at a glance": "एक नज़र में", "due any day now": "अब कभी भी", "Week": "सप्ताह", "under 1": "1 साल से कम", "Care plan": "देखभाल योजना", "See all": "सब देखें", "In range": "सामान्य सीमा में", "A little high": "थोड़ा ज़्यादा", "A little low": "थोड़ा कम", "Worth a recheck": "दोबारा जाँच ठीक रहेगी", "Heartbeat": "धड़कन", "Pressure": "ब्लड प्रेशर", "Kids mode": "बच्चों का मोड", "Height": "लंबाई", "Weight": "वज़न", "Vaccines": "टीके", "At birth": "जन्म के समय", "After each check-up": "हर जाँच के बाद", "All up to date": "सब समय पर", "Your order": "आपका ऑर्डर", "ready to send": "भेजने के लिए तैयार", "To pay": "भुगतान", "Deliver to": "यहाँ पहुँचाएँ", "Safety": "सुरक्षा", "Ready before you need it": "ज़रूरत से पहले तैयार", "SOS calls them first, with your location": "SOS सबसे पहले इन्हें आपकी लोकेशन के साथ कॉल करता है", "Add a contact": "संपर्क जोड़ें", "Two is safer than one": "एक से दो बेहतर", "SOS has nobody to call yet": "SOS के पास अभी कॉल करने को कोई नहीं", "Called first": "सबसे पहले कॉल", "What this device lets Urban Health use": "यह डिवाइस Urban Health को क्या इस्तेमाल करने देता है", "Medicine times and results": "दवा का समय और नतीजे", "Location": "लोकेशन", "Sent with SOS and for home collection": "SOS के साथ और घर से सैंपल के लिए भेजी जाती है", "Camera": "कैमरा", "Photos of reports and prescriptions": "रिपोर्ट और पर्चे की फ़ोटो", "Emergency setup": "इमरजेंसी सेटअप", "Contacts, Medical ID and lock screen": "संपर्क, मेडिकल आईडी और लॉक स्क्रीन", "First aid": "प्राथमिक उपचार", "CPR, choking, bleeding": "CPR, दम घुटना, खून बहना", "works offline": "बिना इंटरनेट चलता है", "On my lock screen": "मेरी लॉक स्क्रीन पर", "Responders see it without unlocking": "बिना अनलॉक किए मदद करने वाले देख सकते हैं", "Let’s make your": "आइए बनाएँ आपका", "health card": "हेल्थ कार्ड", "This builds your Medical ID and 3D body.": "इससे आपकी मेडिकल आईडी और 3D शरीर बनता है।", "Start with a": "शुरुआत करें एक", "photo": "फ़ोटो से", "Inside you": "आपके अंदर", "Your body": "आपका शरीर", "Care": "देखभाल", "Coming up": "आगे क्या है", "This week": "इस सप्ताह"}}, O = {"ta": {"heart": "இதயம்", "sugar": "சர்க்கரை", "kidneys": "சிறுநீரகங்கள்", "liver": "கல்லீரல்", "thyroid": "தைராய்டு", "lungs": "நுரையீரல்", "bones": "எலும்புகள்", "blood": "இரத்தம்", "eyes": "கண்கள்", "teeth": "பற்கள்", "skin": "தோல்", "stomach": "வயிறு", "results": "முடிவுகள்", "reports": "அறிக்கைகள்", "health": "ஆரோக்கியம்"}, "te": {"heart": "గుండె", "sugar": "షుగర్", "kidneys": "కిడ్నీలు", "liver": "కాలేయం", "thyroid": "థైరాయిడ్", "lungs": "ఊపిరితిత్తులు", "bones": "ఎముకలు", "blood": "రక్తం", "eyes": "కళ్లు", "teeth": "దంతాలు", "skin": "చర్మం", "stomach": "కడుపు", "results": "ఫలితాలు", "reports": "రిపోర్టులు", "health": "ఆరోగ్యం"}, "hi": {"heart": "दिल", "sugar": "शुगर", "kidneys": "किडनी", "liver": "लिवर", "thyroid": "थायरॉइड", "lungs": "फेफड़े", "bones": "हड्डियाँ", "blood": "खून", "eyes": "आँखें", "teeth": "दाँत", "skin": "त्वचा", "stomach": "पेट", "results": "नतीजे", "reports": "रिपोर्ट", "health": "सेहत"}}, YOU = { ta: 'உங்கள்', te: 'మీ', hi: 'आपका' };
    Object.keys(X).forEach(function (l) { var d = DICT[l]; Object.keys(X[l]).forEach(function (k) { if (!Object.prototype.hasOwnProperty.call(d, k)) d[k] = X[l][k]; }); });
    var W = Object.keys(O.ta).join('|');
    /* Hindi agrees with the noun: की for feminine (सेहत, शुगर), के for plural, का otherwise */
    var HIG = { health: 'f', sugar: 'f', skin: 'f', results: 'p', reports: 'p', kidneys: 'p', lungs: 'p', bones: 'p', eyes: 'p', teeth: 'p' };
    function own(l, who, a) { return l === 'ta' ? who + 'இன்' : l === 'hi' ? who + (HIG[a] === 'f' ? ' की' : HIG[a] === 'p' ? ' के' : ' का') : who; }
    function you(l, a) { return l !== 'hi' ? YOU[l] : HIG[a] === 'f' ? 'आपकी' : HIG[a] === 'p' ? 'आपके' : 'आपका'; }
    Object.keys(O).forEach(function (l) {
      RULES[l] = (RULES[l] || []).concat([
        [new RegExp('^Your (' + W + ')$'), function (m, a) { return you(l, a) + ' ' + O[l][a]; }],
        [new RegExp('^(.+?)’s (' + W + ')$'), function (m, who, a) { return own(l, who, a) + ' ' + O[l][a]; }],
        [/^(\d+) results?$/, l === 'ta' ? '$1 முடிவுகள்' : l === 'te' ? '$1 ఫలితాలు' : '$1 नतीजे'],
        [/^(\d+) visits?$/, l === 'ta' ? '$1 வருகைகள்' : l === 'te' ? '$1 విజిట్‌లు' : '$1 विज़िट'],
        [/^(\d+) to take$/, l === 'ta' ? 'இன்னும் $1 எடுக்க வேண்டும்' : l === 'te' ? 'ఇంకా $1 వేసుకోవాలి' : '$1 लेनी बाकी'],
        [/^(\d+) weeks? to go$/, l === 'ta' ? 'இன்னும் $1 வாரங்கள்' : l === 'te' ? 'ఇంకా $1 వారాలు' : '$1 सप्ताह बाकी'],
        [/^(\d+) items?$/, l === 'ta' ? '$1 பொருட்கள்' : l === 'te' ? '$1 వస్తువులు' : '$1 चीज़ें'],
        [/^(\d+) yrs?$/, l === 'ta' ? '$1 வயது' : l === 'te' ? '$1 ఏళ్లు' : '$1 साल'],
        [/^(\d+) overdue$/, l === 'ta' ? '$1 தாமதம்' : l === 'te' ? '$1 ఆలస్యం' : '$1 देर से'],
        [/^(.+) sees only learning and games$/, l === 'ta' ? '$1 கற்றலும் விளையாட்டும் மட்டுமே பார்ப்பார்' : l === 'te' ? '$1 కి నేర్చుకోవడం, ఆటలు మాత్రమే కనిపిస్తాయి' : '$1 को सिर्फ़ सीखना और खेल दिखेंगे'],
        [/^Measured (.+)$/, l === 'ta' ? '$1 அன்று அளந்தது' : l === 'te' ? '$1న కొలిచారు' : '$1 को मापा'],
        [/^of (\d+) given$/, l === 'ta' ? '/ $1 போடப்பட்டன' : l === 'te' ? '/ $1 వేశారు' : '/ $1 लगे']
      ]);
    });
  })();

  var lang = 'en';
  try { lang = localStorage.getItem(KEY) || 'en'; } catch (_) {}
  if (!NAMES[lang]) lang = 'en';

  var DAYS = { ta: ['ஞாயிறு', 'திங்கள்', 'செவ்வாய்', 'புதன்', 'வியாழன்', 'வெள்ளி', 'சனி'], te: ['ఆదివారం', 'సోమవారం', 'మంగళవారం', 'బుధవారం', 'గురువారం', 'శుక్రవారం', 'శనివారం'], hi: ['रविवार', 'सोमवार', 'मंगलवार', 'बुधवार', 'गुरुवार', 'शुक्रवार', 'शनिवार'] };
  var MONTHS = { ta: ['ஜனவரி', 'பிப்ரவரி', 'மார்ச்', 'ஏப்ரல்', 'மே', 'ஜூன்', 'ஜூலை', 'ஆகஸ்ட்', 'செப்டம்பர்', 'அக்டோபர்', 'நவம்பர்', 'டிசம்பர்'],
                 te: ['జనవరి', 'ఫిబ్రవరి', 'మార్చి', 'ఏప్రిల్', 'మే', 'జూన్', 'జూలై', 'ఆగస్టు', 'సెప్టెంబర్', 'అక్టోబర్', 'నవంబర్', 'డిసెంబర్'],
                 hi: ['जनवरी', 'फ़रवरी', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अगस्त', 'सितंबर', 'अक्टूबर', 'नवंबर', 'दिसंबर'] };
  var EN_D = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  var EN_M = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var LOWER = {};
  function lowerIndex(l) {
    if (LOWER[l]) return LOWER[l];
    var d = DICT[l] || {}, x = {};
    Object.keys(d).forEach(function (k) { x[k.toLowerCase()] = d[k]; });
    return (LOWER[l] = x);
  }

  function find(key, depth) {
    var d = DICT[lang] || {};
    if (Object.prototype.hasOwnProperty.call(d, key)) return d[key];
    var lo = lowerIndex(lang)[key.toLowerCase()];
    if (lo) return lo;
    var rs = RULES[lang] || [];
    for (var i = 0; i < rs.length; i++) if (rs[i][0].test(key)) return key.replace(rs[i][0], rs[i][1]);
    var dm = key.match(/^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday), (\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December)$/);
    if (dm && DAYS[lang]) return DAYS[lang][EN_D.indexOf(dm[1])] + ', ' + dm[2] + ' ' + MONTHS[lang][EN_M.indexOf(dm[3])];
    if (depth > 2) return null;
    var sym = key.match(/^([^A-Za-z0-9₹\s]+\s*)(.+)$/);                     // "◎ Use current location"
    if (sym) { var r = find(sym[2], depth + 1); if (r) return sym[1] + r; }
    if (key.indexOf(' · ') > 0) {                                            // "08:30 · After food", "Wife · emergency contact"
      var parts = key.split(' · '), hit = false;
      for (var j = 0; j < parts.length; j++) { var p = parts[j].trim(), q = /[A-Za-z]/.test(p) ? find(p, depth + 1) : null; if (q) { parts[j] = q; hit = true; } }
      if (hit) return parts.join(' · ');
    }
    return null;
  }

  function tr(s) {
    if (lang === 'en' || !s) return null;
    var key = s.trim();
    if (!key || !/[A-Za-z]/.test(key)) return null;
    var t = find(key, 0);
    return t == null ? null : s.replace(key, t);
  }

  var SKIP = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, CODE: 1, NOSCRIPT: 1 };
  var ATTRS = ['placeholder', 'aria-label', 'title'];

  function skip(el) {
    for (var e = el; e && e.nodeType === 1; e = e.parentElement) {
      if (SKIP[e.tagName] || e.hasAttribute('data-noi18n') || e.isContentEditable) return true;
    }
    return false;
  }

  function doText(n) {
    if (n.__uhen === undefined) n.__uhen = n.nodeValue;
    var src = n.__uhen;
    if (n.nodeValue !== src && n.nodeValue !== n.__uhto) { n.__uhen = src = n.nodeValue; }   // the app re-wrote it
    var t = lang === 'en' ? src : (tr(src) || src);
    if (n.nodeValue !== t) { n.__uhto = t; n.nodeValue = t; }
  }

  function doAttrs(el) {
    for (var i = 0; i < ATTRS.length; i++) {
      var a = ATTRS[i];
      if (!el.hasAttribute(a)) continue;
      var k = '__uh_' + a, v = el.getAttribute(a);
      if (el[k] === undefined || (v !== el[k] && v !== el[k + 'to'])) el[k] = v;
      var t = lang === 'en' ? el[k] : (tr(el[k]) || el[k]);
      if (v !== t) { el[k + 'to'] = t; el.setAttribute(a, t); }
    }
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { if (root.parentElement && !skip(root.parentElement)) doText(root); return; }
    if (root.nodeType !== 1 || skip(root)) return;
    doAttrs(root);
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode: function (n) { return n.nodeType === 1 && (SKIP[n.tagName] || n.hasAttribute('data-noi18n')) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; }
    });
    var n;
    while ((n = w.nextNode())) { if (n.nodeType === 3) doText(n); else doAttrs(n); }
  }

  var busy = false;
  var mo = new MutationObserver(function (list) {
    if (busy) return;
    busy = true;
    try {
      for (var i = 0; i < list.length; i++) {
        var m = list[i];
        if (m.type === 'characterData') walk(m.target);
        else if (m.type === 'attributes') doAttrs(m.target);
        else for (var j = 0; j < m.addedNodes.length; j++) walk(m.addedNodes[j]);
      }
    } finally { mo.takeRecords(); busy = false; }
  });

  // Telugu also draws on the shared phrase table the earlier app built (/api/v1/i18n: English → [Hindi, Telugu]).
  var merged = false;
  function mergeShared() {
    if (merged || lang !== 'te' || !window.fetch) return;
    merged = true;
    fetch('/api/v1/i18n', { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : {}; }).then(function (d) {
      Object.keys(d || {}).forEach(function (k) { var v = d[k]; if (k.charAt(0) !== '_' && Array.isArray(v) && v[1] && !TE[k]) TE[k] = v[1]; });
      if (lang === 'te') { busy = true; try { walk(document.body); } finally { mo.takeRecords(); busy = false; } }
    }).catch(function () { merged = false; });
  }

  function start() {
    document.documentElement.lang = BCP[lang];
    walk(document.body);
    mergeShared();
    mo.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }

  // ---- voice ------------------------------------------------------------------------------------------------
  function voiceFor(l) {
    if (!('speechSynthesis' in window)) return null;
    var vs = speechSynthesis.getVoices(), want = BCP[l] || 'en-IN';
    for (var i = 0; i < vs.length; i++) if (vs[i].lang === want) return vs[i];
    for (i = 0; i < vs.length; i++) if (vs[i].lang && vs[i].lang.slice(0, 2) === want.slice(0, 2)) return vs[i];
    return null;
  }
  function speak(text, l) {
    if (!('speechSynthesis' in window) || !text) return false;
    var u = new SpeechSynthesisUtterance(text);
    u.lang = BCP[l || lang] || 'en-IN';
    var v = voiceFor(l || lang);
    if (v) u.voice = v;
    u.rate = 0.9;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
    return true;
  }
  function hasVoice(l) { return !!voiceFor(l); }

  // Per-person settings kept on this device: the language a reminder is read in, and whether it is read aloud.
  function personPref(pid) { try { return JSON.parse(localStorage.getItem('uh-voice-' + pid) || '{}'); } catch (_) { return {}; } }
  function setPersonPref(pid, v) { try { localStorage.setItem('uh-voice-' + pid, JSON.stringify(v)); } catch (_) {} }

  var FOODSAY = { ta: TA, te: TE, hi: HI };
  function doseLine(personName, med, l) {
    l = l || lang;
    var note = med.note || '', d = FOODSAY[l] || {};
    var n = d[note] || note;
    return [personName, med.name, n].filter(Boolean).join(', ');
  }

  // ---- first-run picker -------------------------------------------------------------------------------------
  function css() {
    if (document.getElementById('uhl-css')) return;
    var s = document.createElement('style');
    s.id = 'uhl-css';
    s.textContent = '.uhl{position:fixed;inset:0;z-index:90;background:#F2F2EF;display:flex;flex-direction:column;overflow-y:auto;padding:max(18px,env(safe-area-inset-top)) 0 max(24px,env(safe-area-inset-bottom));font-family:inherit;color:#1D1D1F}'
      + '.uhl-in{max-width:520px;width:100%;margin:0 auto;display:flex;flex-direction:column;flex:1}'
      + '.uhl-brand{display:flex;align-items:center;gap:10px;margin:10px 20px 0}.uhl-logo{width:44px;height:44px;border-radius:12px;background:url(/brand/svg/user-icon.svg) center/contain no-repeat;display:grid;place-items:center;color:transparent;font-size:0}'
      + '.uhl h1{font-size:30px;letter-spacing:-.6px;margin:18px 20px 0;line-height:1.1}.uhl .uhl-ta{font-size:19px;font-weight:600;color:#3A3A3C;margin:4px 20px 0}'
      + '.uhl-list{background:#fff;border-radius:16px;margin:18px 16px 0;overflow:hidden}'
      + '.uhl-row,.lg-row{display:flex;align-items:center;gap:14px;padding:14px 16px;width:100%;text-align:left;position:relative;font:inherit;color:inherit;background:none;border:0;cursor:pointer}'
      + '.uhl-row+.uhl-row:before,.lg-row+.lg-row:before{content:"";position:absolute;left:16px;right:0;top:0;height:.5px;background:#E5E5EA}'
      + '.uhl-row.on,.lg-row.on{background:#F4F8FF}.uhl-big{font-size:21px;font-weight:600}.uhl-sub{font-size:13px;color:#86868B}'
      + '.uhl-rad{width:24px;height:24px;border-radius:12px;border:2px solid #C7C7CC;margin-left:auto;flex:none;transition:border .15s}.on>.uhl-rad{border:7px solid #2F5BFF}'
      + '.uhl-sect{font-size:13px;font-weight:600;color:#86868B;margin:20px 32px 8px;text-transform:uppercase;letter-spacing:.2px}'
      + '.uhl-card{background:#fff;border-radius:18px;margin:0 16px;padding:12px 16px;display:flex;align-items:center;gap:12px}'
      + '.uhl-dot{width:40px;height:40px;border-radius:20px;background:#FF9F0A;color:#fff;display:grid;place-items:center;font-weight:700;flex:none}'
      + '.uhl-play{margin-left:auto;width:36px;height:36px;border-radius:18px;background:#EEF2FF;color:#2F5BFF;border:0;font-size:15px;cursor:pointer;flex:none}'
      + '.uhl-note{font-size:13px;color:#86868B;margin:8px 22px 0}.uhl-go{margin:auto 16px 0;padding-top:24px}'
      + '.uhl-btn{display:block;width:100%;height:52px;border-radius:26px;background:#2F5BFF;color:#fff;font:inherit;font-weight:600;font-size:17px;border:0;cursor:pointer}'
      + '.lg-sw{width:51px;height:31px;border-radius:16px;background:#E5E5EA;position:relative;margin-left:auto;flex:none;border:0;cursor:pointer;transition:background .2s}.lg-sw:after{content:"";position:absolute;left:2px;top:2px;width:27px;height:27px;border-radius:14px;background:#fff;box-shadow:0 2px 4px rgba(0,0,0,.2);transition:left .2s}.lg-sw.on{background:#34C759}.lg-sw.on:after{left:22px}'
      + '.lg-pill{font-size:13px;color:#86868B;margin-left:auto}.lg-chips{display:flex;gap:6px;margin-left:auto}.lg-chip{padding:6px 11px;border-radius:15px;background:#F2F2EF;font:inherit;font-size:13px;font-weight:600;border:0;cursor:pointer;color:#1D1D1F}.lg-chip.on{background:#1D1D1F;color:#fff}';
    document.head.appendChild(s);
  }

  var SAMPLE = { en: ['After food · 8:30 AM', 'Amma, Metformin 500 mg, after food'], ta: ['காலை உணவுக்குப் பின் · 8:30 AM', 'அம்மா, Metformin 500 mg, உணவுக்குப் பின்'],
                 te: ['భోజనం తర్వాత · 8:30 AM', 'అమ్మ, Metformin 500 mg, భోజనం తర్వాత'],
                 hi: ['खाने के बाद · 8:30 AM', 'अम्मा, Metformin 500 mg, खाने के बाद'] };
  var SAMPLE_WHO = { en: 'Amma', ta: 'அம்மா', te: 'అమ్మ', hi: 'अम्मा' };

  function picker(save) {
    css();
    return new Promise(function (done) {
      var pick = lang, el = document.createElement('div');
      el.className = 'uhl';
      el.setAttribute('data-noi18n', '');
      el.setAttribute('role', 'dialog');
      el.setAttribute('aria-label', 'Choose your language');
      function draw() {
        el.innerHTML = '<div class="uhl-in"><div class="uhl-brand"><div class="uhl-logo">U</div><div><span style="font-size:18px;letter-spacing:-.01em">Urban <b>Health</b></span></div></div>'
          + '<h1>Choose your language</h1><div class="uhl-ta" lang="ta">உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்</div>'
          + '<div class="uhl-list" role="radiogroup">' + ['en', 'hi', 'ta', 'te'].map(function (l) {
            return '<button class="uhl-row ' + (pick === l ? 'on' : '') + '" role="radio" aria-checked="' + (pick === l) + '" data-l="' + l + '" lang="' + BCP[l] + '"><div><div class="uhl-big">' + NAMES[l] + '</div><div class="uhl-sub">' + { en: 'English', ta: 'Tamil', te: 'Telugu', hi: 'Hindi' }[l] + '</div></div><span class="uhl-rad"></span></button>';
          }).join('') + '</div>'
          + '<div class="uhl-sect">Preview</div><div class="uhl-card" lang="' + BCP[pick] + '"><div class="uhl-dot">' + SAMPLE_WHO[pick].charAt(0) + '</div><div style="flex:1;min-width:0"><b style="font-size:15px">' + SAMPLE_WHO[pick] + ' · Metformin 500 mg</b><div class="uhl-sub">' + SAMPLE[pick][0] + '</div></div><button class="uhl-play" aria-label="Play a sample">▶</button></div>'
          + '<p class="uhl-note">Medicine names stay as printed on the strip. Change language any time in Settings.</p>'
          + '<div class="uhl-go"><button class="uhl-btn">' + (pick === 'en' ? 'Continue' : (pick === 'ta' ? 'தொடரவும் · Continue' : pick === 'hi' ? 'आगे बढ़ें · Continue' : 'కొనసాగించు · Continue')) + '</button></div></div>';
        el.querySelectorAll('[data-l]').forEach(function (b) { b.onclick = function () { pick = b.getAttribute('data-l'); draw(); }; });
        el.querySelector('.uhl-play').onclick = function () { if (!speak(SAMPLE[pick][1], pick)) alertless(); };
        el.querySelector('.uhl-btn').onclick = function () {
          set(pick, save);
          try { localStorage.setItem(CHOSEN, '1'); } catch (_) {}
          el.remove();
          done(pick);
        };
      }
      function alertless() { var n = el.querySelector('.uhl-note'); if (n) n.textContent = 'This phone has no voice for that language yet. Reminders still arrive as notifications.'; }
      draw();
      document.body.appendChild(el);
    });
  }

  function set(l, save) {
    if (!NAMES[l]) return;
    var was = lang;
    lang = l;
    try { localStorage.setItem(KEY, l); } catch (_) {}
    document.documentElement.lang = BCP[l];
    if (was !== l) { busy = true; try { walk(document.body); } finally { mo.takeRecords(); busy = false; } }
    mergeShared();
    if (save) { try { save(l); } catch (_) {} }
  }

  window.UHL = {
    get: function () { return lang; }, name: function (l) { return NAMES[l || lang]; }, names: NAMES,
    chosen: function () { try { return !!localStorage.getItem(CHOSEN); } catch (_) { return true; } },
    adopt: function (serverLang) { if (serverLang && serverLang !== 'en' && NAMES[serverLang] && serverLang !== lang) { set(serverLang); try { localStorage.setItem(CHOSEN, '1'); } catch (_) {} } },
    set: set, t: function (s) { return tr(s) || s; }, picker: picker, css: css,
    speak: speak, hasVoice: hasVoice, personPref: personPref, setPersonPref: setPersonPref, doseLine: doseLine
  };

  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);
})();

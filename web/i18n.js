/* Urban Health — app languages (English, Tamil, Telugu).
   The app is written in English. In another language this file swaps the visible words for their translation
   as pages render, so every screen follows without its own copy of the strings. Medicine names, people's names,
   numbers and anything a person typed are never in the table, so they always stay exactly as entered.
   Every Tamil and Telugu line must be checked by a native speaker before each release. */
(function () {
  'use strict';
  var KEY = 'uh-lang', CHOSEN = 'uh-lang-chosen';
  var NAMES = { en: 'English', ta: 'தமிழ்', te: 'తెలుగు' };
  var BCP = { en: 'en-IN', ta: 'ta-IN', te: 'te-IN' };

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
    'emergency contact, not in family yet': 'அவசரத் தொடர்பு, இன்னும் குடும்பத்தில் இல்லை', 'emergency contact': 'அவசரத் தொடர்பு'
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
    'Reminders sent to this account arrive in this language.': 'ఈ ఖాతాకు రిమైండర్‌లు ఈ భాషలో వస్తాయి.'
  };

  // Words with a number or a name inside them.
  var RULES = {
    ta: [
      [/^Morning (\d{1,2}:\d{2})$/, 'காலை $1'], [/^Afternoon (\d{1,2}:\d{2})$/, 'மதியம் $1'], [/^Evening (\d{1,2}:\d{2})$/, 'மாலை $1'],
      [/^Night (\d{1,2}:\d{2})$/, 'இரவு $1'], [/^Week (\d+)$/, 'வாரம் $1'], [/^Welcome, (.+)$/, 'வரவேற்கிறோம், $1'],
      [/^Invite sent to (.+)$/, '$1-க்கு அழைப்பு அனுப்பப்பட்டது'], [/^Sending a code to (.+)$/, '$1-க்குக் குறியீடு அனுப்புகிறோம்'],
      [/^Renews in (\d+) days$/, '$1 நாட்களில் புதுப்பிக்க வேண்டும்'], [/^(\d+) left$/, '$1 மீதம்'],
      [/^(\d+) left today$/, 'இன்று $1 மீதம்'], [/^(.+) \(you\)$/, '$1 (நீங்கள்)'], [/^Step (\d) of (\d)$/i, 'படி $1 / $2'],
      [/^Up to ₹(.+) a family a year$/, 'ஒரு குடும்பத்திற்கு ஆண்டுக்கு ₹$1 வரை'], [/^₹(.+) a family a year$/, 'ஒரு குடும்பத்திற்கு ஆண்டுக்கு ₹$1'],
      [/^₹(.+) a year for the senior, on top of family cover$/, 'மூத்தவருக்கு ஆண்டுக்கு ₹$1, குடும்பக் காப்பீட்டுக்கு மேல்'],
      [/^Lab reports, prescriptions and scans for (.+) appear here, newest first\.$/, '$1-இன் ஆய்வக அறிக்கைகள், மருந்துச் சீட்டுகள், ஸ்கேன்கள் இங்கே, புதியவை முதலில்.']
    ],
    te: [
      [/^Morning (\d{1,2}:\d{2})$/, 'ఉదయం $1'], [/^Afternoon (\d{1,2}:\d{2})$/, 'మధ్యాహ్నం $1'], [/^Evening (\d{1,2}:\d{2})$/, 'సాయంత్రం $1'],
      [/^Night (\d{1,2}:\d{2})$/, 'రాత్రి $1'], [/^Week (\d+)$/, 'వారం $1']
    ]
  };
  var DICT = { ta: TA, te: TE };

  var lang = 'en';
  try { lang = localStorage.getItem(KEY) || 'en'; } catch (_) {}
  if (!NAMES[lang]) lang = 'en';

  var DAYS = { ta: ['ஞாயிறு', 'திங்கள்', 'செவ்வாய்', 'புதன்', 'வியாழன்', 'வெள்ளி', 'சனி'], te: ['ఆదివారం', 'సోమవారం', 'మంగళవారం', 'బుధవారం', 'గురువారం', 'శుక్రవారం', 'శనివారం'] };
  var MONTHS = { ta: ['ஜனவரி', 'பிப்ரவரி', 'மார்ச்', 'ஏப்ரல்', 'மே', 'ஜூன்', 'ஜூலை', 'ஆகஸ்ட்', 'செப்டம்பர்', 'அக்டோபர்', 'நவம்பர்', 'டிசம்பர்'],
                 te: ['జనవరి', 'ఫిబ్రవరి', 'మార్చి', 'ఏప్రిల్', 'మే', 'జూన్', 'జూలై', 'ఆగస్టు', 'సెప్టెంబర్', 'అక్టోబర్', 'నవంబర్', 'డిసెంబర్'] };
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

  var FOODSAY = { ta: TA, te: TE };
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
    s.textContent = '.uhl{position:fixed;inset:0;z-index:90;background:#F2F2F7;display:flex;flex-direction:column;overflow-y:auto;padding:max(18px,env(safe-area-inset-top)) 0 max(24px,env(safe-area-inset-bottom));font-family:inherit;color:#1D1D1F}'
      + '.uhl-in{max-width:520px;width:100%;margin:0 auto;display:flex;flex-direction:column;flex:1}'
      + '.uhl-brand{display:flex;align-items:center;gap:10px;margin:10px 20px 0}.uhl-logo{width:44px;height:44px;border-radius:12px;background:linear-gradient(135deg,#0A84FF,#5E5CE6);display:grid;place-items:center;color:#fff;font-weight:800;font-size:18px}'
      + '.uhl h1{font-size:30px;letter-spacing:-.6px;margin:18px 20px 0;line-height:1.1}.uhl .uhl-ta{font-size:19px;font-weight:600;color:#3A3A3C;margin:4px 20px 0}'
      + '.uhl-list{background:#fff;border-radius:16px;margin:18px 16px 0;overflow:hidden}'
      + '.uhl-row,.lg-row{display:flex;align-items:center;gap:14px;padding:14px 16px;width:100%;text-align:left;position:relative;font:inherit;color:inherit;background:none;border:0;cursor:pointer}'
      + '.uhl-row+.uhl-row:before,.lg-row+.lg-row:before{content:"";position:absolute;left:16px;right:0;top:0;height:.5px;background:#E5E5EA}'
      + '.uhl-row.on,.lg-row.on{background:#F4F8FF}.uhl-big{font-size:21px;font-weight:600}.uhl-sub{font-size:13px;color:#86868B}'
      + '.uhl-rad{width:24px;height:24px;border-radius:12px;border:2px solid #C7C7CC;margin-left:auto;flex:none;transition:border .15s}.on>.uhl-rad{border:7px solid #0071E3}'
      + '.uhl-sect{font-size:13px;font-weight:600;color:#86868B;margin:20px 32px 8px;text-transform:uppercase;letter-spacing:.2px}'
      + '.uhl-card{background:#fff;border-radius:18px;margin:0 16px;padding:12px 16px;display:flex;align-items:center;gap:12px}'
      + '.uhl-dot{width:40px;height:40px;border-radius:20px;background:#FF9F0A;color:#fff;display:grid;place-items:center;font-weight:700;flex:none}'
      + '.uhl-play{margin-left:auto;width:36px;height:36px;border-radius:18px;background:#E8F1FF;color:#0071E3;border:0;font-size:15px;cursor:pointer;flex:none}'
      + '.uhl-note{font-size:13px;color:#86868B;margin:8px 22px 0}.uhl-go{margin:auto 16px 0;padding-top:24px}'
      + '.uhl-btn{display:block;width:100%;height:52px;border-radius:26px;background:#0071E3;color:#fff;font:inherit;font-weight:600;font-size:17px;border:0;cursor:pointer}'
      + '.lg-sw{width:51px;height:31px;border-radius:16px;background:#E5E5EA;position:relative;margin-left:auto;flex:none;border:0;cursor:pointer;transition:background .2s}.lg-sw:after{content:"";position:absolute;left:2px;top:2px;width:27px;height:27px;border-radius:14px;background:#fff;box-shadow:0 2px 4px rgba(0,0,0,.2);transition:left .2s}.lg-sw.on{background:#34C759}.lg-sw.on:after{left:22px}'
      + '.lg-pill{font-size:13px;color:#86868B;margin-left:auto}.lg-chips{display:flex;gap:6px;margin-left:auto}.lg-chip{padding:6px 11px;border-radius:15px;background:#F2F2F7;font:inherit;font-size:13px;font-weight:600;border:0;cursor:pointer;color:#1D1D1F}.lg-chip.on{background:#1D1D1F;color:#fff}';
    document.head.appendChild(s);
  }

  var SAMPLE = { en: ['After food · 8:30 AM', 'Amma, Metformin 500 mg, after food'], ta: ['காலை உணவுக்குப் பின் · 8:30 AM', 'அம்மா, Metformin 500 mg, உணவுக்குப் பின்'],
                 te: ['భోజనం తర్వాత · 8:30 AM', 'అమ్మ, Metformin 500 mg, భోజనం తర్వాత'] };
  var SAMPLE_WHO = { en: 'Amma', ta: 'அம்மா', te: 'అమ్మ' };

  function picker(save) {
    css();
    return new Promise(function (done) {
      var pick = lang, el = document.createElement('div');
      el.className = 'uhl';
      el.setAttribute('data-noi18n', '');
      el.setAttribute('role', 'dialog');
      el.setAttribute('aria-label', 'Choose your language');
      function draw() {
        el.innerHTML = '<div class="uhl-in"><div class="uhl-brand"><div class="uhl-logo">U</div><div><b style="font-size:17px">Urban Health</b></div></div>'
          + '<h1>Choose your language</h1><div class="uhl-ta" lang="ta">உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்</div>'
          + '<div class="uhl-list" role="radiogroup">' + ['en', 'ta', 'te'].map(function (l) {
            return '<button class="uhl-row ' + (pick === l ? 'on' : '') + '" role="radio" aria-checked="' + (pick === l) + '" data-l="' + l + '" lang="' + BCP[l] + '"><div><div class="uhl-big">' + NAMES[l] + '</div><div class="uhl-sub">' + { en: 'English', ta: 'Tamil', te: 'Telugu' }[l] + '</div></div><span class="uhl-rad"></span></button>';
          }).join('') + '</div>'
          + '<div class="uhl-sect">Preview</div><div class="uhl-card" lang="' + BCP[pick] + '"><div class="uhl-dot">' + SAMPLE_WHO[pick].charAt(0) + '</div><div style="flex:1;min-width:0"><b style="font-size:15px">' + SAMPLE_WHO[pick] + ' · Metformin 500 mg</b><div class="uhl-sub">' + SAMPLE[pick][0] + '</div></div><button class="uhl-play" aria-label="Play a sample">▶</button></div>'
          + '<p class="uhl-note">Medicine names stay as printed on the strip. Change language any time in Settings.</p>'
          + '<div class="uhl-go"><button class="uhl-btn">' + (pick === 'en' ? 'Continue' : (pick === 'ta' ? 'தொடரவும் · Continue' : 'కొనసాగించు · Continue')) + '</button></div></div>';
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

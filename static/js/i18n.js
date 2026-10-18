/* Language of the public website: English (default), Tagalog, Waray-Waray.
   Chosen in the side menu (base.html → "Language"). Saved in the browser
   (cookie "tunga_lang"), so it stays when the person opens other pages.

   Only the website's own words are translated: menus, buttons, headings,
   labels, messages and form hints. Content written by the offices
   (announcement titles and text, news, events, service details, office names,
   people's names) stays as it was written.

   HOW TO FIX OR ADD A WORD
   Find the English text below and change the Tagalog / Waray words:
       "English text": ["Tagalog", "Waray-Waray"],
   The English must be exactly what shows on the page (capital letters too).
   A word that is not listed here simply stays in English.
   To keep something in English always, add data-no-translate to its tag. */
(function () {
  'use strict';

  var T = {
    /* ---------- header, menu, footer ---------- */
    "Home": ["Pangunahing Pahina", "Panguna nga Pahina "],
    "About": ["Tungkol", "Mahitungod"],
    "About Us": ["Tungkol sa Amin", "Mahitungod ha Amon"],
    "Offices": ["Mga Tanggapan", "Mga Opisina"],
    "All Offices": ["Lahat ng Tanggapan", "Ngatanan nga Opisina"],
    "Announcements": ["Mga Anunsyo", "Mga Pahibaro"],
    "Announcement": ["Anunsyo", "Pahibaro"],
    "Gallery": ["Galeriya", "Galeriya"],
    "Contact Us": ["Makipag-ugnayan", "Kontaka Kami"],
    "Contact us": ["Makipag-ugnayan sa amin", "Kontaka kami"],
    "History": ["Kasaysayan", "Kasaysayan"],
    "Barangays": ["Mga Barangay", "Mga Barangay"],
    "Municipal Officials": ["Mga Opisyal ng Bayan", "Mga Opisyal han Bungto"],
    "Login / Sign Up": ["Mag-login / Mag-sign Up", "Mag-login / Magparehistro"],
    "MUNICIPALITY OF": ["BAYAN NG", "BUNGTO HAN"],
    "Quick Links": ["Mabilisang Link", "Dali nga mga Link"],
    "Public Assistance": ["Tulong sa Publiko", "Bulig ha Publiko"],
    "Privacy Policy": ["Patakaran sa Privacy", "Polisiya han Privacy"],
    "Terms of Use": ["Mga Tuntunin ng Paggamit", "Mga Termino han Paggamit"],
    "Terms Of Use": ["Mga Tuntunin ng Paggamit", "Mga Termino han Paggamit"],
    "Accessibility Statement": ["Pahayag sa Accessibility", "Pahayag han Accessibility"],
    "Accessibility": ["Aksesibilidad", "Aksesibilidad"],
    "Have any questions or need help? We're here for you.": ["May tanong o kailangan ng tulong? Narito kami para sa iyo.", "May-ada pakiana o kinahanglan hin bulig? Ania kami para ha imo."],
    "© Municipality of Tunga. All Rights Reserved.": ["© Bayan ng Tunga. Nakalaan ang Lahat ng Karapatan.", "© Bungto han Tunga. Reserbado an Ngatanan nga Katungod."],
    "Search the site...": ["Maghanap sa website...", "Pamilnga ha website..."],
    "Search": ["Maghanap", "Pamilnga"],

    /* ---------- testing notice ---------- */
    "Testing phase:": ["Sinusubukan pa:", "Ginsusulay pa:"],
    "The Tunga Digital Governance Portal is currently in its testing phase. All content on this website, including announcements, news, events, office details, services, and forms, is sample data used for demonstration purposes only and is not official information from the Municipality of Tunga, Leyte. Forms submitted here will not be processed. For official transactions and information, please visit the Municipal Hall.":
      ["Ang Tunga Digital Governance Portal ay kasalukuyang sinusubukan pa. Ang lahat ng nilalaman ng website na ito, kasama ang mga anunsiyo, balita, kaganapan, detalye ng tanggapan, serbisyo, at form, ay halimbawang datos lamang para sa demonstrasyon at hindi opisyal na impormasyon mula sa Bayan ng Tunga, Leyte. Hindi ipoproseso ang mga form na ipapasa rito. Para sa mga opisyal na transaksiyon at impormasyon, mangyaring pumunta sa Munisipyo.",
       "An Tunga Digital Governance Portal ginsusulay pa yana. An ngatanan nga sulod hini nga website, upod an mga pahibaro, balita, hitabo, detalye han opisina, serbisyo, ngan mga form, pananglitan la nga datos para ha demonstrasyon ngan diri opisyal nga impormasyon tikang ha Bungto han Tunga, Leyte. Diri ipoproseso an mga form nga ipapasa dinhi. Para ha opisyal nga transaksyon ngan impormasyon, alayon pagkadto ha Munisipyo."],

    /* ---------- side menu ---------- */
    "My account": ["Aking account", "Akon account"],
    "Account": ["Account", "Account"],
    "Profile and your submitted forms": ["Profile at ang mga form na ipinasa mo", "Profile ngan an imo mga ginpasa nga form"],
    "Settings": ["Mga Setting", "Mga Setting"],
    "Password and preferences": ["Password at mga kagustuhan", "Password ngan mga karuyag"],
    "Notifications": ["Mga Abiso", "Mga Notipikasyon"],
    "Updates from the municipality": ["Mga update mula sa munisipyo", "Mga update tikang ha munisipyo"],
    "New updates from the municipality": ["Mga bagong update mula sa munisipyo", "Mga bag-o nga update tikang ha munisipyo"],
    "Mark all as read": ["Markahang nabasa lahat", "Markaha nga nabasa ngatanan"],
    "No notifications.": ["Walang abiso.", "Waray notipikasyon."],
    "No new updates in the last 30 days.": ["Walang bagong update sa nakaraang 30 araw.", "Waray bag-o nga update ha naglabay nga 30 ka adlaw."],
    "New": ["Bago", "Bag-o"],
    "NEW": ["BAGO", "BAG-O"],
    "Urgent": ["Agaran", "Dinalian"],
    "Help": ["Tulong", "Bulig"],
    "Help & Support": ["Tulong at Suporta", "Bulig ngan Suporta"],
    "Contact the municipality": ["Makipag-ugnayan sa munisipyo", "Kontaka an munisipyo"],
    "Rate this website": ["I-rate ang website", "I-rate ini nga website"],
    "Tell us how we can improve": ["Sabihin kung paano pa kami gagaling", "Isugid kon paonan-o kami mapauswag"],
    "Log Out": ["Mag-log Out", "Mag-log Out"],
    "Citizen": ["Mamamayan", "Lumulupyo"],
    "Office Representative": ["Kinatawan ng Tanggapan", "Representante han Opisina"],
    "Manage the whole website": ["Pamahalaan ang buong website", "Dumalahon an bug-os nga website"],
    "Post and manage your office's content": ["Mag-post at pamahalaan ang nilalaman ng iyong tanggapan", "Mag-post ngan dumalahon an sulod han imo opisina"],
    "Language": ["Wika", "Yinaknan"],
    "Change profile picture": ["Palitan ang larawan sa profile", "Balyui an litrato ha profile"],
    "Remove this notification": ["Alisin ang abisong ito", "Kuhaa ini nga notipikasyon"],
    "Close": ["Isara", "Sirad-i"],
    "Close menu": ["Isara ang menu", "Sirad-i an menu"],

    /* ---------- My Account / Settings / rating pop-ups ---------- */
    "My Account": ["Aking Account", "Akon Account"],
    "Profile picture": ["Larawan sa profile", "Litrato ha profile"],
    "Upload photo": ["Mag-upload ng larawan", "Mag-upload hin litrato"],
    "Remove": ["Alisin", "Kuhaa"],
    "JPG, PNG or WEBP, up to 5 MB.": ["JPG, PNG o WEBP, hanggang 5 MB.", "JPG, PNG o WEBP, tubtob 5 MB."],
    "Your name, email, mobile number and profile picture": ["Ang iyong pangalan, email, numero ng mobile at larawan sa profile", "An imo ngaran, email, numero han mobile ngan litrato ha profile"],
    "Full Name": ["Buong Pangalan", "Bug-os nga Ngaran"],
    "First Name": ["Pangalan", "Ngaran"],
    "Last Name": ["Apelyido", "Apelyido"],
    "Username": ["Username", "Username"],
    "Email Address": ["Email Address", "Email Address"],
    "Email address cannot be changed.": ["Hindi na mapapalitan ang email address.", "Diri na mababalyuan an email address."],
    "Mobile Number": ["Numero ng Mobile", "Numero han Mobile"],
    "Mobile Number (optional)": ["Numero ng Mobile (opsyonal)", "Numero han Mobile (opsyonal)"],
    "Save Changes": ["I-save ang mga Pagbabago", "I-save an mga Pagbag-o"],
    "Save": ["I-save", "I-save"],
    "Cancel": ["Kanselahin", "Kanselaha"],
    "My Form Submissions": ["Aking mga Ipinasang Form", "Akon mga Ginpasa nga Form"],
    "The forms you filled out online, and their status. Offices can no longer process requests that aren't finished yet.":
      ["Ang mga form na sinagutan mo online at ang kanilang katayuan. Hindi na maipoproseso ng mga tanggapan ang mga kahilingang hindi pa tapos.",
       "An mga form nga imo ginpun-an online ngan an ira kahimtang. Diri na maproseso han mga opisina an mga hangyo nga diri pa tapos."],
    "Loading…": ["Naglo-load…", "Ginlo-load…"],
    "Loading form…": ["Nilo-load ang form…", "Ginlo-load an form…"],
    "You haven't submitted any forms online yet.": ["Wala ka pang naipapasang form online.", "Waray ka pa nakapasa hin form online."],
    "Submitted": ["Naipasa", "Ginpasa"],
    "Received": ["Natanggap", "Nakarawat"],
    "Processing": ["Pinoproseso", "Ginpoproseso"],
    "Ready for pickup": ["Handa nang kunin", "Andam na kuhaon"],
    "Declined": ["Tinanggihan", "Ginbalibaran"],
    "Sent to the office. Waiting for the office to receive it.": ["Naipadala sa tanggapan. Hinihintay na matanggap ito ng tanggapan.", "Ginpadara ha opisina. Ginhuhulat nga karawaton ini han opisina."],
    "The office has received your form.": ["Natanggap na ng tanggapan ang iyong form.", "Nakarawat na han opisina an imo form."],
    "The office is working on your request.": ["Inaasikaso na ng tanggapan ang iyong kahilingan.", "Gin-aatiman na han opisina an imo hangyo."],
    "Your request is ready. You may get it at the office.": ["Handa na ang iyong kahilingan. Maaari mo itong kunin sa tanggapan.", "Andam na an imo hangyo. Puydi mo ini kuhaon ha opisina."],
    "The office could not process your request. See the note from the office.": ["Hindi naproseso ng tanggapan ang iyong kahilingan. Tingnan ang tala mula sa tanggapan.", "Diri naproseso han opisina an imo hangyo. Kitaa an nota tikang ha opisina."],
    "Note from the office": ["Tala mula sa tanggapan", "Nota tikang ha opisina"],
    "Download my filled form": ["I-download ang aking sinagutang form", "I-download an akon ginpun-an nga form"],
    "How satisfied are you with this service?": ["Gaano ka nasiyahan sa serbisyong ito?", "Kontento ka ba hini nga serbisyo?"],
    "Send rating": ["Ipadala ang rating", "Ipadara an rating"],
    "Comment or suggestion (optional)": ["Komento o mungkahi (opsyonal)", "Komento o suhestyon (opsyonal)"],
    "Very satisfied": ["Lubos na nasiyahan", "Kontento gud"],
    "Satisfied": ["Nasiyahan", "Kontento"],
    "Neutral": ["Katamtaman", "Tunga-tunga"],
    "Dissatisfied": ["Hindi nasiyahan", "Diri kontento"],
    "Very dissatisfied": ["Lubos na hindi nasiyahan", "Diri gud kontento"],
    "Current Password": ["Kasalukuyang Password", "Yana nga Password"],
    "New Password": ["Bagong Password", "Bag-o nga Password"],
    "Confirm New Password": ["Kumpirmahin ang Bagong Password", "Kumpirmaha an Bag-o nga Password"],
    "Update Password": ["I-update ang Password", "I-update an Password"],
    "At least 8 characters": ["Hindi bababa sa 8 character", "Kaminusan 8 ka character"],
    "One uppercase letter": ["Isang malaking titik", "Usa nga dako nga letra"],
    "One lowercase letter": ["Isang maliit na titik", "Usa nga gutiay nga letra"],
    "One number": ["Isang numero", "Usa nga numero"],
    "One special character (e.g. ! @ # $ %)": ["Isang espesyal na karakter (hal. ! @ # $ %)", "Usa nga espesyal nga karakter (pananglitan ! @ # $ %)"],
    "Both passwords match": ["Magkatugma ang dalawang password", "Parehas an duha nga password"],
    "Delete my account": ["Burahin ang aking account", "Panasa an akon account"],
    "This permanently deletes your account and your personal data from the Tunga Portal. It can't be undone.":
      ["Permanenteng mabubura nito ang iyong account at personal na datos sa Tunga Portal. Hindi na ito maibabalik.",
       "Permanente nga mapapanas hini an imo account ngan personal nga datos ha Tunga Portal. Diri na ini mabalik."],
    "You can create a new account later with the same email.": ["Maaari kang gumawa ng bagong account sa ibang pagkakataon gamit ang parehong email.", "Puydi ka maghimo hin bag-o nga account ha sunod gamit an pareho nga email."],
    "Enter your password to confirm": ["Ilagay ang iyong password para kumpirmahin", "Ibutang an imo password para kumpirmahon"],
    "I understand that my account and data will be permanently deleted.": ["Nauunawaan ko na permanenteng mabubura ang aking account at datos.", "Nasabtan ko nga permanente nga mapapanas an akon account ngan datos."],
    "Office Representative and Super Admin accounts can't be deleted here. Please contact the Super Admin.": ["Hindi mabubura dito ang mga account ng Kinatawan ng Tanggapan at Super Admin. Makipag-ugnayan sa Super Admin.", "Diri mapapanas dinhi an mga account han Representante han Opisina ngan Super Admin. Alayon pagkontak ha Super Admin."],
    "How easy is it to find information and use the services on the Tunga Portal? Your feedback helps us improve it.":
      ["Gaano kadaling makahanap ng impormasyon at gumamit ng mga serbisyo sa Tunga Portal? Makatutulong ang iyong feedback para mapabuti ito.",
       "Kadali ba pagbiling hin impormasyon ngan paggamit han mga serbisyo ha Tunga Portal? Makakabulig an imo feedback para mapauswag ini."],
    "Your rating": ["Ang iyong rating", "An imo rating"],
    "Send feedback": ["Ipadala ang feedback", "Ipadara an feedback"],
    "What did you like? What should we add or fix? (optional)": ["Ano ang nagustuhan mo? Ano ang dapat naming idagdag o ayusin? (opsyonal)", "Ano an imo naruyagan? Ano an amon angay idugang o ayadon? (opsyonal)"],

    /* ---------- home page ---------- */
    "Building a Better": ["Itaguyod ang Mas Maunlad na", "Pagtukod hin Mas Mauswag nga"],
    "Your government is here to serve you. Transparent. Accessible. Reliable.": ["Narito ang iyong pamahalaan para maglingkod sa iyo. Bukas. Abot-kamay. Maaasahan.", "Ania an imo gobyerno para magserbisyo ha imo. Transparent. Mahirani. Masasarigan."],
    "Discover Services": ["Tuklasin ang mga Serbisyo", "Kitaa an mga Serbisyo"],
    "View Announcements": ["Tingnan ang mga Anunsiyo", "Kitaa an mga Pahibaro"],
    "Browse Offices": ["Tingnan ang mga Tanggapan", "Kitaa an mga Opisina"],
    "Emergency Contact Information": ["Mga Numero para sa Emergency", "Mga Numero para ha Emerhensya"],
    "Emergency Hotlines": ["Mga Hotline para sa Emergency", "Mga Hotline para ha Emerhensya"],
    "CALL": ["TUMAWAG", "TAWAG"],
    "Call": ["Tumawag", "Tawag"],
    "Latest Announcements": ["Pinakabagong mga Anunsiyo", "Pinakabag-o nga mga Pahibaro"],
    "Upcoming Events": ["Mga Paparating na Kaganapan", "Maabot nga mga Hitabo"],
    "News": ["Balita", "Mga Balita"],
    "Photo Gallery": ["Galeriya ng mga Larawan", "Galeriya han mga Litrato"],
    "View All": ["Tingnan Lahat", "Kitaa Ngatanan"],
    "View all": ["Tingnan lahat", "Kitaa ngatanan"],
    "Read more": ["Magbasa pa", "Basaha pa"],
    "No upcoming events at this time.": ["Walang paparating na kaganapan sa ngayon.", "Waray maabot nga hitabo yana."],
    "No upcoming events scheduled yet.": ["Wala pang nakatakdang kaganapan.", "Waray pa nakaiskedyul nga hitabo."],
    "No upcoming events scheduled.": ["Walang nakatakdang kaganapan.", "Waray nakaiskedyul nga hitabo."],
    "No news published yet. Check back soon.": ["Wala pang nailalathalang balita. Bumalik muli sa susunod.", "Waray pa nagawas nga balita. Balik la ha sunod."],
    "No news posted yet.": ["Wala pang nai-post na balita.", "Waray pa na-post nga balita."],

    /* ---------- announcements page ---------- */
    "Announcements, News": ["Mga Anunsiyo, Balita", "Mga Pahibaro, Balita"],
    "and Updates": ["at Update", "ngan Update"],
    "Stay informed with the latest announcements, news, events and updates from the Municipality of Tunga and all its offices.":
      ["Manatiling may alam sa pinakabagong mga anunsiyo, balita, kaganapan at update mula sa Bayan ng Tunga at sa lahat ng tanggapan nito.",
       "Pabilin nga may maaram ha pinakabag-o nga mga pahibaro, balita, hitabo ngan update tikang ha Bungto han Tunga ngan ha ngatanan nga opisina hini."],
    "All Updates": ["Lahat ng Update", "Ngatanan nga Update"],
    "News and Updates": ["Mga Balita at Update", "Mga Balita ngan Update"],
    "Events": ["Mga Kaganapan", "Mga Hitabo"],
    "Event": ["Kaganapan", "Hitabo"],
    "From Our Offices": ["Mula sa Aming mga Tanggapan", "Tikang ha Amon mga Opisina"],
    "Search announcements, news...": ["Maghanap ng anunsiyo, balita...", "Bilnga an pahibaro, balita..."],
    "Featured": ["Tampok", "Tampok"],
    "Latest News": ["Pinakabagong Balita", "Pinakabag-o nga Balita"],
    "Most Read": ["Pinakabinabasa", "Pinakaginbabasa"],
    "Search News": ["Maghanap ng Balita", "Bilnga an Balita"],
    "Categories": ["Mga Kategorya", "Mga Kategorya"],
    "All Categories": ["Lahat ng Kategorya", "Ngatanan nga Kategorya"],
    "Topics": ["Mga Paksa", "Mga Topiko"],
    "Up Next": ["Susunod", "Sunod"],
    "Past Events": ["Mga Nakaraang Kaganapan", "Mga Naglabay nga Hitabo"],
    "No past events yet.": ["Wala pang nakaraang kaganapan.", "Waray pa naglabay nga hitabo."],
    "View Calendar": ["Tingnan ang Kalendaryo", "Kitaa an Kalendaryo"],
    "View Archive": ["Tingnan ang Archive", "Kitaa an Archive"],
    "View All Announcements": ["Tingnan Lahat ng Anunsiyo", "Kitaa Ngatanan nga Pahibaro"],
    "View All News": ["Tingnan Lahat ng Balita", "Kitaa Ngatanan nga Balita"],
    "View All Offices": ["Tingnan Lahat ng Tanggapan", "Kitaa Ngatanan nga Opisina"],
    "View All Officials": ["Tingnan Lahat ng Opisyal", "Kitaa Ngatanan nga Opisyal"],
    "Need Assistance?": ["Kailangan ng Tulong?", "Kinahanglan hin Bulig?"],
    "Have questions about an announcement? Our Public Assistance Desk is open Monday to Friday, 8:00 AM–5:00 PM.":
      ["May tanong tungkol sa isang anunsiyo? Bukas ang aming Public Assistance Desk mula Lunes hanggang Biyernes, 8:00 AM–5:00 PM.",
       "May pakiana mahitungod ha usa nga pahibaro? Bukas an amon Public Assistance Desk tikang Lunes tubtob Biyernes, 8:00 AM–5:00 PM."],
    "Have a Story to Share?": ["May Kuwentong Ibabahagi?", "May-ada Istorya nga Ipaambit?"],
    "Send news tips and photos from your barangay to the Public Information Office.": ["Magpadala ng balita at larawan mula sa iyong barangay sa Public Information Office.", "Pagpadara hin balita ngan litrato tikang ha imo barangay ngadto ha Public Information Office."],
    "Hosting an Event?": ["May Idaraos na Kaganapan?", "Maghihimo hin Hitabo?"],
    "Barangays and local organizations may request the use of the LGU Grounds or Session Hall through the Office of the Municipal Mayor.":
      ["Maaaring humiling ang mga barangay at lokal na organisasyon na gamitin ang LGU Grounds o Session Hall sa pamamagitan ng Tanggapan ng Punong Bayan.",
       "Puydi mangaro an mga barangay ngan lokal nga organisasyon nga gamiton an LGU Grounds o Session Hall pinaagi ha Opisina han Mayor."],
    "Subscribe to Updates": ["Mag-subscribe sa mga Update", "Mag-subscribe ha mga Update"],
    "Get the latest announcements and updates delivered straight to your email.": ["Matanggap ang pinakabagong anunsiyo at update diretso sa iyong email.", "Karawata an pinakabag-o nga pahibaro ngan update direkta ha imo email."],
    "Subscribe": ["Mag-subscribe", "Mag-subscribe"],
    "Contact PIO": ["Makipag-ugnayan sa PIO", "Kontaka an PIO"],
    "Report a Concern": ["Mag-ulat ng Problema", "Ireport an Problema"],
    "Event Posters": ["Mga Poster ng Kaganapan", "Mga Poster han Hitabo"],
    "See the latest announcement from each municipal office. Click an office to see only its announcements and news.":
      ["Tingnan ang pinakabagong anunsiyo mula sa bawat tanggapan ng bayan. Pindutin ang isang tanggapan para makita lamang ang mga anunsiyo at balita nito.",
       "Kitaa an pinakabag-o nga pahibaro tikang ha kada opisina han bungto. Pinduta an usa nga opisina para makita la an mga pahibaro ngan balita hini."],
    "Browse by Office": ["Tingnan ayon sa Tanggapan", "Kitaa pinaagi ha Opisina"],
    "Filter": ["Salain", "Salaa"],
    "Sort by": ["Ayusin ayon sa", "Han-aya pinaagi ha"],
    "Date created (newest first)": ["Petsa ng paggawa (pinakabago muna)", "Petsa han paghimo (pinakabag-o anay)"],
    "Date created (oldest first)": ["Petsa ng paggawa (pinakaluma muna)", "Petsa han paghimo (pinakadaan anay)"],
    "Date modified (latest first)": ["Petsa ng pagbago (pinakabago muna)", "Petsa han pagbag-o (pinakabag-o anay)"],
    "Date modified (oldest first)": ["Petsa ng pagbago (pinakaluma muna)", "Petsa han pagbag-o (pinakadaan anay)"],
    "Clear": ["I-clear", "Limpyaha"],
    "All": ["Lahat", "Ngatanan"],
    "No announcements match your search.": ["Walang anunsiyong tugma sa iyong hinanap.", "Waray pahibaro nga angay ha imo ginbilng."],
    "No events match your search.": ["Walang kaganapang tugma sa iyong hinanap.", "Waray hitabo nga angay ha imo ginbilng."],
    "No news matches your search.": ["Walang balitang tugma sa iyong hinanap.", "Waray balita nga angay ha imo ginbilng."],
    "No updates match your search.": ["Walang update na tugma sa iyong hinanap.", "Waray update nga angay ha imo ginbilng."],
    "No offices match your search.": ["Walang tanggapang tugma sa iyong hinanap.", "Waray opisina nga angay ha imo ginbilng."],
    "Watch video": ["Panoorin ang video", "Tan-awa an video"],
    "Open on YouTube": ["Buksan sa YouTube", "Abriha ha YouTube"],
    "No further details were provided for this announcement.": ["Walang ibang detalye para sa anunsiyong ito.", "Waray iba nga detalye para hini nga pahibaro."],
    "No further details were provided for this story.": ["Walang ibang detalye para sa balitang ito.", "Waray iba nga detalye para hini nga balita."],
    "No further details were provided for this event.": ["Walang ibang detalye para sa kaganapang ito.", "Waray iba nga detalye para hini nga hitabo."],
    "EXPIRED": ["TAPOS NA", "TAPOS NA"],

    /* categories (fixed lists) */
    "GENERAL": ["PANGKALAHATAN", "KADAMOAN"],
    "General": ["Pangkalahatan", "Kadamoan"],
    "Health": ["Kalusugan", "Panlawas"],
    "Education": ["Edukasyon", "Edukasyon"],
    "Agriculture": ["Agrikultura", "Agrikultura"],
    "Environment": ["Kapaligiran", "Palibot"],
    "Community": ["Komunidad", "Komunidad"],
    "Infrastructure": ["Imprastruktura", "Imprastruktura"],
    "Tourism": ["Turismo", "Turismo"],
    "Sports": ["Palakasan", "Isport"],
    "Governance": ["Pamamahala", "Pagdumala"],

    /* ---------- offices ---------- */
    "Our Offices": ["Aming mga Tanggapan", "Amon mga Opisina"],
    "Office Directory": ["Direktoryo ng mga Tanggapan", "Direktoryo han mga Opisina"],
    "Explore the different offices of the Municipality of Tunga. Click any office to view information, services offered, announcements, and downloadable forms.":
      ["Tuklasin ang iba't ibang tanggapan ng Bayan ng Tunga. Pindutin ang alinmang tanggapan para makita ang impormasyon, mga serbisyo, anunsiyo, at mga form na maida-download.",
       "Kitaa an lain-lain nga opisina han Bungto han Tunga. Pinduta an bisan ano nga opisina para makita an impormasyon, mga serbisyo, pahibaro, ngan mga form nga puydi i-download."],
    "Search offices by name or service...": ["Maghanap ng tanggapan ayon sa pangalan o serbisyo...", "Bilnga an opisina pinaagi ha ngaran o serbisyo..."],
    "Can't find the office you're looking for?": ["Hindi mo makita ang tanggapang hinahanap mo?", "Diri nimo makita an opisina nga imo ginbibilng?"],
    "Use our Contact Directory to find contact details of all municipal offices.": ["Gamitin ang aming Contact Directory para makita ang contact ng lahat ng tanggapan ng bayan.", "Gamita an amon Contact Directory para makita an kontak han ngatanan nga opisina han bungto."],
    "View Contact Directory": ["Tingnan ang Contact Directory", "Kitaa an Contact Directory"],
    "View Office": ["Tingnan ang Tanggapan", "Kitaa an Opisina"],
    "About the Office": ["Tungkol sa Tanggapan", "Mahitungod han Opisina"],
    "Services Offered": ["Mga Serbisyong Inaalok", "Mga Serbisyo nga Gintatanyag"],
    "Services of the Office": ["Mga Serbisyo ng Tanggapan", "Mga Serbisyo han Opisina"],
    "Services": ["Mga Serbisyo", "Mga Serbisyo"],
    "Downloadable Forms": ["Mga Form na Maida-download", "Mga Form nga Puydi i-download"],
    "Organizational Chart": ["Talaan ng Organisasyon", "Tsart han Organisasyon"],
    "Office Hours": ["Oras ng Tanggapan", "Oras han Opisina"],
    "Location": ["Lokasyon", "Lugar"],
    "Telephone": ["Telepono", "Telepono"],
    "Phone": ["Telepono", "Telepono"],
    "Address": ["Address", "Adres"],
    "Mission": ["Misyon", "Misyon"],
    "Vision": ["Bisyon", "Bisyon"],
    "Mandate": ["Mandato", "Mandato"],
    "Goal": ["Layunin", "Tumong"],
    "Objective": ["Mithiin", "Katuyoan"],
    "Service Pledge": ["Pangako sa Serbisyo", "Saad ha Serbisyo"],
    "Download": ["I-download", "I-download"],
    "Fill Out Online": ["Sagutan Online", "Pun-a Online"],
    "Fill Out Form": ["Sagutan ang Form", "Pun-a an Form"],
    "download the PDF": ["i-download ang PDF", "i-download an PDF"],
    "log in to download the PDF": ["mag-login para i-download ang PDF", "mag-login para i-download an PDF"],
    "Checklist of Requirements": ["Listahan ng mga Kinakailangan", "Listahan han mga Kinahanglanon"],
    "Requirement": ["Kinakailangan", "Kinahanglanon"],
    "Where to Secure": ["Saan Kukunin", "Diin Kukuhaon"],
    "Client Steps": ["Mga Hakbang ng Kliyente", "Mga Lakang han Kliyente"],
    "Agency Actions": ["Mga Aksiyon ng Tanggapan", "Mga Aksyon han Opisina"],
    "Fees to be Paid": ["Mga Babayaran", "Mga Babayaran"],
    "Processing Time": ["Tagal ng Pagproseso", "Kadugayon han Pagproseso"],
    "Person Responsible": ["Taong Responsable", "Tawo nga Responsable"],
    "TOTAL": ["KABUUAN", "KABUG-OSAN"],
    "Classification:": ["Klasipikasyon:", "Klasipikasyon:"],
    "Type of Transaction:": ["Uri ng Transaksiyon:", "Klase han Transaksyon:"],
    "Who May Avail:": ["Sino ang Maaaring Mag-avail:", "Hin-o an Puydi Mag-avail:"],
    "Office or Division:": ["Tanggapan o Dibisyon:", "Opisina o Dibisyon:"],
    "Legal Basis": ["Batayang Legal", "Basehan ha Balaod"],
    "Schedule of Service": ["Iskedyul ng Serbisyo", "Iskedyul han Serbisyo"],
    "Select a service to see its full details": ["Pumili ng serbisyo para makita ang buong detalye", "Pili hin serbisyo para makita an bug-os nga detalye"],
    "Select a service to see its description in the Services of the Office section below.": ["Pumili ng serbisyo para makita ang paglalarawan nito sa bahaging Mga Serbisyo ng Tanggapan sa ibaba.", "Pili hin serbisyo para makita an paglaladawan hini ha bahin han Mga Serbisyo han Opisina ha ubos."],
    "This office hasn't published any services yet.": ["Wala pang nailalathalang serbisyo ang tanggapang ito.", "Waray pa nagpublikar hin serbisyo ini nga opisina."],
    "No announcements from this office yet.": ["Wala pang anunsiyo mula sa tanggapang ito.", "Waray pa pahibaro tikang hini nga opisina."],
    "No news from this office yet.": ["Wala pang balita mula sa tanggapang ito.", "Waray pa balita tikang hini nga opisina."],
    "No photos from this office yet.": ["Wala pang larawan mula sa tanggapang ito.", "Waray pa litrato tikang hini nga opisina."],
    "No client steps added yet.": ["Wala pang naidagdag na hakbang.", "Waray pa nadugang nga lakang."],
    "No requirements added yet.": ["Wala pang naidagdag na kinakailangan.", "Waray pa nadugang nga kinahanglanon."],
    "Back to office": ["Bumalik sa tanggapan", "Balik ha opisina"],
    "View more images about this office": ["Tingnan ang iba pang larawan ng tanggapang ito", "Kitaa an iba pa nga litrato hini nga opisina"],
    "Serves the residents of the Municipality of Tunga.": ["Naglilingkod sa mga residente ng Bayan ng Tunga.", "Nagseserbisyo ha mga lumulupyo han Bungto han Tunga."],
    "Serves the public through the services listed above.": ["Naglilingkod sa publiko sa pamamagitan ng mga serbisyong nakalista sa itaas.", "Nagseserbisyo ha publiko pinaagi han mga serbisyo nga nakalista ha igbaw."],
    "Submit": ["Ipasa", "Ipasa"],
    "Submit Form": ["Ipasa ang Form", "Ipasa an Form"],
    "Back": ["Bumalik", "Balik"],
    "Next": ["Susunod", "Sunod"],
    "Previous": ["Nakaraan", "Naglabay"],
    "Required": ["Kailangan", "Kinahanglan"],

    /* ---------- gallery ---------- */
    "All Photos": ["Lahat ng Larawan", "Ngatanan nga Litrato"],
    "Photos from municipal events, projects and everyday life across Tunga's offices.": ["Mga larawan mula sa mga kaganapan, proyekto at pang-araw-araw na buhay sa mga tanggapan ng Tunga.", "Mga litrato tikang ha mga hitabo, proyekto ngan adlaw-adlaw nga kinabuhi ha mga opisina han Tunga."],
    "See Photos": ["Tingnan ang mga Larawan", "Kitaa an mga Litrato"],
    "Albums": ["Mga Album", "Mga Album"],

    /* ---------- about ---------- */
    "Our Mission": ["Ang Aming Misyon", "An Amon Misyon"],
    "Our Vision": ["Ang Aming Bisyon", "An Amon Bisyon"],
    "Our Core Values": ["Ang Aming mga Pangunahing Pagpapahalaga", "An Amon mga Panguna nga Bili"],
    "Our History": ["Ang Aming Kasaysayan", "An Amon Kasaysayan"],
    "Our Officials": ["Ang Aming mga Opisyal", "An Amon mga Opisyal"],
    "Barangays of Tunga": ["Mga Barangay ng Tunga", "Mga Barangay han Tunga"],
    "Population (2025 PSA Estimate)": ["Populasyon (Tantiya ng PSA 2025)", "Populasyon (Banabana han PSA 2025)"],
    "Total Land Area": ["Kabuuang Lawak ng Lupa", "Kabug-osan nga Kadako han Tuna"],
    "Households": ["Mga Sambahayan", "Mga Panimalay"],
    "Establishments": ["Mga Establisimyento", "Mga Establisimyento"],
    "Established": ["Itinatag", "Gintukod"],
    "Present": ["Kasalukuyan", "Yana"],
    "Related pages": ["Mga kaugnay na pahina", "Mga kaupod nga pahina"],

    /* ---------- contact ---------- */
    "Get in Touch": ["Makipag-ugnayan", "Kontaka Kami"],
    "We are here to help! Reach out to us for inquiries, feedback, or assistance.": ["Narito kami para tumulong! Makipag-ugnayan sa amin para sa mga tanong, feedback, o tulong.", "Ania kami para bumulig! Kontaka kami para ha mga pakiana, feedback, o bulig."],
    "You can contact us through the following channels. We will respond as soon as possible.": ["Maaari mo kaming kontakin sa mga sumusunod na paraan. Sasagot kami sa lalong madaling panahon.", "Puydi mo kami kontakon pinaagi hini nga mga paagi. Mabaton kami dayon."],
    "Find the contact details of our offices.": ["Hanapin ang contact ng aming mga tanggapan.", "Bilnga an kontak han amon mga opisina."],
    "Send Us a Message": ["Padalhan Kami ng Mensahe", "Padar-i Kami hin Mensahe"],
    "Send Message": ["Ipadala ang Mensahe", "Ipadara an Mensahe"],
    "How Can We Help You?": ["Paano Ka Namin Matutulungan?", "Paonan-o Ka Namon Mabubuligan?"],
    "Choose a topic below so we can direct your inquiry to the right office.": ["Pumili ng paksa sa ibaba para maipadala namin ang iyong tanong sa tamang tanggapan.", "Pili hin topiko ha ubos para maipadara namon an imo pakiana ngadto ha husto nga opisina."],
    "General Inquiry": ["Pangkalahatang Tanong", "Kadamoan nga Pakiana"],
    "Request Information": ["Humiling ng Impormasyon", "Pangaro hin Impormasyon"],
    "Feedback / Suggestion": ["Feedback / Mungkahi", "Feedback / Suhestyon"],
    "Topic (optional)": ["Paksa (opsyonal)", "Topiko (opsyonal)"],
    "Select an office to send your message to": ["Pumili ng tanggapang padadalhan ng iyong mensahe", "Pili hin opisina nga padadad-an han imo mensahe"],
    "Your Name": ["Ang Iyong Pangalan", "An Imo Ngaran"],
    "Your Email": ["Ang Iyong Email", "An Imo Email"],
    "Subject": ["Paksa", "Topiko"],
    "Message": ["Mensahe", "Mensahe"],
    "Our Location": ["Aming Lokasyon", "Amon Lugar"],
    "Get directions": ["Kumuha ng direksiyon", "Kuhaa an direksyon"],
    "View larger map": ["Tingnan ang mas malaking mapa", "Kitaa an mas dako nga mapa"],
    "Facebook Page": ["Facebook Page", "Facebook Page"],
    "Monday – Friday": ["Lunes – Biyernes", "Lunes – Biyernes"],
    "Closed on Saturdays, Sundays and Holidays.": ["Sarado tuwing Sabado, Linggo at mga Pista Opisyal.", "Sarado kon Sabado, Domingo ngan mga Holiday."],

    /* ---------- login / sign up / forgot password ---------- */
    "Log In": ["Mag-login", "Mag-login"],
    "Log in": ["Mag-login", "Mag-login"],
    "Citizen Login": ["Login ng Mamamayan", "Login han Lumulupyo"],
    "Welcome back! Please sign in to continue to your account.": ["Maligayang pagbabalik! Mag-sign in para magpatuloy sa iyong account.", "Maupay nga pagbalik! Alayon pag-sign in para magpadayon ha imo account."],
    "Log in to access permits, requests, and updates from your municipal government — anytime, anywhere.": ["Mag-login para makita ang mga permit, kahilingan, at update mula sa iyong pamahalaang bayan — kahit kailan, kahit saan.", "Mag-login para makita an mga permit, hangyo, ngan update tikang ha imo gobyerno han bungto — bisan kanus-a, bisan diin."],
    "Email or Username": ["Email o Username", "Email o Username"],
    "Password": ["Password", "Password"],
    "Confirm Password": ["Kumpirmahin ang Password", "Kumpirmaha an Password"],
    "Remember me": ["Tandaan ako", "Hinumdomi ako"],
    "Forgot password?": ["Nakalimutan ang password?", "Nakalimtan an password?"],
    "Don't have an account?": ["Wala ka pang account?", "Waray ka pa account?"],
    "Create one now": ["Gumawa ngayon", "Paghimo yana"],
    "or continue with": ["o magpatuloy gamit ang", "o padayon gamit an"],
    "or sign up with": ["o mag-sign up gamit ang", "o magparehistro gamit an"],
    "Continue with Google": ["Magpatuloy gamit ang Google", "Padayon gamit an Google"],
    "Create Account": ["Gumawa ng Account", "Paghimo hin Account"],
    "Already have an account?": ["May account ka na?", "May-ada ka na account?"],
    "Sign up to start using citizen services online.": ["Mag-sign up para magamit ang mga serbisyo online.", "Magparehistro para magamit an mga serbisyo online."],
    "Create your citizen account to request documents, follow announcements, and stay connected with your local government.": ["Gumawa ng iyong account para humiling ng dokumento, sumubaybay sa mga anunsiyo, at manatiling konektado sa iyong lokal na pamahalaan.", "Paghimo han imo account para mangaro hin dokumento, sumunod ha mga pahibaro, ngan magpabilin nga konektado ha imo lokal nga gobyerno."],
    "Verification Code": ["Verification Code", "Verification Code"],
    "Send Code": ["Ipadala ang Code", "Ipadara an Code"],
    "I agree to the": ["Sumasang-ayon ako sa", "Uyon ako ha"],
    "and": ["at", "ngan"],
    "Reset Password": ["I-reset ang Password", "I-reset an Password"],
    "Remembered your password?": ["Naalala mo na ang password?", "Nahinumdoman mo na an password?"],
    "Forgot your password? Enter your email or username below and we'll send you a code to reset it.": ["Nakalimutan ang password? Ilagay ang iyong email o username sa ibaba at magpapadala kami ng code para ma-reset ito.", "Nakalimtan an password? Ibutang an imo email o username ha ubos ngan magpapadara kami hin code para ma-reset ini."],
    "Enter your email or username to receive a verification code.": ["Ilagay ang iyong email o username para makatanggap ng verification code.", "Ibutang an imo email o username para makarawat hin verification code."],
    "Enter your email address": ["Ilagay ang iyong email address", "Ibutang an imo email address"],
    "Enter your password": ["Ilagay ang iyong password", "Ibutang an imo password"],
    "Create a password": ["Gumawa ng password", "Paghimo hin password"],
    "Create a new password": ["Gumawa ng bagong password", "Paghimo hin bag-o nga password"],
    "Re-enter your password": ["Ilagay muli ang iyong password", "Ibutang utro an imo password"],
    "Re-enter your new password": ["Ilagay muli ang bagong password", "Ibutang utro an bag-o nga password"],
    "6-digit code": ["6-digit na code", "6-digit nga code"],

    /* ---------- map, search ---------- */
    "Tunga Map": ["Mapa ng Tunga", "Mapa han Tunga"],
    "Search school, health center, market…": ["Maghanap ng paaralan, health center, palengke…", "Bilnga an eskwelahan, health center, merkado…"],
    "Type a keyword...": ["Mag-type ng keyword...", "Pag-type hin keyword..."],
    "Search results": ["Mga resulta ng paghahanap", "Mga resulta han pagbilng"],
    "No results found.": ["Walang nahanap.", "Waray nabilngan."]
  };

  // weekday letters in the events calendar, and month names (calendar title "October 2026", "OCT")
  var DAYS = { Mo: ["Lu", "Lu"], Tu: ["Ma", "Ma"], We: ["Mi", "Mi"], Th: ["Hu", "Hu"], Fr: ["Bi", "Bi"], Sa: ["Sa", "Sa"], Su: ["Li", "Do"] };
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  var MONTHS_TL = ["Enero", "Pebrero", "Marso", "Abril", "Mayo", "Hunyo", "Hulyo", "Agosto", "Setyembre", "Oktubre", "Nobyembre", "Disyembre"];
  var MONTHS_WAR = ["Enero", "Pebrero", "Marso", "Abril", "Mayo", "Hunyo", "Hulyo", "Agosto", "Septyembre", "Oktubre", "Nobyembre", "Disyembre"];
  var MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
  var MON_TL = ["ENE", "PEB", "MAR", "ABR", "MAY", "HUN", "HUL", "AGO", "SET", "OKT", "NOB", "DIS"];
  // sentences with a changing part
  var PATTERNS = [
    [/^Welcome, (.+)$/, ["Maligayang pagdating, $1", "Maupay nga pag-abot, $1"]],
    [/^You rated it (\d)\/5 · update$/, ["Na-rate mo ito ng $1/5 · baguhin", "Gin-rate mo ini hin $1/5 · bag-oha"]],
    [/^You rated this service: (.+)\. Thank you!$/, ["Na-rate mo ang serbisyong ito: $1. Salamat!", "Gin-rate mo ini nga serbisyo: $1. Salamat!"]],
    [/^Note from the office · (.+)$/, ["Tala mula sa tanggapan · $1", "Nota tikang ha opisina · $1"]]
  ];

  var LANGS = { en: -1, tl: 0, war: 1 };
  var lang = getLang();
  var original = new WeakMap();          // text node -> its English text
  var ATTRS = ["placeholder", "title", "aria-label"];
  // never translated: code, typed text, and places that show content written by
  // the offices or the person (announcement text, legal pages, names, emails)
  var SKIP = "script,style,noscript,textarea,code,pre,[data-no-translate],[contenteditable]," +
             ".ann-dlg-content,.ann-dlg-subtitle,.legal-body,.side-panel__name,.side-panel__email";

  function getLang() {
    // the choice is in the side menu of signed-in people; when signed out
    // (no side menu on the page) the website is shown in English
    if (!document.querySelector("[data-lang-choice]")) return "en";
    var m = document.cookie.match(/(?:^|;\s*)tunga_lang=(en|tl|war)/);
    return m ? m[1] : "en";
  }
  function saveLang(l) {
    document.cookie = "tunga_lang=" + l + "; path=/; max-age=31536000; SameSite=Lax";
  }

  // English -> chosen language (or null when there is no translation)
  function tr(text) {
    var i = LANGS[lang];
    if (i < 0) return null;
    var m = text.match(/^(\s*)([\s\S]*?)(\s*(?:→|…|\*|›))?(\s*)$/);
    var core = m[2].replace(/\s+/g, " "), tail = (m[3] || "") + m[4];
    var full = (m[2] + (m[3] || "")).replace(/\s+/g, " ");
    if (T[full]) return m[1] + T[full][i] + m[4];       // e.g. "Loading…" listed with its dots
    var hit = T[core];
    if (hit) return m[1] + hit[i] + tail;
    if (DAYS[core]) return m[1] + DAYS[core][i] + tail;
    var mi = MONTHS.indexOf(core.split(" ")[0]);
    if (mi > -1 && /^\w+ \d{4}$/.test(core)) return m[1] + (i ? MONTHS_WAR : MONTHS_TL)[mi] + core.slice(core.indexOf(" ")) + tail;
    mi = MON.indexOf(core);
    if (mi > -1) return m[1] + MON_TL[mi] + tail;
    for (var p = 0; p < PATTERNS.length; p++) {
      if (PATTERNS[p][0].test(core)) return m[1] + core.replace(PATTERNS[p][0], PATTERNS[p][1][i]) + tail;
    }
    return null;
  }

  function doText(node) {
    var en = original.has(node) ? original.get(node) : node.nodeValue;
    if (!en.trim()) return;
    var out = tr(en);
    if (out !== null) {
      if (!original.has(node)) original.set(node, en);
      if (node.nodeValue !== out) node.nodeValue = out;
    } else if (original.has(node) && node.nodeValue !== en) {
      node.nodeValue = en;                // back to English
    }
  }
  function doAttrs(el) {
    ATTRS.forEach(function (a) {
      if (!el.hasAttribute(a)) return;
      var key = "data-en-" + a, en = el.getAttribute(key);
      if (en === null) en = el.getAttribute(a);
      var out = tr(en);
      if (out !== null) { el.setAttribute(key, en); el.setAttribute(a, out); }
      else if (el.hasAttribute(key)) el.setAttribute(a, en);
    });
  }
  function skipped(el) { return el && el.closest && el.closest(SKIP); }

  function translate(root) {
    if (!root) return;
    if (root.nodeType === 3) { if (!skipped(root.parentElement)) doText(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 11) return;
    if (root.nodeType === 1 && skipped(root)) return;
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode: function (n) {
        if (n.nodeType === 1) return n.matches(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var n = root.nodeType === 1 ? root : w.nextNode();
    if (root.nodeType === 1) doAttrs(root);
    while ((n = w.nextNode())) { if (n.nodeType === 3) doText(n); else doAttrs(n); }
  }
  function translateTemplates() {       // pop-up contents kept in <template>
    document.querySelectorAll("template").forEach(function (t) { translate(t.content); });
  }

  function apply() {
    document.documentElement.lang = lang === "en" ? "en" : (lang === "tl" ? "tl" : "war");
    translate(document.body);
    translateTemplates();
    document.querySelectorAll("[data-lang-choice]").forEach(function (b) {
      var on = b.getAttribute("data-lang-choice") === lang;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    document.documentElement.classList.remove("i18n-pending");
  }

  // words added later (pop-ups, messages, loaded lists) are translated too
  var busy = false;
  new MutationObserver(function (list) {
    if (busy || lang === "en") return;
    busy = true;
    list.forEach(function (m) {
      if (m.type === "childList") m.addedNodes.forEach(translate);
      else if (m.type === "characterData") translate(m.target);
    });
    busy = false;
  }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });

  // the language buttons in the side menu
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-lang-choice]");
    if (!b) return;
    lang = b.getAttribute("data-lang-choice");
    saveLang(lang);
    busy = true; apply(); busy = false;
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply); else apply();
  window.TungaLang = { get: function () { return lang; }, translate: translate };
})();
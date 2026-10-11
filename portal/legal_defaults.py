"""Starting text for the three legal pages (Privacy Policy, Terms of Use,
Accessibility Statement). The Super Admin edits them in Website Settings →
Legal Pages; this text is only what a fresh install starts with (and what
"Reset to draft" brings back).

These are DRAFTS based on what the Tunga Portal actually does. They must be
reviewed and approved by the LGU's Legal Office and Data Protection Officer
before the website is used by the public. Replace everything in [brackets].

Writing format (the same in the Super Admin box):
  ## Heading          → a section heading
  - item              → a bullet point
  empty line          → a new paragraph
"""

PRIVACY_POLICY = """The Municipality of Tunga, Leyte ("we", "the LGU") respects your privacy. This Privacy Policy explains what personal information this website collects, why, how it is protected, and your rights under the Data Privacy Act of 2012 (Republic Act No. 10173).

## Who we are
This website is run by the Local Government Unit of Tunga, Leyte.
Data Protection Officer: [Name of the DPO]
Email: [DPO email address]
Address: [Municipal Hall address]

## What information we collect
- When you create an account: your first and last name, email address, mobile number and password. Your password is stored in a scrambled (hashed) form that no one, including us, can read.
- When you sign in with Google: your name, email address and profile picture from your Google account.
- When you fill in a form online: the answers you type into the office's form.
- When you upload a profile photo: the photo.
- When you use Contact Us: nothing is stored on this website. Your message is written and sent from your own email app (such as Gmail).
- Automatically: cookies that keep you signed in and protect the forms on this site, and the internet address (IP address) of failed sign-in attempts, which is kept for one day to stop password guessing.

## Why we use your information
- To create and manage your account and confirm your email address
- To process the forms and requests you send to our offices
- To keep the website and your account secure
- To answer your questions and improve our services

We do not sell your personal information, and we do not use it for advertising.

## Who else handles your information
To run this website we use trusted service providers that handle data on our behalf:
- Website hosting and database: [Render / DigitalOcean]
- Storage of uploaded files and photos: [Cloudinary / DigitalOcean Spaces]
- Sending verification codes by email: Brevo
- Google, for "Continue with Google" sign-in and the "I'm not a robot" check (reCAPTCHA)

We may also share information when the law requires it.

## How we protect your information
- The whole website uses a secure, encrypted connection (HTTPS).
- Passwords are stored hashed; sign-in and verification codes are limited to stop guessing.
- Only authorized LGU staff can open the dashboards, and each office representative can only see their own office's records.
- Actions in the dashboards are recorded, and the website is backed up regularly.

## How long we keep your information
- Your account: until you ask us to delete it, or it is no longer needed.
- Forms you submitted: for as long as the office needs them for the service, and as required by government record-keeping rules.
- Failed sign-in records: one day.
- Backups: [number] days.

## Your rights
Under the Data Privacy Act you have the right to be informed, to access your data, to object, to have wrong data corrected, to have your data erased or blocked, to data portability, and to be paid damages for any harm caused by unlawful processing. You may also file a complaint with the National Privacy Commission (privacy.gov.ph).

To use any of these rights, contact our Data Protection Officer at [DPO email address].

## Changes to this policy
We may update this policy from time to time. The date of the latest version is shown at the top of this page."""

TERMS_OF_USE = """Welcome to the official website of the Municipality of Tunga, Leyte. By using this website, you agree to these Terms of Use. If you do not agree, please do not use the website.

## Purpose of the website
This website gives the public information about the LGU and its offices, announcements, news, events, services and downloadable forms, and lets registered users fill in some forms online.

## Your account
- Give true and complete information when you sign up.
- Keep your password private. You are responsible for what is done using your account.
- Tell us right away if you think someone else has used your account.
- The LGU may suspend or close accounts that are misused.

## Proper use
You agree not to:
- Submit false, misleading or someone else's information
- Upload harmful files, viruses, or offensive or illegal content
- Try to break into the website, its dashboards or other users' accounts
- Send spam, or use automated tools to collect information from the website

## Information on this website
We work to keep the information accurate and up to date, but it may change without notice. If anything on this website differs from an official document or from what a municipal office tells you, the official document and the office prevail.

## Online forms and requests
Submitting a form online does not mean your request is approved. Each office will process it following its own requirements, fees and schedule, which are listed in its services.

## Links to other websites
This website links to other sites such as Google, Gmail and Facebook. We are not responsible for their content or their privacy practices.

## Logos, photos and content
The seal and logo of the Municipality of Tunga and the content of this website belong to the LGU or to their owners. You may share public information for non-commercial purposes if you mention the source. You may not use the seal or logo in a way that suggests you represent the LGU.

## Limitation of liability
The website is provided "as is". The LGU is not liable for loss or damage caused by using, or being unable to use, the website, including when it is under maintenance.

## Changes to these terms
We may update these Terms of Use. The date of the latest version is shown at the top of this page.

## Governing law
These terms follow the laws of the Republic of the Philippines.

## Contact
For questions about these terms, contact [office email address] or visit the Municipal Hall at [address]."""

ACCESSIBILITY_STATEMENT = """The Municipality of Tunga, Leyte wants everyone, including persons with disabilities and senior citizens, to be able to use this website. We use the Web Content Accessibility Guidelines (WCAG) 2.1, Level AA, as our guide.

## What we have done
- The website works on phones, tablets and computers.
- Text can be made bigger using your browser's zoom (Ctrl and +), and the layout adjusts.
- Pictures have short text descriptions for screen readers.
- Pages can be used with a keyboard.
- Text and buttons use colors with clear contrast.
- Pages are kept light so they load on slow internet connections.

## Known limitations
We are still working on these:
- Some downloadable forms are scanned PDF files that screen readers cannot read.
- The interactive map is mainly visual. Office addresses and contact numbers are also written on the Contact Us and office pages.
- Some older photos may not have descriptions yet.

## Need help or found a problem?
If any part of this website is hard for you to use, or you need information in another format (such as a printed copy or a phone call), please tell us:
- Email: [office email address]
- Phone: [office phone number]
- Visit: [Municipal Hall address], [office hours]

We will do our best to respond within [number] working days.

## Review of this statement
This statement was last reviewed on the date shown at the top of this page."""

# key, title, url name, text
PAGES = [
    ("privacy", "Privacy Policy", "privacy_policy", PRIVACY_POLICY),
    ("terms", "Terms of Use", "terms_of_use", TERMS_OF_USE),
    ("accessibility", "Accessibility Statement", "accessibility", ACCESSIBILITY_STATEMENT),
]
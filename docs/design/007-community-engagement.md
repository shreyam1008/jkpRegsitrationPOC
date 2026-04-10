# Community Engagement & Outreach

Last updated: 06 April 2026
Status: Draft — not yet reflected in proto/schema.

This document defines the new data capture areas for community engagement, outreach, and volunteer coordination. These fields extend the core satsangi registration profile to support local networking, language-based seva assignment, and volunteer management across ashrams and home cities.

All new fields are designed to be quick to fill during registration (toggles, checkboxes, dropdowns). Most are optional to keep the registration flow lean.

### Conditional Display Logic

To avoid overwhelming the registrant, fields are grouped into two tiers:

1. **Always shown** — Communication & WhatsApp, Languages (known + primary), Local Networking, and the two core volunteering toggles.
2. **Shown only if willing to volunteer** — If either `willing_to_volunteer_in_ashram` or `willing_to_volunteer_in_home_city` is checked, the following expand: volunteer interests, past seva description, language-related sevas, and professional background.

---

## 1. Communication & WhatsApp

> *As a staff member, I want to capture a satsangi's WhatsApp number (which may differ from their primary phone), their preferred way of being contacted, and their consent to be reached out for local programs, volunteer coordination, and feedback — so that coordinators can contact them appropriately and respectfully.*

| Field | Type | Required | Notes |
|---|---|---|---|
| `whatsapp_number` | string | Optional | May differ from `phone_number` |
| `preferred_contact_method` | enum | Optional | `whatsapp \| email \| sms \| phone` |
| `consent_to_contact_for_programs` | boolean | Required | Explicit opt-in to be contacted for ashram events, local events, satsangs, volunteer work, newsletters, and feedback collection |

---

## 2. Languages Known

> *As a coordinator, I want to know which languages a satsangi is proficient in, which one is their primary language, and whether they are willing to do language-related sevas — so that I can assign them to translation work, facilitate groups of similar-language visitors, or have them conduct tours for those groups.*

Only languages a person is **proficient** in should be captured — this is seva-oriented, not academic. The registration flow should keep this quick (checkboxes for common languages).

| Field | Type | Required | Notes |
|---|---|---|---|
| `languages_known` | multi-select | Optional | Checkboxes: Hindi, English, Gujarati, Bengali, Tamil, Telugu, Kannada, Marathi, Punjabi, Malayalam, Odia, Urdu, etc. Managed via lookup table. |
| `primary_language` | single-select | Optional | From the languages selected above |
| `language_related_sevas` | multi-select | Optional | **Volunteer-gated** — only shown if willing to volunteer. From a managed list. Initial options below. |

### Language-Related Sevas

- **Translation Seva** — translating during satsangs, events, or for written material.
- **Language Facilitation** — helping similar-language visitors navigate the ashram and its programs.
- **Tour Guide** — conducting ashram tours for groups in that language.

> In the future, people with specific language knowledge can be contacted for additional sevas beyond the ones they initially selected — the language data itself is the long-term asset.

---

## 3. Volunteering (Seva)

> *As a seva coordinator, I want to know whether a satsangi is willing to volunteer at the ashram, in their home city, or both — and optionally, which types of seva interest them — so that I can match them to open roles and plan manpower for events and daily operations.*

The two willingness toggles are **always shown**. The detail fields below only expand if at least one toggle is checked.

| Field | Type | Required | Notes |
|---|---|---|---|
| `willing_to_volunteer_in_ashram` | boolean | Optional | Always shown. Seva during ashram visits |
| `willing_to_volunteer_in_home_city` | boolean | Optional | Always shown. Seva in their city of residence (local events, satsang setup, etc.) |
| `volunteer_interests` | multi-select | Optional | **Volunteer-gated.** From a managed lookup list. Examples below. |
| `past_seva_description` | free text | Optional | **Volunteer-gated.** Any prior seva experience or details the satsangi wants to share |

### Volunteer Interest Options (managed via lookup table)

Cooking/Prasad, Cleaning, Event Management, Reception/Front-Desk, Teaching/Children's Programs, Kirtan/Music, Photography/Videography, Driving/Logistics, IT/Tech Support, Medical/First-Aid, Accounting/Admin, Construction/Maintenance, Gardening, Security, etc.

> Language-related sevas (translation, facilitation, tours) are captured separately under **Languages** above — they are linked to language proficiency, not general volunteering.

---

## 4. Local Networking

> *As an area coordinator, I want to know a satsangi's local satsang center, their zone, and whether they are interested in local satsangs — so that I can organize local programs, grow the community in each city, and notify interested people when a new satsang group is formed in their area.*

| Field | Type | Required | Notes |
|---|---|---|---|
| `local_satsang_center` | FK to centers lookup | Optional | e.g., "Delhi - Dwarka", "Mumbai - Andheri" |
| `zone` | FK to zones lookup | Optional | Already planned in project plan's lookup tables (see `006-project-plan.md` §5) |
| `interested_in_local_satsangs` | boolean | Optional | Whether they want to be informed about local satsang groups and events in their area |
| `interested_in_hosting_satsang` | boolean | Optional | Whether they are open to hosting a satsang at their residence. A lighter follow-up — not asked upfront during registration but can be captured if the person volunteers the interest, or followed up on later via contact. |

> **UX Note:** `interested_in_local_satsangs` is the primary field shown during registration — it's a low-commitment ask. `interested_in_hosting_satsang` is secondary; it can be shown as a follow-up if local satsangs is checked, or captured later when coordinators reach out to people in a given area.

---

## 5. Professional Background

> *As a volunteer coordinator, I want to know a satsangi's occupation — both from a categorized list and as a specific free-text description — so that I can tap into specialized professional skills when matching people to seva roles (e.g., a doctor for a medical camp, a CA for financial auditing, a teacher for children's programs).*

**Volunteer-gated** — this entire section only appears if the satsangi has indicated willingness to volunteer (ashram or home city).

| Field | Type | Required | Notes |
|---|---|---|---|
| `occupation_category` | single-select | Optional | From a managed lookup list. Initial options below. |
| `occupation_detail` | free text | Optional | More specific description, e.g., "Pediatric surgeon at AIIMS" or "Chartered Accountant, 15 years" |

### Occupation Categories (managed via lookup table)

Doctor/Medical, Engineer, Teacher/Professor, Lawyer/Legal, CA/Finance, IT/Software, Business/Entrepreneur, Government Service, Student, Retired, Homemaker, Farmer/Agriculture, Artist/Creative, Other.

---

## 6. Informational Guides (Printable Desk Material)

> *As a registration desk operator, I want ready-to-print informational guides available within the app — so that every desk across all ashrams can hand out consistent, up-to-date material to satsangis covering community links, resources, and general ashram information.*

These are **not data capture fields** — they are printable assets managed within the system and available at every registration desk.

### Guide Contents

- **General Ashram Information** — overview of the ashram, facilities, timings, rules, and maps.
- **Community WhatsApp Groups** — QR codes linking to relevant WhatsApp community groups (area-wise or ashram-wise).
- **Facebook Page** — QR code linking to the official JKP Facebook page.
- **YouTube Channel** — QR code linking to the official YouTube channel for satsang recordings and pravachans.
- **Weekly Zoom Satsang** — QR code or link to sign up for the regular online satsang.
- **Book Orders** — website link / QR code to order books of Shri Maharaj Ji.

### Implementation Notes

- Guides should be **manageable by super admin** — update links/QR codes without developer involvement.
- Each guide should be **printable as a single A4/A5 page** with clean formatting.
- QR codes should be generated from the managed URLs so they stay in sync if links change.
- Different guides can be created per ashram or per language if needed.

---

## Summary of All New Fields

| # | Domain | Fields | Display | Registration UX Impact |
|---|---|---|---|---|
| 1 | **Communication** | whatsapp_number, preferred_contact_method, consent_to_contact_for_programs | Always | 3 quick fields; consent is a single checkbox |
| 2 | **Languages** | languages_known, primary_language | Always | Checkboxes + 1 dropdown |
| 2b | **Language Sevas** | language_related_sevas | Volunteer-gated | Optional multi-select |
| 3 | **Volunteering** | willing_in_ashram, willing_in_home_city | Always | 2 toggles |
| 3b | **Volunteer Detail** | volunteer_interests, past_seva_description | Volunteer-gated | Optional multi-select + optional text |
| 4 | **Local Networking** | local_satsang_center, zone, interested_in_local_satsangs, interested_in_hosting_satsang | Always (hosting is secondary) | 2 dropdowns + 1–2 toggles; all optional |
| 5 | **Professional** | occupation_category, occupation_detail | Volunteer-gated | 1 dropdown + 1 text; both optional |
| 6 | **Info Guides** | (printable assets, not data fields) | N/A | Managed by super admin, printed at desks |

**Total: ~15 new fields.** Most optional. Non-communication/non-networking detail fields only appear when the satsangi indicates willingness to volunteer — keeping the default registration flow lean.

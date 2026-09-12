# Functional Design — Lauridsen Fotos Photography Portfolio

This document describes **what the website does and how it behaves** — page by page, in
terms of hard requirements (must-haves, non-negotiable) and soft requirements (nice-to-haves
that can flex or be added later). It deliberately avoids technology choices; those are
covered separately in `technical_design.md`.

## Overview

The site serves a photography business with four functional pillars:

1. A public **portfolio** organized into categories and albums.
2. Static **contact** and **pricing** pages.
3. Unlisted, **password-protected, self-expiring client delivery galleries** for handing off
   finished shoots to paying clients.
4. A photo-led **timeline** showcasing creative/non-client sessions.

All content (photos, albums, pricing, text) is managed by the owner through an **admin
dashboard** — no code changes are ever needed to update the site day-to-day.

### Confirmed direction

- Content managed through an **admin dashboard** (owner logs in, uploads/manages via web UI).
- Client galleries use **auto-generated unique passwords per gallery**.
- Portfolio covers **mixed/general** photography genres (not genre-specific layout).
- Contact page has a **working contact form** that emails the owner.
- Client galleries **expire after a fixed default period (e.g. 90 days)**, configurable per gallery.
- Client gallery visitors can **view and download** all images (originals + full-album ZIP); no favorites/selection workflow.
- Timeline is **photo-led with short captions**, not long-form articles.
- Pricing page shows **fixed packages/tiers** with what's included and price.
- **No automated emails** to clients (owner shares links manually).
- Public portfolio images get **basic copy deterrents** (disabled right-click/drag-save, web-sized exports), not watermarks.
- Site supports **Danish + English**, switchable.
- Navigation: **Home, Portfolio, Timeline, Pricing, Contact, About** (client galleries and admin are unlisted/direct-link only).

### Working assumptions (revisit if any of these are wrong)

- Single admin user (just the owner) — no multi-user/staff accounts.
- No e-commerce / print-ordering / online payments in this version.
- No visitor comments on Timeline entries — display-only, to avoid moderation overhead.
- Client galleries use a shared password per gallery (no per-client named accounts).

---

## 1. Site-wide principles

**Hard requirements**
- Visual tone: modern, minimalist, but not sterile — restrained color palette and generous
  whitespace, punctuated by one deliberate accent (a color, a type pairing, or motion detail)
  so it doesn't read as a generic template.
- Fully responsive: phone, tablet, desktop.
- Danish and English content, switchable via a persistent language toggle; the toggle choice
  is remembered across pages for that visitor.
- Fast-loading galleries: images are never served at full original resolution on public pages.
- Every public page is reachable from the main navigation (Home, Portfolio, Timeline, Pricing,
  Contact, About). Client galleries are **not** in navigation or sitemap — reachable only via
  direct link.
- The owner never edits content by touching code — all photos, albums, timeline entries,
  pricing text, and contact info are managed through the admin dashboard.

**Soft requirements**
- Subtle motion/transition on page load and image hover (e.g. gentle fade/scale) to add
  personality without becoming a gimmick.
- Consistent typography and grid system reused across Portfolio, Timeline, and client
  galleries so the photography — not the chrome — stays the focus.

---

## 2. Home page

**Hard requirements**
- Acts as a landing/hero page: a strong hero image (or short rotating set), the
  business name/tagline, and clear entry points into Portfolio, Timeline, and Contact.
- No functional logic beyond navigation — it's a static, curated entry point the owner can
  update (hero image, tagline) from the admin dashboard.

**Soft requirements**
- Optionally surface 1–2 "featured" albums or the latest Timeline entry as teasers.

---

## 3. Portfolio page (public albums by category)

**Hard requirements**
- Portfolio landing view lists **categories** (e.g. Weddings, Portraits, Events, ...) —
  the owner defines categories and assigns albums to them from the admin dashboard.
- Each category opens into one or more **albums**; each album is a curated set of images
  the owner uploads and orders.
- Visitors browse images in a full-screen/lightbox viewer with next/previous navigation.
- Public images are protected with basic deterrents: disabled right-click/drag-save context
  menu and web-optimized (not original-resolution) exports.
- Categories, albums, and their cover images/ordering are fully manageable from the admin
  dashboard (create/edit/delete/reorder) — no code changes needed to update the portfolio.

**Soft requirements**
- Albums can have a short description/story text alongside the images.
- A category or album can be marked "hidden/draft" so the owner can prepare it before
  publishing.

---

## 4. Timeline / showcase blog page

**Hard requirements**
- Reverse-chronological feed of "sessions" that were shot for showcase/creative purposes
  (not paid client deliveries).
- Each entry is **photo-led**: a handful of images plus a short caption/story text — not a
  long-form written article.
- Entries are created and published from the admin dashboard (title, date, short caption,
  photo set).
- No visitor interaction beyond viewing (no comments, likes, or accounts) — keeps the page
  maintenance-free.

**Soft requirements**
- Entries can optionally be tagged (e.g. by theme or location) for light filtering.
- An entry can link back to a related Portfolio category if relevant.

---

## 5. Pricing page

**Hard requirements**
- Displays fixed packages/tiers (name, description of what's included, price) rather than
  vague ranges.
- Fully static/informational — no booking or payment flow.
- Content (package names, inclusions, prices) editable from the admin dashboard without
  code changes.

**Soft requirements**
- A short FAQ or "how booking works" blurb beneath the packages.
- A call-to-action linking to the Contact page from each package.

---

## 6. Contact page

**Hard requirements**
- A working contact form (name, email, message, optionally shoot type/date) that sends the
  submission to the owner's email/inbox.
- Basic spam protection (e.g. honeypot field / rate limiting at the functional level —
  mechanism decided in technical design).
- Confirms submission success/failure clearly to the visitor.

**Soft requirements**
- Static fallback info (email address, social links) shown alongside the form for visitors
  who prefer not to use it.

---

## 7. About page

**Hard requirements**
- Static page: photographer bio, photo, and any credentials/style statement. Editable from
  the admin dashboard.

**Soft requirements**
- Can include a short "how I work" section to set expectations before a visitor books.

---

## 8. Client delivery galleries (private, unlisted, expiring)

This is the most behaviorally distinct page type and gets the most detailed treatment.

**Hard requirements**
- **Creation**: the owner creates a client gallery from the admin dashboard by uploading the
  session's images. The system generates: a unique, unlisted URL and a unique,
  auto-generated password for that gallery.
- **Access control**: the page is not linked from anywhere on the public site and is not
  included in any sitemap/search-indexable listing. A visitor needs the exact URL **and**
  the correct password to view it. Wrong password shows a generic error (no hints).
- **Content**: once unlocked, the client can view all images in the gallery and download
  them — both individually and as a single ZIP of the full album.
- **Expiry**: every gallery has an expiry date, defaulting to a fixed period (e.g. 90 days)
  from creation, editable per gallery by the owner at creation or afterward.
- **Deletion on expiry**: once a gallery passes its expiry date, the images are deleted from
  storage and the page itself stops being accessible (attempting the old URL shows an
  "expired/no longer available" message, not the content) — this happens automatically,
  without the owner needing to manually clean up.
- **No public trace**: expired or active client galleries never appear in Portfolio,
  Timeline, navigation, or any public listing.

**Soft requirements**
- The owner can see, from the admin dashboard, a list of all active client galleries with
  their expiry dates, and can manually extend, shorten, or delete one early.
- The owner can regenerate a gallery's password if it needs to be re-shared.
- A visible (but not alarming) "this gallery expires on [date]" notice shown to the client
  on the page itself, so they know to download in time — since there are no automated email
  reminders (per the decision above).

---

## 9. Admin dashboard

**Hard requirements**
- Single-owner login (username/password or equivalent), not publicly discoverable/linked.
- From the dashboard the owner can, without touching code:
  - Manage Portfolio categories/albums (create, edit, reorder, delete, publish/hide).
  - Manage Timeline entries (create, edit, delete, publish/hide).
  - Manage Pricing content (packages, inclusions, prices).
  - Manage static page text (Home hero/tagline, About, Contact static info).
  - Create, view, edit, and delete client galleries (upload images, set/extend expiry,
    view/regenerate password, see remaining time before expiry).
  - Manage Danish/English text for all of the above.

**Soft requirements**
- Bulk image upload (drag multiple files at once) for both Portfolio albums and client
  galleries.
- Simple image reordering via drag-and-drop.

---

## 10. Cross-cutting requirements

**Hard requirements**
- Client galleries are never crawlable/indexable by search engines (even though technically
  unlisted, this is an explicit requirement, not an accident of omission).
- Deleted/expired client images are actually removed from storage, not just hidden — this is
  a data-retention requirement, not only a UI one.
- No e-commerce, online payments, or print-ordering flows in this version.
- No visitor accounts anywhere on the site (client gallery access is password-only, no
  registration).

**Soft requirements**
- Site should be maintainable long-term by the owner alone, with no ongoing need for a
  developer to publish new photos, albums, or Timeline entries.

---

## Site map (functional, not technical)

| Page                            | Linked from nav? | Access                           |
| ------------------------------- | ---------------- | -------------------------------- |
| Home                            | Yes              | Public                           |
| Portfolio (categories → albums) | Yes              | Public                           |
| Timeline                        | Yes              | Public                           |
| Pricing                         | Yes              | Public                           |
| Contact                         | Yes              | Public                           |
| About                           | Yes              | Public                           |
| Client gallery (per session)    | No               | Unlisted URL + password, expires |
| Admin dashboard                 | No               | Unlisted URL + owner login       |

## Next step

Technical design (hosting, storage, image pipeline, auth mechanism, i18n implementation,
contact-form delivery and spam protection, and how automatic expiry/deletion is actually
carried out) will be worked out next and captured in `technical_design.md`.

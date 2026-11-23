# VC Conf partner service — Agent API

Base URL: https://vc-conf-partner-decks.onrender.com
Auth: header `Authorization: Bearer <AGENT_TOKEN>` (env var AGENT_TOKEN on Render). Admin basic auth still works for the UI.

## Build or rebuild a partner kit (posters + materials page) — one call
POST /api/agent/kit (JSON)
- company (required), code (promo code, e.g. EVE10), reg_url (e.g. https://vcconf.com?145)
- website (logo is pulled from it) or logo_url (direct image), logo_scale ("70" default)
- first_name (contact first name for the greeting)
- posting_dates (free text with all dates, e.g. "Nov 25 LinkedIn, Dec 15 email, Jan 11 LinkedIn, Jan 18 email"); first_post_date ("Nov 25")
- confirmed (bool, default true)
- is_speaker, speaker_name, speaker_role, speaker_topic, photo_url (speaker-partner variant: posters show the speaker photo + name, pill "Speaker · Company"; to upload a photo file use POST /poster/fill with photo=@file, then POST /poster/{id}/materials)
- partner_id (int, optional: update an existing partner instead of matching by company+code)
Returns: title, markdown (page copy), notion_url / html_url (materials page), poster_url, poster_square_url, poster_banner_url, partner_id, partner_conflict, notion_error, logo_warn.
Calling it again for the same company+code updates the same page.

## Partners
- GET /api/partners?q=<text> — list
- GET /api/partners/{id} — one partner with publications
- PATCH /api/partners/{id} — update fields (company, code, reg_url, notion_page_url, posting_dates_raw, first_post_date, notes, confirmed, first_name, website, logo_url, logo_scale, …)
- POST /api/partners/{id}/rebuild-preview {posting_dates_raw, first_post_date} — preview publication schedule
- POST /api/partners/{id}/rebuild {posting_dates_raw, first_post_date} — apply schedule
- POST /api/partners/{id}/refresh-copy {optional fields} — rewrite the materials page text, posters stay
- POST /api/partners/{id}/publications {date: YYYY-MM-DD, channel, post_number, notes, url}

## Other
- GET /api/calendar — publications calendar
- GET /api/agent/guide — this file

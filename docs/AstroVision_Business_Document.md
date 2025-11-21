# Astro Vision (Phase-1) — Business Document

## 1. Executive Summary

Astro Vision — Core REST is a backend service that computes natal charts, life-event timelines, and relationship compatibility using professional-grade astronomical calculations and a curated knowledge base of aspect interpretations ("aspect cards"). Phase‑1 exposes this intelligence through a stable JSON API so product teams can build web, mobile, and partner experiences on top.

The system combines Swiss Ephemeris calculations, custom aspect-period logic, and a structured knowledge base to deliver:
- Natal chart positions by sign and house.
- Time-bounded life events and timelines derived from transits.
- Western synastry compatibility scores for pairs and groups.
- Vedic Ashtakoota (Gun Milan) scores.
- A curated library of aspect cards with bilingual content (English/Hindi) used to generate consistent narratives.

Existing scoring and many narratives are intentionally simple placeholders, but all request/response contracts, headers, and error envelopes are production‑grade.

## 2. What Astro Vision Is

Astro Vision is a REST-based astrology engine focused on three business domains:

- **Natal** — describing an individual’s birth chart (planet positions and basic profile).
- **Reports** — generating life-event windows, timelines, and short daily/weekly outlooks.
- **Compatibility** — evaluating relationship fit for individuals and groups, including Western synastry and Vedic Ashtakoota.

The engine is headless: it does not render UI itself (except for a separate aspect-card admin tool) and is designed to be consumed by frontends, other microservices, and partner integrations.

## 3. Who It’s For

Primary personas implied by the codebase:

- **End Users** — consumers using a mobile or web app to view their natal chart, life events, and compatibility with others.
- **Astrologers / Astrology Product Owners** — domain experts who curate aspect cards, review interpretations, and validate scoring models via the aspect card admin UI (`aspect_card_utils.aspect_card_mgmt`).
- **Product & Growth Teams** — teams who embed the API into customer journeys (onboarding, retention campaigns, relationship reports, etc.).
- **Engineers / Platform Teams** — developers integrating the REST API into larger systems or apps.

## 4. What Phase‑1 Delivers

Phase‑1, as implemented in this repository, delivers:

- A FastAPI-based REST service with:
  - Uniform error envelopes and metadata (`schemas.ErrorResponse`, `schemas.Meta`).
  - Request/response validation using Pydantic models in `schemas.py`.
  - Health and readiness probes (`/healthz`, `/readyz`).
- Core features:
  - **Natal chart build**: `/api/natal/build-chart`.
  - **Natal aspects** (with knowledge-base backed “aspect cards”): `/api/natal/aspects`.
  - **Basic natal characteristics & KPIs** (placeholder narrative): `/api/natal/characteristics`.
  - **Life events** derived from transit windows: `/api/reports/life-events`.
  - **Report timelines** with aspect-based summaries and key points: `/api/reports/timeline`.
  - **Daily/weekly outlook** using aspect facets: `/api/reports/daily-weekly`.
  - **Upcoming events** (short horizon life events): `/api/reports/upcoming-events`.
  - **Pairwise synastry compatibility**: `/api/compat/synastry`.
  - **Group compatibility** (up to 10 people): `/api/compat/group`.
  - **Soulmate DOB suggestions** (simple heuristic): `/api/compat/soulmate-finder`.
  - **Vedic Ashtakoota (Gun Milan)**: `/api/compat/ashtakoota`.
- A curated knowledge base of ~500 aspect cards in `kb/aspects`, indexable via `kb/index.json` and served by a dedicated admin app.

## 5. Problem Statement / User Pain Points

Based on implemented features and data models, Phase‑1 addresses these pains:

- **Fragmented astrology tooling** — Natal charts, timelines, synastry, and Vedic matching are often handled by separate tools. Astro Vision unifies them into a single API.
- **Manual interpretation & inconsistency** — Human astrologers or simple scripts often produce inconsistent text. Aspect cards and structured facets centralize interpretations so that the same aspect always carries aligned meaning, life-event tags, and key points.
- **Lack of automation for time windows** — Calculating when key aspect windows start, peak, and end (for transits) is computationally heavy. `astro_core.calc_aspect_periods` and `services.report_services` automate this and expose ready-to-use life events and report timelines.
- **Opaque compatibility scores** — Compatibility is often presented as a single non-explained number. Astro Vision breaks this into KPIs (emotional, communication, chemistry, stability, group KPIs, etc.) and provides explanations/facets in the Vedic module.
- **Difficulty localizing content** — Bilingual fields (`locales.en`, `locales.hi`) and multilingual “core” texts in aspect cards allow localization without changing the core engine.

## 6. Solution Overview

At a business level, Astro Vision works as follows:

1. **Input capture** — Clients send structured JSON payloads with birth details (`BirthPayload`, `PersonPayload`) and report parameters (time periods, start dates).
2. **Celestial computation** — `astro_core.astro_core` uses Swiss Ephemeris to calculate planetary positions, aspects, and aspect periods, supporting both sidereal (e.g., Lahiri) and tropical modes.
3. **Knowledge-base enrichment** — Aspect windows and natal aspects are mapped to aspect card IDs (e.g., `JUP_CON_MOO__v1.0.0`) and enriched with:
   - Core meanings, facets, and life-event types.
   - Bilingual narrative fields.
   - Actionable advice grouped by aspect phase (applying/exact/separating).
4. **Scoring and aggregation** — Services compute:
   - Natal aspect strengths.
   - Pairwise synastry KPIs and overall scores.
   - Group cohesion and per-KPI group harmony scores.
   - Vedic Ashtakoota (8 kootas) total and banded interpretation.
5. **Response packaging** — Results are returned in uniform envelopes with `meta` and `data` sections, enabling traceability and observability.

What is automated vs manual:

- **Automated**
  - All astronomical and astrological calculations (planet positions, aspects, windows, Ashtakoota scoring).
  - Construction of timelines, daily/weekly outlooks, and group compatibility stats.
  - Fetching and shaping of aspect card fields into report-friendly structures.
- **Manual / Expert‑driven**
  - Authoring and maintaining aspect cards in the `kb/aspects` knowledge base.
  - Deciding which KPIs, thresholds, and narratives are “production ready” beyond current placeholders.

## 7. Key Features (Phase‑1)

### 7.1 Feature Summary Table

| # | Journey            | Feature                                 | Endpoint / Module                      | Description |
|---|--------------------|------------------------------------------|----------------------------------------|-------------|
| 1 | Natal              | Natal Chart Build                       | `/api/natal/build-chart`              | Computes planetary positions, zodiac signs, and houses using Whole Sign houses. |
| 2 | Natal              | Natal Aspects                           | `/api/natal/aspects`                  | Detects aspects between natal planets and enriches them with aspect card content. |
| 3 | Natal              | Natal Characteristics & KPIs            | `/api/natal/characteristics`          | Returns a high-level personality description and KPI list (currently placeholder text). |
| 4 | Reports            | Life Events                             | `/api/reports/life-events`            | Generates upcoming major/minor life events from transit-to-natal aspects. |
| 5 | Reports            | Upcoming Events (Short Horizon)         | `/api/reports/upcoming-events`        | Short-horizon version of life events for near-term planning. |
| 6 | Reports            | Timeline                                | `/api/reports/timeline`               | Produces a timeline of aspect windows with descriptions, facets, and key points. |
| 7 | Reports            | Daily/Weekly Outlook                    | `/api/reports/daily-weekly`           | Aggregates facets into themed areas for short-form updates. |
| 8 | Compatibility      | Pairwise Synastry                       | `/api/compat/synastry`                | Calculates KPIs (emotional, communication, chemistry, stability, elemental balance) and an overall score. |
| 9 | Compatibility      | Group Compatibility                     | `/api/compat/group`                   | Analyzes up to 10 people, returning pairwise and group harmony KPIs and a summary. |
|10 | Compatibility      | Soulmate Finder                         | `/api/compat/soulmate-finder`         | Suggests candidate dates of birth near the subject’s birth year (placeholder heuristic). |
|11 | Compatibility      | Vedic Ashtakoota (Gun Milan)           | `/api/compat/ashtakoota`              | Computes 8-koota score (0–36) and explanation for marriage suitability. |
|12 | Knowledge Base     | Aspect Card JSON API + Admin UI        | `aspect_card_utils.aspect_card_mgmt`  | Provides CRUD for aspect cards and read-only views, powering narrative content. |
|13 | Platform / Infra   | Health & Readiness                      | `/healthz`, `/readyz`                 | Basic liveness/readiness checks for orchestration. |

### 7.2 Journey Grouping

- **Natal Journey**
  - User provides birth details.
  - API returns:
    - Chart table of planets with sign and house.
    - Aspect list with strengths and characteristics.
    - Basic description and 2–3 personality KPIs.

- **Reports Journey**
  - User selects a horizon (e.g., 6 months, 1 week) and start date.
  - API returns:
    - List of life events with dates and descriptions.
    - Timeline items with aspect windows and key points/actionables.
    - Daily/weekly areas summarizing themes using “facets” from aspect cards.

- **Compatibility Journey (Synastry)**
  - User submits two profiles.
  - API returns:
    - KPI scores (emotional, communication, chemistry, stability, elemental balance).
    - Total compatibility score and narrative summary.

- **Group Compatibility Journey**
  - User submits 2–10 profiles plus a context type (Friendship Group, Professional Team, Sport Team, Family, Relative).
  - API returns:
    - Pairwise scores and short descriptions per pair.
    - Group harmony scores per KPI and a total group score.
    - Short summary with strengths and watchouts.

- **Vedic Matchmaking Journey**
  - User submits two profiles and optional parameters (ayanamsa, coordinate system, strict tradition, exceptions).
  - API returns:
    - Detailed koota scores with explanation text.
    - Total Gun Milan score and match band.

## 8. User Personas & Journeys

### 8.1 Personas

- **P1: Consumer / End User**
  - Wants quick, understandable outputs: natal insights, upcoming events, and compatibility scores.
  - Experiences Astro Vision through a client app that calls this API.

- **P2: Astrologer / Content Curator**
  - Manages the aspect card library using the admin UI.
  - Ensures interpretations, life-event tags, and actionables align with the brand’s philosophy.

- **P3: Product / Growth Manager**
  - Designs journeys that embed Astro Vision outputs (e.g., on signup, during campaigns, or for premium reports).
  - Uses compatibility scores and life events for segmentation and triggers.

- **P4: Backend / Platform Engineer**
  - Integrates the API with authentication, billing, and customer databases.
  - Monitors health probes and error envelopes.

### 8.2 Example Journeys

#### Journey 1 — Natal Insight (End User)

1. User enters name, date/time/place of birth and confirms location/timezone.
2. Client app calls `/api/natal/build-chart`.
3. Client optionally calls `/api/natal/aspects` and `/api/natal/characteristics`.
4. UI displays:
   - Planet table (e.g., “Sun in Leo, 5th house”).
   - Aspect list with tags (e.g., key facets like career/relationships).
   - A short personality overview and KPI bars.

#### Journey 2 — Life Events & Timeline (End User)

1. User chooses a time horizon (e.g., next 3 months or next week) and start date.
2. Client app calls `/api/reports/life-events` and/or `/api/reports/timeline`.
3. Service identifies active transit-to-natal aspect windows and maps them to life-event tags.
4. UI shows:
   - Cards like “Major career window” or “Relationship focus”, with start, exact, and end dates.
   - A timeline view summarizing what to expect when.

#### Journey 3 — Relationship Compatibility (Couple)

1. User enters details for self and partner.
2. Client calls `/api/compat/synastry`.
3. Service computes synastry KPIs and a total score out of 10, plus a summary sentence referencing strongest KPI and top aspects.
4. UI displays:
   - Overall percentage and label (e.g., good/strong).
   - KPI bars for emotional, communication, chemistry, stability, and elemental balance.

#### Journey 4 — Group Dynamics (Team / Family)

1. Organizer enters 2–10 people and selects a group type (e.g., “Professional Team”).
2. Client calls `/api/compat/group`.
3. Service runs pairwise synastry, aggregates KPIs, and computes overall group cohesion.
4. UI shows:
   - Heatmap of pairwise scores.
   - Top strengths and risk areas for the group.

#### Journey 5 — Vedic Matchmaking (Marriage)

1. User enters details for self and partner.
2. Client calls `/api/compat/ashtakoota` (optionally specifying ayanamsa and coordinate system).
3. Service calculates the 8 kootas and returns total points (0–36) with explanation.
4. UI displays:
   - Total score and band (e.g., “Strong Match”).
   - Per-koota breakdown (varna, vashya, tara, yoni, graha maitri, gana, bhakoot, nadi).

## 9. Inputs & Outputs (Business View)

### 9.1 Inputs

| Category        | Input                          | Notes |
|-----------------|---------------------------------|-------|
| Identity        | `name`                         | Person’s display name. |
| Birth Data      | `dateOfBirth`                  | ISO `YYYY-MM-DD`. |
|                 | `timeOfBirth`                  | `HH:MM` or `HH:MM:SS` (24h). |
|                 | `placeOfBirth`                 | Human-readable (city, country). |
| Coordinates     | `latitude`, `longitude`        | Decimal degrees; north/east positive. |
| Timezone        | `timeZone`                     | IANA string (e.g., `Asia/Kolkata`). |
| Reporting Views | `timePeriod`                   | `1Y`, `6M`, `1M`, `1W`, `1D` depending on endpoint. |
|                 | `reportStartDate` / `start_date` | Report anchor date. |
|                 | `horizon_days`                 | Days ahead for life events / upcoming events. |
|                 | `mode`                         | For daily/weekly: `DAILY` or `WEEKLY`. |
| Compatibility   | `type` (pair/group)           | Business context: `General`, `Marriage`, `Friendship`, `Professional`, `Friendship Group`, etc. |
| Headers         | `X-Request-ID`, `X-Session-ID`, `X-Transaction-ID`, `X-User-ID`, `X-App-ID` | Optional; used for tracing and analytics. |

### 9.2 Outputs

| Category        | Output                         | Description |
|-----------------|--------------------------------|-------------|
| Natal Chart     | Planet entries (`planetName`, `planetSign`, `planetDegree`, `houseNumber`, `houseName`, `houseSign`) | Tabular chart for UI display. |
| Natal Aspects   | Aspect list                    | Aspect label, angle, distance from exact, strength, plus `characteristics` from aspect cards. |
| Characteristics | Description & KPIs             | Short narrative and 2–3 KPIs (currently static placeholder text). |
| Life Events     | List of `LifeEvent`           | Each has aspect label, type (MAJOR/MINOR), dates, and description. |
| Timeline        | `TimelineItem` list + summary | Items include aspect, dates, optional description, keyPoints (actionables), and facets-based themes. |
| Daily/Weekly    | `DailyWeeklyData`             | Short summary plus dictionary of areas/themes mapped from facets. |
| Synastry Pair   | `CompatibilityData`           | KPI list (name, score, description), normalized totalScore (0–1), and summary string. |
| Group           | `GroupCompatibilityData`      | Pairwise rows, groupHarmony KPI list, and totalGroupScore (0–1). |
| Soulmate Finder | `datesOfBirth`                | List of DOB suggestions near user’s birth year. |
| Vedic           | `AshtakootaData`              | Raw koota results, derived insights, and explanation string. |
| Meta            | `Meta`                        | Timestamp, requestId, session/app/user IDs, and API version. |
| Errors          | `ErrorResponse`               | Structured error with code, message, and per-field detail. |

## 10. Value / Benefits

- **Better Accuracy** — Uses Swiss Ephemeris and configurable ayanamsa for precise planetary positions.
- **Consistent Interpretations** — Aspect cards provide a single source of truth for meanings, life-event labels, and actionables reused across journeys.
- **Personalization** — Most outputs are computed specifically for an individual’s birth data and time window; compatibility outputs consider both charts and context type.
- **Multi-system Coverage** — Supports Western natal, Western synastry, group compatibility, and Vedic Ashtakoota within one service.
- **Localization Ready** — Aspect cards carry bilingual fields (currently English and Hindi) used in timelines and daily/weekly outputs.
- **Scalability** — Stateless HTTP API with clear liveness/readiness endpoints that can be horizontally scaled.

## 11. Constraints & Out‑of‑Scope (Phase‑1)

- **No Authentication/Authorization** — The core service does not implement auth, rate limiting, or quota management. These must be provided by the hosting environment or API gateway. (Assumption (verify): upstream system will handle auth.)
- **No Persistent User Accounts** — The service is stateless; there is no built-in user or session database in this repo.
- **Limited Narrative Depth** — Several endpoints (e.g., `/api/natal/characteristics`, parts of reports) use placeholder text rather than full production copy.
- **No PDF/Document Generation** — There is no PDF/Word export pipeline in this codebase; integration with document generation tools is out of scope for Phase‑1. (Assumption (verify))
- **No Messaging Integrations** — There are no WhatsApp/email/SMS connectors in this repo. (Assumption (verify))
- **Ops / Monitoring Minimal** — Basic logging via middleware and exception handlers is present; structured tracing, metrics, and alerts are not fully implemented.

## 12. Future Roadmap (Phase‑2+)

These items are not implemented but are implied by comments or patterns; they should be treated as assumptions until confirmed:

- **Deeper Natal Characteristics** — Replace placeholder natal characteristics narrative with AI‑ or KB‑backed descriptions using aspect cards and KPIs. *Assumption (verify).* (See comment in `api_router.natal_characteristics`.)
- **Richer Dignities & Scores** — Populate `dignities_table` with real dignities and essential scores instead of dummy values. *Assumption (verify).* 
- **Language Expansion** — Expand `locales` beyond English/Hindi to additional languages using the same aspect card structure. *Assumption (verify).* 
- **Advanced Report Generation** — Use `TimelineData.aiSummary` as input for richer AI-written report paragraphs and multi-section documents. *Assumption (verify).* 
- **Client-Specific Integrations** — Attach downstream systems (CRM, notifications) using upcoming events and timelines as triggers. *Assumption (verify).* 

## 13. Glossary

- **Ayanamsha** — The angular offset between tropical and sidereal zodiacs; determines how sidereal positions are calculated. Configured in `astro_core.astro_core`.
- **Aspect** — Specific angular relationship between two planets (e.g., Conjunction 0°, Sextile 60°, Square 90°, Trine 120°, Opposition 180°).
- **Aspect Card** — A JSON document in `kb/aspects` describing the meaning, life-event tags, facets, and actionables for a specific planet–aspect–planet combination (e.g., `JUP_CON_MOO__v1.0.0`).
- **Ashtakoota (Gun Milan)** — A Vedic compatibility framework assigning up to 36 points across 8 kootas (Varna, Vashya, Tara, Yoni, Graha Maitri, Gana, Bhakoot, Nadi) to evaluate marriage suitability.
- **Compatibility (Synastry)** — Comparison of two natal charts to assess relationship potential using planetary aspects and element/modality balance.
- **Facets** — Themed interpretations in aspect cards (e.g., career, relationships, money, health) used to populate timeline and daily/weekly “areas”.
- **Gun** — A “point” in the Vedic Ashtakoota system; total score ranges from 0 to 36.
- **House** — A division of the natal chart representing life areas (e.g., 1st house: self, 7th house: partnership). Whole Sign houses are used by default.
- **KB (Knowledge Base)** — The `kb` folder containing aspect cards, index, and structured CSV used for interpretations and life-event tagging.
- **Meta Envelope** — Standard metadata block (`Meta`) returned with every response, containing timestamp, request ID, and API version.
- **Sidereal / Tropical** — Two zodiac reference systems: sidereal anchors to fixed stars (using ayanamsa), while tropical anchors to the equinox.
- **Synastry Group Analysis** — Extension of synastry to multiple people, summarizing pairwise dynamics and overall group harmony.

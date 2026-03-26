# Airbnb Benchmark Tool

## Project Overview
Tool per confrontare prezzi e disponibilità delle property Airbnb di Vladimiro con i competitor. Dashboard Streamlit deployata su Streamlit Cloud.

## Architecture
- **Frontend**: Streamlit (Python)
- **Database**: Supabase (project: `eijyeltpbafgltqgiytz`, region: eu-west-1, org: Habenas)
- **Pricing API**: Airbnb internal GraphQL API (no Apify needed for this tool)
- **Deploy**: Streamlit Cloud → https://airbnb-benchmark-jbo5rwmrsf2e98mdh2sunj.streamlit.app
- **Repo**: https://github.com/vla-sys/airbnb-benchmark.git

## Key Files
- `app.py` — Main Streamlit app (UI, auth, calendar rendering, Supabase integration)
- `scraper.py` — Airbnb calendar & pricing scraper via internal GraphQL API
- `requirements.txt` — Python dependencies
- `saved_competitors.json` — Local fallback for competitor storage
- `last_refresh.json` — Local fallback for refresh timestamps

## Benchmark Properties
- **Ca'Mugo** 🏔️ — Listing ID: `1363939812329907610`, Borca di Cadore, Dolomiti
- **Ca'Mirto** 🏖️ — Listing ID: `12323106`, San Teodoro, Sardegna

## Supabase Tables
- `saved_competitors` — (property_name, competitor_name, airbnb_url, listing_id) with UNIQUE on (property_name, listing_id)
- `refresh_log` — (property_name, last_refresh) with UNIQUE on property_name
- RLS enabled with "Allow all" policies (single-user app, anon key)

## Streamlit Cloud Secrets
Configured in Streamlit Cloud Settings → Secrets:
- `password` — Login password
- `SUPABASE_URL` — https://eijyeltpbafgltqgiytz.supabase.co
- `SUPABASE_KEY` — Supabase anon key

## Scraper Details
- Uses Airbnb's internal `PdpAvailabilityCalendar` GraphQL endpoint for calendar/availability
- Uses `StaysPdpSections` endpoint for pricing (fetches BOOK_IT_SIDEBAR section)
- Price extraction: parses "X nights x €price" pattern from response, fallback to structuredDisplayPrice
- Interpolation: forward + backward fill for available days only (no prices shown for booked days)
- Monthly probes: synthetic check-in windows generated for months with few available dates
- Guaranteed monthly sampling: at least 1 API call per month for price coverage

## Known Limitations
- Airbnb API returns NO price for fully booked dates → those months show interpolated prices from nearest available
- Ca'Mirto July mostly booked → prices interpolated from June (~€651) may not reflect actual July pricing (~€978 in Aug)
- API hash values (`CALENDAR_HASH`, `PDP_SECTIONS_HASH`) may need updating if Airbnb changes their GraphQL schema

## Apify (separate project: airbnb-monitor)
- Token: configured in airbnb-monitor/config.py
- Actor: `tri_angle/airbnb-scraper` with `locationQueries` input
- Free tier: $5/month, sufficient for ~4000 results/month
- Old project at `/Users/vladimiromazzotti/Dropbox/Claude Code/airbnb-monitor/`

## UI/UX
- Premium dark hero header with gradient
- Glassmorphism effects
- Login gate with password
- Per-property competitor lists (Salvati / Nuovo URL / Gestisci tabs)
- Monthly calendar with color-coded price comparison (green = benchmark cheaper, red = competitor cheaper)
- Months selector (1-12), precision slider, refresh button with timestamp
- Sidebar hidden, deploy button hidden

## Development Notes
- Always test locally before pushing (`python3 -c "import ast; ast.parse(open('app.py').read())"`)
- Push to main triggers auto-deploy on Streamlit Cloud (~1-2 min)
- User prefers Italian UI
- User wants to be consulted before major changes

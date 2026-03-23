# StudyMind (Study Analyser)

A Django web app to log study sessions, track assignments, and generate an AI-assisted daily study timetable based on:
- upcoming deadlines, and
- your historical focus levels per subject.

## Features

- **Student dashboard**: log study sessions (duration + focus level), see totals and streaks
- **Assignments**: add deadlines + estimated hours, mark completed
- **AI-generated timetable**: prioritizes urgent deadlines and weaker-focus subjects
- **Chat widget (optional)**: powered by Google Gemini via `google-generativeai`

## How the timetable is generated

The schedule you see in the **Schedule** tab is computed server-side in:
- `STYDY_ANALYSER/studyanalyser/student/views.py` -> `generate_study_plan(user)`

High-level logic:
1. Picks up to **2 urgent assignments** due within the next **3 days** (and not completed).
2. Computes **average focus % per subject** from your `StudySession` history.
3. Fills a fixed set of daily **time slots**:
   - urgent assignments first (also estimates remaining hours from logged sessions)
   - then remaining subjects sorted by **lowest average focus first**
4. Labels each slot as:
   - **Deep Work** when avg focus `< 50%`
   - **Standard Study** when `50-79%`
   - **Review** when `>= 80%`

The dashboard view (`user_dashboard`) calls `generate_study_plan(request.user)` on each page load, so the timetable updates automatically when you log sessions / add assignments / mark work done.

## Requirements

- Python 3.x (use a version compatible with your Django version)
- Django (see `STYDY_ANALYSER/studyanalyser/requirements.txt`)

## Run locally

From the repo root:

```powershell
cd .\STYDY_ANALYSER\studyanalyser
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Environment variables

Create a `.env` file (recommended) or set environment variables in your shell.

### Django

- `DJANGO_SECRET_KEY` (recommended for production)
- `DJANGO_DEBUG` (`1` for dev, `0` for production)
- `DJANGO_ALLOWED_HOSTS` (comma-separated, e.g. `example.com,www.example.com`)
- `DJANGO_TIME_ZONE` (default: `Asia/Kolkata`)

### Gemini chat (optional)

- `GEMINI_API_KEY` (required to enable chat)
- `GEMINI_MODEL` (optional, default: `gemini-1.5-flash`)

## GitHub (push this project)

This repo already includes a `.gitignore` that avoids committing secrets and local data (like `.env`, `db.sqlite3`, and `venv/`).

Typical workflow:

```powershell
cd C:\Users\VICTUS\Downloads\STUDY_ANALYSER\STYDY_ANALYSER
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

Note: In the remote URL, don’t include `<` `>` — replace them with your real username/repo.

## Project structure (important paths)

- `STYDY_ANALYSER/studyanalyser/manage.py` – Django entrypoint
- `STYDY_ANALYSER/studyanalyser/studyanalyser/settings.py` – settings (env-driven)
- `STYDY_ANALYSER/studyanalyser/student/` – app (models, views, forms, chat)
- `STYDY_ANALYSER/studyanalyser/templates/` – templates (dashboard UI)
- `STYDY_ANALYSER/studyanalyser/static/` – static assets (dev)

# FocusFlow — Premium To-Do Web App

A responsive task manager built with Python Flask, SQLite, HTML, CSS and JavaScript.

## Features
- Add, complete/undo, and delete tasks
- Priority levels: Low, Medium, High
- Optional due dates
- Search and All/Pending/Completed filters
- Live statistics and progress bar
- SQLite persistence

## Run locally (Windows)
1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. Open Terminal and run:

   ```bash
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   py app.py
   ```

4. Open `http://127.0.0.1:5000` in your browser.

If `py` does not work, use `python` instead.

## Deploy
This project includes a `Procfile` and `render.yaml` for Render deployment.
For reliable persistent SQLite storage on Render, attach a persistent disk and place the database on that disk (or use a managed PostgreSQL database). The default SQLite file is suitable for local development, but an ephemeral hosting filesystem can reset on redeploy/restart.


### Keep SQLite data persistent on Render
The default free filesystem is ephemeral. If you deploy with a Render paid web service and attach a persistent disk mounted at `/var/data`, add this environment variable:

`DATABASE_PATH=/var/data/tasks.db`

This tells FocusFlow to store its SQLite database on the persistent disk. Without a persistent disk, data may be lost when the service restarts or redeploys.

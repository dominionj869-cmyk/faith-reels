
import os
import sqlite3
from datetime import datetime
from html import escape

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Faith Reels")

DB_PATH = os.getenv("DB_PATH", "faith_reels.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_db():
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                caption TEXT NOT NULL,
                video_url TEXT NOT NULL,
                platforms TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Queued'
            )
            """
        )


setup_db()


@app.get("/", response_class=HTMLResponse)
def home():
    with get_db() as db:
        videos = db.execute(
            "SELECT * FROM videos ORDER BY id DESC"
        ).fetchall()

    rows = ""

    for video in videos:
        rows += (
            "<tr><td>" + str(video["id"]) + "</td>"
            "<td>" + escape(video["title"]) + "</td>"
            "<td>" + escape(video["platforms"]) + "</td>"
            "<td>" + escape(video["scheduled_at"]) + "</td>"
            "<td>" + escape(video["status"]) + "</td></tr>"
        )

    if not rows:
        rows = (
            "<tr><td colspan='5'>"
            "No videos scheduled yet."
            "</td></tr>"
        )

    page = """
    <!doctype html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Faith Reels</title>
    <style>
    body {
        font-family: Arial, sans-serif;
        background: #101827;
        color: white;
        margin: 0;
        padding: 20px;
    }
    main {
        max-width: 850px;
        margin: auto;
    }
    .panel {
        background: #1d293b;
        padding: 18px;
        border-radius: 14px;
        margin: 16px 0;
    }
    input:not([type=checkbox]), textarea, select {
        box-sizing: border-box;
        width: 100%;
        padding: 12px;
        margin: 7px 0 14px;
        border-radius: 7px;
        border: 1px solid #526078;
    }
    button {
        background: #25a56a;
        color: white;
        padding: 13px;
        border: 0;
        border-radius: 8px;
        width: 100%;
        font-weight: bold;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    th, td {
        padding: 9px 5px;
        border-bottom: 1px solid #405067;
        text-align: left;
        overflow-wrap: anywhere;
    }
    h1 {
        color: #69e6a2;
    }
    </style>
    </head>
    <body>
    <main>
    <h1>Faith Reels</h1>
    <p>Plan your Christian video content in one place.</p>

    <div class="panel">
    <h2>Add a video</h2>
    <form method="post" action="/add">

    <label>Video title</label>
    <input name="title" required maxlength="150">

    <label>Caption</label>
    <textarea name="caption" required maxlength="2000"></textarea>

    <label>Direct HTTPS video URL</label>
    <input name="video_url" type="url"
    placeholder="https://example.com/video.mp4" required>

    <label>Platforms (select one or more)</label>
    <select name="platforms" multiple required size="4">
    <option value="YouTube">YouTube</option>
    <option value="Instagram">Instagram</option>
    <option value="Facebook">Facebook</option>
    <option value="TikTok">TikTok</option>
    </select>

    <small>On mobile, press and hold to select multiple options if supported.</small>

    <label>Schedule date and time</label>
    <input name="scheduled_at" type="datetime-local" required>

    <p>
    <label>
    <input type="checkbox" name="rights" value="yes" required>
    I own this video or have permission to publish it.
    </label>
    </p>

    <button type="submit">Add to queue</button>
    </form>
    </div>

    <div class="panel">
    <h2>Video queue</h2>
    <table>
    <tr>
    <th>ID</th>
    <th>Title</th>
    <th>Platforms</th>
    <th>Scheduled</th>
    <th>Status</th>
    </tr>
    ROWS
    </table>
    </div>

    <p>
    Videos are saved to this dashboard only.
    Automatic social media publishing is not connected yet.
    </p>
    </main>
    </body>
    </html>
    """

    return HTMLResponse(page.replace("ROWS", rows))


@app.post("/add")
def add_video(
    title: str = Form(...),
    caption: str = Form(...),
    video_url: str = Form(...),
    platforms: list[str] = Form(...),
    scheduled_at: str = Form(...),
    rights: str = Form(...)
):
    if rights != "yes":
        return HTMLResponse(
            "Permission confirmation is required.",
            status_code=400
        )

    if not video_url.startswith("https://"):
        return HTMLResponse(
            "Use a secure HTTPS video URL.",
            status_code=400
        )

    allowed = {
        "YouTube",
        "Instagram",
        "Facebook",
        "TikTok"
    }

    selected = [p for p in platforms if p in allowed]

    if not selected:
        return HTMLResponse(
            "Select at least one platform.",
            status_code=400
        )

    if not title.strip() or not caption.strip():
        return HTMLResponse(
            "Title and caption are required.",
            status_code=400
        )

    try:
        when = datetime.fromisoformat(scheduled_at)
    except ValueError:
        return HTMLResponse(
            "Invalid schedule time.",
            status_code=400
        )

    with get_db() as db:
        db.execute(
            """
            INSERT INTO videos
            (title, caption, video_url, platforms,
             scheduled_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title.strip(),
                caption.strip(),
                video_url.strip(),
                ", ".join(selected),
                when.isoformat(),
                "Queued"
            )
        )

    return RedirectResponse("/", status_code=303)


@app.get("/health")
def health():
    return {"status": "ok", "app": "Faith Reels"}


import os
import json
import html
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def db_request(method, path, data=None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase environment variables are missing.")

    url = SUPABASE_URL + "/rest/v1/videos" + path
    body = None

    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", "Bearer " + SUPABASE_KEY)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept-Profile", "public")
    req.add_header("Content-Profile", "public")
    req.add_header("Prefer", "return=representation")

    with urllib.request.urlopen(req, timeout=20) as response:
        result = response.read().decode("utf-8")
        return json.loads(result) if result else []


def page(message=""):
    rows = ""
    error = ""

    try:
        videos = db_request(
            "GET",
            "?select=id,title,platforms,scheduled_at,status"
            "&order=scheduled_at.desc"
        )

        for video in videos:
            rows += (
                "<tr><td>" + html.escape(str(video["id"])) + "</td>"
                "<td>" + html.escape(video["title"]) + "</td>"
                "<td>" + html.escape(video["platforms"]) + "</td>"
                "<td>" + html.escape(video["scheduled_at"]) + "</td>"
                "<td>" + html.escape(video["status"]) + "</td></tr>"
            )

    except Exception as exc:
        error = str(exc)

    if not rows:
        rows = "<tr><td colspan='5'>No videos found.</td></tr>"

    notice = ""
    if message:
        notice = "<p class='notice'>" + html.escape(message) + "</p>"

    if error:
        notice += (
            "<p class='error'>Database connection error: "
            + html.escape(error)
            + "</p>"
        )

    return """
    <!doctype html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Faith Reels</title>
    <style>
    body{font-family:Arial,sans-serif;max-width:900px;margin:24px auto;
    padding:0 14px;background:#f7f7fb;color:#222}
    input,textarea,select,button{box-sizing:border-box;width:100%;
    padding:12px;margin:7px 0;border:1px solid #ccc;border-radius:7px}
    label{display:block;margin-top:12px;font-weight:bold}
    button{background:#176b50;color:white;font-weight:bold;border:0}
    .notice{background:#e1f5e8;padding:12px}
    .error{background:#ffe6e6;padding:12px;overflow-wrap:anywhere}
    .tablebox{overflow-x:auto}table{width:100%;background:white;
    border-collapse:collapse}th,td{padding:9px;border:1px solid #ddd;
    text-align:left}h1{color:#176b50}
    </style>
    </head>
    <body>
    <h1>Faith Reels</h1>
    <p>Plan your Christian video content in one place.</p>
    """ + notice + """
    <h2>Add a video</h2>
    <form action="/add" method="post">
    <label>Video title</label>
    <input name="title" required maxlength="200">
    <label>Caption</label>
    <textarea name="caption" required rows="4"></textarea>
    <label>Direct HTTPS video URL</label>
    <input name="video_url" type="url" placeholder="https://..."
    required>
    <label>Platforms (select one or more)</label>
    <select name="platforms" multiple required size="4">
    <option>YouTube</option>
    <option>Instagram</option>
    <option>Facebook</option>
    <option>TikTok</option>
    </select>
    <p>On mobile, press and hold to select multiple options if supported.</p>
    <label>Schedule date and time</label>
    <input name="scheduled_at" type="datetime-local" required>
    <label><input type="checkbox" name="permission" value="yes"
    required style="width:auto"> I own this video or have permission
    to publish it.</label>
    <button type="submit">Add to queue</button>
    </form>
    <h2>Video queue</h2>
    <div class="tablebox"><table>
    <tr><th>ID</th><th>Title</th><th>Platforms</th>
    <th>Scheduled</th><th>Status</th></tr>
    """ + rows + """
    </table></div>
    <p>Videos are saved in Supabase. Automatic social media publishing
    is not connected yet.</p>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def home():
    return page()


@app.get("/health")
def health():
    return {"status": "ok", "supabase_configured": bool(
        SUPABASE_URL and SUPABASE_KEY
    )}


@app.post("/add")
def add_video(
    title: str = Form(...),
    caption: str = Form(...),
    video_url: str = Form(...),
    platforms: list[str] = Form(...),
    scheduled_at: str = Form(...),
    permission: str = Form(...)
):
    title = title.strip()
    caption = caption.strip()
    video_url = video_url.strip()
    platforms = list(dict.fromkeys(platforms))

    allowed = ["YouTube", "Instagram", "Facebook", "TikTok"]

    if not title or not caption:
        return HTMLResponse(page("Enter a title and caption."))

    if not video_url.startswith("https://"):
        return HTMLResponse(page("Use an HTTPS video URL."))

    if not platforms or any(p not in allowed for p in platforms):
        return HTMLResponse(page("Select valid platforms."))

    if permission != "yes":
        return HTMLResponse(page("Confirm you have publishing permission."))

    try:
        schedule = datetime.fromisoformat(scheduled_at)

        if schedule.tzinfo is None:
            lagos = timezone(timedelta(hours=1))
            schedule = schedule.replace(tzinfo=lagos)

        schedule = schedule.astimezone(timezone.utc).isoformat()

        db_request("POST", "?select=id", {
            "title": title,
            "caption": caption,
            "video_url": video_url,
            "platforms": ", ".join(platforms),
            "scheduled_at": schedule,
            "status": "Queued"
        })

        return RedirectResponse("/", status_code=303)

    except Exception as exc:
        return HTMLResponse(
            page("Could not save video: " + str(exc)),
            status_code=500
        )

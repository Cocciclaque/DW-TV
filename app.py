import os, json, time, requests
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv
API_URL = "https://api.start.gg/gql/alpha"
API_KEY = os.getenv("START_GG_KEY")

load_dotenv()

CONFIG_PATH = os.path.join(os.getcwd(), "config.json")
print("CONFIG PATH IS : " + CONFIG_PATH)
app = Flask(__name__, template_folder="templates")

# Simple loader: always re-read the file
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "event_slugs": {},
            "scrollSpeed": 0.25,
            "refreshIntervalMs": 15000,
            "rotation": {"enabled": False}
        }


def graphql_query(query: str, variables: dict):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    resp = requests.post(API_URL, json={"query": query, "variables": variables}, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def get_event_id(event_slug: str) -> int:
    query = """
    query ($slug: String!) {
      event(slug: $slug) { id name }
    }
    """
    data = graphql_query(query, {"slug": event_slug})
    return data["event"]["id"]


def get_ongoing_sets(event_slug: str):
    query = """
    query ($eventId: ID!) {
      event(id: $eventId) {
        name
        sets(perPage: 20, sortType: STANDARD) {
          nodes {
            id
            startedAt
            completedAt
            winnerId
            displayScore
            station { number prefix }
            slots { entrant { name } }
          }
        }
      }
    }
    """
    eid = get_event_id(event_slug)
    data = graphql_query(query, {"eventId": eid})
    event_name = data["event"]["name"]  # <-- grab game/event name
    sets = data["event"]["sets"]["nodes"]
    ongoing = []
    now = int(time.time())
    for s in sets:
        if s.get("startedAt") and not s.get("completedAt"):
            players = [slot["entrant"]["name"] for slot in s["slots"] if slot.get("entrant")]
            elapsed = now - int(s["startedAt"])
            station = None
            if s.get("station"):
                prefix = s["station"].get("prefix") or ""
                number = s["station"].get("number")
                station = f"{prefix} {number}" if prefix else str(number)
            ongoing.append({
                "id": s["id"],
                "players": players,
                "score": s.get("displayScore"),
                "elapsed": elapsed,
                "station": station,
                "game": event_name  # <-- add game name
            })
    return ongoing

@app.route("/config")
def get_config():
    return jsonify(load_config())

@app.route("/api/ongoing/<page>")
def api_ongoing(page):
    cfg = load_config()
    slug = cfg.get("event_slugs", {}).get(page)
    if not slug:
        return jsonify({"error": "invalid page"}), 404
    return jsonify(get_ongoing_sets(slug))

@app.route("/index/<page>")
def index(page):
    cfg = load_config()
    if page not in cfg.get("event_slugs", {}):
        return "Invalid page", 404
    return render_template("board.html", page=page)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

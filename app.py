# app.py
import os
import time
import requests
from flask import Flask, jsonify, render_template

API_URL = "https://api.start.gg/gql/alpha"
API_KEY = os.getenv("START_GG_KEY") or "27e07da4ef74268bb5e236cc182c740a"

EVENT_SLUGS = {
    "1": "tournament/tournament-template-3/event/tekken-singles",
    "2": "tournament/tournament-template-3/event/strive-singles",
}

app = Flask(__name__, template_folder="templates")


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

@app.route("/api/ongoing/<page>")
def api_ongoing(page):
    slug = EVENT_SLUGS.get(page)
    if not slug:
        return jsonify({"error": "invalid page"}), 404
    return jsonify(get_ongoing_sets(slug))


@app.route("/index/<page>")
def index(page):
    slug = EVENT_SLUGS.get(page)
    if not slug:
        return "Invalid page", 404
    return render_template("board.html", page=page)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

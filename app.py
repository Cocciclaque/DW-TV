"""
startgg_ongoing_safe.py

Improved: automatically handles "query complexity too high" errors by retrying
with a lighter query and smaller per-page size.

Requirements:
    pip install requests

Usage:
    API_KEY = os.getenv("START_GG_KEY") or "<YOUR_KEY>"
    ongoing = get_ongoing_sets_for_event(API_KEY, "<event_slug_or_id>")
"""
import os
import time
import requests
from typing import List, Dict, Optional

API_URL = "https://api.start.gg/gql/alpha"

# Two GraphQL queries:
#  - FULL_QUERY: more fields (useful but heavier).
#  - LIGHT_QUERY: minimal fields to detect "ongoing" status.
FULL_QUERY = """
query EventSets($eventId: ID!, $page: Int!, $perPage: Int!) {
  event(id: $eventId) {
    id
    name
    sets(page: $page, perPage: $perPage, sortType: STANDARD) {
      pageInfo { total page perPage totalPages }
      nodes {
        id
        startAt
        startedAt
        completedAt
        state
        round
        station { number }
        stream { streamName }
        winnerId
        displayScore
        updatedAt
        slots(includeByes: true) {
          id
          entrant { id name }
          standing { id placement }
        }
      }
    }
  }
}
"""

LIGHT_QUERY = """
query EventSetsLight($eventId: ID!, $page: Int!, $perPage: Int!) {
  event(id: $eventId) {
    id
    name
    sets(page: $page, perPage: $perPage, sortType: STANDARD) {
      pageInfo { total page perPage totalPages }
      nodes {
        id
        startAt
        startedAt
        completedAt
        winnerId
        displayScore
        slots(includeByes: true) {
          id
          entrant { id name }
        }
      }
    }
  }
}
"""

class GraphQLComplexityError(RuntimeError):
    """Raised when the server rejects the query due to complexity limits."""
    pass

def _graphql_query(api_key: str, query: str, variables: dict) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    resp = requests.post(API_URL, json={"query": query, "variables": variables}, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        # look for complexity message
        msgs = data["errors"]
        # try to detect complexity error
        for e in msgs:
            msg_text = e.get("message", "")
            if "complexity" in msg_text.lower() or "maximum of 1000 objects" in msg_text.lower():
                raise GraphQLComplexityError(msg_text)
        # otherwise raise general runtime error with errors
        raise RuntimeError(f"GraphQL errors: {msgs}")
    return data["data"]

def get_event_id_from_slug(api_key: str, event_slug: str) -> int:
    query = """
    query EventBySlug($slug: String!) {
      event(slug: $slug) {
        id
        name
      }
    }
    """
    data = _graphql_query(api_key, query, {"slug": event_slug})
    event = data.get("event")
    if not event:
        raise ValueError(f"Event not found for slug: {event_slug}")
    return int(event["id"])

def fetch_event_sets_page(api_key: str, event_id: int, page: int = 1, per_page: int = 50, light: bool = False) -> dict:
    """
    Fetch one page of sets for an event. If the query is too complex, it will raise GraphQLComplexityError.
    Set 'light=True' to use a minimal query that is much less likely to trigger the complexity limit.
    """
    query = LIGHT_QUERY if light else FULL_QUERY
    variables = {"eventId": event_id, "page": page, "perPage": per_page}
    data = _graphql_query(api_key, query, variables)
    # defensive: the shape should be data["event"]["sets"]
    return data["event"]["sets"]

def fetch_all_sets_for_event(api_key: str, event_id: int, per_page: int = 50, max_pages: Optional[int] = None,
                             force_light: bool = False) -> List[dict]:
    """
    Collects all sets for an event using pagination.
    If the server responds with a complexity error, this function will automatically retry
    from the start using the light query + smaller per_page.
    """
    # Attempt full fetch (unless force_light)
    attempt_light = force_light
    tried_full_once = False

    while True:
        try:
            # choose per_page and query mode
            if attempt_light:
                used_per_page = min(per_page, 10)  # small page size for light mode
                light_mode = True
            else:
                used_per_page = per_page
                light_mode = False

            sets = []
            page = 1
            while True:
                container = fetch_event_sets_page(api_key, event_id, page=page, per_page=used_per_page, light=light_mode)
                nodes = container.get("nodes") or []
                sets.extend(nodes)

                page_info = container.get("pageInfo", {})
                total_pages = page_info.get("totalPages")
                if total_pages is None:
                    if len(nodes) < used_per_page:
                        break
                    page += 1
                else:
                    if page >= total_pages:
                        break
                    page += 1

                if max_pages and page > max_pages:
                    break

                # small sleep to avoid bursts
                time.sleep(0.08)

            return sets

        except GraphQLComplexityError as gce:
            # If we already tried light, re-raise with helpful message
            if attempt_light:
                raise RuntimeError("Even the light query hit the complexity limit. Try further reducing per_page or contacting start.gg dev support.") from gce

            # otherwise, switch to light mode and retry
            print("start.gg: query complexity too high for the full query. Retrying with a lighter query and smaller per_page...")
            attempt_light = True
            # loop will retry

def is_set_ongoing(set_node: dict) -> bool:
    started_at = set_node.get("startedAt") or set_node.get("startAt")
    completed_at = set_node.get("completedAt")
    winner_id = set_node.get("winnerId")

    # primary heuristic: started + no completedAt
    if started_at and not completed_at:
        return True
    # fallback: started + no winner
    if started_at and not winner_id:
        return True
    return False

def get_ongoing_sets_for_event(api_key: str, event: str, per_page: int = 50, force_light: bool = False) -> List[dict]:
    """
    Returns ongoing sets for a given event (slug or numeric id).
    If a complexity error happens, automatically falls back to the light query.
    Set force_light=True to skip attempting the full query.
    """
    try:
        event_id = int(event)
    except (ValueError, TypeError):
        event_id = get_event_id_from_slug(api_key, event)

    all_sets = fetch_all_sets_for_event(api_key, event_id, per_page=per_page, force_light=force_light)
    ongoing = [s for s in all_sets if is_set_ongoing(s)]
    return ongoing


# Example usage:
if __name__ == "__main__":
    API_KEY = os.getenv("START_GG_KEY") or "27e07da4ef74268bb5e236cc182c740a"
    EVENT_SLUGS = ["tournament/tournament-template-3/event/tekken-singles",
                    "tournament/tournament-template-3/event/strive-singles"]
    for EVENT_SLUG in EVENT_SLUGS:
        try:
            ongoing_sets = get_ongoing_sets_for_event(API_KEY, EVENT_SLUG, per_page=50)
            print(f"Found {len(ongoing_sets)} ongoing sets (returned minimal info).")
            for s in ongoing_sets:
                # print a compact summary
                e_names = []
                for slot in s.get("slots", []):
                    ent = slot.get("entrant")
                    if ent:
                        e_names.append(ent.get("name") or f"entrant:{ent.get('id')}")
                print(f"Set {s['id']} | startedAt={s.get('startedAt')} | score={s.get('displayScore')} | players={e_names}")
        except Exception as e:
            print("Error:", e)

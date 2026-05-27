import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 10))

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

# Folder where KB HTML files are saved, relative to this script.
KB_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb_output")


def get_all_tickets():
    # Fetch every ticket in the table. We diff against seen_ids locally
    # rather than filtering in the query, so out-of-order or non-sequential
    # IDs (e.g. after deletions) are handled correctly.
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/ticket_requests",
        headers=HEADERS,
        params={"order": "id.asc"},
    )
    response.raise_for_status()
    return response.json()


def find_matching_kb_articles(keywords):
    # If the ticket has no keywords there's nothing to match against, so return early.
    if not keywords:
        return []

    # --- How keyword matching works ---
    #
    # Both tickets and KB articles store their keywords as arrays in the database.
    # For example:
    #   Ticket keywords    : ["account access", "error message"]
    #   KB article keywords: ["account access", "login", "password reset"]
    #
    # We ask the database: "give me every KB article whose keyword list shares
    # at least ONE keyword with the ticket's keyword list."
    # That's called an ARRAY OVERLAP check — it doesn't require an exact match,
    # just any single keyword in common.
    #
    # The database operator for this is "&&" (overlap).
    # Supabase's REST API expresses it as "ov." in the query string.
    #
    # We format the ticket's keywords into the shape the API expects:
    #   ["account access", "error message"]  →  {"account access","error message"}
    #
    # The final URL filter looks like:
    #   ?keywords=ov.{"account access","error message"}
    #
    # The database then returns only KB articles that have at least one of
    # those keywords in their own keywords column.

    kw_filter = "{" + ",".join(f'"{k}"' for k in keywords) + "}"

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/kb_articles",
        headers=HEADERS,
        params={"keywords": f"ov.{kw_filter}"},
    )
    response.raise_for_status()
    return response.json()


def generate_kb_html(kb):
    """Write an HTML file for a KB article and return its file:// URL."""
    os.makedirs(KB_OUTPUT_DIR, exist_ok=True)

    keywords_html = "".join(f'<span class="tag">{k}</span>' for k in kb["keywords"])
    # Replace newlines in resolution with <br> so steps render correctly in the browser.
    resolution_html = kb["resolution"].replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{kb['id']} — ATM Knowledge Base</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #edf0f3;
      margin: 0;
      padding: 2rem 1rem;
      color: #1b2b3e;
    }}
    .card {{
      background: #fff;
      border: 1px solid #d0d9e2;
      border-radius: 8px;
      max-width: 680px;
      margin: 0 auto;
      padding: 2rem;
      box-shadow: 0 4px 16px rgba(27,43,62,0.1);
    }}
    .kb-id {{
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      color: #c85a1a;
      text-transform: uppercase;
      margin-bottom: 0.5rem;
    }}
    h1 {{
      font-size: 1.1rem;
      font-weight: 700;
      margin: 0 0 1.5rem;
      color: #1b2b3e;
    }}
    .section-label {{
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: #7a90a4;
      margin-bottom: 0.4rem;
    }}
    .section {{
      margin-bottom: 1.4rem;
    }}
    .resolution {{
      background: #f7f9fb;
      border: 1px solid #d0d9e2;
      border-radius: 6px;
      padding: 1rem 1.1rem;
      line-height: 1.7;
      font-size: 0.9375rem;
    }}
    .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }}
    .tag {{
      background: #edf0f3;
      border: 1px solid #b0bec9;
      border-radius: 4px;
      padding: 0.2rem 0.55rem;
      font-size: 0.8rem;
      color: #3d5168;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="kb-id">{kb['id']}</div>
    <h1>{kb['description']}</h1>

    <div class="section">
      <div class="section-label">Resolution</div>
      <div class="resolution">{resolution_html}</div>
    </div>

    <div class="section">
      <div class="section-label">Keywords</div>
      <div class="tags">{keywords_html}</div>
    </div>
  </div>
</body>
</html>"""

    file_path = os.path.join(KB_OUTPUT_DIR, f"{kb['id']}.html")
    with open(file_path, "w") as f:
        f.write(html)

    return f"file://{file_path}"


def terminal_link(text, url):
    """Wrap text in an OSC 8 terminal hyperlink (clickable in iTerm2 and most modern terminals)."""
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def print_ticket(ticket, matches):
    print("\n" + "=" * 60)
    print(f"  NEW TICKET #{ticket['id']}")
    print("=" * 60)
    print(f"  Title       : {ticket['title']}")
    print(f"  Submitted by: {ticket['submitted_by']}")
    print(f"  Priority    : {ticket['priority']}")
    print(f"  Description : {ticket['description'] or '—'}")
    print(f"  Keywords    : {', '.join(ticket['keywords']) or '—'}")
    print()

    if matches:
        # Generate an HTML file for each match and build a clickable link per ID.
        links = []
        for kb in matches:
            url = generate_kb_html(kb)
            links.append(terminal_link(f"[{kb['id']}]", url))

        print(f"  Matching KB Articles ({len(matches)} found): {' '.join(links)}")
    else:
        print("  No matching KB articles found.")

    print()


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return

    # Seed seen_ids with all tickets that already exist at startup.
    # This prevents old tickets from being displayed — only tickets
    # that arrive after the script is running will be processed.
    existing_tickets = get_all_tickets()
    seen_ids = {ticket["id"] for ticket in existing_tickets}

    print(f"ATM Ticket Monitor running. Found {len(seen_ids)} open tickets.\n")

    while True:
        try:
            all_tickets = get_all_tickets()

            for ticket in all_tickets:
                if ticket["id"] not in seen_ids:
                    matches = find_matching_kb_articles(ticket.get("keywords", []))
                    print_ticket(ticket, matches)
                    seen_ids.add(ticket["id"])

        except requests.RequestException as e:
            print(f"[Error] Could not reach Supabase: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

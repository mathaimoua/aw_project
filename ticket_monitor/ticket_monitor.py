import os
import re
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

# Common English words that carry no useful meaning for matching.
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "was", "are", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "this", "that", "these",
    "those", "i", "my", "we", "our", "you", "your", "he", "she", "they",
    "their", "his", "her", "not", "no", "so", "if", "as", "up", "out",
    "about", "into", "than", "then", "there", "can", "also", "just", "any",
}


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


def get_all_kb_articles():
    # Fetch every KB article. The KB table is small so this is fast,
    # and fetching everything lets us score all articles — not just
    # the ones that share keywords with the ticket.
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/kb_articles",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def significant_words(text):
    """
    Break text into lowercase words, remove stop words and short words.
    Returns a set of meaningful words for overlap comparison.

    Example:
      "I'm having issues connecting to IQ+"
      → {"issues", "connecting", "iq+"}
    """
    words = re.findall(r"[a-z0-9+]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOP_WORDS}


def score_kb_article(ticket, kb):
    """
    Score a KB article against a ticket using three signals:

    1. Keyword overlap (+3 per match)
       Compares the ticket's keyword list against the KB's keyword list.
       Keywords are curated by the user so they carry the most weight.

    2. Description word overlap (+1 per match)
       Compares significant words in the ticket's description against
       significant words in the KB's description.

    3. Resolution word overlap (+1 per match)
       Compares significant words in the ticket's description against
       significant words in the KB's resolution steps.
       Useful when the resolution mentions the same problem terms.

    The final score is the sum of all three signals.
    A higher score means a closer match.
    """
    ticket_keywords = set(k.lower() for k in ticket.get("keywords", []))
    kb_keywords = set(k.lower() for k in kb.get("keywords", []))
    keyword_score = len(ticket_keywords & kb_keywords) * 3

    ticket_desc_words = significant_words(ticket.get("description") or "")
    desc_score = len(ticket_desc_words & significant_words(kb.get("description") or ""))
    resolution_score = len(ticket_desc_words & significant_words(kb.get("resolution") or ""))

    return keyword_score + desc_score + resolution_score


def rank_kb_articles(ticket, kb_articles):
    """
    Score every KB article against the ticket and return them sorted
    highest score first, filtering out any with a score of zero.
    """
    scored = [
        (kb, score_kb_article(ticket, kb))
        for kb in kb_articles
    ]
    scored = [(kb, score) for kb, score in scored if score > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def generate_kb_html(kb):
    """Write an HTML file for a KB article and return its file:// URL."""
    os.makedirs(KB_OUTPUT_DIR, exist_ok=True)

    keywords_html = "".join(f'<span class="tag">{k}</span>' for k in kb["keywords"])
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


def print_ticket(ticket, ranked_matches):
    print("\n" + "=" * 60)
    print(f"  NEW TICKET #{ticket['id']}")
    print("=" * 60)
    print(f"  Title       : {ticket['title']}")
    print(f"  Submitted by: {ticket['submitted_by']}")
    print(f"  Priority    : {ticket['priority']}")
    print(f"  Description : {ticket['description'] or '—'}")
    print(f"  Keywords    : {', '.join(ticket['keywords']) or '—'}")
    print()

    if ranked_matches:
        # The first result is the highest-scoring article — surface it as the recommendation.
        best_kb, best_score = ranked_matches[0]
        best_url = generate_kb_html(best_kb)
        best_link = terminal_link(f"[{best_kb['id']}]", best_url)
        print(f"  Recommended KB Article: {best_link}  (score: {best_score})")

        # List any additional matches below the recommendation.
        if len(ranked_matches) > 1:
            other_links = []
            for kb, score in ranked_matches[1:]:
                url = generate_kb_html(kb)
                other_links.append(terminal_link(f"[{kb['id']}]", url) + f" ({score})")
            print(f"  Other matches: {',  '.join(other_links)}")
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
            kb_articles = get_all_kb_articles()

            for ticket in all_tickets:
                if ticket["id"] not in seen_ids:
                    ranked_matches = rank_kb_articles(ticket, kb_articles)
                    print_ticket(ticket, ranked_matches)
                    seen_ids.add(ticket["id"])

        except requests.RequestException as e:
            print(f"[Error] Could not reach Supabase: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

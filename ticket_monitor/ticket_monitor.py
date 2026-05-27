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


def get_all_tickets():
    # Fetch every ticket in the table. We diff against seen_ids locally
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

    kw_filter = "{" + ",".join(f'"{k}"' for k in keywords) + "}"

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/kb_articles",
        headers=HEADERS,
        params={"keywords": f"ov.{kw_filter}"},
    )
    response.raise_for_status()
    return response.json()


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
        print(f"  Matching KB Articles ({len(matches)} found):")
        for kb in matches:
            print(f"\n  [{kb['id']}]")
            print(f"    Issue      : {kb['description']}")
            print(f"    Resolution : {kb['resolution']}")
            print(f"    Keywords   : {', '.join(kb['keywords'])}")
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

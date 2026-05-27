# Supabase SQL Setup

Run the following in **Database → SQL Editor → New query** in your Supabase dashboard.

```sql
-- 1. Function to generate random KB IDs between kb100001 and kb199999
CREATE OR REPLACE FUNCTION generate_kb_id()
RETURNS text LANGUAGE plpgsql AS $$
DECLARE
  new_id text;
BEGIN
  LOOP
    new_id := 'kb' || (floor(random() * 99999 + 100001))::int::text;
    EXIT WHEN NOT EXISTS (SELECT 1 FROM kb_articles WHERE id = new_id);
  END LOOP;
  RETURN new_id;
END;
$$;

-- 2. KB articles table
CREATE TABLE kb_articles (
  id          text        PRIMARY KEY DEFAULT generate_kb_id(),
  keywords    text[]      NOT NULL DEFAULT '{}',
  description text        NOT NULL,
  resolution  text        NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- 3. Ticket requests table
CREATE TABLE ticket_requests (
  id           serial      PRIMARY KEY,
  submitted_by text        NOT NULL,
  title        text        NOT NULL,
  description  text,
  keywords     text[]      NOT NULL DEFAULT '{}',
  priority     text        NOT NULL DEFAULT 'Medium',
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- 4. RLS policies (allow anon inserts/reads)
ALTER TABLE ticket_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_articles     ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow anon insert" ON ticket_requests
  FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "allow anon select" ON ticket_requests
  FOR SELECT TO anon USING (true);

CREATE POLICY "allow anon select" ON kb_articles
  FOR SELECT TO anon USING (true);
```

---

## KB Article Seed Data

Run the following to insert KB articles that resolve the existing test tickets.
The `id` column is omitted — the database generates it automatically via `generate_kb_id()`.

```sql
-- KB: Matches ticket #1 (test ticket submitted via web form)
INSERT INTO kb_articles (keywords, description, resolution) VALUES (
  ARRAY['first ticket', 'test', 'react', 'web form', '1'],
  'Test ticket submitted via the ATM web form',
  'This KB article exists to validate keyword matching for test tickets submitted through the ATM web form. No action is required. Confirm the ticket was received in the database and that the Python monitor detected it correctly.'
);

-- KB: Matches ticket #2 (new user cannot access IQ+)
INSERT INTO kb_articles (keywords, description, resolution) VALUES (
  ARRAY['IQ+', 'access', 'first time', 'new user', 'login', 'credentials'],
  'New user is unable to log in to IQ+ for the first time',
  E'1. Confirm the user has been provisioned in the IQ+ system by checking the admin portal.\n2. If the account does not exist, submit a provisioning request with the user''s full name and email.\n3. If the account exists but credentials are wrong, use the admin portal to reset their password and send them a temporary login link.\n4. Instruct the user to log in with the temporary credentials and change their password on first login.\n5. If the issue persists after reset, escalate to the IQ+ platform team.'
);

-- KB: Matches ticket #3 (suspicious activity, remove IQ+ access)
INSERT INTO kb_articles (keywords, description, resolution) VALUES (
  ARRAY['remove access', 'remove', 'hacked', 'login', 'suspicious', 'virus', 'security'],
  'Suspicious login activity detected — user access removal requested',
  E'1. Log in to the IQ+ admin portal immediately.\n2. Locate the user account by ID or email and set the account status to Suspended.\n3. Invalidate all active sessions for that user to force an immediate logout.\n4. Document the suspicious activity with timestamps and IP addresses if available.\n5. Notify the security team and open a security incident ticket.\n6. Do not reinstate access until the security team has completed their review and cleared the account.'
);
```

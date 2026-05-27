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

CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  paper_id TEXT NOT NULL,
  paper_title TEXT NOT NULL DEFAULT '',
  brief_date TEXT NOT NULL DEFAULT '',
  signal TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT 'site',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS feedback_user_created_idx ON feedback(user_id, created_at DESC);
--> statement-breakpoint
CREATE INDEX IF NOT EXISTS feedback_user_paper_idx ON feedback(user_id, paper_id, created_at DESC);

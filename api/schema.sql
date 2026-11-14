CREATE TABLE IF NOT EXISTS scores (
  user_id    INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  username   TEXT,
  best       INTEGER NOT NULL,
  games      INTEGER NOT NULL DEFAULT 1,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scores_best ON scores (best DESC);

CREATE TABLE IF NOT EXISTS scores_bots (
  user_id    INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  username   TEXT,
  best       INTEGER NOT NULL,
  games      INTEGER NOT NULL DEFAULT 1,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scores_bots_best ON scores_bots (best DESC);

"""Durable checkpoints; reserve operations before executing external work."""

import json
import sqlite3
import uuid
from pathlib import Path


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
        self.db.commit()

    def close(self):
        self.db.close()

    def create(self, config):
        state = {"id": uuid.uuid4().hex[:12], "config": config, "status": "running",
                 "requests": 0, "model_calls": 0, "input_tokens": 0, "output_tokens": 0,
                 "reserved_output_tokens": 0, "elapsed": 0, "evidence": [],
                 "messages": [], "pending": [], "events": [], "usage_complete": True}
        self.save(state)
        return state

    def save(self, state):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO runs VALUES (?, ?)",
                            (state["id"], json.dumps(state)))

    def load(self, run_id):
        row = self.db.execute("SELECT state FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown run: " + run_id)
        return json.loads(row[0])

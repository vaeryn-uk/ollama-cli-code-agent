import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any

import ollama

SESSION_DIR = ".ocla"

@dataclass
class Session:
    name: str
    path: str = field(init=False)
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.path = os.path.join(SESSION_DIR, f"{self.name}.json")
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.messages = data.get("messages", [])

    def save(self):
        os.makedirs(SESSION_DIR, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"messages": self.messages}, f, indent=2)

    def add(self, message: Dict[str, Any]):
        if isinstance(message, ollama.Message):
            message = message.__dict__

        self.messages.append(message)

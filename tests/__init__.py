import os
import sys
import types

# Ensure package imports work without installing the project
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

# Provide a dummy 'ollama' module so import succeeds before tests patch it
module = sys.modules.setdefault('ollama', types.ModuleType('ollama'))

class Message:
    class ToolCall:
        pass

module.Message = Message

import json
import os

def load_memory():
    if os.path.exists("memory.json"):
        with open("memory.json", "r") as file:
            data = json.load(file)
            return data["summary"]
    else:
        return "No previous conversation history."

def save_memory(summary):
    with open("memory.json", "w") as file:
        json.dump({"summary": summary}, file)
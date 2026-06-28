from flask import Flask, request, render_template_string, session
from agent import run_agent, end_session, load_memory
from database import load_conversation, save_conversation
import markdown
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>My AI Agent</title>
    <style>
    table {
        border-collapse: collapse;
        width: 100%;
        margin-top: 10px;
    }
    th, td {
        border: 1px solid #ccc;
        padding: 8px;
        text-align: left;
    }
    th {
        background-color: #f0f0f0;
    }
    </style>
</head>
<body style="font-family: sans-serif; max-width: 600px; margin: 50px auto;">
    <h1>Ask my agent something</h1>
    <form method="POST" action="/">
        <input type="text" name="question" style="width: 100%; padding: 10px;" placeholder="Type your question here">
        <button type="submit" style="margin-top: 10px; padding: 10px 20px;">Ask</button>
    </form>
    {% if answer %}
        <h3>Answer:</h3>
        <div>{{ answer | safe }}</div>
    {% endif %}
    
    <hr style="margin-top: 40px;">
    
    <form method="POST" action="/end_session">
        <button type="submit" style="padding: 10px 20px; background: #ddd;">End session & save memory</button>
    </form>
    {% if memory_message %}
        <p>{{ memory_message }}</p>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    
    session_id = session["session_id"]
    
    messages = load_conversation(session_id)
    if messages is None:
        previous_summary = load_memory()
        messages = [
            {"role": "user", "content": "Here is a summary of our previous conversation: " + previous_summary + ". Please keep this in mind as we continue."},
            {"role": "assistant", "content": "Understood, I'll keep that context in mind."}
        ]
    
    answer = None
    if request.method == "POST":
        question = request.form["question"]
        raw_answer, messages = run_agent(question, messages)
        answer = markdown.markdown(raw_answer, extensions=["tables"])
        save_conversation(session_id, messages)
    
    return render_template_string(HTML_PAGE, answer=answer)

@app.route("/end_session", methods=["POST"])
def end_session_route():
    session_id = session.get("session_id")
    messages = load_conversation(session_id)
    memory_message = end_session(messages if messages else [])
    return render_template_string(HTML_PAGE, answer=None, memory_message=memory_message)

if __name__ == "__main__":
    app.run(debug=False)
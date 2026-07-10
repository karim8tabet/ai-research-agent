from flask import Flask, request, render_template_string, session
from agent import run_agent, end_session, load_memory
from database import load_conversation, save_conversation
import markdown
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent</title>
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f1117;
            color: #e2e8f0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 48px 16px 80px;
        }

        .container {
            width: 100%;
            max-width: 720px;
        }

        /* Header */
        header {
            text-align: center;
            margin-bottom: 40px;
        }
        .logo {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 52px;
            height: 52px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            border-radius: 14px;
            margin-bottom: 16px;
        }
        .logo svg { width: 28px; height: 28px; fill: #fff; }
        header h1 {
            font-size: 1.75rem;
            font-weight: 700;
            color: #f8fafc;
            letter-spacing: -0.02em;
        }
        header p {
            margin-top: 6px;
            font-size: 0.9rem;
            color: #64748b;
        }

        /* Ask card */
        .card {
            background: #1e2130;
            border: 1px solid #2d3148;
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 20px;
        }

        .input-row {
            display: flex;
            gap: 10px;
        }
        .input-row input[type="text"] {
            flex: 1;
            background: #0f1117;
            border: 1px solid #2d3148;
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 0.95rem;
            color: #e2e8f0;
            outline: none;
            transition: border-color 0.2s;
        }
        .input-row input[type="text"]::placeholder { color: #475569; }
        .input-row input[type="text"]:focus { border-color: #6366f1; }

        .btn-primary {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: #fff;
            border: none;
            border-radius: 10px;
            padding: 12px 22px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: opacity 0.2s, transform 0.1s;
        }
        .btn-primary:hover { opacity: 0.9; }
        .btn-primary:active { transform: scale(0.98); }

        /* Answer */
        .answer-card {
            background: #1e2130;
            border: 1px solid #2d3148;
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 20px;
        }
        .answer-label {
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6366f1;
            margin-bottom: 14px;
        }
        .answer-body {
            font-size: 0.95rem;
            line-height: 1.7;
            color: #cbd5e1;
        }
        .answer-body p { margin-bottom: 12px; }
        .answer-body p:last-child { margin-bottom: 0; }
        .answer-body h1, .answer-body h2, .answer-body h3 {
            color: #f1f5f9;
            margin: 18px 0 8px;
            font-weight: 600;
        }
        .answer-body ul, .answer-body ol {
            margin: 8px 0 12px 20px;
        }
        .answer-body li { margin-bottom: 4px; }
        .answer-body code {
            background: #0f1117;
            border: 1px solid #2d3148;
            border-radius: 5px;
            padding: 2px 6px;
            font-size: 0.85em;
            color: #a5b4fc;
            font-family: 'SF Mono', 'Fira Code', monospace;
        }
        .answer-body pre {
            background: #0f1117;
            border: 1px solid #2d3148;
            border-radius: 10px;
            padding: 16px;
            overflow-x: auto;
            margin: 12px 0;
        }
        .answer-body pre code {
            background: none;
            border: none;
            padding: 0;
            font-size: 0.88em;
        }
        .answer-body table {
            border-collapse: collapse;
            width: 100%;
            margin: 14px 0;
            font-size: 0.9em;
        }
        .answer-body th, .answer-body td {
            border: 1px solid #2d3148;
            padding: 10px 14px;
            text-align: left;
        }
        .answer-body th {
            background: #161827;
            color: #a5b4fc;
            font-weight: 600;
        }
        .answer-body tr:nth-child(even) td { background: #191c2b; }

        /* Footer actions */
        .footer-row {
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
        }
        .btn-secondary {
            background: transparent;
            color: #94a3b8;
            border: 1px solid #2d3148;
            border-radius: 10px;
            padding: 10px 18px;
            font-size: 0.88rem;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s, color 0.2s, border-color 0.2s;
        }
        .btn-secondary:hover {
            background: #2d3148;
            color: #e2e8f0;
            border-color: #3d4160;
        }

        .status-msg {
            font-size: 0.88rem;
            color: #6366f1;
            background: #1e2130;
            border: 1px solid #2d3148;
            border-radius: 10px;
            padding: 10px 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm1 17.93V18a1 1 0 0 0-2 0v1.93A8 8 0 0 1 4.07 13H6a1 1 0 0 0 0-2H4.07A8 8 0 0 1 11 4.07V6a1 1 0 0 0 2 0V4.07A8 8 0 0 1 19.93 11H18a1 1 0 0 0 0 2h1.93A8 8 0 0 1 13 19.93z"/>
                </svg>
            </div>
            <h1>AI Research Agent</h1>
            <p>Ask anything — your agent remembers context across sessions.</p>
        </header>

        <div class="card">
            <form method="POST" action="/">
                <div class="input-row">
                    <input type="text" name="question" placeholder="Ask your agent a question..." autofocus>
                    <button type="submit" class="btn-primary">Ask</button>
                </div>
            </form>
        </div>

        {% if answer %}
        <div class="answer-card">
            <div class="answer-label">Response</div>
            <div class="answer-body">{{ answer | safe }}</div>
        </div>
        {% endif %}

        <div class="footer-row">
            <form method="POST" action="/end_session">
                <button type="submit" class="btn-secondary">End session &amp; save memory</button>
            </form>
            {% if memory_message %}
            <span class="status-msg">{{ memory_message }}</span>
            {% endif %}
        </div>
    </div>
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
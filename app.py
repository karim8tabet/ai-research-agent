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
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Agent</title>
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
            background: #fff;
            color: #111;
            height: 100vh;
            display: grid;
            grid-template-rows: auto 1fr auto;
            max-width: 680px;
            margin: 0 auto;
        }

        /* ── Header ── */
        header {
            padding: 28px 32px 20px;
            border-bottom: 1px solid #ebebeb;
        }
        header h1 {
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #999;
        }

        /* ── Thread ── */
        #thread {
            overflow-y: auto;
            padding: 0 32px;
            display: flex;
            flex-direction: column;
        }
        #thread::-webkit-scrollbar { width: 0; }

        .turn {
            padding: 28px 0;
            border-bottom: 1px solid #f2f2f2;
        }
        .turn:last-child { border-bottom: none; }

        .turn-label {
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .turn.user .turn-label { color: #bbb; }
        .turn.agent .turn-label { color: #111; }

        .turn-body {
            font-size: 0.97rem;
            line-height: 1.72;
            color: #222;
        }
        .turn.user .turn-body {
            color: #666;
            font-size: 0.93rem;
        }

        .turn-body p { margin-bottom: 10px; }
        .turn-body p:last-child { margin-bottom: 0; }
        .turn-body h1, .turn-body h2, .turn-body h3 {
            font-weight: 600;
            margin: 16px 0 6px;
            letter-spacing: -0.01em;
        }
        .turn-body ul, .turn-body ol { margin: 8px 0 10px 18px; }
        .turn-body li { margin-bottom: 4px; }
        .turn-body code {
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 0.83em;
            background: #f5f5f5;
            border-radius: 4px;
            padding: 2px 6px;
        }
        .turn-body pre {
            background: #f5f5f5;
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            margin: 12px 0;
        }
        .turn-body pre code { background: none; padding: 0; font-size: 0.88em; }
        .turn-body table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 0.9em; }
        .turn-body th, .turn-body td { border: 1px solid #e8e8e8; padding: 8px 12px; text-align: left; }
        .turn-body th { background: #fafafa; font-weight: 600; }

        /* Thinking dots */
        .thinking {
            display: none;
            padding: 28px 0;
        }
        .thinking.visible { display: block; }
        .thinking-label {
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #111;
            margin-bottom: 12px;
        }
        .dots { display: flex; gap: 5px; }
        .dots span {
            width: 6px; height: 6px;
            background: #ccc;
            border-radius: 50%;
            animation: pulse 1.4s infinite;
        }
        .dots span:nth-child(2) { animation-delay: 0.2s; }
        .dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes pulse {
            0%, 80%, 100% { opacity: 0.3; transform: scale(0.85); }
            40% { opacity: 1; transform: scale(1); }
        }

        /* ── Input ── */
        footer {
            border-top: 1px solid #ebebeb;
            padding: 20px 32px;
        }
        .compose {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .compose input[type="text"] {
            flex: 1;
            border: none;
            outline: none;
            font-size: 0.97rem;
            font-family: inherit;
            color: #111;
            background: transparent;
            padding: 4px 0;
        }
        .compose input::placeholder { color: #ccc; }
        .compose button[type="submit"] {
            background: #111;
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 9px 18px;
            font-size: 0.82rem;
            font-weight: 600;
            font-family: inherit;
            letter-spacing: 0.02em;
            cursor: pointer;
            transition: background 0.15s;
            white-space: nowrap;
        }
        .compose button[type="submit"]:hover { background: #333; }

        .footer-meta {
            margin-top: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .btn-end {
            background: none;
            border: none;
            font-size: 0.75rem;
            color: #ccc;
            font-family: inherit;
            cursor: pointer;
            padding: 0;
            transition: color 0.15s;
        }
        .btn-end:hover { color: #999; }
        .status-msg { font-size: 0.75rem; color: #999; }
    </style>
</head>
<body>
    <div id="server-answer" style="display:none">{{ answer | safe if answer else '' }}</div>

    <header>
        <h1>Research Agent</h1>
    </header>

    <div id="thread">
        <div class="thinking" id="thinking">
            <div class="thinking-label">Agent</div>
            <div class="dots"><span></span><span></span><span></span></div>
        </div>
    </div>

    <footer>
        <form method="POST" action="/" id="ask-form">
            <div class="compose">
                <input type="text" name="question" id="question-input" placeholder="Ask anything…" autocomplete="off" autofocus>
                <button type="submit">Send</button>
            </div>
        </form>
        <div class="footer-meta">
            <form method="POST" action="/end_session" style="display:contents">
                <button type="submit" class="btn-end">End session &amp; save memory</button>
            </form>
            {% if memory_message %}
            <span class="status-msg">{{ memory_message }}</span>
            {% endif %}
        </div>
    </footer>

    <script>
    (function () {
        const STORAGE_KEY = 'agent_thread_v2';
        const thread = document.getElementById('thread');
        const thinking = document.getElementById('thinking');
        const form = document.getElementById('ask-form');
        const input = document.getElementById('question-input');
        const serverAnswer = document.getElementById('server-answer').innerHTML.trim();

        function load() {
            try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
            catch { return []; }
        }
        function save(h) { localStorage.setItem(STORAGE_KEY, JSON.stringify(h)); }

        function addTurn(role, html, prepend) {
            const div = document.createElement('div');
            div.className = 'turn ' + role;
            const label = role === 'user' ? 'You' : 'Agent';
            div.innerHTML = '<div class="turn-label">' + label + '</div><div class="turn-body">' + html + '</div>';
            if (prepend) {
                thread.insertBefore(div, thread.firstChild);
            } else {
                thread.insertBefore(div, thinking);
            }
        }

        function scrollBottom() { thread.scrollTop = thread.scrollHeight; }

        let history = load();
        history.forEach(m => addTurn(m.role, m.html, false));
        scrollBottom();

        if (serverAnswer) {
            const pending = localStorage.getItem('agent_pending');
            localStorage.removeItem('agent_pending');
            if (pending) {
                const safe = pending.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                history.push({ role: 'user', html: safe });
                addTurn('user', safe);
            }
            history.push({ role: 'agent', html: serverAnswer });
            addTurn('agent', serverAnswer);
            save(history);
            scrollBottom();
        }

        form.addEventListener('submit', function () {
            const q = input.value.trim();
            if (!q) return;
            localStorage.setItem('agent_pending', q);
            // Show user bubble immediately
            const safe = q.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            addTurn('user', safe);
            // Show thinking indicator
            thinking.classList.add('visible');
            scrollBottom();
            // Disable input so it's clear something is happening
            input.disabled = true;
            form.querySelector('button').disabled = true;
        });
    })();
    </script>
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
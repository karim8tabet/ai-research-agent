from flask import Flask, request, render_template_string, session, jsonify, send_from_directory
from dotenv import load_dotenv
from agent import run_agent, end_session, load_memory
from database import load_conversation, save_conversation
from document_store import add_document, list_documents, delete_document, delete_all_documents, shared_document_names
import markdown
import nh3
import os
import uuid
 
load_dotenv()
 
# The React front end (frontend/) is built into frontend/dist.
# Flask serves its asset files directly, so one server runs the whole app.
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
 
app = Flask(__name__, static_folder=os.path.join(FRONTEND_DIST, "assets"), static_url_path="/assets")
 
secret = os.environ.get("FLASK_SECRET_KEY")
if not secret:
    raise RuntimeError("FLASK_SECRET_KEY is not set. Add it to your .env file before starting the app.")
app.secret_key = secret
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # uploads are limited to 10 MB
 
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
            input.readOnly = true;
            form.querySelector('button').disabled = true;
        });
    })();
    </script>
</body>
</html>
"""
 

MEMORY_PRIMING_MESSAGES = 2
MAX_QUESTION_LENGTH = 2000
 
TOOL_LABELS = {
    "search_web": "Searched the web",
    "read_webpage": "Read a webpage",
    "search_documents": "Searched documents",
}
 
 
def get_session_messages():
    """Return this browser session's ID and its conversation so far."""
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
    return session_id, messages
 
 
def build_system_prompt(owner_id):
    """Tell the agent which documents it can search, so it knows when to use search_documents."""
    shared = ", ".join(shared_document_names()) or "none"
    uploaded = ", ".join(d["filename"] for d in list_documents(owner_id)) or "none"
    return ("Your document library contains these shared documents: " + shared + ". "
            "The user has uploaded: " + uploaded + ". "
            "Use search_documents for questions about any of these documents.")


def render_answer(text):
    """Turn the agent's Markdown into HTML, then strip anything dangerous with nh3."""
    html = markdown.markdown(text, extensions=["tables"])
    return nh3.clean(html)
 
 
def field(block, name):
    """Read a field from a content block.
    Fresh blocks are Anthropic objects; blocks loaded from SQLite are plain dicts."""
    if isinstance(block, dict):
        return block.get(name)
    return getattr(block, name, None)
 
 
def describe_tool_call(block):
    """A short, human-readable description of one tool call, for the interface."""
    name = field(block, "name")
    tool_input = field(block, "input") or {}
    detail = tool_input.get("url") if name == "read_webpage" else tool_input.get("query")
    return {"tool": name, "label": TOOL_LABELS.get(name, name), "detail": detail or ""}
 
 
def tools_used(messages):
    """List the tool calls made in a list of messages, in order."""
    calls = []
    for message in messages:
        if message.get("role") != "assistant" or not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if field(block, "type") == "tool_use":
                calls.append(describe_tool_call(block))
    return calls
 
 
def build_history(messages):
    """Rebuild the visible chat (questions, answers and the tools behind each answer)
    from the full conversation the agent sees."""
    turns = []
    pending_tools = []
    for message in messages[MEMORY_PRIMING_MESSAGES:]:
        content = message.get("content")
        if message.get("role") == "user":
            if isinstance(content, str):  # a real question; lists are tool results
                turns.append({"role": "user", "text": content})
            continue
 
        blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
        tool_blocks = [b for b in blocks if field(b, "type") == "tool_use"]
        if tool_blocks:
            pending_tools.extend(describe_tool_call(b) for b in tool_blocks)
            continue
 
        text = "".join(field(b, "text") or "" for b in blocks if field(b, "type") == "text")
        turns.append({"role": "agent", "html": render_answer(text), "tools": pending_tools})
        pending_tools = []
    return turns

@app.route("/api/history", methods=["GET"])
def api_history():
    _, messages = get_session_messages()
    return jsonify({"turns": build_history(messages)})
 
 
@app.route("/api/chat", methods=["POST"])
def api_chat():
    if not request.is_json:
        return jsonify({"error": "Requests must be sent as JSON."}), 415
 
    question = (request.get_json(silent=True) or {}).get("question", "")
    if not isinstance(question, str) or not question.strip():
        return jsonify({"error": "Please type a question."}), 400
    question = question.strip()
    if len(question) > MAX_QUESTION_LENGTH:
        return jsonify({"error": "Questions are limited to " + str(MAX_QUESTION_LENGTH) + " characters."}), 400
 
    session_id, messages = get_session_messages()
    start = len(messages)
    raw_answer, messages = run_agent(question, messages, session_id, build_system_prompt(session_id))
    save_conversation(session_id, messages)
 
    return jsonify({
        "answer_html": render_answer(raw_answer),
        "tools": tools_used(messages[start:]),
    })
 
 
@app.route("/api/end_session", methods=["POST"])
def api_end_session():
    if not request.is_json:
        return jsonify({"error": "Requests must be sent as JSON."}), 415
    session_id, messages = get_session_messages()
    message = end_session(messages)
    delete_all_documents(session_id)  # uploads only last until the session ends
    return jsonify({"message": message})


@app.route("/api/documents", methods=["GET"])
def api_list_documents():
    session_id, _ = get_session_messages()
    return jsonify({"shared": shared_document_names(), "documents": list_documents(session_id)})


@app.route("/api/documents", methods=["POST"])
def api_upload_document():
    # File uploads can't be required to be JSON, so a custom header plays the same role:
    # another website can't add this header to a request without permission this server never grants.
    if request.headers.get("X-Requested-With") != "fetch":
        return jsonify({"error": "Missing request header."}), 400
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Please choose a file."}), 400

    session_id, _ = get_session_messages()
    try:
        document = add_document(session_id, uploaded.filename, uploaded.read())
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"document": document}), 201


@app.route("/api/documents/<doc_id>", methods=["DELETE"])
def api_delete_document(doc_id):
    session_id, _ = get_session_messages()
    delete_document(session_id, doc_id)
    return jsonify({"deleted": doc_id})


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"error": "Files are limited to 10 MB."}), 413
 
 
 
@app.route("/", methods=["GET", "POST"])
def home():
    index_file = os.path.join(FRONTEND_DIST, "index.html")
    if request.method == "GET" and os.path.exists(index_file):
        return send_from_directory(FRONTEND_DIST, "index.html")
 
    session_id, messages = get_session_messages()
    
    answer = None
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        if not question:
            return render_template_string(HTML_PAGE, answer=None)
        raw_answer, messages = run_agent(question, messages, session_id, build_system_prompt(session_id))
        answer = render_answer(raw_answer)
        save_conversation(session_id, messages)
    
    return render_template_string(HTML_PAGE, answer=answer)
 
@app.route("/end_session", methods=["POST"])
def end_session_route():
    session_id = session.get("session_id")
    messages = load_conversation(session_id)
    memory_message = end_session(messages if messages else [])
    if session_id:
        delete_all_documents(session_id)
    return render_template_string(HTML_PAGE, answer=None, memory_message=memory_message)
 
if __name__ == "__main__":
    app.run(debug=False)
    

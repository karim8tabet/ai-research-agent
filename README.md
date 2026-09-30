# AI Research Agent

A web-based AI assistant that can handle multi-step research tasks on its own. It can **search the web**, **read full webpages**, and **pull facts out of private documents**, instead of just answering from memory like a typical chatbot.

Built with the **Claude API**, **Flask**, and **ChromaDB**.

---

## What This Actually Does

Most chatbots just answer using whatever they learned during training, which means they can be outdated or wrong about anything specific. This project works differently. It's an **agent**, meaning it can decide on its own to take actions before answering a question, rather than just guessing based on what it already knows.

When you ask it a question, it can:

- **Search the web** for current information
- **Open and read a specific webpage** in full, not just a search snippet
- **Search a private knowledge base** of documents it has been given (in this project, Apple's and Microsoft's 10-K annual filings)

It decides which of these tools to use, in what order, and can chain them together. For example, it might search the web, pick a promising link from the results, and then read that full page before answering.

It also remembers previous sessions, in a lightweight way that doesn't get more expensive to run the more it's used. Long-term memory is currently designed for a single user running the app on their own machine.

---

## Why I Built It This Way

This wasn't just calling the Claude API and printing the answer. A number of real engineering decisions went into making it reliable, safe, and affordable to run.

- **The agent's reasoning is bounded.** It's capped at a fixed number of reasoning steps per question, so it can't spiral into an expensive, endless loop.
- **It fails gracefully instead of crashing.** If a tool breaks, like a website being down or a search API timing out, the app doesn't fall over. It tells the agent that step failed and lets it adjust.
- **Memory doesn't get more expensive over time.** Instead of re-reading the entire chat history every time, old conversations get compressed into short summaries.
- **Security wasn't an afterthought.** I ran an AI-assisted security audit on my own code and fixed three real vulnerabilities before considering this done.
- **I tested it like an adversary.** I deliberately tried to get it to make things up, and documented where it held up and where its reasoning has limits.

---

## Project Structure

| File | Purpose |
|---|---|
| `agent.py` | The core logic. Defines the tools, runs the reasoning loop, and ends sessions. |
| `app.py` | The Flask web server. Handles page routes and session management. |
| `memory.py` | Long-term memory that persists across conversations. |
| `database.py` | Short-term memory within a single conversation, backed by SQLite. |
| `build_knowledge_base.py` | Reads documents and prepares them for search. |

---

## The Three Tools

### `search_web(query)`

Searches the web through the **Serper API** and returns the top 5 results. The agent uses this when a question needs current or general information it wasn't given specific documents for.

### `read_webpage(url)`

Takes a specific URL, often one the agent just found through search, and opens it, pulling out the readable paragraph text using **BeautifulSoup** to strip out ads, navigation menus, and other clutter. The extracted text is capped at **3,000 characters** so one huge page doesn't overwhelm the agent.

**SSRF protection.** Since the agent itself decides which URLs to fetch, without safeguards it could be tricked, say through a malicious search result, into fetching something it shouldn't, like an internal server or a cloud provider's internal address that can leak credentials. This is called server-side request forgery (SSRF). To prevent it:

- Only `http` and `https` addresses are allowed.
- Before fetching, the tool looks up the real IP address behind the hostname and blocks anything pointing to a private network, the machine's own local address, or other reserved ranges, so names like `localhost` can't slip through.
- Redirects are handled manually, with each hop checked the same way and a limit of three, so a harmless-looking public page can't bounce the request to an internal address.

### `search_documents(query)`

This is the **RAG** tool, short for retrieval-augmented generation. Instead of the AI trying to recall facts from memory, which risks it making things up, this tool searches a database of the actual documents and hands the AI the relevant paragraphs before it answers. It's the difference between asking someone to recall a report from memory versus handing them the report already opened to the right page.

Every result is **labeled with the file it came from**, so the agent always knows which company a passage belongs to. It was tested using Apple's FY2025 10-K and Microsoft's 10-K, specifically to check that it could tell the two documents apart and pull the right facts from the right company.

---

## How the Reasoning Loop Works

Under the hood, the agent runs a loop: it reasons about the question, decides whether it needs a tool, uses one if so, looks at the result, and reasons again, repeating until it has enough information to answer.

Two safeguards keep this loop reliable:

- **A hard cap of 5 loops** prevents the agent from endlessly searching and re-searching, wasting time and money. The trade-off is that on very broad questions it can occasionally hit this limit before it feels done (see Known Limitations).
- **Error handling at two levels.** Every tool call is wrapped in its own safety net, so if one tool fails, the agent is told that step didn't work instead of the whole conversation breaking. The Claude API call itself is also protected, so a rate limit or network blip shows the user a friendly fallback message instead of a crash.

---

## Memory System

Memory is split into two separate systems, because remembering the current conversation and remembering someone across visits are different problems with different costs.

### Long-Term Memory

At the end of each session, the AI writes a short **2–3 sentence summary** of what was discussed and saves it. The next session loads that summary, not the full transcript. Reloading the entire chat history every time would make costs and load times keep growing; compressing to a summary keeps things just as fast and cheap on the hundredth conversation as the first.

It's stored in a single `memory.json` file, so it's shared by everyone using the same running instance of the app, which makes it best suited to personal, single-user use.

### Per-Session Memory

Each browser session gets its own private conversation thread, stored in a local **SQLite** database instead of only in the server's temporary memory.

This came from a real bug: the development server's auto-reload feature was silently wiping out the ongoing conversation between messages, because it was only held in memory that got cleared on every code change. Moving the conversation into a database file fixed this, and as a bonus, conversations now survive a full server restart too.

---

## The Document Search Pipeline

This is how documents get turned into something the agent can search:

1. **Chunking.** Documents are broken into chunks of roughly **500 words** each: small enough for focused search results, large enough to keep useful context together.
2. **Labeling.** Each chunk is stored with the name of the file it came from.
3. **Embedding.** Each chunk is converted into a numerical representation, called an **embedding**, using ChromaDB's built-in local model. This runs on your own machine, so there's no extra API cost to prepare documents.
4. **Rebuilding.** Running `build_knowledge_base.py` wipes and rebuilds the entire collection from scratch each time. This keeps things simple and always accurate, at the cost of re-running it whenever a document is added.

---

## Testing and Results

Rather than just testing reasonable questions, I specifically tried to trick the agent into making things up, across four scenarios:

1. A fabricated policy claim
2. A fact that belongs to a different document than the one being searched
3. An out-of-scope factual question
4. A current events question

**In all four cases, the agent either correctly fell back to a web search or explicitly said the information wasn't available. It never invented a false answer.**

### Known Limitations

**It doesn't know when a partial answer is good enough.** For very broad, multi-part questions, like summarizing an entire product launch event, it can hit its 5-step limit before it's satisfied. It's tuned to prioritize thoroughness over speed, and doesn't yet recognize when it has enough for a solid partial answer.

**It struggles with lopsided comparisons.** When two documents cover a topic in similar depth, like standardized financial figures, it does well. But when one covers a topic heavily and the other barely mentions it, for example supply chain risk in Apple's hardware-focused filing versus Microsoft's cloud-and-software-focused one, the agent doesn't yet treat the absence itself as a legitimate answer, and can keep searching for information that isn't there.

---

## Security

I ran an AI-assisted audit of my own code and found and fixed three real vulnerabilities.

1. **Unsafe secret key fallback.** The original code could run without the app's secret signing key properly set, which would allow session cookies to be forged. The app now **refuses to start** if the key isn't configured. In security, failing loudly is safer than failing quietly.
2. **Server-side request forgery (SSRF).** Protection on the webpage reading tool, described above under `read_webpage`.
3. **Cross-site scripting (XSS).** Because the agent reads arbitrary webpages, a malicious page could try to get it to repeat raw HTML or script tags in its answer, which the browser would then run. Every answer is now passed through the **nh3** sanitizer after being converted from Markdown, keeping normal formatting like bold text, lists, and tables while stripping scripts and other dangerous HTML.

---

## Tech Stack

| Technology | Role |
|---|---|
| **Claude API** (Anthropic) | Reasoning and tool-use logic |
| **Flask** | Web server and interface |
| **SQLite** | Per-session conversation storage |
| **ChromaDB** | Vector database for document search |
| **BeautifulSoup** | Webpage text extraction |
| **Serper API** | Web search |
| **nh3** | HTML sanitization |

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/karim8tabet/ai-research-agent.git
cd ai-research-agent
```

### 2. Create and activate a virtual environment

This keeps the project's Python packages separate from everything else on your machine.

```bash
python -m venv venv
source venv/bin/activate
```

On Windows, activate it with `venv\Scripts\activate` instead.

### 3. Install the required packages

```bash
pip install -r requirements.txt
```

### 4. Set up your environment variables

Copy the template:

```bash
cp .env.example .env
```

Then open the new `.env` file and add your keys:

```
ANTHROPIC_API_KEY=your_key_here
SERPER_API_KEY=your_key_here
FLASK_SECRET_KEY=your_own_random_string
```

- The **Anthropic key** comes from the Anthropic console.
- The **Serper key** comes from [serper.dev](https://serper.dev).
- The **Flask secret key** can be any random string you make up. It just needs to exist and stay the same between runs.

### 5. Build the knowledge base

Run this before starting the app for the first time. It reads whatever documents are in the `documents` folder and prepares them for search.

```bash
python build_knowledge_base.py
```

### 6. Run the app

```bash
python app.py
```

Then open a browser and go to **http://localhost:5000**.

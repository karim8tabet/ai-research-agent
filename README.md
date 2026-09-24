**AI Research Agent**

A web based AI assistant that can handle multi step research tasks on its own. It can search the web, read full webpages, and pull facts out of private documents, instead of just answering from memory like a typical chatbot.

Built with the Claude API, Flask, and ChromaDB.

What this actually does

Most chatbots just answer using whatever they learned during training, which means they can be outdated or wrong about anything specific. This project works differently. It's an agent, meaning it can decide on its own to take actions before answering a question, rather than just guessing based on what it already knows.

When you ask it a question, it can do any of the following:

Search the web for current information
Open and read a specific webpage in full, not just a search snippet
Search a private knowledge base of documents it has been given (in this project, Apple's and Microsoft's 10-K annual filings)

It decides which of these tools to use, in what order, and can chain them together. For example, it might search the web, pick a promising link from the results, and then read that full page before answering.

It also remembers you across visits, in a lightweight way that does not get more expensive to run the more it is used.

Why I built it this way

This wasn't just calling the Claude API and printing the answer. A number of real engineering decisions went into making it reliable, safe, and affordable to run.

The agent's reasoning is bounded. It does not loop forever trying to find the perfect answer. It is capped at a fixed number of reasoning steps per question, so it can't spiral into an expensive, endless loop.

It fails gracefully instead of crashing. If a tool breaks, like a website being down or a search API timing out, the app doesn't fall over. It tells the agent that step failed and lets it adjust from there.

Memory is designed so it doesn't get more expensive to run the longer you use it. Instead of re-reading the entire chat history every time, which would get slower and pricier the more you talk to it, old conversations get compressed into short summaries.

Security wasn't an afterthought. I ran an AI assisted security audit on my own code and fixed two real vulnerabilities before considering this done.

I also tested it like an adversary, not just a normal user. I deliberately tried to get it to make things up, and documented where it held up and where its reasoning actually has limits.

Project structure

agent.py is the core logic. It defines the tools, runs the reasoning loop, and ends sessions.

app.py is the Flask web server. It handles page routes and session management.

memory.py handles long term memory that persists across different conversations.

database.py handles short term memory within a single conversation, backed by SQLite.

build_knowledge_base.py is a one time script that reads documents and prepares them for search.

The three tools
search_web(query)

Searches the web through the Serper API and returns the top 5 results. This is what the agent uses when a question needs current or general information it wasn't given specific documents for.

read_webpage(url)

Takes a specific URL, often one the agent just found through search, and actually opens it, pulling out the readable paragraph text using BeautifulSoup to strip out ads, navigation menus, and other clutter. The extracted text is capped at 3,000 characters so it doesn't overwhelm the agent with one huge page.

This tool has protection against something called SSRF, or server side request forgery. In plain terms, since the agent itself decides what URLs to fetch, without safeguards it could theoretically be tricked, say through a malicious search result, into fetching something it shouldn't, like an internal server or a cloud provider's internal address that can leak credentials. To prevent this, the tool only allows normal web addresses using http or https, and blocks any address that points to a private network or the machine's own local address.

search_documents(query)

This is the RAG tool, short for retrieval augmented generation. In plain terms, instead of the AI trying to recall facts from a document from memory, which risks it making things up, this tool searches a database of the actual uploaded documents and hands the AI the relevant paragraphs to read before answering. It's the difference between asking someone to recall a report from memory versus handing them the report already opened to the right page.

It was tested using Apple's FY2025 10-K and Microsoft's 10-K, specifically to check that it could tell the two documents apart and pull the right facts from the right company.

How the agent's reasoning loop works

Under the hood, the agent runs a loop. It reasons about the question, decides whether it needs a tool, uses one if so, looks at the result, and reasons again, repeating until it has enough information to answer.

Two safeguards keep this loop reliable. There is a hard cap of 5 loops, which prevents the agent from endlessly searching and re-searching on a single question and wasting time and money. The trade off is that on very broad questions, it can occasionally hit this limit before it feels fully done, which is covered more under known limitations below.

There is also error handling at two levels. Every individual tool call is wrapped in its own safety net, so if one tool fails, the agent is told that step didn't work instead of the whole conversation breaking. The call to the Claude API itself is also protected, so if the AI service has an issue like a rate limit or a network blip, the user sees a friendly fallback message instead of a crash.

Memory system

I split memory into two separate systems, because remembering the current conversation and remembering someone across visits are different problems with different costs.

Long term memory works across sessions. At the end of each session, the AI writes a short two to three sentence summary of what was discussed and saves it. The next time a session starts, that short summary is loaded in, not the full transcript. The reason for this is that reloading the entire chat history every time would make costs and load times keep growing the more the app gets used. Compressing to a short summary keeps things just as fast and cheap on the hundredth conversation as the first.

Per session memory handles a single conversation. Each browser session gets its own private conversation thread, stored in a small local SQLite database instead of being held only in the server's temporary memory. This matters because I ran into a real bug early on where the app's auto reload feature used during development was silently wiping out the ongoing conversation between messages, since it was only being stored in memory that got cleared on every code change. Moving the conversation into an actual database file fixed this, and as a bonus, conversations now also survive a full server restart, not just a reload.

The document search pipeline

This is how documents get turned into something the agent can search.

Documents are broken into chunks of roughly 500 words each. Small enough for accurate, focused search results, large enough to keep useful context together.

Each chunk is converted into a numerical representation, called an embedding, using ChromaDB's built in local model. This runs on your own machine, so there is no extra API cost just to prepare documents for search.

Running build_knowledge_base.py wipes and rebuilds the entire searchable collection from scratch each time. This keeps things simple and always accurate, at the cost of having to manually re-run it any time a new document is added.

Testing and results

Rather than just testing whether it works on a reasonable question, I specifically tried to trick the agent into making things up, across four scenarios: a fabricated policy claim, a question about a fact that belongs to a different document than the one being searched, an out of scope factual question, and a current events question.

In all four cases, the agent either correctly fell back to a web search or explicitly said the information wasn't available. It never invented a false answer.

There are also a couple of real limitations I found through testing, worth being upfront about.

The agent doesn't have a good sense of when a partial answer is good enough. For very broad, multi part questions, like summarizing an entire product launch event, it can hit its 5 step limit before it's fully satisfied with its answer. It's currently tuned to prioritize thoroughness over speed, and doesn't yet know how to recognize when it has enough to give a solid partial answer and stop there.

It also struggles with lopsided comparisons between documents. When comparing two documents on a topic both cover in similar depth, like standardized financial figures, it does well. But when one document covers a topic heavily and the other barely mentions it, for example supply chain risk being a major topic in Apple's hardware focused filing but barely discussed in Microsoft's cloud and software focused filing, the agent doesn't yet recognize that the absence itself is a legitimate answer, and can end up searching for information that simply isn't there.

Security

I ran an AI assisted audit of my own code and found and fixed two real vulnerabilities.

The first was an unsafe fallback for the app's secret signing key. The original code used a method that would silently substitute a blank value if the secret key environment variable wasn't set, which sounds harmless but actually means the app's session cookies could be forged, since anyone could guess an empty string as the key. The fix makes the app refuse to start at all if this key isn't properly configured, rather than silently running in an insecure state. In security, failing loudly is safer than failing quietly.

The second was SSRF protection on the webpage reading tool, described above under read_webpage.

Tech stack

Claude API from Anthropic handles the reasoning and tool use logic. Flask runs the web server and interface. SQLite stores per session conversations. ChromaDB is the vector database used for document search. BeautifulSoup handles webpage text extraction. Serper API provides web search.






Setup

Clone the repository, then move into the project folder.

git clone https://github.com/karim8tabet/ai-research-agent.git
cd ai-research-agent

Create a virtual environment and activate it, so the project's Python packages stay separate from everything else on your machine.

python -m venv venv
source venv/bin/activate

On Windows, activate it with venv\Scripts\activate instead.

Install the required packages.

pip install -r requirements.txt

Copy the environment variable template and fill it in with your own values.

cp .env.example .env

Then open the new .env file and add your actual keys.

ANTHROPIC_API_KEY=your_key_here
SERPER_API_KEY=your_key_here
FLASK_SECRET_KEY=your_own_random_string

The Anthropic key comes from the Anthropic console, the Serper key comes from serper.dev, and the Flask secret key can be any random string you make up yourself, it just needs to exist and stay the same between runs.

Build the knowledge base before running the app for the first time. This reads whatever documents are in the documents folder and prepares them for search.

python build_knowledge_base.py

Run the app.

python app.py

Once it's running, open a browser and go to http://localhost:5000 to start using it.

import anthropic
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
from memory import load_memory, save_memory
import chromadb

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

previous_summary = load_memory()

messages = [
    {"role": "user", "content": "Here is a summary of our previous conversation: " + previous_summary + ". Please keep this in mind as we continue."},
    {"role": "assistant", "content": "Understood, I'll keep that context in mind."}
]

def search_web(query):
    try:
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": os.environ.get("SERPER_API_KEY"),
            "Content-Type": "application/json"
        }
        payload = {"q": query}
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        
        results = []
        for item in data["organic"][:5]:
            results.append(item["title"] + ": " + item["snippet"])
        
        return "\n".join(results)
    except Exception as e:
        print("Search failed: " + str(e))
        return "The web search failed, so I don't have current information on this. I'll answer based on what I already know."

def read_webpage(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        paragraphs = soup.find_all("p")
        text = " ".join([p.get_text() for p in paragraphs])
        
        return text[:3000]
    except Exception as e:
        print("Failed to read webpage: " + str(e))
        return "Could not read this webpage. It may be blocking automated access or no longer available."
    
chroma_client = chromadb.PersistentClient(path="./chroma_db")
document_collection = chroma_client.get_or_create_collection(name="firm_documents")

def search_documents(query):
    results = document_collection.query(
        query_texts=[query],
        n_results=3
    )
    
    chunks = results["documents"][0]
    return "\n\n".join(chunks)


tools = [
    {
        "name": "search_web",
        "description": "Search the web for current information. Use this when you need up-to-date facts, news, or anything that might have happened recently.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_webpage",
        "description": "Read the full text content of a specific webpage. Use this after search_web when you need more detail than the short snippets provide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL of the webpage to read"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "search_documents",
        "description": "Search the firm's internal documents for relevant information. Use this when the question is about specific company data, filings, policies, or internal information that wouldn't be found through a general web search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for in the internal documents"
                }
            },
            "required": ["query"]
        }
    }
]

def run_agent(user_input, messages):
    messages.append({"role": "user", "content": user_input})
    
    max_iterations = 5
    iteration_count = 0
    
    while True:
        iteration_count += 1
        if iteration_count > max_iterations:
            return "I wasn't able to finish this within a reasonable number of steps. Could you try rephrasing your question?", messages
        
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                tools=tools,
                messages=messages
            )
        except Exception as e:
            print("Claude API call failed: " + str(e))
            return "Sorry, something went wrong talking to Claude. Please try again.", messages
        
        messages.append({"role": "assistant", "content": response.content})
        
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        if block.name == "search_web":
                            search_query = block.input["query"]
                            print("Searching: " + search_query)
                            search_results = search_web(search_query)
                            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": search_results})
                        elif block.name == "read_webpage":
                            page_url = block.input["url"]
                            print("Reading: " + page_url)
                            page_content = read_webpage(page_url)
                            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": page_content})
                        elif block.name == "search_documents":
                            doc_query = block.input["query"]
                            print("Searching documents: " + doc_query)
                            doc_results = search_documents(doc_query)
                            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": doc_results})
                    except Exception as e:
                        print("TOOL FAILED: " + block.name + " - " + str(e))
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "This tool failed to run."})
            
            messages.append({"role": "user", "content": tool_results})
        else:
            reply = response.content[0].text
            return reply, messages

def end_session(messages):
    summary_request = messages + [{"role": "user", "content": "Summarize everything important from this conversation in 2-3 sentences, focused on facts worth remembering for next time."}]
    
    summary_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=summary_request
    )
    
    new_summary = summary_response.content[0].text
    save_memory(new_summary)
    return "Memory saved. You can close this page now."
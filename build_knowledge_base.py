import os
import chromadb
from pypdf import PdfReader

def read_pdf(filepath):
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def read_txt(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()

def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="firm_documents")

documents_folder = "documents"

for filename in os.listdir(documents_folder):
    filepath = os.path.join(documents_folder, filename)
    
    if filename.endswith(".pdf"):
        text = read_pdf(filepath)
    elif filename.endswith(".txt"):
        text = read_txt(filepath)
    else:
        continue
    
    chunks = chunk_text(text)
    
    for i, chunk in enumerate(chunks):
        chunk_id = filename + "_chunk_" + str(i)
        collection.add(
            documents=[chunk],
            ids=[chunk_id]
        )
    
    print("Processed: " + filename + " (" + str(len(chunks)) + " chunks)")

print("Knowledge base built successfully.")
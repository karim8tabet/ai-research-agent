from agent import search_documents, read_webpage, is_safe_url

print("--- Document search ---")
print(search_documents("iPhone net sales")[:500])

print("\n--- Safety check ---")
print("localhost:", is_safe_url("http://localhost/"))
print("example.com:", is_safe_url("https://example.com/"))

print("\n--- Reading a real page ---")
print(read_webpage("https://example.com/")[:300])
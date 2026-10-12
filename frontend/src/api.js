// All communication with the Flask back end lives here.
// Components call these functions and never deal with fetch directly.

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });

  let data = {};
  try {
    data = await response.json();
  } catch {
    // The server sent something that isn't JSON, such as a crash page.
  }

  if (!response.ok) {
    throw new Error(data.error || "The server returned an error (" + response.status + ").");
  }
  return data;
}

export function getHistory() {
  return request("/api/history");
}

export function askQuestion(question) {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export function endSession() {
  return request("/api/end_session", { method: "POST", body: "{}" });
}

export function getDocuments() {
  return request("/api/documents");
}

// Files are sent as FormData, not JSON, so this skips the JSON helper above.
// The browser sets the right Content-Type for FormData by itself.
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/documents", {
    method: "POST",
    headers: { "X-Requested-With": "fetch" },
    body: formData,
  });

  let data = {};
  try {
    data = await response.json();
  } catch {
    // not JSON
  }
  if (!response.ok) {
    throw new Error(data.error || "The upload failed (" + response.status + ").");
  }
  return data;
}

export function deleteDocument(id) {
  return request("/api/documents/" + encodeURIComponent(id), { method: "DELETE" });
}

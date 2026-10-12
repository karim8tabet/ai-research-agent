import { useEffect, useState } from "react";
import { getHistory, askQuestion, endSession, getDocuments, uploadDocument, deleteDocument } from "./api.js";
import MessageList from "./components/MessageList.jsx";
import Composer from "./components/Composer.jsx";
import DocumentPanel from "./components/DocumentPanel.jsx";

export default function App() {
  // Each turn is { role: "user", text } or { role: "agent", html, tools }.
  const [turns, setTurns] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [sharedDocs, setSharedDocs] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);

  // Load this session's earlier conversation once, when the page opens.
  useEffect(() => {
    getHistory()
      .then((data) => setTurns(data.turns))
      .catch(() => setError("Couldn't load your earlier messages. Is the Flask server running?"));

    getDocuments()
      .then((data) => {
        setSharedDocs(data.shared);
        setDocuments(data.documents);
      })
      .catch(() => {});
  }, []);

  async function handleUpload(file) {
    setError("");
    setIsUploading(true);
    try {
      const data = await uploadDocument(file);
      setDocuments((current) => [...current, data.document]);
      setStatus("Added " + data.document.filename + ". You can ask about it now.");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleRemove(id) {
    setError("");
    try {
      await deleteDocument(id);
      setDocuments((current) => current.filter((doc) => doc.id !== id));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSend(question) {
    setError("");
    setStatus("");
    setTurns((current) => [...current, { role: "user", text: question }]);
    setIsThinking(true);

    try {
      const data = await askQuestion(question);
      setTurns((current) => [
        ...current,
        { role: "agent", html: data.answer_html, tools: data.tools },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsThinking(false);
    }
  }

  async function handleEndSession() {
    setStatus("Saving memory…");
    try {
      const data = await endSession();
      setDocuments([]); // the server deleted this session's uploads
      setStatus(data.message);
    } catch (err) {
      setStatus("");
      setError(err.message);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>Research Agent</h1>
      </header>

      <MessageList turns={turns} isThinking={isThinking} />

      <footer>
        {error && <p className="error">{error}</p>}
        <DocumentPanel
          shared={sharedDocs}
          documents={documents}
          isUploading={isUploading}
          onUpload={handleUpload}
          onRemove={handleRemove}
        />
        <Composer onSend={handleSend} disabled={isThinking} />
        <div className="footer-meta">
          <button className="btn-end" onClick={handleEndSession} disabled={isThinking}>
            End session &amp; save memory
          </button>
          {status && <span className="status-msg">{status}</span>}
        </div>
      </footer>
    </div>
  );
}

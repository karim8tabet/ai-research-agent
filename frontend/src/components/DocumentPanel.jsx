import { useRef } from "react";

// Shows the shared documents, the visitor's own uploads, and an upload button.
export default function DocumentPanel({ shared, documents, isUploading, onUpload, onRemove }) {
  const fileInput = useRef(null);

  function handleFileChosen(event) {
    const file = event.target.files[0];
    if (file) onUpload(file);
    event.target.value = ""; // so choosing the same file again still triggers onChange
  }

  return (
    <div className="documents">
      <div className="documents-row">
        <span className="documents-title">Documents</span>
        {shared.length > 0 && (
          <span className="doc-chip shared" title={shared.join(", ")}>
            {shared.length} shared
          </span>
        )}
        {documents.map((doc) => (
          <span key={doc.id} className="doc-chip">
            <span className="doc-name">{doc.filename}</span>
            <button
              className="doc-remove"
              onClick={() => onRemove(doc.id)}
              aria-label={"Remove " + doc.filename}
            >
              ×
            </button>
          </span>
        ))}
        <button
          className="doc-upload"
          onClick={() => fileInput.current.click()}
          disabled={isUploading}
        >
          {isUploading ? "Uploading…" : "+ Add document"}
        </button>
        {/* The real file picker is hidden; the button above opens it. */}
        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.txt,.md"
          onChange={handleFileChosen}
          hidden
        />
      </div>
      <p className="documents-note">
        PDF, .txt or .md, up to 10 MB. Only you can search your documents, and they're deleted
        when you end the session.
      </p>
    </div>
  );
}

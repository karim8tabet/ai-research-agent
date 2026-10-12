import { useState } from "react";

export default function Composer({ onSend, disabled }) {
  const [question, setQuestion] = useState("");

  function handleSubmit(event) {
    event.preventDefault(); // stop the browser from reloading the page
    const trimmed = question.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setQuestion("");
  }

  return (
    <form className="compose" onSubmit={handleSubmit}>
      <input
        type="text"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder={disabled ? "Waiting for the agent…" : "Ask anything…"}
        maxLength={2000}
        autoComplete="off"
        autoFocus
        aria-label="Your question"
      />
      <button type="submit" disabled={disabled || !question.trim()}>
        Send
      </button>
    </form>
  );
}

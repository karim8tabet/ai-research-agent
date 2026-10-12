import { useEffect, useRef } from "react";
import Message from "./Message.jsx";
import ThinkingIndicator from "./ThinkingIndicator.jsx";

export default function MessageList({ turns, isThinking }) {
  const bottomRef = useRef(null);

  // Scroll to the newest message whenever the conversation changes.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, isThinking]);

  return (
    <main id="thread">
      {turns.length === 0 && !isThinking && (
        <p className="empty">
          Ask a question. The agent can search the web, read webpages and search a private
          document library using retrieval-augmented generation (RAG).
        </p>
      )}
      {turns.map((turn, index) => (
        <Message key={index} turn={turn} />
      ))}
      {isThinking && <ThinkingIndicator />}
      <div ref={bottomRef} />
    </main>
  );
}

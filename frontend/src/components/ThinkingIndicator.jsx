export default function ThinkingIndicator() {
  return (
    <div className="turn agent" aria-live="polite">
      <div className="turn-label">Agent</div>
      <div className="thinking">
        <div className="dots" aria-hidden="true">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <span className="thinking-text">Researching…</span>
      </div>
    </div>
  );
}

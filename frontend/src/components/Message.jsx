import ToolSteps from "./ToolSteps.jsx";

export default function Message({ turn }) {
  if (turn.role === "user") {
    return (
      <div className="turn user">
        <div className="turn-label">You</div>
        {/* Plain text: React escapes it automatically. */}
        <div className="turn-body">{turn.text}</div>
      </div>
    );
  }

  return (
    <div className="turn agent">
      <div className="turn-label">Agent</div>
      <ToolSteps tools={turn.tools} />
      {/* The answer arrives as HTML that Flask already sanitized with nh3,
          which strips scripts and other dangerous markup before it gets here. */}
      <div className="turn-body" dangerouslySetInnerHTML={{ __html: turn.html }} />
    </div>
  );
}

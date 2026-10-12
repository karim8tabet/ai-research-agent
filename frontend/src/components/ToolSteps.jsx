import { useState } from "react";

const ICONS = {
  search_web: "⌕",
  read_webpage: "↗",
  search_documents: "▤",
};

// Shows which tools the agent used to reach its answer, collapsed by default.
export default function ToolSteps({ tools }) {
  const [open, setOpen] = useState(false);
  if (!tools || tools.length === 0) return null;

  const count = tools.length === 1 ? "1 step" : tools.length + " steps";

  return (
    <div className="tool-steps">
      <button className="tool-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? "Hide" : "Show"} research · {count}
      </button>
      {open && (
        <ol className="tool-list">
          {tools.map((step, index) => (
            <li key={index}>
              <span className="tool-icon" aria-hidden="true">{ICONS[step.tool] || "•"}</span>
              <span className="tool-label">{step.label}</span>
              {step.detail && <span className="tool-detail">{step.detail}</span>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

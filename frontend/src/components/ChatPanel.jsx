import { useRef, useEffect } from "react";

const STARTER_PROMPTS = [
  "Find me a lipstick under ₹9,000",
  "Show me highly rated lipsticks",
  "Which one has the best reviews?",
  "Compare the first two",
];

export function ChatPanel({ messages, sending, input, onInput, onSend, onPrompt, error, onDismissError }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages]);

  return (
    <div className="chat-panel">
      <div className="chat-window">
        {!messages.length ? (
          <div className="chat-welcome">
            <div className="chat-welcome__orb" aria-hidden="true">✦</div>
            <span className="eyebrow">GLOWCART AI</span>
            <h2>What are you shopping for?</h2>
            <p>
              I can compare products using catalog ratings, review volume,
              and stored review evidence.
            </p>
            <div className="prompt-grid">
              {STARTER_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  className="prompt-chip"
                  onClick={() => onPrompt(prompt)}
                >
                  <span>{prompt}</span>
                  <b>→</b>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="chat-messages">
            {messages.map((msg, i) => (
              <div
                key={`${msg.role}-${i}`}
                className={`msg-row msg-row--${msg.role}`}
              >
                {msg.role === "assistant" && (
                  <div className="msg-avatar" aria-hidden="true">G</div>
                )}
                <div className="msg-bubble">{msg.text}</div>
              </div>
            ))}
            {sending && (
              <div className="msg-row msg-row--assistant">
                <div className="msg-avatar" aria-hidden="true">G</div>
                <div className="msg-bubble typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      {error && (
        <div className="error-banner" role="alert">
          <span aria-hidden="true">!</span>
          <p>{error}</p>
          <button onClick={onDismissError} aria-label="Dismiss error">×</button>
        </div>
      )}

      <form
        className="composer"
        onSubmit={(e) => { e.preventDefault(); onSend(); }}
      >
        <input
          value={input}
          onChange={(e) => onInput(e.target.value)}
          placeholder="Find a lipstick, compare options, or continue checkout..."
          disabled={sending}
          maxLength={2000}
          aria-label="Shopping message"
        />
        <button
          type="submit"
          className="composer__send"
          disabled={!input.trim() || sending}
          aria-label="Send message"
        >
          →
        </button>
      </form>

      <p className="composer-note">
        <span aria-hidden="true">⌁</span>{" "}
        AI uses LLM for language understanding. Prices, inventory, totals, and payments are
        controlled by the application.
      </p>
    </div>
  );
}

/**
 * AuditTimeline — renders a vertical timeline of audit events.
 * groups: optional array of { label, eventTypes[] } for grouping
 */
export function AuditTimeline({ audit, limit }) {
  const events = limit ? (audit ?? []).slice(0, limit) : (audit ?? []);

  if (!events.length) {
    return (
      <p className="audit-empty">
        Important shopping and payment actions will appear here.
      </p>
    );
  }

  return (
    <ol className="audit-timeline" aria-label="Agent activity timeline">
      {events.map((event, index) => {
        const status = event.status || "";
        let dotCls = "audit-dot";
        if (status === "success" || status === "PAID") dotCls += " audit-dot--success";
        else if (status === "failed" || status === "error") dotCls += " audit-dot--danger";
        else if (status === "warning") dotCls += " audit-dot--warning";

        const title = (event.event_type || "event")
          .replaceAll("_", " ")
          .replace(/\b\w/g, (l) => l.toUpperCase());

        return (
          <li key={`${event.id ?? index}-${event.event_type}`} className="audit-event">
            <span className={dotCls} aria-hidden="true" />
            <div className="audit-event__content">
              <strong>{title}</strong>
              {event.description && <p>{event.description}</p>}
              {event.created_at && (
                <time dateTime={event.created_at}>
                  {new Date(event.created_at).toLocaleTimeString("en-IN", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </time>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

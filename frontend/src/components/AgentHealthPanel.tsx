import { useEffect, useState } from "react";

interface AgentHealth {
  name: string;
  status: "healthy" | "degraded" | "error" | "unknown";
  last_executed_at: string | null;
  p95_latency_ms: number | null;
  error_rate_15m: number;
  total_executions_15m: number;
  active_degradation_flags: string[];
}

const STATUS_LABELS: Record<string, string> = {
  healthy: "Healthy",
  degraded: "Degraded",
  error: "Error",
  unknown: "Unknown",
};

export default function AgentHealthPanel() {
  const [agents, setAgents] = useState<AgentHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastFetchError, setLastFetchError] = useState(false);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch(`/api/v1/agents/health?tenant_id=tenant-alpha`);
        if (!res.ok) throw new Error("fetch failed");
        const data = await res.json();
        setAgents(
          Object.entries(data.agents).map(([name, metrics]) => ({
            name,
            ...(metrics as Omit<AgentHealth, "name">),
          }))
        );
        setLastFetchError(false);
      } catch {
        setLastFetchError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <section className="panel" aria-label="Agent health" aria-busy="true">
        <div className="panel-header">
          <h2>Agent Health</h2>
        </div>
        <div className="status-grid" role="list">
          {Array.from({ length: 5 }).map((_, i) => (
            <article className="run-card skeleton" key={i} role="listitem" aria-label="Loading agent health">
              <div className="run-card-top">
                <div className="skeleton-text skeleton-short" />
                <div className="skeleton-pill" />
              </div>
              <div className="skeleton-text" />
              <div className="skeleton-text" />
              <div className="skeleton-text" />
            </article>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="panel" aria-label="Agent health">
      <div className="panel-header">
        <h2>Agent Health</h2>
        <span className="legend">
          {lastFetchError ? "Live data unavailable - showing last known state" : "Real-time agent metrics (15m window)"}
        </span>
      </div>
      {lastFetchError && (
        <div role="alert" aria-live="polite" className="fetch-error-banner">
          Unable to fetch live data. Data may be outdated.
        </div>
      )}
      <div className="status-grid" role="list">
        {agents.map((agent) => (
          <article className="run-card" key={agent.name} role="listitem">
            <div className="run-card-top">
              <strong>{agent.name}</strong>
              {/* Status uses BOTH color class AND text label - WCAG no color-only state */}
              <span
                className={`status-pill status-${agent.status}`}
                aria-label={`Status: ${STATUS_LABELS[agent.status] ?? agent.status}`}
              >
                {STATUS_LABELS[agent.status] ?? agent.status}
              </span>
            </div>
            <p>Executions (15m): {agent.total_executions_15m}</p>
            <p>Error rate: {(agent.error_rate_15m * 100).toFixed(1)}%</p>
            <p>
              P95 latency:{" "}
              {agent.p95_latency_ms !== null ? `${agent.p95_latency_ms.toFixed(0)}ms` : "N/A"}
            </p>
            {agent.last_executed_at && (
              <p>
                Last run:{" "}
                <time dateTime={agent.last_executed_at}>
                  {new Date(agent.last_executed_at).toLocaleTimeString()}
                </time>
              </p>
            )}
            {agent.active_degradation_flags.length > 0 && (
              <ul aria-label="Active degradation flags">
                {agent.active_degradation_flags.map((flag) => (
                  <li key={flag}>{flag}</li>
                ))}
              </ul>
            )}
          </article>
        ))}
        {agents.length === 0 && !lastFetchError && (
          <p>No agent data available yet. Run a prediction to populate metrics.</p>
        )}
      </div>
    </section>
  );
}

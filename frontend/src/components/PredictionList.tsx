import { useEffect, useState } from "react";

interface Prediction {
  prediction_id: string;
  tenant_id: string;
  status: string;
  confidence_interval?: { lower: number; upper: number };
  created_at: string;
}

export default function PredictionList({ tenantId }: { tenantId: string }) {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch(`/api/v1/predictions?tenant_id=${tenantId}`);
        if (response.ok) {
          const data = (await response.json()) as Prediction[];
          setPredictions(data);
        }
      } catch {
        setPredictions([]);
      }
    }
    void load();
  }, [tenantId]);

  const filtered = predictions.filter((p) =>
    filter ? p.status === filter : true,
  );

  return (
    <section className="panel" aria-label="Prediction history">
      <div className="panel-header">
        <h2>Predictions</h2>
        <label>
          Filter by status:
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-label="Filter predictions by status"
          >
            <option value="">All</option>
            <option value="completed">Completed</option>
            <option value="degraded">Degraded</option>
            <option value="escalated">Escalated</option>
          </select>
        </label>
      </div>
      <div className="run-grid" role="list">
        {filtered.map((p) => (
          <article className="run-card" key={p.prediction_id} role="listitem">
            <div className="run-card-top">
              <strong>{p.prediction_id.slice(0, 12)}...</strong>
              <span className={`status-pill status-${p.status}`}>{p.status}</span>
            </div>
            <p>Tenant: {p.tenant_id}</p>
            {p.confidence_interval ? (
              <p>
                CI: {p.confidence_interval.lower} - {p.confidence_interval.upper}
              </p>
            ) : null}
            <p>Created: {new Date(p.created_at).toLocaleString()}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

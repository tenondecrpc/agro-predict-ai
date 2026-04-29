import { useState } from "react";

interface FeatureFlag {
  flag_id: string;
  name: string;
  enabled: boolean;
  tenant_scope: string | null;
  kill_switch: boolean;
}

export default function FeatureFlagManager() {
  const [flags, setFlags] = useState<FeatureFlag[]>([
    { flag_id: "ff-1", name: "new_prediction_model", enabled: false, tenant_scope: null, kill_switch: false },
    { flag_id: "ff-2", name: "advanced_explainability", enabled: true, tenant_scope: "tenant-alpha", kill_switch: false },
  ]);

  function toggleFlag(flagId: string) {
    setFlags(flags.map((f) => (f.flag_id === flagId ? { ...f, enabled: !f.enabled } : f)));
  }

  function killSwitch(flagId: string) {
    setFlags(flags.map((f) => (f.flag_id === flagId ? { ...f, kill_switch: true, enabled: false } : f)));
  }

  return (
    <section className="panel" aria-label="Feature flags">
      <div className="panel-header">
        <h2>Feature Flags</h2>
      </div>
      <div className="run-grid" role="list">
        {flags.map((f) => (
          <article className="run-card" key={f.flag_id} role="listitem">
            <div className="run-card-top">
              <strong>{f.name}</strong>
              <span className={`status-pill status-${f.enabled ? "completed" : "paused"}`}>
                {f.enabled ? "enabled" : "disabled"}
              </span>
            </div>
            <p>Scope: {f.tenant_scope || "global"}</p>
            <div className="button-row">
              <button type="button" onClick={() => toggleFlag(f.flag_id)}>
                {f.enabled ? "Disable" : "Enable"}
              </button>
              <button type="button" onClick={() => killSwitch(f.flag_id)} disabled={f.kill_switch}>
                {f.kill_switch ? "Killed" : "Kill Switch"}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

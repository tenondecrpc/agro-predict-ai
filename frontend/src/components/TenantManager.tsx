import { useState } from "react";

interface Tenant {
  tenant_id: string;
  name: string;
  status: string;
  budget_limit: number;
  budget_consumed: number;
}

export default function TenantManager() {
  const [tenants, setTenants] = useState<Tenant[]>([
    { tenant_id: "tenant-alpha", name: "Alpha Corp", status: "active", budget_limit: 10000, budget_consumed: 2500 },
    { tenant_id: "tenant-beta", name: "Beta Farms", status: "active", budget_limit: 5000, budget_consumed: 1200 },
  ]);
  const [newName, setNewName] = useState("");

  function addTenant() {
    if (!newName.trim()) return;
    const tenant: Tenant = {
      tenant_id: `tenant-${Date.now()}`,
      name: newName,
      status: "active",
      budget_limit: 1000,
      budget_consumed: 0,
    };
    setTenants([...tenants, tenant]);
    setNewName("");
  }

  return (
    <section className="panel" aria-label="Tenant management">
      <div className="panel-header">
        <h2>Tenants</h2>
      </div>
      <div className="button-row" style={{ marginBottom: "1rem" }}>
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New tenant name"
          aria-label="New tenant name"
        />
        <button type="button" onClick={addTenant}>
          Create Tenant
        </button>
      </div>
      <div className="run-grid" role="list">
        {tenants.map((t) => (
          <article className="run-card" key={t.tenant_id} role="listitem">
            <div className="run-card-top">
              <strong>{t.name}</strong>
              <span className={`status-pill status-${t.status}`}>{t.status}</span>
            </div>
            <p>ID: {t.tenant_id}</p>
            <p>Budget: ${t.budget_consumed} / ${t.budget_limit}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

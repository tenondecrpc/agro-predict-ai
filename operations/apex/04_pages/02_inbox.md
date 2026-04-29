# Page 2 - Inbox / Lista de Solicitudes

The default landing page after login. Shows all active purchase
requests for the cooperative.

## Page properties

- **Page number**: 2
- **Name**: `Inbox`
- **Title**: `Solicitudes activas`
- **Navigation Menu**: Show

## Region 1 - KPI strip

Region type: **Cards**, source: **REST Source** -> `RDS_REQUESTS_LIST`.

Or simpler: a Static Content region with 4 cards, each populated by a
small computed item:

```html
<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:16px; margin-bottom:24px;">

  <div style="background:#fff; border-radius:12px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
    <div style="color:#94a3b8; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.5px;">Solicitudes activas</div>
    <div style="font-size:2rem; font-weight:700; color:#15803d; margin-top:4px;">&P2_KPI_ACTIVE.</div>
  </div>

  <div style="background:#fff; border-radius:12px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
    <div style="color:#94a3b8; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.5px;">Monto en proceso (Gs.)</div>
    <div style="font-size:2rem; font-weight:700; color:#15803d; margin-top:4px;">&P2_KPI_AMOUNT.</div>
  </div>

  <div style="background:#fff; border-radius:12px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
    <div style="color:#94a3b8; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.5px;">Pendientes de aprobacion</div>
    <div style="font-size:2rem; font-weight:700; color:#a16207; margin-top:4px;">&P2_KPI_PENDING.</div>
  </div>

  <div style="background:#fff; border-radius:12px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
    <div style="color:#94a3b8; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.5px;">Cycle time promedio</div>
    <div style="font-size:2rem; font-weight:700; color:#15803d; margin-top:4px;">3.2 dias</div>
  </div>

</div>
```

For demo, hardcode `P2_KPI_*` items to plausible values:
- `P2_KPI_ACTIVE = 5`
- `P2_KPI_AMOUNT = 28.450M`
- `P2_KPI_PENDING = 1`

(They can be Display Only items with default values - the demo does
not need real aggregation.)

## Region 2 - Filtros

Static Content above the report:

```html
<div style="display:flex; gap:12px; margin-bottom:16px;">
  <select id="P2_FILTER_CROP" style="padding:8px 16px; border-radius:24px; border:1px solid #cbd5e1;">
    <option value="">Cultivo: todos</option>
    <option>soja</option><option>maiz</option><option>trigo</option><option>sorgo</option>
  </select>
  <select id="P2_FILTER_STATUS" style="padding:8px 16px; border-radius:24px; border:1px solid #cbd5e1;">
    <option value="">Estado: todos</option>
    <option>draft</option><option>in_quoting</option><option>ready_for_review</option>
    <option>recommended</option><option>approved</option>
  </select>
  <select id="P2_FILTER_URGENCY" style="padding:8px 16px; border-radius:24px; border:1px solid #cbd5e1;">
    <option value="">Urgencia: todas</option>
    <option>normal</option><option>urgente</option><option>critica</option>
  </select>
</div>
```

The filters are visual for the demo. Connect to the report later if
time permits.

## Region 3 - Lista de solicitudes

Region type: **Interactive Report** (or **Classic Report** if you
prefer simpler styling).

- **Source Type**: REST Source
- **REST Data Source**: `RDS_REQUESTS_LIST`
- **Bind Variables**:
  - `tenant_id`: `&TENANT_ID.`
  - `team_id`: `&TEAM_ID.`

### Columns

Configure these columns (drop the rest as Hidden):

| Column | Display | Notes |
|---|---|---|
| `title` | Plain text | Click target -> request detail |
| `target_crop` | HTML expression | See badge below |
| `fenological_window` | HTML expression | Pill `pre-siembra`, `siembra`... |
| `urgency` | HTML expression | Color-coded pill |
| `target_delivery_date` | Date | Format `DD-MON-YYYY` |
| `current_stock_days` | Number | Append " dias" with format mask |
| `status` | HTML expression | Status pill |
| `request_id` | Hidden | Used for the link |

### Title link

In the `title` column properties:

- **Link**: page 4 with `P4_REQUEST_ID = #request_id#`
- **Display Type**: Plain Text - emphasized

### Crop badge HTML expression

```html
<span style="display:inline-flex; align-items:center; gap:6px;
       padding:4px 12px; border-radius:24px;
       background:#dcfce7; color:#15803d; font-size:0.85rem; font-weight:500;">
  &nbsp;#TARGET_CROP#
</span>
```

### Urgency badge HTML expression

```html
<span style="padding:2px 10px; border-radius:12px; font-size:0.8rem; font-weight:600;
  CASE WHEN '#URGENCY#' = 'critica' THEN 'background:#fee2e2; color:#b91c1c;'
       WHEN '#URGENCY#' = 'urgente' THEN 'background:#fef3c7; color:#a16207;'
       ELSE 'background:#dbeafe; color:#1e40af;' END">
  #URGENCY#
</span>
```

> APEX's HTML expressions support `CASE`-style conditionals only via
> `Apex_String.Format` or template directives. The simpler path is to
> create a SQL computed column in the REST source result that returns
> the full HTML; or skip the conditional color and pick a single one
> per row using the urgency string directly. The demo arc only shows
> `critica`, so a single style is fine.

### Status pill

Same pattern. Map values:

- `draft` -> grey `#cbd5e1`
- `in_quoting` -> blue `#dbeafe`
- `ready_for_review` -> amber `#fef3c7`
- `recommended` -> green `#dcfce7`
- `approved` -> green stronger `#86efac`
- `closed` -> grey

## Region 4 - "Nueva solicitud" button

Top-right of the page: a button that links to page 3
(`Create Request`). Visible only when `:G_ROLE = 'solicitante'`.

In the button's **Server-side Condition**:

```
Type: PL/SQL Expression
Expression: :G_ROLE = 'solicitante'
```

## Demo behaviour

- The presenter logs in as Comprador (page 1).
- Page 2 shows 5 requests; the urea-zafra-soja-26/27 row has urgency
  `critica` and category `fertilizante`.
- Click on its title -> page 4.

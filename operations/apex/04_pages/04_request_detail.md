# Page 4 - Request Detail and Quotations

The hub page for one request. Shows the request summary and the list
of received quotations. Drives the buyer to upload, compare, and
recommend.

## Page properties

- **Page number**: 4
- **Name**: `Solicitud detalle`
- **Page item P4_REQUEST_ID**: Hidden, populated from the URL.

## Region 1 - Resumen de la solicitud

Region type: **Form** with REST Source `RDS_REQUEST_DETAIL`.

- **Bind variable** `request_id`: `&P4_REQUEST_ID.`
- **Bind variable** `tenant_id`: `&TENANT_ID.`
- **Form mode**: Read-only

Render the fields in a 2-column grid using the **Custom CSS**
template:

```
Title (full row)
-----------------------------------
Cultivo destino   |   Zafra
Ventana fenologica|   Hectareas
Departamento entrega | Stock dias
Fecha limite entrega | Urgencia
Total estimado    |   Status
```

### Status pill (display only)

Add an HTML region next to the form with a small computed pill:

```html
<div style="display:inline-block; padding:4px 12px; border-radius:12px;
            background:#dcfce7; color:#15803d; font-weight:600;">
  &P4_STATUS.
</div>
```

(`P4_STATUS` is populated by the form's REST source).

## Region 2 - Items de la solicitud

A small table region listing `request.items`. Source: extract from the
REST detail response.

If APEX has trouble surfacing the nested array, ship a static
placeholder for the demo:

```
Item: Urea granulada 46% N
Cantidad: 800.000 kg
Unidad: kg
```

## Region 3 - Cotizaciones recibidas

Region type: **Interactive Report**, REST source
`RDS_QUOTATIONS_LIST`.

- **Bind**: `request_id` -> `&P4_REQUEST_ID.`, `tenant_id` -> `&TENANT_ID.`

### Columns

| Column | Display | Notes |
|---|---|---|
| supplier_name (computed) | Plain text | See below |
| total_pyg_normalized | Number | Format `999G999G999G999` |
| currency | Plain text | |
| lead_time_days | Number | Append " dias" |
| warranty_months | Number | Append " meses" |
| status | HTML | Pill (validated/quarantined) |
| anomaly_icon (computed) | HTML | warning sign if flagged |
| ml_band (computed) | HTML | colored confidence band |

### Computing `supplier_name`

The quotation list does not include the supplier's legal name by
default. Two options:

**Option A - PL/SQL post-processing**: in the report's "Initialization
PL/SQL Code", join against a second REST call to `RDS_SUPPLIER_DETAIL`
per row. Slow but works.

**Option B - Cache once**: at page load, hit `RDS_SUPPLIERS_LIST`,
build a `supplier_id -> legal_name` map in an APEX session collection,
then use `APEX_COLLECTION.GET_ATTRIBUTE` in the column SQL.

For the demo, **Option B** is the way:

In a **Before Header** PL/SQL process:

```plsql
DECLARE
  l_response  CLOB;
  l_count     PLS_INTEGER;
BEGIN
  IF NOT APEX_COLLECTION.COLLECTION_EXISTS('SUPPLIERS_BY_ID') THEN
    l_response := APEX_WEB_SERVICE.MAKE_REST_REQUEST(
      p_url => '&BACKEND_URL./api/v1/procurement/suppliers?tenant_id=' || :TENANT_ID,
      p_http_method => 'GET'
    );
    APEX_JSON.PARSE(l_response);
    APEX_COLLECTION.CREATE_OR_TRUNCATE_COLLECTION('SUPPLIERS_BY_ID');
    l_count := APEX_JSON.GET_COUNT(p_path => '.');
    FOR i IN 1 .. l_count LOOP
      APEX_COLLECTION.ADD_MEMBER(
        p_collection_name => 'SUPPLIERS_BY_ID',
        p_c001 => APEX_JSON.GET_VARCHAR2(p_path => '[%d].supplier_id', p0 => i),
        p_c002 => APEX_JSON.GET_VARCHAR2(p_path => '[%d].legal_name', p0 => i)
      );
    END LOOP;
  END IF;
END;
```

Then the report column for `supplier_name` is a computed expression:

```sql
(SELECT c002 FROM apex_collections
  WHERE collection_name = 'SUPPLIERS_BY_ID' AND c001 = '#SUPPLIER_ID#')
```

### Anomaly icon column

HTML expression on a computed `quality_flags` field:

```html
<span style="color:#a16207; font-size:1.2rem;" title="Anomalia detectada">
  !
</span>
```

Only render the span when `#ANOMALY_SCORE#` >= 0.6 (use a Server-side
Condition or wrap in `<template>`).

### ML confidence band

Add a small bar based on `metadata_json.ml_p_on_time`. For the demo,
the simpler approach: do not surface ML in the row, render it on
page 6 only.

## Region 4 - Action bar

Sticky bottom bar with two buttons:

- `Cargar cotizacion` -> opens page 5 with `P5_REQUEST_ID = &P4_REQUEST_ID.`
- `Comparar y recomendar` -> opens page 6 with `P6_REQUEST_ID = &P4_REQUEST_ID.`
  - Server-side condition: at least 2 quotations validated. For the
    demo, leave always-enabled (the seeded request has 4 validated).

```html
<div style="position:sticky; bottom:0; background:#fff; padding:16px;
            border-top:1px solid #e2e8f0; display:flex; gap:12px; justify-content:flex-end;">
  <a href="f?p=&APP_ID.:5:&APP_SESSION.::NO::P5_REQUEST_ID:&P4_REQUEST_ID."
     class="t-Button">Cargar cotizacion</a>
  <a href="f?p=&APP_ID.:6:&APP_SESSION.::NO::P6_REQUEST_ID:&P4_REQUEST_ID."
     class="t-Button t-Button--hot" style="background:#15803d;">
    Comparar y recomendar
  </a>
</div>
```

## Demo behaviour

- Click on the urea request from the inbox.
- Page 4 shows the cooperative's solicitation, the 4 cotizaciones,
  and the two action buttons.
- Click "Comparar y recomendar" -> page 6.

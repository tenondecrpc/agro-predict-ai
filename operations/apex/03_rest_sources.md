# 03 - REST Data Sources

Configure once at **Shared Components** -> **REST Data Sources**.
All endpoints live under `&BACKEND_URL./api/v1/procurement/`.

For each entry below:

1. Click **Create** -> **From Scratch**.
2. **REST Data Source Type**: `Generic JSON`.
3. **Name** as listed.
4. **URL Endpoint** as listed (use `&BACKEND_URL.` for the host).
5. **Authentication**: `None` (the backend runs without auth in dev).
6. Click **Discover** -> APEX inspects the JSON structure and lets
   you accept the defaults. Click **Create**.

## Inventory

| Name | Operation | URL Endpoint |
|---|---|---|
| `RDS_REQUESTS_LIST` | GET | `&BACKEND_URL./api/v1/procurement/requests` |
| `RDS_REQUEST_DETAIL` | GET | `&BACKEND_URL./api/v1/procurement/requests/:request_id` |
| `RDS_REQUEST_CREATE` | POST | `&BACKEND_URL./api/v1/procurement/requests` |
| `RDS_REQUEST_TRANSITION` | POST | `&BACKEND_URL./api/v1/procurement/requests/:request_id/transition` |
| `RDS_REQUEST_RECOMMEND` | POST | `&BACKEND_URL./api/v1/procurement/requests/:request_id/recommend` |
| `RDS_QUOTATIONS_LIST` | GET | `&BACKEND_URL./api/v1/procurement/requests/:request_id/quotations` |
| `RDS_QUOTATION_DETAIL` | GET | `&BACKEND_URL./api/v1/procurement/quotations/:quotation_id` |
| `RDS_QUOTATION_CREATE` | POST | `&BACKEND_URL./api/v1/procurement/quotations` |
| `RDS_QUOTATION_EXTRACT` | POST | `&BACKEND_URL./api/v1/procurement/quotations/extract` |
| `RDS_QUOTATION_NEGOTIATE` | POST | `&BACKEND_URL./api/v1/procurement/quotations/:quotation_id/negotiate` |
| `RDS_SUPPLIERS_LIST` | GET | `&BACKEND_URL./api/v1/procurement/suppliers` |
| `RDS_SUPPLIER_DETAIL` | GET | `&BACKEND_URL./api/v1/procurement/suppliers/:supplier_id` |
| `RDS_SUPPLIER_CREATE` | POST | `&BACKEND_URL./api/v1/procurement/suppliers` |
| `RDS_WEATHER_RISK` | GET | `&BACKEND_URL./api/v1/procurement/weather/risk` |
| `RDS_FX_USD_PYG` | GET | `&BACKEND_URL./api/v1/procurement/fx/usd_pyg` |
| `RDS_AUDIT` | GET | `&BACKEND_URL./api/v1/procurement/audit` |

## Per-source configuration tips

### List endpoints (RDS_REQUESTS_LIST, RDS_QUOTATIONS_LIST, RDS_SUPPLIERS_LIST)

After Discover, set:

- **Pagination Type**: `None`
- **Parameters**: add the query params explicitly so APEX surfaces them as bind variables:
  - `tenant_id` (Static, default `&TENANT_ID.`)
  - `team_id` (Static, default `&TEAM_ID.`)
  - `status`, `team_id` (Optional, leave empty by default)

### Detail endpoints

- The path parameter (`:request_id`) is automatically picked up by
  APEX as a bind variable. When you reference the source from a page,
  bind it to a page item like `P4_REQUEST_ID`.
- Add `tenant_id` as a query parameter with default `&TENANT_ID.`.

### POST endpoints (CREATE / TRANSITION / RECOMMEND / EXTRACT / NEGOTIATE)

- After Discover, switch the **Operations** tab.
- For the POST operation:
  - **Database Operation**: `Insert Row` for create endpoints, `Execute` for action endpoints (`/transition`, `/recommend`, `/extract`, `/negotiate`).
  - **Request Body**: switch from `Auto` to `Custom`. Provide the JSON template (see below per page).

### `RDS_REQUEST_RECOMMEND` quirks

- The endpoint returns `200` on success and `422` on escalation. APEX
  treats both as valid responses. Read the body's `status` field to
  branch.
- The body is empty (`{}` or no body) - put the path param
  `request_id` and the query param `tenant_id`.

### `RDS_QUOTATION_EXTRACT` body template

Set the **Request Body** to:

```json
{
  "raw_text": ":P5_RAW_TEXT",
  "request_id": ":P5_REQUEST_ID",
  "tenant_id": ":TENANT_ID"
}
```

APEX substitutes `:P5_RAW_TEXT` with the page item value at runtime.

### `RDS_QUOTATION_NEGOTIATE` body template

```json
{
  "target_improvements": {
    "price_pct": :P6_PRICE_PCT,
    "lead_time_days": :P6_LEAD_TIME_DAYS
  },
  "tone": ":P6_TONE",
  "tenant_id": ":TENANT_ID"
}
```

If the user does not pick a `price_pct`, you must omit the key. APEX
lets you do this with a small PL/SQL transform on the request body
(see [04_pages/06_compare_recommend.md](04_pages/06_compare_recommend.md)).

### `RDS_REQUEST_CREATE` body template

Compose from page items P3_*. See [04_pages/03_create_request.md](04_pages/03_create_request.md)
for the full body template.

## Sanity test

After all sources are created, go to **Shared Components** ->
**REST Data Sources** -> click `RDS_REQUESTS_LIST` -> **Test**.

Set parameters:
- `tenant_id`: `tenant-yguazu`
- `team_id`: `team-compras`

Click **Send Request**. You should see 5 requests in the response.

If you get a 404 or timeout: check ngrok is running, the backend is
running, and `&BACKEND_URL.` substitution is the current ngrok URL
(every ngrok restart = new URL).

# Page 6 - Comparar / Recomendar / Negociar (STAR PAGE)

This is the page that demonstrates the entire AI value proposition.
Build it first; everything else is supporting context.

## Page properties

- **Page number**: 6
- **Name**: `Comparar y recomendar`
- **Page item P6_REQUEST_ID**: Hidden, from URL.

## Hidden state items

| Item | Type | Notes |
|---|---|---|
| `P6_RECOMMENDATION_JSON` | Hidden | Stores the full pipeline response |
| `P6_RECOMMENDED_QUOTATION_ID` | Hidden | Used by the negotiator section |
| `P6_RECOMMENDED_SUPPLIER_NAME` | Hidden | For display |
| `P6_RECOMMENDED_SUPPLIER_ID` | Hidden | For display |
| `P6_DECISION_BAND` | Hidden | `buy_now` etc. |
| `P6_COMPOSITE_SCORE` | Hidden | |
| `P6_URGENCY_SCORE` | Hidden | |
| `P6_OFFER_SCORE` | Hidden | |
| `P6_REASONING_MARKDOWN` | Hidden | |
| `P6_WEATHER_RISK` | Hidden | |
| `P6_FX_RATE` | Hidden | |
| `P6_NEGOTIATION_TEXT` | Display Only | Multi-line |
| `P6_NEGOTIATION_SOURCE` | Display Only | `llm` / `fallback` |

## Region 1 - Comparativa normalizada

Region type: **Interactive Report** with REST source
`RDS_QUOTATIONS_LIST`. Bind `request_id` and `tenant_id`.

Columns to display:

| Column | Display |
|---|---|
| supplier_name (computed via collection - same trick as page 4) | Bold |
| currency | Pill |
| total_amount | Number, with currency suffix |
| total_pyg_normalized | Number `999G999G999G999`, large font |
| lead_time_days | Number "X dias" |
| warranty_months | Number "X meses" or `-` |
| payment_terms | Text |
| anomaly_score | Number with warning icon when >= 0.6 |

Add **Highlights** to color the cells:

- **Best price**: green background on the row with the lowest
  `total_pyg_normalized`.
- **Fastest delivery**: blue background on the row with the lowest
  `lead_time_days`.
- **Anomaly flagged**: amber row when `anomaly_score >= 0.6`.

## Region 2 - Recomendacion (initially hidden)

Big card region styled as the "decision".

Trigger: a button `BTN_RECOMMEND` at the top of the page that runs
the pipeline.

### Button: `Generar recomendacion`

Dynamic Action:

1. Show loading overlay with text "Calculando recomendacion con IA...".
2. Execute Server-side PL/SQL:

```plsql
DECLARE
  l_response    CLOB;
  l_status_code NUMBER;
BEGIN
  APEX_WEB_SERVICE.g_request_headers.DELETE;
  APEX_WEB_SERVICE.g_request_headers(1).name  := 'Content-Type';
  APEX_WEB_SERVICE.g_request_headers(1).value := 'application/json';

  l_response := APEX_WEB_SERVICE.MAKE_REST_REQUEST(
    p_url         => '&BACKEND_URL./api/v1/procurement/requests/'
                     || :P6_REQUEST_ID
                     || '/recommend?tenant_id=' || :TENANT_ID,
    p_http_method => 'POST',
    p_body        => '{}'
  );
  l_status_code := APEX_WEB_SERVICE.g_status_code;

  IF l_status_code = 200 THEN
    :P6_RECOMMENDATION_JSON := l_response;
    APEX_JSON.PARSE(l_response);
    :P6_RECOMMENDED_QUOTATION_ID :=
      APEX_JSON.GET_VARCHAR2('recommendation.recommended_quotation_id');
    :P6_RECOMMENDED_SUPPLIER_ID :=
      APEX_JSON.GET_VARCHAR2('recommendation.recommended_supplier_id');
    :P6_DECISION_BAND :=
      APEX_JSON.GET_VARCHAR2('recommendation.decision_band');
    :P6_COMPOSITE_SCORE :=
      APEX_JSON.GET_NUMBER('recommendation.composite_score');
    :P6_URGENCY_SCORE :=
      APEX_JSON.GET_NUMBER('recommendation.urgency_score');
    :P6_OFFER_SCORE :=
      APEX_JSON.GET_NUMBER('recommendation.offer_score');
    :P6_REASONING_MARKDOWN :=
      APEX_JSON.GET_CLOB('recommendation.reasoning_markdown');
    :P6_WEATHER_RISK := APEX_JSON.GET_NUMBER('weather_risk_score');
    :P6_FX_RATE := APEX_JSON.GET_NUMBER('fx_rate_usd_pyg');

    -- Look up the legal name from the supplier collection prepared
    -- in the page Before Header (same code as page 4).
    SELECT c002
      INTO :P6_RECOMMENDED_SUPPLIER_NAME
      FROM apex_collections
     WHERE collection_name = 'SUPPLIERS_BY_ID'
       AND c001 = :P6_RECOMMENDED_SUPPLIER_ID;
  ELSE
    RAISE_APPLICATION_ERROR(-20001, 'Pipeline falló: ' || l_status_code);
  END IF;
END;
```

3. **Refresh** all P6_* items.
4. **Show** the recommendation region.

### Region body

```html
<div style="background:#fff; border-radius:16px; padding:24px;
            border:2px solid #15803d; box-shadow:0 2px 8px rgba(21,128,61,0.1);">

  <div style="display:flex; align-items:center; gap:16px; margin-bottom:16px;">
    <div style="font-size:1.4rem; font-weight:700; color:#15803d;">
      Recomendacion: &P6_RECOMMENDED_SUPPLIER_NAME.
    </div>
    <div style="padding:4px 12px; border-radius:12px;
                background:#dcfce7; color:#15803d; font-weight:600;">
      &P6_DECISION_BAND.
    </div>
  </div>

  <div style="display:grid; grid-template-columns:repeat(3, 1fr);
              gap:16px; margin-bottom:24px;">

    <div style="text-align:center; padding:16px; background:#f0fdf4; border-radius:12px;">
      <div style="color:#94a3b8; font-size:0.8rem;">SCORE COMPUESTO</div>
      <div style="font-size:2.5rem; font-weight:700; color:#15803d;">
        &P6_COMPOSITE_SCORE.
      </div>
      <div style="color:#475569; font-size:0.85rem;">/ 100</div>
    </div>

    <div style="text-align:center; padding:16px; background:#fef3c7; border-radius:12px;">
      <div style="color:#94a3b8; font-size:0.8rem;">URGENCY SCORE</div>
      <div style="font-size:2.5rem; font-weight:700; color:#a16207;">
        &P6_URGENCY_SCORE.
      </div>
      <div style="color:#475569; font-size:0.85rem;">
        Riesgo climatico: &P6_WEATHER_RISK.
      </div>
    </div>

    <div style="text-align:center; padding:16px; background:#dbeafe; border-radius:12px;">
      <div style="color:#94a3b8; font-size:0.8rem;">OFFER SCORE</div>
      <div style="font-size:2.5rem; font-weight:700; color:#1e40af;">
        &P6_OFFER_SCORE.
      </div>
      <div style="color:#475569; font-size:0.85rem;">
        FX USD/PYG: &P6_FX_RATE.
      </div>
    </div>

  </div>

  <div id="reasoning_markdown" style="background:#f8fafc; padding:16px;
       border-radius:12px; max-height:400px; overflow-y:auto;
       font-family:Inter, sans-serif; line-height:1.6;">
    <em>&P6_REASONING_MARKDOWN.</em>
  </div>

</div>
```

> The reasoning is rendered as plain Markdown text. APEX does not
> auto-render Markdown; for a polished look, run a small JS at page
> load that converts `&P6_REASONING_MARKDOWN.` to HTML using
> `marked.js`. Quick include in the page header:
>
> ```html
> <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
> <script>
>   document.addEventListener('apexreadyend', () => {
>     const el = document.getElementById('reasoning_markdown');
>     if (el && window.marked) el.innerHTML = marked.parse(el.innerText);
>   });
> </script>
> ```

## Region 3 - Generador de mensaje de negociacion

Below the recommendation card.

### Page items

| Item | Type | Label |
|---|---|---|
| `P6_NEGOTIATE_PRICE_PCT` | Number | Mejorar precio (%) |
| `P6_NEGOTIATE_LEAD_TIME` | Number | Reducir plazo a (dias) |
| `P6_NEGOTIATE_TONE` | Radio | cordial / formal / asertivo |

### Button: `Generar mensaje`

Dynamic Action -> Execute PL/SQL:

```plsql
DECLARE
  l_body     CLOB;
  l_response CLOB;
  l_status   NUMBER;
  l_targets  VARCHAR2(500);
BEGIN
  l_targets := '{}';
  IF :P6_NEGOTIATE_PRICE_PCT IS NOT NULL OR :P6_NEGOTIATE_LEAD_TIME IS NOT NULL THEN
    l_targets := '{';
    IF :P6_NEGOTIATE_PRICE_PCT IS NOT NULL THEN
      l_targets := l_targets || '"price_pct": ' || :P6_NEGOTIATE_PRICE_PCT;
    END IF;
    IF :P6_NEGOTIATE_LEAD_TIME IS NOT NULL THEN
      IF LENGTH(l_targets) > 1 THEN l_targets := l_targets || ','; END IF;
      l_targets := l_targets || '"lead_time_days": ' || :P6_NEGOTIATE_LEAD_TIME;
    END IF;
    l_targets := l_targets || '}';
  END IF;

  l_body := '{
    "target_improvements": ' || l_targets || ',
    "tone": "' || NVL(:P6_NEGOTIATE_TONE, 'cordial') || '",
    "tenant_id": "' || :TENANT_ID || '"
  }';

  APEX_WEB_SERVICE.g_request_headers.DELETE;
  APEX_WEB_SERVICE.g_request_headers(1).name  := 'Content-Type';
  APEX_WEB_SERVICE.g_request_headers(1).value := 'application/json';

  l_response := APEX_WEB_SERVICE.MAKE_REST_REQUEST(
    p_url         => '&BACKEND_URL./api/v1/procurement/quotations/'
                     || :P6_RECOMMENDED_QUOTATION_ID || '/negotiate',
    p_http_method => 'POST',
    p_body        => l_body
  );
  l_status := APEX_WEB_SERVICE.g_status_code;

  IF l_status = 200 THEN
    APEX_JSON.PARSE(l_response);
    :P6_NEGOTIATION_TEXT := APEX_JSON.GET_CLOB('message_text');
    :P6_NEGOTIATION_SOURCE := APEX_JSON.GET_VARCHAR2('source');
  ELSE
    RAISE_APPLICATION_ERROR(-20001, 'Negotiator falló: ' || l_status);
  END IF;
END;
```

### Region body

```html
<div style="background:#fff; border-radius:16px; padding:24px; margin-top:24px;
            border:1px solid #e2e8f0;">
  <h3 style="margin-top:0; color:#1e293b;">Mensaje de negociacion</h3>

  <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-bottom:16px;">
    <div>
      <label>Mejorar precio</label>
      <span class="t-Form-itemWrapper">&P6_NEGOTIATE_PRICE_PCT.%</span>
    </div>
    <div>
      <label>Reducir plazo a</label>
      <span class="t-Form-itemWrapper">&P6_NEGOTIATE_LEAD_TIME. dias</span>
    </div>
    <div>
      <label>Tono</label>
      <span class="t-Form-itemWrapper">&P6_NEGOTIATE_TONE.</span>
    </div>
  </div>

  <div style="background:#f8fafc; padding:16px; border-radius:12px;
              white-space:pre-wrap; font-family:Inter; max-height:400px; overflow-y:auto;">
    &P6_NEGOTIATION_TEXT.
  </div>

  <div style="margin-top:8px; color:#94a3b8; font-size:0.85rem;">
    Generado por: &P6_NEGOTIATION_SOURCE.
  </div>

  <div style="margin-top:16px; display:flex; gap:8px;">
    <button class="t-Button" onclick="navigator.clipboard.writeText(document.querySelector('[data-region=\\'message-text\\']').innerText)">
      Copiar al portapapeles
    </button>
    <button class="t-Button t-Button--hot" style="background:#15803d;">
      Marcar como enviado
    </button>
  </div>
</div>
```

## Demo behaviour

This is the 60-second showcase:

1. The page loads and shows the 4 cotizaciones in the comparative table.
2. Click "Generar recomendacion". Loading 3 seconds.
3. The recommendation card appears: Tecnomyl, composite ~65, decision
   band `buy_with_followup` (or `buy_now` depending on weather).
4. The 3 score cards show urgency, offer, composite numerically.
5. The Markdown reasoning is rendered with citations to ML p_on_time,
   weather risk score, and supplier history.
6. Pick "Mejorar precio 4%" and "Reducir plazo 7 dias", click
   "Generar mensaje".
7. The Spanish negotiation email appears, ready to copy or send.

That is the demo. Page 6 alone proves the value proposition.

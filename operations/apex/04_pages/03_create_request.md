# Page 3 - Nueva Solicitud

Form to create a new purchase request. POSTs to
`/api/v1/procurement/requests`.

For the live demo this page is **not the main flow** (the seed
already provides 5 requests). Build it last, after page 6.

## Page properties

- **Page number**: 3
- **Name**: `Nueva solicitud`
- **Title**: `Crear solicitud`

## Form region

Region type: **Form**. Source: leave as `Local Database` initially -
we will use a Process to POST manually.

### Page items

| Item | Type | Label | Notes |
|---|---|---|---|
| `P3_TITLE` | Text Field | Titulo | Required, autocomplete optional |
| `P3_DESCRIPTION` | Textarea | Descripcion | Optional |
| `P3_CATEGORY` | Select List | Categoria | Static LOV: fertilizante, semilla, fitosanitario, maquinaria, repuesto, combustible |
| `P3_TARGET_CROP` | Select List | Cultivo destino | Static LOV: soja, maiz, trigo, sorgo, girasol |
| `P3_TARGET_ZAFRA` | Text Field | Zafra/Campania | Default: `2026/27 primera` |
| `P3_FENOLOGICAL_WINDOW` | Select List | Ventana fenologica | LOV: pre-siembra, siembra, vegetativo, reproductivo, cosecha |
| `P3_TARGET_HECTARES` | Number Field | Hectareas | |
| `P3_DELIVERY_DEPARTMENT` | Select List | Departamento de entrega | LOV: Itapua, Alto Parana, Caaguazu, Canindeyu, San Pedro, Concepcion, ... |
| `P3_TARGET_DELIVERY_DATE` | Date Picker | Fecha limite de entrega | |
| `P3_CURRENT_STOCK_DAYS` | Number Field | Dias de cobertura actual | |
| `P3_URGENCY` | Radio Group | Urgencia | LOV: normal, urgente, critica |
| `P3_BUDGET_CAP` | Number Field | Presupuesto estimado (Gs.) | |
| `P3_WEIGHT_PRICE` | Number Field | Peso precio | Default 40 |
| `P3_WEIGHT_DELIVERY` | Number Field | Peso plazo | Default 30 |
| `P3_WEIGHT_QUALITY` | Number Field | Peso calidad | Default 20 |
| `P3_WEIGHT_TERMS` | Number Field | Peso condiciones | Default 10 |
| `P3_ITEM_DESCRIPTION` | Text Field | Item descripcion | |
| `P3_ITEM_QUANTITY` | Number Field | Cantidad | |
| `P3_ITEM_UNIT` | Select List | Unidad | LOV: kg, ton, litro, unidad |
| `P3_WEIGHTS_TOTAL` | Display Only | Suma de pesos | Computed |

### Dynamic action: live weight sum

On change of any of `P3_WEIGHT_*`:

```javascript
var total = parseInt($v('P3_WEIGHT_PRICE')||0)
          + parseInt($v('P3_WEIGHT_DELIVERY')||0)
          + parseInt($v('P3_WEIGHT_QUALITY')||0)
          + parseInt($v('P3_WEIGHT_TERMS')||0);
$s('P3_WEIGHTS_TOTAL', total + ' / 100');
$x('P3_WEIGHTS_TOTAL').style.color = total === 100 ? '#15803d' : '#b91c1c';
```

### Buttons

- `Guardar borrador` - submit page, runs the create process with
  status=draft.
- `Publicar solicitud` - same, status=in_quoting.

## Process - "Create Request" (After Submit)

Type: **Execute Code (PL/SQL)** that calls the REST source.

```plsql
DECLARE
  l_response_clob CLOB;
  l_request_body  CLOB;
  l_status_code   NUMBER;
BEGIN
  l_request_body := APEX_JSON.STRINGIFY(
    APEX_JSON.parse_to_clob(
      '{
        "tenant_id": "' || :TENANT_ID || '",
        "team_id": "' || :TEAM_ID || '",
        "requested_by": "' || :G_USER_ID || '",
        "title": "' || REPLACE(:P3_TITLE, '"', '\"') || '",
        "description": "' || REPLACE(NVL(:P3_DESCRIPTION,''), '"', '\"') || '",
        "category": "' || NVL(:P3_CATEGORY, 'otro') || '",
        "urgency": "' || NVL(:P3_URGENCY, 'normal') || '",
        "currency": "PYG",
        "target_delivery_date": "' || TO_CHAR(:P3_TARGET_DELIVERY_DATE, 'YYYY-MM-DD') || '",
        "target_crop": "' || NVL(:P3_TARGET_CROP, '') || '",
        "target_zafra": "' || NVL(:P3_TARGET_ZAFRA, '') || '",
        "fenological_window": "' || NVL(:P3_FENOLOGICAL_WINDOW, '') || '",
        "target_hectares": ' || NVL(TO_CHAR(:P3_TARGET_HECTARES), 'null') || ',
        "delivery_department": "' || NVL(:P3_DELIVERY_DEPARTMENT, '') || '",
        "current_stock_days": ' || NVL(TO_CHAR(:P3_CURRENT_STOCK_DAYS), 'null') || ',
        "criteria_weights": {
          "price": ' || NVL(TO_CHAR(:P3_WEIGHT_PRICE), '40') || ',
          "delivery": ' || NVL(TO_CHAR(:P3_WEIGHT_DELIVERY), '30') || ',
          "quality": ' || NVL(TO_CHAR(:P3_WEIGHT_QUALITY), '20') || ',
          "terms": ' || NVL(TO_CHAR(:P3_WEIGHT_TERMS), '10') || '
        },
        "items": [
          {
            "description": "' || :P3_ITEM_DESCRIPTION || '",
            "quantity": ' || :P3_ITEM_QUANTITY || ',
            "unit": "' || :P3_ITEM_UNIT || '"
          }
        ]
      }'
    )
  );

  APEX_WEB_SERVICE.g_request_headers(1).name  := 'Content-Type';
  APEX_WEB_SERVICE.g_request_headers(1).value := 'application/json';

  l_response_clob := APEX_WEB_SERVICE.MAKE_REST_REQUEST(
    p_url         => '&BACKEND_URL./api/v1/procurement/requests',
    p_http_method => 'POST',
    p_body        => l_request_body
  );
  l_status_code := APEX_WEB_SERVICE.g_status_code;

  IF l_status_code BETWEEN 200 AND 299 THEN
    APEX_JSON.PARSE(l_response_clob);
    APEX_UTIL.SET_SESSION_STATE('P3_NEW_REQUEST_ID', APEX_JSON.GET_VARCHAR2('request_id'));
  ELSE
    RAISE_APPLICATION_ERROR(-20001, 'Backend error ' || l_status_code || ': ' || l_response_clob);
  END IF;
END;
```

After this process succeeds, branch to page 4 with
`P4_REQUEST_ID = &P3_NEW_REQUEST_ID.`.

> Tip: APEX's manual JSON building gets verbose. The cleaner path is
> to use the REST Data Source CRUD operation, but for fields like
> nested `criteria_weights` and `items`, manual is more reliable.
> Spend at most 30 minutes on this page; if it does not work, ship a
> static "Create" form that opens an alert with the JSON to paste
> into Swagger UI for the demo.

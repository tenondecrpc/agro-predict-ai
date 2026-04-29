# Page 5 - Upload Quotation (LLM Extractor)

Lets the buyer paste raw quotation text (or a transcribed PDF) and
have the LLM extractor (`POST /quotations/extract`) return a
structured preview the buyer can edit and confirm.

For the demo, this page is the "wow" moment for the IA extractor.
Build it after the page 6 hero is solid.

## Page properties

- **Page number**: 5
- **Name**: `Cargar cotizacion`
- **Page item P5_REQUEST_ID**: Hidden, from URL.

## Page items

| Item | Type | Label | Notes |
|---|---|---|---|
| `P5_SUPPLIER_ID` | Select List | Proveedor | LOV from `RDS_SUPPLIERS_LIST` |
| `P5_RAW_TEXT` | Textarea | Texto crudo de la cotizacion | 12 rows |
| `P5_EXTRACTED_JSON` | Hidden | Result of the extractor call |
| `P5_TOTAL_AMOUNT` | Number | Total | Filled from extractor |
| `P5_LEAD_TIME_DAYS` | Number | Plazo (dias) | Filled from extractor |
| `P5_VALIDITY_UNTIL` | Date | Validez hasta | Filled from extractor |
| `P5_CURRENCY` | Select List | Moneda | Filled from extractor |
| `P5_WARRANTY_MONTHS` | Number | Garantia (meses) | Filled from extractor |
| `P5_PAYMENT_TERMS` | Text Field | Condiciones de pago | Filled from extractor |
| `P5_EXTRACTION_CONFIDENCE` | Display Only | Confianza | Show as percentage |
| `P5_EXTRACTION_SOURCE` | Display Only | Origen | `llm` or `fallback` |

## Region 1 - Pegar texto

Static Content with the textarea (item `P5_RAW_TEXT`) plus a button
"Procesar con IA" that fires a Dynamic Action.

Sample text the demo can paste (so the LLM does not need to be on
during a live demo):

```
Cooperativa Yguazu
Atencion: Sra Ana Rojas

Cotizacion T-2026-045
Fecha: 28 de abril 2026
Validez: 30 dias

Producto: Urea granulada 46% N
Origen: Egipto
Presentacion: bolsa 50kg
Cantidad ofertada: 800.000 kg (16.000 bolsas)
Precio unitario: USD 28.50 por bolsa
Tipo de cambio referencia: 7.400 PYG/USD

Total: USD 456.000 (mas IVA 5%)
Incoterm: CIF Yguazu, Itapua
Plazo de entrega: 10 dias desde firma de orden
Forma de pago: 30 dias post-entrega
Garantia de calidad: 12 meses, certificado ISO 9001 incluido
Descuento por volumen: 3.5% para mas de 10.000 bolsas

Tecnomyl S.A.
RUC 80012345-6
ventas@tecnomyl.com.py
```

## Dynamic Action - "Procesar con IA"

Trigger: Click on button `BTN_EXTRACT`.

Action 1: **Show** loading region.

Action 2: **Execute Server-side Code** (PL/SQL) -

```plsql
DECLARE
  l_request_body CLOB;
  l_response     CLOB;
  l_status_code  NUMBER;
BEGIN
  l_request_body := '{
    "raw_text": ' || APEX_JSON.STRINGIFY(:P5_RAW_TEXT) || ',
    "request_id": "' || :P5_REQUEST_ID || '",
    "tenant_id": "' || :TENANT_ID || '"
  }';

  APEX_WEB_SERVICE.g_request_headers.DELETE;
  APEX_WEB_SERVICE.g_request_headers(1).name  := 'Content-Type';
  APEX_WEB_SERVICE.g_request_headers(1).value := 'application/json';

  l_response := APEX_WEB_SERVICE.MAKE_REST_REQUEST(
    p_url         => '&BACKEND_URL./api/v1/procurement/quotations/extract',
    p_http_method => 'POST',
    p_body        => l_request_body
  );
  l_status_code := APEX_WEB_SERVICE.g_status_code;

  IF l_status_code = 200 THEN
    APEX_JSON.PARSE(l_response);
    :P5_EXTRACTED_JSON := l_response;
    :P5_TOTAL_AMOUNT := APEX_JSON.GET_NUMBER('total_amount');
    :P5_LEAD_TIME_DAYS := APEX_JSON.GET_NUMBER('lead_time_days');
    :P5_VALIDITY_UNTIL := TO_DATE(APEX_JSON.GET_VARCHAR2('validity_until_iso'), 'YYYY-MM-DD');
    :P5_CURRENCY := APEX_JSON.GET_VARCHAR2('currency');
    :P5_WARRANTY_MONTHS := APEX_JSON.GET_NUMBER('warranty_months');
    :P5_PAYMENT_TERMS := APEX_JSON.GET_VARCHAR2('payment_terms');
    :P5_EXTRACTION_CONFIDENCE := TO_CHAR(APEX_JSON.GET_NUMBER('extraction_confidence') * 100) || '%';
    :P5_EXTRACTION_SOURCE := APEX_JSON.GET_VARCHAR2('extraction_source');
  ELSE
    RAISE_APPLICATION_ERROR(-20001, 'Extractor falló: ' || l_status_code);
  END IF;
END;
```

Action 3: **Refresh** the page items (so the extracted values appear
in the form).

Action 4: **Hide** loading region.

## Region 2 - Preview de la extraccion (initially hidden)

Form region showing the editable extracted fields (P5_TOTAL_AMOUNT,
P5_LEAD_TIME_DAYS, etc.). Hidden until P5_EXTRACTED_JSON is non-null.

Add a banner at the top:

```html
<div style="background:#dcfce7; border-left:4px solid #15803d;
           padding:12px 16px; margin-bottom:16px; border-radius:8px;">
  <strong>Extraido por IA</strong> - confianza
  <strong>&P5_EXTRACTION_CONFIDENCE.</strong>,
  origen <em>&P5_EXTRACTION_SOURCE.</em>.
  Verifique los datos antes de confirmar.
</div>
```

## Confirm button

`Confirmar y guardar` triggers another PL/SQL process that POSTs to
`/api/v1/procurement/quotations` with the extracted + edited values.
After success, redirect to page 4.

The body template:

```plsql
l_request_body := '{
  "tenant_id": "' || :TENANT_ID || '",
  "request_id": "' || :P5_REQUEST_ID || '",
  "supplier_id": "' || :P5_SUPPLIER_ID || '",
  "created_by": "' || :G_USER_ID || '",
  "currency": "' || :P5_CURRENCY || '",
  "includes_iva": false,
  "payment_terms": "' || :P5_PAYMENT_TERMS || '",
  "total_amount": ' || :P5_TOTAL_AMOUNT || ',
  "lead_time_days": ' || :P5_LEAD_TIME_DAYS || ',
  "validity_until": "' || TO_CHAR(:P5_VALIDITY_UNTIL, 'YYYY-MM-DD') || '",
  "warranty_months": ' || NVL(TO_CHAR(:P5_WARRANTY_MONTHS), 'null') || ',
  "items": []
}';
```

## Demo behaviour

- Click "Cargar cotizacion" from page 4.
- Paste the prepared text. Click "Procesar con IA".
- 2-4 second loading. Form fills in: total USD 456000, lead time 10
  days, validez 30 dias, garantia 12 meses, etc.
- Confidence badge shows 85%, source `llm`. (If the LLM is off, it
  falls back; demo presenter says "and even when the LLM is off, the
  parser fills in totals + lead time deterministically".)
- Click "Confirmar y guardar". Returns to page 4 with 5 quotations
  now (or the same 4 if you skip this step).

> If running short, the demo can skip page 5 entirely. The seeded
> data already shows 4 quotations on page 4. The page 6 hero is more
> important than this one.

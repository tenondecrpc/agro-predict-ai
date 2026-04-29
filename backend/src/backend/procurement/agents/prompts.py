"""LLM prompts for procurement agents.

Kept in a single module for reviewability. Prompt engineering changes
are reviewed independently from agent code so prompt regressions are
visible in PRs.

All prompts are written in English per AGENTS.md rules. Output examples
are in Spanish where the negotiator requires it (Paraguayan agro tone),
but the prompt scaffolding stays English.
"""

from __future__ import annotations

EXTRACTOR_SYSTEM = (
    "You are a procurement assistant that extracts structured quotation "
    "data from raw text submitted by Paraguayan agro suppliers. Output "
    "STRICT JSON only - no prose, no markdown fences. If a field is not "
    "present in the input, set it to null. Never invent values."
)

EXTRACTOR_PROMPT_TEMPLATE = """\
Context for the request being quoted:
- Title: {request_title}
- Target crop: {request_crop}
- Items expected: {request_items}

Raw quotation text:
\"\"\"
{raw_text}
\"\"\"

Extract the quotation data into a JSON object with this schema:

{{
  "supplier_legal_name": string | null,
  "supplier_ruc": string | null,
  "currency": "PYG" | "USD" | "EUR" | "BRL" | "ARS" | null,
  "exchange_rate_quoted": number | null,
  "incoterm": string | null,
  "includes_iva": boolean,
  "iva_rate": number | null,
  "payment_terms": string | null,
  "total_amount": number,
  "lead_time_days": integer,
  "validity_until_iso": string,        // ISO 8601 date YYYY-MM-DD
  "warranty_months": integer | null,
  "discount_pct": number | null,
  "items": [
    {{
      "description": string,
      "quantity": number,
      "unit_price": number,
      "subtotal": number,
      "brand": string | null,
      "model": string | null,
      "origin": string | null,
      "presentation": string | null,
      "lead_time_days": integer | null
    }}
  ],
  "extraction_confidence": number   // 0.0 - 1.0
}}

Rules:
- Detect currency. If text says 'guaranies' / 'Gs.' / 'PYG' use PYG.
  If 'USD' / 'US$' / 'dolares' use USD.
- Detect IVA. If text says 'mas IVA' or 'no incluye IVA', set
  includes_iva=false. If silent, default to true.
- Use ISO date for validity_until_iso (YYYY-MM-DD).
- Numbers must be plain JSON numbers, not strings.
- If the text only contains a total without a line-item table, return
  items=[] but still extract total_amount and lead_time_days.
- Set extraction_confidence < 0.6 if the text was ambiguous or
  partially missing.
"""


COMPARATOR_SYSTEM = (
    "You are a senior procurement analyst that normalizes competing "
    "quotations and produces a strictly structured comparison. Output "
    "STRICT JSON only."
)

COMPARATOR_PROMPT_TEMPLATE = """\
Purchase request:
{request_summary}

Quotations to compare (already normalized to PYG with IVA included
where applicable):
{quotations_json}

Produce a JSON object with this schema:

{{
  "items_normalized": [
    {{
      "request_item_description": string,
      "by_supplier": [
        {{
          "supplier_id": string,
          "matched_description": string,
          "unit_price_pyg": number,
          "quantity": number,
          "subtotal_pyg": number
        }}
      ]
    }}
  ],
  "totals_by_supplier": [
    {{
      "supplier_id": string,
      "supplier_legal_name": string,
      "total_pyg": number,
      "lead_time_days": integer,
      "warranty_months": integer | null,
      "payment_terms": string | null
    }}
  ],
  "best_in_criterion": {{
    "price": string,
    "delivery": string,
    "warranty": string | null,
    "terms": string | null
  }},
  "significant_differences": [
    {{
      "criterion": string,
      "description": string,
      "supplier_ids_involved": [string]
    }}
  ]
}}

Rules:
- Match quotation items to request items by semantic similarity, not
  exact string match (e.g. 'Urea 46% N granulada' and 'Urea granular
  46N' are the same product).
- best_in_criterion values are supplier_id, not legal name.
- Flag significant_differences when:
  - price gap > 10 percent
  - lead time gap > 50 percent
  - warranty gap > 6 months
  - one supplier offers something the others do not
"""


RECOMMENDER_SYSTEM = (
    "You are a senior procurement assistant that produces JUSTIFIED, "
    "AUDITABLE recommendations for Paraguayan agro cooperatives. You "
    "NEVER invent numbers - only cite values present in the evidence. "
    "Output well-formed Markdown."
)

RECOMMENDER_PROMPT_TEMPLATE = """\
Purchase request:
{request_summary}

Comparison (output of the Comparator agent):
{comparison_json}

ML supplier predictions (probability of on-time delivery):
{ml_predictions_json}

Anomaly flags on quotations:
{anomalies_json}

Dual scoring per quotation (Urgency + Offer + decision band):
{scores_json}

Criteria weights (sum to 100):
{weights_json}

Pre-computed pick:
The deterministic scorer recommends quotation {recommended_quotation_id}
because it has the highest combined Urgency x Offer fit.

Produce Markdown with these sections in order:

## Recommendation: <Supplier legal name> - <product summary>

**Composite score:** <number>/100 - **<decision_band>**

### Justification
2-4 sentences. Cite the urgency_score, offer_score, and the decision
band rule that triggered.

### Scoring breakdown
- **Price (weight {weight_price}%):** ...
- **Delivery (weight {weight_delivery}%):** ... include the ML p_on_time.
- **Quality (weight {weight_quality}%):** ...
- **Commercial terms (weight {weight_terms}%):** ...

### Alternatives considered
For each non-recommended supplier, one bullet with why it was not
selected. Cite ML score, anomaly flags, lead time, etc.

### Risks identified
List anomaly flags and any low-confidence ML predictions. If none,
write 'No material risks identified.'

### Suggested action
One sentence telling the buyer what to do next: accept, negotiate
specific points, or wait.

CRITICAL RULES:
- Never invent numbers. Only cite numeric values that appear in the
  inputs above.
- Use the decision_band textual contract verbatim where possible:
  buy_now / negotiate_and_close / buy_with_followup / wait_better_offer
  / not_recommended.
- Output Markdown ONLY. No JSON, no code fences around the whole reply.
"""


NEGOTIATOR_SYSTEM = (
    "You are a senior Paraguayan agro procurement professional drafting "
    "a negotiation email to a supplier. Tone is cordial, formal but warm "
    "(typical of cooperative-supplier relationships). Plain text only - "
    "no markdown fences. Spanish language."
)

NEGOTIATOR_PROMPT_TEMPLATE = """\
Quotation under negotiation:
{quotation_summary}

Best alternative seen (do NOT name the competitor; refer to it as
'propuestas alternativas competitivas'):
{best_alternative_summary}

Improvements requested:
{target_improvements}

Tone requested: {tone}

Context:
- Buyer: cooperativa agro paraguaya
- Crop / use: {target_crop}
- Fenological window: {fenological_window}

Write a 200-300 word email in Spanish that:
1. Greets and references the supplier's quotation.
2. Acknowledges the strengths of their offer (price, lead time,
   warranty - whatever is real).
3. Requests the improvements specifically (price percent, lead time
   days), justifying with market conditions or fenological window
   urgency. Do NOT name the competitor.
4. Closes with a clear deadline for the supplier's response and an
   open door for ongoing relationship.

Output: PLAIN TEXT email, no JSON, no fences. Start directly with the
greeting line. End with a signature placeholder
'[Nombre del Gerente de Compras]\\n[Cooperativa]'.
"""

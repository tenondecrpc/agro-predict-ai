# 05 - Demo Script (90 seconds)

The narrative the presenter follows during the live demo. Time
budget: 90 seconds. Practice it twice before the event.

```
[0:00] OPENING (10s)
"Los procesos de compra empresariales en el sector cooperativo agro
paraguayo pierden 4 a 8 horas semanales transcribiendo cotizaciones,
comparando manualmente, justificando decisiones y redactando mensajes.
AgroBuy es un copiloto inteligente sobre Oracle APEX que automatiza
ese ciclo completo."

[0:10] LOG IN AS COMPRADOR (5s)
- Open page 1 (Login).
- Click "Comprador - Ana Rojas".
- Lands on page 2 (Inbox).

[0:15] INBOX (8s)
- "Cinco solicitudes activas para Cooperativa Yguazu, Itapua,
  campania 2026/27."
- Highlight the urea zafra-soja request - urgency CRITICA.
- Click on the title.

[0:23] REQUEST DETAIL (10s)
- Page 4 shows the request and 4 cotizaciones recibidas.
- "Cuatro proveedores cotizaron: Tecnomyl, Agrofertil, Atlantic,
  Ciabay. Cada uno con condiciones distintas - moneda, plazo,
  garantia."
- Click "Comparar y recomendar".

[0:33] COMPARATIVE TABLE (8s)
- Page 6 region 1: 4 rows side-by-side, normalized to PYG with FX
  del dia.
- Highlight: "Atlantic es el mas barato pero su precio cae 18% bajo
  la banda historica - el sistema marca alerta."
- Click "Generar recomendacion".

[0:41] AI PIPELINE EXECUTING (3s)
- Loading state. 2-3 seconds.

[0:44] RECOMMENDATION (15s)
- Region 2 reveals: Recomendacion Tecnomyl, score 65/100, banda
  buy_with_followup.
- Three score cards visible: composite, urgency, offer.
- "Urgency es alto porque el clima muestra riesgo de sequia segun
  Open-Meteo, y el stock cubre solo 6 dias."
- "Offer score combina prediccion ML de cumplimiento - Tecnomyl tiene
  92% de probabilidad de cumplir plazo basado en 22 entregas previas
  con ISO 9001."
- Scroll down to see the markdown justification with explicit citations
  to numbers.

[0:59] NEGOTIATION (15s)
- Region 3: pick "Mejorar precio 4%, plazo 7 dias, tono cordial".
- Click "Generar mensaje".
- 2 second loading.
- The Spanish email appears: 250 palabras, tono profesional agro PY,
  cita "propuestas alternativas competitivas" sin nombrar al
  competidor.
- "El mensaje esta listo para enviar. Ahorro de 20-30 minutos de
  redaccion por cotizacion."

[1:14] DASHBOARD / WRAP-UP (16s) - OPTIONAL
- Switch role to Director (URL bar or page 1).
- Show executive dashboard: monto comprado, cycle time, top suppliers.
- "Gs. 1.250M comprado este mes, 18% ahorro vs presupuesto, cycle
  time bajo de 5 a 3 dias."

[1:30] CLOSING (10s)
- "Cuatro agentes LLM, modelo ML predictivo entrenado, scoring dual
  Urgency-Offer con datos climaticos en vivo, todo sobre Oracle APEX
  como UI principal. Demo open source en GitHub."

[1:40] END
```

## Pre-demo checklist (30 minutes before)

- [ ] Docker Compose up (`docker compose ps` shows postgres + redis + worker healthy)
- [ ] Backend running on `0.0.0.0:8000`
- [ ] ngrok running, URL copied to APEX `BACKEND_URL` substitution
- [ ] Re-seed if anything was modified: `python -m backend.procurement.fixtures.seed`
- [ ] Sanity test: `curl $BACKEND_PUBLIC_URL/api/v1/procurement/requests?tenant_id=tenant-yguazu` returns 5 requests
- [ ] Fire one warm-up call to the LLM endpoint to avoid cold start during demo
- [ ] Browser tab on page 1 ready to go
- [ ] Backup video recording prepared in case live fails

## Risk mitigations

| Risk | Mitigation |
|---|---|
| ngrok URL rotated | Update `&BACKEND_URL.` substitution in APEX, save, refresh page |
| LLM call slow / fails | The fallback path on every agent ensures the pipeline still completes - source field will read `fallback` |
| Network drops mid-demo | Backup video, plus the seeded data lets you walk through pages 1-4 without API calls |
| APEX session times out | Login again as Comprador (page 1) - the application items reset cleanly |

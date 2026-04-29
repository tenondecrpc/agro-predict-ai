# Page 1 - Login / Mock Role Selector

A simple landing page that lets the demo presenter switch roles
without dealing with real authentication.

## Page properties

- **Page number**: 1
- **Name**: `Login`
- **Page Mode**: Normal
- **Navigation Menu**: Hide
- **Authentication**: `Page is Public`

## Body

Single Static Content region with this HTML:

```html
<div style="max-width:560px; margin:80px auto; text-align:center;">
  <h1 style="color:#15803d; font-size:2.5rem; margin-bottom:8px;">AgroBuy</h1>
  <p style="color:#475569; font-size:1.05rem; margin-bottom:8px;">
    Copiloto inteligente de compras para cooperativas agro paraguayas
  </p>
  <p style="color:#94a3b8; font-size:0.9rem; margin-bottom:48px;">
    Cooperativa Yguazu &middot; Itapua, Paraguay &middot; Campania 2026/27
  </p>

  <p style="color:#1e293b; font-weight:600; margin-bottom:24px;">
    Seleccione su rol
  </p>

  <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:16px;">
    &P1_ROLE_BUTTONS.
  </div>
</div>
```

## Page item P1_ROLE_BUTTONS (Display Only)

Add a hidden item `P1_ROLE_BUTTONS` of type **Display Only**, then
in the **Source** tab paste this PL/SQL Function Body Returning:

```plsql
DECLARE
  l_html VARCHAR2(4000);
BEGIN
  l_html := '
  <a href="f?p=&APP_ID.:2:&APP_SESSION.::NO::G_ROLE,G_USER_NAME,G_USER_ID:solicitante,Carlos Lopez,solicitante@yguazu.coop.py"
     class="t-Button t-Button--hot" style="padding:24px; height:auto;">
    <span style="font-size:2rem; display:block;">@</span>
    <span style="font-weight:600;">Solicitante</span>
    <span style="display:block; color:#475569; font-size:0.85rem;">Carlos Lopez</span>
  </a>
  <a href="f?p=&APP_ID.:2:&APP_SESSION.::NO::G_ROLE,G_USER_NAME,G_USER_ID:comprador,Ana Rojas,ana.rojas@yguazu.coop.py"
     class="t-Button t-Button--hot" style="padding:24px; height:auto; background:#15803d;">
    <span style="font-size:2rem; display:block;">+</span>
    <span style="font-weight:600;">Comprador</span>
    <span style="display:block; color:#fff; font-size:0.85rem;">Ana Rojas</span>
  </a>
  <a href="f?p=&APP_ID.:2:&APP_SESSION.::NO::G_ROLE,G_USER_NAME,G_USER_ID:aprobador,Luis Mendez,aprobador@yguazu.coop.py"
     class="t-Button t-Button--hot" style="padding:24px; height:auto;">
    <span style="font-size:2rem; display:block;">#</span>
    <span style="font-weight:600;">Consejo</span>
    <span style="display:block; color:#475569; font-size:0.85rem;">Luis Mendez</span>
  </a>
  <a href="f?p=&APP_ID.:2:&APP_SESSION.::NO::G_ROLE,G_USER_NAME,G_USER_ID:director,Jose Benitez,director@yguazu.coop.py"
     class="t-Button t-Button--hot" style="padding:24px; height:auto;">
    <span style="font-size:2rem; display:block;">$</span>
    <span style="font-weight:600;">Director</span>
    <span style="display:block; color:#475569; font-size:0.85rem;">Jose Benitez</span>
  </a>
  ';
  RETURN l_html;
END;
```

The link uses APEX's `f?p=` URL convention to set the application
items `G_ROLE`, `G_USER_NAME`, `G_USER_ID` and redirect to page 2.

## Notes

- Keep the demo simple. The Comprador button is the primary one
  (use it for the main flow); the others are visual proof of the
  multi-role coherence the brief evaluates.
- For accessibility (brief criterion): each role badge has a label
  text in addition to the icon.

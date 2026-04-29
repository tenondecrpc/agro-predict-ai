# 02 - Workspace and Application Shell

## Create the application

In the APEX App Builder:

1. Click **Create**.
2. Choose **New Application**.
3. Fill in:
   - **Name**: `AgroBuy - Copiloto Compras Agro`
   - **Appearance** -> Theme Style: `Vita - Light`
   - **Appearance** -> Application Icon: pick a leaf or sprout icon if available; otherwise a green circle.
4. Under **Features**, enable: `Theme Style Selection`, `Activity Reporting`, `Configuration Management`. Leave everything else off (less clutter).
5. Click **Create Application**.

You should now have an app with a default home page. Delete the
default home page; we will replace it.

## Application items (global state)

App items hold the mock role / user / tenant context. Create them at
**Shared Components** -> **Application Items**:

| Name | Scope | Purpose |
|---|---|---|
| `G_TENANT_ID` | Application | Always `tenant-yguazu` for the demo. |
| `G_TEAM_ID` | Application | Always `team-compras` for the demo. |
| `G_USER_ID` | Application | Buyer email (`ana.rojas@yguazu.coop.py`). |
| `G_USER_NAME` | Application | Buyer display name. |
| `G_ROLE` | Application | `solicitante` / `comprador` / `aprobador` / `director`. |
| `G_BACKEND_URL` | Application | The current ngrok URL. |

## Application substitution strings

**Shared Components** -> **Application Definition** -> **Substitutions**:

| Substitution String | Substitution Value |
|---|---|
| `BACKEND_URL` | `https://your-ngrok.ngrok-free.app` |
| `TENANT_ID` | `tenant-yguazu` |
| `TEAM_ID` | `team-compras` |

These let you reference `&BACKEND_URL.` inside SQL and PL/SQL without
hardcoding it across pages.

## Theme tweaks

**Shared Components** -> **Themes** -> **Vita** -> Edit:

- Primary color: `#15803d` (green-700)
- Accent color: `#a16207` (amber-700)
- Border radius: 12px
- Font: Inter (the default Vita stack works; pick `Open Sans` if Inter is unavailable).

## Navigation menu

**Shared Components** -> **Lists** -> **Desktop Navigation Menu**.
Replace the default items with:

| Label | Target | Image (optional) |
|---|---|---|
| Inicio | Page 2 (Inbox) | fa-home |
| Nueva solicitud | Page 3 (Create) | fa-plus-circle |
| Catalogo proveedores | Page 7 (optional, can skip) | fa-truck |
| Dashboard | Page 8 (optional) | fa-chart-line |

Hide the menu on Page 1 (login) - in Page 1's properties set
`Navigation Menu`: `Hide`.

## Header bar (across all pages)

**Shared Components** -> **Templates** -> **Page Templates** -> the
default template. In the page header HTML, add a region or just hand-
edit:

```html
<div class="t-Header-branding">
  <a href="f?p=&APP_ID.:2:&APP_SESSION." class="t-Header-logo-link">
    <span class="t-Header-logo-text">AgroBuy</span>
  </a>
  <span style="color:#475569; margin-left:8px; font-size:0.85em;">
    Cooperativa Yguazu &middot; Itapua, Paraguay &middot; Campania 2026/27
  </span>
</div>
<div class="t-Header-nav">
  <span class="t-Button t-Button--noUI" style="color:#15803d;">
    Rol: &G_ROLE. &middot; &G_USER_NAME.
  </span>
</div>
```

> The `&G_ROLE.` and `&G_USER_NAME.` references render the
> application-item values verbatim.

You are ready to wire REST Data Sources.

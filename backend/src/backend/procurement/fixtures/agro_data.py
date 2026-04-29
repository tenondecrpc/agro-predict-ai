"""Hardcoded demo dataset for the AgroBuy procurement copilot.

The data is recognizable for a Paraguayan agro audience but uses
synthetic RUCs and contact info. Suppliers are real industry names
shipped as a demo seed; cooperative buyer is "Cooperativa Yguazu".

NOTHING in this file should be assumed to reflect real commercial
relationships, prices, or performance. The numbers are calibrated for
visual demo impact, not market accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class SupplierSeed:
    legal_name: str
    ruc: str
    commercial_name: str
    contact_email: str
    contact_phone: str
    primary_categories: str
    is_importer: bool
    senave_registered: bool
    iso_certified: bool
    primary_origin_countries: str | None
    profile: str  # 'top' | 'mid' | 'bottom' - drives history calibration


SUPPLIERS: list[SupplierSeed] = [
    SupplierSeed(
        legal_name="Tecnomyl S.A.",
        ruc="80012345-6",
        commercial_name="Tecnomyl",
        contact_email="ventas@tecnomyl.com.py",
        contact_phone="+595 71 203400",
        primary_categories="fertilizante,fitosanitario",
        is_importer=True,
        senave_registered=True,
        iso_certified=True,
        primary_origin_countries="EG,RU,CN",
        profile="top",
    ),
    SupplierSeed(
        legal_name="Agrofertil S.A.",
        ruc="80022345-7",
        commercial_name="Agrofertil",
        contact_email="comercial@agrofertil.com.py",
        contact_phone="+595 21 290600",
        primary_categories="fertilizante",
        is_importer=True,
        senave_registered=True,
        iso_certified=True,
        primary_origin_countries="MA,RU,US",
        profile="top",
    ),
    SupplierSeed(
        legal_name="Atlantic Comercio Agroindustrial S.A.",
        ruc="80045678-9",
        commercial_name="Atlantic",
        contact_email="ventas@atlantic.com.py",
        contact_phone="+595 21 555600",
        primary_categories="fertilizante,fitosanitario",
        is_importer=True,
        senave_registered=False,
        iso_certified=False,
        primary_origin_countries="RU,BY",
        profile="bottom",
    ),
    SupplierSeed(
        legal_name="Glymax Paraguay S.A.",
        ruc="80067890-1",
        commercial_name="Glymax",
        contact_email="ventas@glymax.com.py",
        contact_phone="+595 61 587900",
        primary_categories="fitosanitario,fertilizante",
        is_importer=True,
        senave_registered=True,
        iso_certified=False,
        primary_origin_countries="CN,AR",
        profile="mid",
    ),
    SupplierSeed(
        legal_name="Dekalpar S.A.",
        ruc="80078901-2",
        commercial_name="Dekalpar",
        contact_email="info@dekalpar.com.py",
        contact_phone="+595 21 220330",
        primary_categories="semilla",
        is_importer=False,
        senave_registered=True,
        iso_certified=True,
        primary_origin_countries="PY,BR,AR",
        profile="top",
    ),
    SupplierSeed(
        legal_name="Agrotec S.A.",
        ruc="80089012-3",
        commercial_name="Agrotec",
        contact_email="ventas@agrotec.com.py",
        contact_phone="+595 21 415700",
        primary_categories="fitosanitario,maquinaria,semilla",
        is_importer=True,
        senave_registered=True,
        iso_certified=True,
        primary_origin_countries="DE,US,BR",
        profile="mid",
    ),
    SupplierSeed(
        legal_name="BASF Paraguaya S.A.",
        ruc="80090123-4",
        commercial_name="BASF",
        contact_email="ventas.py@basf.com",
        contact_phone="+595 21 600100",
        primary_categories="fitosanitario",
        is_importer=True,
        senave_registered=True,
        iso_certified=True,
        primary_origin_countries="DE,BR",
        profile="top",
    ),
    SupplierSeed(
        legal_name="Ciabay S.A.",
        ruc="80101234-5",
        commercial_name="Ciabay",
        contact_email="ventas@ciabay.com.py",
        contact_phone="+595 21 511000",
        primary_categories="fertilizante,semilla,fitosanitario",
        is_importer=True,
        senave_registered=True,
        iso_certified=False,
        primary_origin_countries="PY,BR,RU",
        profile="mid",
    ),
]


@dataclass(frozen=True)
class CatalogSeed:
    sku_code: str
    name: str
    category: str
    subcategory: str
    standard_unit: str
    typical_presentation: str
    iva_rate: Decimal
    market_price_min_usd: Decimal
    market_price_max_usd: Decimal
    senave_required: bool
    notes: str


AGRO_CATALOG: list[CatalogSeed] = [
    CatalogSeed(
        sku_code="UREA-46N",
        name="Urea granulada 46% N",
        category="fertilizante",
        subcategory="urea",
        standard_unit="kg",
        typical_presentation="bolsa 50kg",
        iva_rate=Decimal("5.00"),
        market_price_min_usd=Decimal("380.00"),
        market_price_max_usd=Decimal("460.00"),
        senave_required=False,
        notes="Precio CIF Asuncion 2025-2026 por tonelada metrica.",
    ),
    CatalogSeed(
        sku_code="MAP-11-52",
        name="Fosfato monoamonico (MAP) 11-52-0",
        category="fertilizante",
        subcategory="map",
        standard_unit="kg",
        typical_presentation="big bag 1 ton",
        iva_rate=Decimal("5.00"),
        market_price_min_usd=Decimal("620.00"),
        market_price_max_usd=Decimal("780.00"),
        senave_required=False,
        notes="Precio CIF Asuncion por tonelada metrica.",
    ),
    CatalogSeed(
        sku_code="KCL-60K",
        name="Cloruro de potasio (KCl) 60% K2O",
        category="fertilizante",
        subcategory="kcl",
        standard_unit="kg",
        typical_presentation="big bag 1 ton",
        iva_rate=Decimal("5.00"),
        market_price_min_usd=Decimal("320.00"),
        market_price_max_usd=Decimal("420.00"),
        senave_required=False,
        notes="Precio CIF Asuncion por tonelada metrica.",
    ),
    CatalogSeed(
        sku_code="GLIFOSATO-48",
        name="Glifosato 48% concentrado soluble",
        category="fitosanitario",
        subcategory="glifosato",
        standard_unit="litro",
        typical_presentation="tambor 200L",
        iva_rate=Decimal("10.00"),
        market_price_min_usd=Decimal("4.20"),
        market_price_max_usd=Decimal("5.80"),
        senave_required=True,
        notes="Registro SENAVE obligatorio.",
    ),
    CatalogSeed(
        sku_code="SOJA-NS-6248",
        name="Soja semilla certificada NS 6248 IPRO",
        category="semilla",
        subcategory="soja semilla",
        standard_unit="kg",
        typical_presentation="bolsa 40kg",
        iva_rate=Decimal("0.00"),
        market_price_min_usd=Decimal("0.95"),
        market_price_max_usd=Decimal("1.35"),
        senave_required=True,
        notes="Variedad IPRO de alta demanda en Itapua y Alto Parana.",
    ),
    CatalogSeed(
        sku_code="ATRAZINA-50",
        name="Atrazina 50% suspension concentrada",
        category="fitosanitario",
        subcategory="atrazina",
        standard_unit="litro",
        typical_presentation="tambor 200L",
        iva_rate=Decimal("10.00"),
        market_price_min_usd=Decimal("3.20"),
        market_price_max_usd=Decimal("4.40"),
        senave_required=True,
        notes="Uso en pre-emergente de maiz.",
    ),
]


@dataclass(frozen=True)
class RequestSeed:
    title: str
    description: str
    category: str
    target_crop: str
    target_zafra: str
    fenological_window: str
    target_hectares: Decimal
    delivery_department: str
    delivery_location: str
    current_stock_days: int
    urgency: str
    target_delivery_offset_days: int  # added to today() at seed time
    item_description: str
    item_quantity: Decimal
    item_unit: str


REQUESTS: list[RequestSeed] = [
    RequestSeed(
        title="Compra de 800 ton urea 46% para zafra soja 26/27",
        description=(
            "Compra anticipada de urea granulada 46% N para distribuir a "
            "socios productores en pre-siembra de soja primera 2026/27. "
            "Plazo critico: ventana fenologica de pre-siembra antes del "
            "15 de septiembre."
        ),
        category="fertilizante",
        target_crop="soja",
        target_zafra="2026/27 primera",
        fenological_window="pre-siembra",
        target_hectares=Decimal("85000"),
        delivery_department="Itapua",
        delivery_location="Deposito central Cooperativa Yguazu",
        current_stock_days=6,
        urgency="critica",
        target_delivery_offset_days=45,
        item_description="Urea granulada 46% N",
        item_quantity=Decimal("16000"),
        item_unit="kg",
    ),
    RequestSeed(
        title="Compra de glifosato 48% para barbecho quimico campaña 26/27",
        description=(
            "Stock de glifosato para barbecho quimico previo a siembra "
            "directa de soja. Distribucion progresiva durante agosto-septiembre."
        ),
        category="fitosanitario",
        target_crop="soja",
        target_zafra="2026/27 primera",
        fenological_window="pre-siembra",
        target_hectares=Decimal("60000"),
        delivery_department="Itapua",
        delivery_location="Deposito Yguazu",
        current_stock_days=12,
        urgency="urgente",
        target_delivery_offset_days=35,
        item_description="Glifosato 48% concentrado soluble",
        item_quantity=Decimal("48000"),
        item_unit="litro",
    ),
    RequestSeed(
        title="Compra de semilla soja certificada NS 6248 IPRO",
        description=(
            "Adquisicion de semilla certificada para siembra directa "
            "campaña 2026/27. Variedad NS 6248 IPRO de alta demanda."
        ),
        category="semilla",
        target_crop="soja",
        target_zafra="2026/27 primera",
        fenological_window="siembra",
        target_hectares=Decimal("28000"),
        delivery_department="Itapua",
        delivery_location="Deposito Yguazu",
        current_stock_days=20,
        urgency="normal",
        target_delivery_offset_days=60,
        item_description="Soja semilla certificada NS 6248 IPRO",
        item_quantity=Decimal("1960000"),
        item_unit="kg",
    ),
    RequestSeed(
        title="Compra de MAP 11-52-0 para fertilizacion de base maiz zafrina",
        description=(
            "Fertilizante de base para siembra de maiz zafrina febrero 2027. "
            "Logistica desde puerto fluvial hacia deposito en Caaguazu."
        ),
        category="fertilizante",
        target_crop="maiz",
        target_zafra="2027 zafrina",
        fenological_window="pre-siembra",
        target_hectares=Decimal("32000"),
        delivery_department="Caaguazu",
        delivery_location="Deposito secundario Coronel Oviedo",
        current_stock_days=18,
        urgency="urgente",
        target_delivery_offset_days=120,
        item_description="Fosfato monoamonico (MAP) 11-52-0",
        item_quantity=Decimal("9600"),
        item_unit="kg",
    ),
    RequestSeed(
        title="Compra de atrazina 50% para control pre-emergente maiz",
        description=(
            "Atrazina para control de malezas pre-emergente en maiz "
            "zafrina. Aplicacion programada febrero-marzo 2027."
        ),
        category="fitosanitario",
        target_crop="maiz",
        target_zafra="2027 zafrina",
        fenological_window="pre-siembra",
        target_hectares=Decimal("32000"),
        delivery_department="Caaguazu",
        delivery_location="Deposito secundario Coronel Oviedo",
        current_stock_days=30,
        urgency="normal",
        target_delivery_offset_days=130,
        item_description="Atrazina 50% suspension concentrada",
        item_quantity=Decimal("64000"),
        item_unit="litro",
    ),
]


@dataclass(frozen=True)
class QuotationSeed:
    request_index: int  # which request this is for
    supplier_legal_name: str  # match against SUPPLIERS
    currency: str
    exchange_rate_quoted: Decimal | None
    incoterm: str | None
    includes_iva: bool
    payment_terms: str
    total_amount_pyg_normalized: Decimal
    total_amount_native: Decimal  # in the quotation's currency
    lead_time_days: int
    validity_offset_days: int
    warranty_months: int | None
    discount_pct: Decimal | None
    item_unit_price: Decimal  # in native currency
    presentation: str | None
    origin: str | None
    note: str | None = None


# 15 quotations across 5 requests (3 per request mostly).
# Calibrated so the demo arc has a clear narrative:
#   Request 0 (urea):  Tecnomyl wins (decent price, fast, ISO);
#                      Atlantic flagged anomaly (price 18% under band);
#                      Agrofertil close second.
QUOTATIONS: list[QuotationSeed] = [
    # === Request 0 - Urea zafra soja ===
    QuotationSeed(
        request_index=0,
        supplier_legal_name="Tecnomyl S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Yguazu",
        includes_iva=False,
        payment_terms="30 dias post-entrega",
        total_amount_pyg_normalized=Decimal("3380000000"),
        total_amount_native=Decimal("456000"),
        lead_time_days=10,
        validity_offset_days=20,
        warranty_months=12,
        discount_pct=Decimal("3.5"),
        item_unit_price=Decimal("28.50"),
        presentation="bolsa 50kg",
        origin="Egipto",
        note="ISO 9001 certificado de origen incluido.",
    ),
    QuotationSeed(
        request_index=0,
        supplier_legal_name="Agrofertil S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Yguazu",
        includes_iva=False,
        payment_terms="45 dias",
        total_amount_pyg_normalized=Decimal("3450000000"),
        total_amount_native=Decimal("466000"),
        lead_time_days=15,
        validity_offset_days=20,
        warranty_months=12,
        discount_pct=None,
        item_unit_price=Decimal("29.10"),
        presentation="bolsa 50kg",
        origin="Marruecos",
        note=None,
    ),
    QuotationSeed(
        request_index=0,
        supplier_legal_name="Atlantic Comercio Agroindustrial S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="FOB Encarnacion",
        includes_iva=False,
        payment_terms="60 dias",
        total_amount_pyg_normalized=Decimal("2900000000"),
        total_amount_native=Decimal("392000"),
        lead_time_days=21,
        validity_offset_days=15,
        warranty_months=None,
        discount_pct=None,
        item_unit_price=Decimal("24.50"),
        presentation="bolsa 50kg",
        origin="Rusia",
        note="Precio agresivo. Verificar concentracion real de N.",
    ),
    QuotationSeed(
        request_index=0,
        supplier_legal_name="Ciabay S.A.",
        currency="PYG",
        exchange_rate_quoted=None,
        incoterm="CIF Yguazu",
        includes_iva=True,
        payment_terms="30 dias",
        total_amount_pyg_normalized=Decimal("3520000000"),
        total_amount_native=Decimal("3520000000"),
        lead_time_days=12,
        validity_offset_days=15,
        warranty_months=6,
        discount_pct=Decimal("2.0"),
        item_unit_price=Decimal("220000"),
        presentation="bolsa 50kg",
        origin="Brasil",
        note=None,
    ),
    # === Request 1 - Glifosato ===
    QuotationSeed(
        request_index=1,
        supplier_legal_name="Glymax Paraguay S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Yguazu",
        includes_iva=False,
        payment_terms="30 dias",
        total_amount_pyg_normalized=Decimal("1800000000"),
        total_amount_native=Decimal("243000"),
        lead_time_days=8,
        validity_offset_days=25,
        warranty_months=6,
        discount_pct=Decimal("4.0"),
        item_unit_price=Decimal("5.06"),
        presentation="tambor 200L",
        origin="China",
        note="Registro SENAVE vigente.",
    ),
    QuotationSeed(
        request_index=1,
        supplier_legal_name="BASF Paraguaya S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Yguazu",
        includes_iva=False,
        payment_terms="60 dias",
        total_amount_pyg_normalized=Decimal("2050000000"),
        total_amount_native=Decimal("277000"),
        lead_time_days=14,
        validity_offset_days=25,
        warranty_months=12,
        discount_pct=None,
        item_unit_price=Decimal("5.77"),
        presentation="tambor 200L",
        origin="Brasil",
        note="Marca Roundup Original DI.",
    ),
    QuotationSeed(
        request_index=1,
        supplier_legal_name="Agrotec S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Yguazu",
        includes_iva=False,
        payment_terms="30 dias",
        total_amount_pyg_normalized=Decimal("1920000000"),
        total_amount_native=Decimal("259000"),
        lead_time_days=12,
        validity_offset_days=20,
        warranty_months=6,
        discount_pct=Decimal("2.5"),
        item_unit_price=Decimal("5.40"),
        presentation="tambor 200L",
        origin="Argentina",
        note=None,
    ),
    # === Request 2 - Soja semilla ===
    QuotationSeed(
        request_index=2,
        supplier_legal_name="Dekalpar S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Yguazu",
        includes_iva=False,
        payment_terms="30 dias",
        total_amount_pyg_normalized=Decimal("17500000000"),
        total_amount_native=Decimal("2365000"),
        lead_time_days=20,
        validity_offset_days=30,
        warranty_months=None,
        discount_pct=Decimal("3.0"),
        item_unit_price=Decimal("1.21"),
        presentation="bolsa 40kg",
        origin="Paraguay",
        note="Lote certificado SENAVE; tasa de germinacion >95%.",
    ),
    QuotationSeed(
        request_index=2,
        supplier_legal_name="Ciabay S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Yguazu",
        includes_iva=False,
        payment_terms="45 dias",
        total_amount_pyg_normalized=Decimal("18100000000"),
        total_amount_native=Decimal("2445000"),
        lead_time_days=25,
        validity_offset_days=30,
        warranty_months=None,
        discount_pct=None,
        item_unit_price=Decimal("1.25"),
        presentation="bolsa 40kg",
        origin="Brasil",
        note=None,
    ),
    QuotationSeed(
        request_index=2,
        supplier_legal_name="Agrotec S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Yguazu",
        includes_iva=False,
        payment_terms="30 dias",
        total_amount_pyg_normalized=Decimal("17900000000"),
        total_amount_native=Decimal("2418000"),
        lead_time_days=18,
        validity_offset_days=30,
        warranty_months=None,
        discount_pct=Decimal("2.0"),
        item_unit_price=Decimal("1.23"),
        presentation="bolsa 40kg",
        origin="Argentina",
        note=None,
    ),
    # === Request 3 - MAP ===
    QuotationSeed(
        request_index=3,
        supplier_legal_name="Agrofertil S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Coronel Oviedo",
        includes_iva=False,
        payment_terms="60 dias",
        total_amount_pyg_normalized=Decimal("4900000000"),
        total_amount_native=Decimal("662000"),
        lead_time_days=18,
        validity_offset_days=30,
        warranty_months=12,
        discount_pct=Decimal("2.5"),
        item_unit_price=Decimal("69.00"),
        presentation="big bag 1 ton",
        origin="EEUU",
        note=None,
    ),
    QuotationSeed(
        request_index=3,
        supplier_legal_name="Tecnomyl S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Coronel Oviedo",
        includes_iva=False,
        payment_terms="30 dias",
        total_amount_pyg_normalized=Decimal("4750000000"),
        total_amount_native=Decimal("641000"),
        lead_time_days=14,
        validity_offset_days=30,
        warranty_months=12,
        discount_pct=Decimal("4.0"),
        item_unit_price=Decimal("66.80"),
        presentation="big bag 1 ton",
        origin="Marruecos",
        note=None,
    ),
    QuotationSeed(
        request_index=3,
        supplier_legal_name="Atlantic Comercio Agroindustrial S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="FOB Asuncion",
        includes_iva=False,
        payment_terms="90 dias",
        total_amount_pyg_normalized=Decimal("4500000000"),
        total_amount_native=Decimal("608000"),
        lead_time_days=28,
        validity_offset_days=20,
        warranty_months=None,
        discount_pct=None,
        item_unit_price=Decimal("63.30"),
        presentation="big bag 1 ton",
        origin="Rusia",
        note="Logistica desde puerto fluvial Asuncion al cliente.",
    ),
    # === Request 4 - Atrazina ===
    QuotationSeed(
        request_index=4,
        supplier_legal_name="Glymax Paraguay S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Coronel Oviedo",
        includes_iva=False,
        payment_terms="30 dias",
        total_amount_pyg_normalized=Decimal("1700000000"),
        total_amount_native=Decimal("230000"),
        lead_time_days=10,
        validity_offset_days=25,
        warranty_months=6,
        discount_pct=Decimal("3.0"),
        item_unit_price=Decimal("3.59"),
        presentation="tambor 200L",
        origin="China",
        note=None,
    ),
    QuotationSeed(
        request_index=4,
        supplier_legal_name="BASF Paraguaya S.A.",
        currency="USD",
        exchange_rate_quoted=Decimal("7400"),
        incoterm="CIF Coronel Oviedo",
        includes_iva=False,
        payment_terms="60 dias",
        total_amount_pyg_normalized=Decimal("1950000000"),
        total_amount_native=Decimal("263000"),
        lead_time_days=14,
        validity_offset_days=25,
        warranty_months=12,
        discount_pct=None,
        item_unit_price=Decimal("4.11"),
        presentation="tambor 200L",
        origin="Brasil",
        note="Marca propia con soporte tecnico incluido.",
    ),
]


def historical_calibration(profile: str) -> tuple[float, float, int]:
    """Return (on_time_rate, mean_delay_days, n_records) for a profile."""
    if profile == "top":
        return 0.92, 1.5, 22
    if profile == "mid":
        return 0.78, 4.0, 18
    return 0.55, 8.0, 15


def synthetic_dates_for_record(
    *, awarded_offset_days: int, lead_time: int, on_time: bool, mean_delay: float
) -> tuple[date, date, date | None, int]:
    """Build (awarded, promised, actual, delay_days) for a history record."""
    today = date.today()
    awarded = today - timedelta(days=awarded_offset_days)
    promised = awarded + timedelta(days=lead_time)
    if on_time:
        return awarded, promised, promised, 0
    delay = max(1, int(round(mean_delay + (awarded_offset_days % 5 - 2) * 0.5)))
    actual = promised + timedelta(days=delay)
    return awarded, promised, actual, delay

"""Real-batch ingestion checks and auditable EKP arithmetic; blank means unknown."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

COST_COMPONENT_FIELDS = (
    "meat_cost_tl", "spice_cost_tl", "casing_cost_tl", "labor_cost_tl",
    "energy_cost_tl", "packaging_cost_tl", "fason_service_cost_tl",
    "inhouse_processing_cost_tl", "overhead_cost_tl", "other_cost_tl",
)
MODEL1_FEATURE_MAP = {
    "Et_girdi_kg": "planned_meat_input_kg",
    "Kuyruk_yagi_girdi_kg": "planned_tail_fat_input_kg",
    "Baharat_girdi_kg": "planned_spice_input_kg",
    "Tuz_girdi_kg": "planned_salt_input_kg",
    "Diger_kucuk_girdi_kg": "planned_other_inputs_kg",
    "Kilif_metre": "planned_casing_m",
    "Et_fiyat_TL_kg": "planned_meat_price_tl_kg",
    "Kuyruk_yagi_fiyat_TL_kg": "planned_tail_fat_price_tl_kg",
    "Baharat_fiyat_TL_kg": "planned_spice_price_tl_kg",
    "Tuz_fiyat_TL_kg": "planned_salt_price_tl_kg",
    "Kilif_fiyat_TL_m": "planned_casing_price_tl_m",
    "Fason_birim_bedel_TL_kg_girdi": "planned_fason_rate_tl_kg_input",
    "Iscilik_maliyeti_TL_saat": "planned_labor_rate_tl_hour",
    "Elektrik_fiyati_TL_kWh": "planned_electricity_rate_tl_kwh",
    "Ambalaj_TL_kg_net_urun": "planned_packaging_rate_tl_kg",
    "Bolge": "planned_region",
    "Recete_profili": "planned_recipe_profile",
    "Isleme_modeli": "planned_process_method",
}
# name, type, unit, required purpose, accepted values, source, measurement time
FIELD_DICTIONARY = [
    ("batch_id","string","id","EKP, traceability, time evaluation","Unique non-empty","MES / production order","Assigned before production"),
    ("source_type","enum","category","Every row","real | synthetic | external_benchmark","Dataset owner","Known at ingestion"),
    ("source_system","string","text","Real-data provenance","Non-empty for real rows","ERP / MES / scale / accounting","At ingestion"),
    ("source_reference","string","text","Real-data provenance","Traceable record ID; no secrets","Source document/system","At ingestion"),
    ("validation_status","enum","category","Evaluation eligibility","pending | validated | rejected","Data steward","After review"),
    ("validated_at","datetime","ISO-8601 timezone","Time-based target availability","Timezone offset required for validated rows","Data steward / audit log","After measurement and before the target is used for model training"),
    ("record_created_at","datetime","ISO-8601 timezone","Required for time-based evaluation availability audit","Timezone offset required","Import/source log","At entry; must precede test-time training cutoff"),
    ("production_started_at","datetime","ISO-8601 timezone","Chronological evaluation","Timezone offset required","MES / batch sheet","Production start"),
    ("production_ended_at","datetime","ISO-8601 timezone","Optional","Timezone offset required","MES / batch sheet","Production end"),
    ("measurement_at","datetime","ISO-8601 timezone","Actual net-output target","Timezone offset required","Calibrated scale record","After production start"),
    ("measurement_method","string","text","Measured net-output provenance","Scale/tare/SOP reference","Measurement record","At weighing"),
    ("loss_measurement_at","datetime","ISO-8601 timezone","Mass balance","Timezone offset required","Scale / process record","At loss measurement"),
    ("loss_measurement_method","string","text","Mass balance","Method/stage reference","Process SOP","At loss measurement"),
    ("losses_complete","boolean","true/false","Mass balance","true | false","Process owner","After production"),
    ("currency","enum","ISO code","EKP","TRY only; no implicit FX","Accounting record","Cost period"),
    ("cost_period","enum","category","EKP","per_batch only","Accounting policy","Cost period"),
    ("cost_period_start","datetime","ISO-8601 timezone","Optional cost audit","Timezone offset required","Ledger","Cost period"),
    ("cost_period_end","datetime","ISO-8601 timezone","Optional cost audit","Timezone offset required","Ledger","Cost period"),
    ("recipe_code","string","text","Optional context","Source-system value","Approved recipe","Frozen plan"),
    ("recipe_name","string","text","Optional context","Source-system value","Approved recipe","Frozen plan"),
    ("process_method","string","text","Optional context","Source-system value","Production order","Plan or actual; distinguish"),
    ("meat_type","string","text","Optional context","Source-system value","Recipe / purchasing","Frozen plan"),
    ("meat_input_kg","number","kg","Optional actual input","Finite >= 0","Batch weighing","Consumption"),
    ("meat_unit_price_tl_kg","number","TL/kg","Optional cost detail","Finite >= 0","Invoice / ledger","Cost period"),
    ("meat_cost_tl","number","TL/batch","Cost breakdown","Finite >= 0; disjoint","Invoice / ledger","Cost period"),
    ("spice_input_kg","number","kg","Optional actual input","Finite >= 0","Batch weighing","Consumption"),
    ("spice_details_json","json string","kg, TL/kg, TL","Optional detail","Per-spice quantity × unit price = item cost; aggregate is included once in spice_cost_tl","Recipe / invoice","Plan/actual timing must be explicit"),
    ("spice_details_complete","boolean","true/false","Spice detail reconciliation","true requires item quantities, unit prices, costs, and aggregate spice_cost_tl","Recipe / invoice owner","At cost close"),
    ("spice_cost_tl","number","TL/batch","Cost breakdown","Finite >= 0; disjoint","Invoice / ledger","Cost period"),
    ("casing_quantity_m","number","m","Optional actual input","Finite >= 0","Batch sheet","Consumption"),
    ("casing_cost_tl","number","TL/batch","Cost breakdown","Finite >= 0; disjoint","Invoice / ledger","Cost period"),
    ("labor_hours","number","hour","Optional actual consumption","Finite >= 0; not a pre-run feature","Timekeeping","After/during production"),
    ("labor_cost_tl","number","TL/batch","Cost breakdown","Finite >= 0; disjoint","Payroll / ledger","Cost period"),
    ("energy_kwh","number","kWh","Optional actual consumption","Finite >= 0; not a pre-run feature","Meter","During/after production"),
    ("energy_cost_tl","number","TL/batch","Cost breakdown","Finite >= 0; disjoint","Utility / ledger","Cost period"),
    ("packaging_cost_tl","number","TL/batch","Cost breakdown","Finite >= 0; disjoint","Invoice / ledger","Cost period"),
    ("fason_service_cost_tl","number","TL/batch","Cost breakdown","Finite >= 0; disjoint","Contract / invoice","Cost period"),
    ("inhouse_processing_cost_tl","number","TL/batch","Cost breakdown","Finite >= 0; disjoint in-house production cost","Internal cost ledger / allocation policy","Cost period"),
    ("overhead_cost_tl","number","TL/batch","Cost breakdown","Finite >= 0; disjoint allocation","Accounting policy","Cost period"),
    ("other_cost_tl","number","TL/batch","Cost breakdown","Finite >= 0; explain; disjoint","Invoice / ledger","Cost period"),
    ("other_cost_description","string","text","Other cost audit","Describe charges not represented by another component","Invoice / ledger","Cost period"),
    ("cost_breakdown_complete","boolean","true/false","Cost reconciliation","true requires every cost field, zero explicit","Accounting owner","After close"),
    ("total_cost_tl","number","TL/batch","EKP calculation","Finite >= 0; TRY; per_batch","Closed accounting record","After close"),
    ("input_mass_kg","number","kg","Optional mass balance","Finite > 0","Calibrated scale","Production input"),
    ("net_output_kg","number","kg","EKP target/formula","Finite > 0; measured, not predicted","Calibrated scale","After production"),
    ("drying_loss_kg","number","kg","Complete mass balance","Finite >= 0","Scale / process","After production"),
    ("sorting_loss_kg","number","kg","Complete mass balance","Finite >= 0","Scale / process","After production"),
    ("other_loss_kg","number","kg","Complete mass balance","Finite >= 0; do not duplicate","Scale / process","After production"),
    ("drying_loss_pct","number","%","Optional diagnostic","Finite 0..100; never Scenario A","Process record","Timing must be explicit"),
    ("sorting_loss_pct","number","%","Optional diagnostic","Finite 0..100; never Scenario A","Process record","Timing must be explicit"),
    ("loss_percentage_basis","enum","category","If loss percent present","input_mass | sequential_mass | unknown","Process definition","Plan vs measured explicit"),
    ("plan_snapshot_at","datetime","ISO-8601 timezone","Scenario A feature eligibility","<= production start","Frozen ERP/MES snapshot","Before production"),
    ("planned_meat_input_kg","number","kg","Scenario A input","Finite >= 0","Frozen order / recipe","Snapshot"),
    ("planned_tail_fat_input_kg","number","kg","Scenario A input","Finite >= 0","Frozen order / recipe","Snapshot"),
    ("planned_spice_input_kg","number","kg","Scenario A input","Finite >= 0","Frozen order / recipe","Snapshot"),
    ("planned_salt_input_kg","number","kg","Scenario A input","Finite >= 0","Frozen order / recipe","Snapshot"),
    ("planned_other_inputs_kg","number","kg","Scenario A input","Finite >= 0","Frozen order / recipe","Snapshot"),
    ("planned_casing_m","number","m","Scenario A input","Finite >= 0","Frozen order / recipe","Snapshot"),
    ("planned_meat_price_tl_kg","number","TL/kg","Scenario A input","Finite >= 0","Frozen quote","Snapshot"),
    ("planned_tail_fat_price_tl_kg","number","TL/kg","Scenario A input","Finite >= 0","Frozen quote","Snapshot"),
    ("planned_spice_price_tl_kg","number","TL/kg","Scenario A input","Finite >= 0","Frozen quote","Snapshot"),
    ("planned_salt_price_tl_kg","number","TL/kg","Scenario A input","Finite >= 0","Frozen quote","Snapshot"),
    ("planned_casing_price_tl_m","number","TL/m","Scenario A input","Finite >= 0","Frozen quote","Snapshot"),
    ("planned_fason_rate_tl_kg_input","number","TL/kg input","Scenario A input","Finite >= 0","Frozen contract","Snapshot"),
    ("planned_labor_rate_tl_hour","number","TL/hour","Scenario A input","Finite >= 0; tariff not actual cost","Frozen rate card","Snapshot"),
    ("planned_electricity_rate_tl_kwh","number","TL/kWh","Scenario A input","Finite >= 0; tariff not consumption","Frozen tariff","Snapshot"),
    ("planned_packaging_rate_tl_kg","number","TL/kg","Scenario A input","Finite >= 0","Frozen quote","Snapshot"),
    ("planned_region","enum","category","Scenario A input","Known Model1 category","Frozen order","Snapshot"),
    ("planned_recipe_profile","enum","category","Scenario A input","ERZURUM_CI | MEB_STANDART","Frozen order","Snapshot"),
    ("planned_process_method","enum","category","Scenario A input","Fason | Kurum içi","Frozen order","Snapshot"),
]
CSV_COLUMNS = [entry[0] for entry in FIELD_DICTIONARY]
NUMERIC_FIELDS = {entry[0] for entry in FIELD_DICTIONARY if entry[1] == "number"}
DATETIME_FIELDS = {entry[0] for entry in FIELD_DICTIONARY if entry[1] == "datetime"}
STRING_FIELDS = {entry[0] for entry in FIELD_DICTIONARY if entry[1] in {"string", "enum", "json string"}}
PERCENT_FIELDS = {"drying_loss_pct", "sorting_loss_pct"}
REQUIRED_FIELDS = {
    "batch_id", "source_type", "source_system", "source_reference", "validation_status",
    "production_started_at", "measurement_at", "measurement_method",
    "currency", "cost_period", "total_cost_tl", "net_output_kg",
}
ENUMS = {
    "source_type": {"real", "synthetic", "external_benchmark"},
    "validation_status": {"pending", "validated", "rejected"},
    "currency": {"TRY"},
    "cost_period": {"per_batch"},
    "loss_percentage_basis": {"input_mass", "sequential_mass", "unknown"},
    "planned_region": {"Akdeniz", "Doğu Anadolu", "Ege", "Güneydoğu Anadolu", "Karadeniz", "Marmara", "İç Anadolu"},
    "planned_recipe_profile": {"ERZURUM_CI", "MEB_STANDART"},
    "planned_process_method": {"Fason", "Kurum içi"},
}
BOOL_FIELDS = {"losses_complete", "cost_breakdown_complete", "spice_details_complete"}


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _number(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise InvalidOperation
    result = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    if not result.is_finite():
        raise InvalidOperation
    return result


def _time(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError
    return parsed


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().casefold() in {"true", "1", "yes"}:
        return True
    if isinstance(value, str) and value.strip().casefold() in {"false", "0", "no"}:
        return False
    raise ValueError


def _rounding_uncertainty(value: Decimal) -> Decimal:
    return Decimal(5).scaleb(value.as_tuple().exponent - 1)


def calculate_cost_total(components: Iterable[Mapping[str, Any]]) -> Decimal:
    seen: set[str] = set()
    total = Decimal(0)
    for component in components:
        name = component.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Cost component needs a name")
        name = name.strip()
        identity = name.casefold()
        if identity in seen:
            raise ValueError(f"Duplicate cost component: {name}")
        seen.add(identity)
        try:
            amount = _number(component.get("amount_tl"))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(f"Invalid amount for cost component: {name}") from None
        if amount < 0:
            raise ValueError(f"Negative amount for cost component: {name}")
        total += amount
    if not seen:
        raise ValueError("At least one explicit cost component is required")
    return total


def calculate_ekp(total_cost_tl: Any | None, net_output_kg: Any, *,
                  currency: str = "TRY", cost_period: str = "per_batch",
                  components: Iterable[Mapping[str, Any]] | None = None) -> Decimal:
    """Compute TL/kg; no FX conversion, component imputation, or double counting."""
    if currency != "TRY":
        raise ValueError("EKP requires TRY; currency conversion is not implicit")
    if cost_period != "per_batch":
        raise ValueError("EKP requires a per-batch total cost")
    try:
        output = _number(net_output_kg)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Net output must be a finite number greater than zero") from None
    if output <= 0:
        raise ValueError("Net output must be greater than zero")
    component_rows = list(components) if components is not None else None
    component_total = calculate_cost_total(component_rows) if component_rows is not None else None
    if total_cost_tl is None:
        if component_total is None:
            raise ValueError("Provide total cost or explicit cost components")
        total = component_total
    else:
        try:
            total = _number(total_cost_tl)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Total cost must be finite") from None
        if total < 0:
            raise ValueError("Total cost cannot be negative")
        if component_total is not None:
            rounding_tolerance = Decimal("0.005") * Decimal(len(component_rows) + 1)
            if abs(total - component_total) > rounding_tolerance:
                raise ValueError("Total cost does not reconcile with explicit components")
    return total / output


def validate_records(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Keep every source row and report each row/field error; never silently coerce."""
    rows = list(records)
    issues: list[dict[str, Any]] = []
    seen: dict[str, list[int]] = {}
    parsed_rows = []

    def issue(row_no, batch_id, field, code, message, severity="error"):
        issues.append({"row_number": row_no, "batch_id": str(batch_id) if batch_id is not None else None,
                       "field": field, "code": code, "message": message, "severity": severity})

    for row_no, original in enumerate(rows, start=2):
        if not isinstance(original, Mapping):
            issue(row_no, None, "__row__", "wrong_type", "Each row must be a mapping.")
            parsed_rows.append(({}, {}, {}))
            continue
        row = dict(original)
        batch = row.get("batch_id")
        for field in row.keys() - set(CSV_COLUMNS):
            issue(row_no, batch, field, "unknown_field", "Unexpected field; schema is strict.")
        for field in REQUIRED_FIELDS:
            if field not in row or _blank(row[field]):
                issue(row_no, batch, field, "required", "Required value is missing.")
        if not _blank(batch):
            seen.setdefault(str(batch).strip(), []).append(row_no)
        nums, times, bools = {}, {}, {}
        for field in NUMERIC_FIELDS:
            if _blank(row.get(field)):
                continue
            try:
                value = _number(row[field])
            except (InvalidOperation, TypeError, ValueError):
                issue(row_no, batch, field, "invalid_number", "Value must be finite numeric data; NaN and infinity are rejected.")
                continue
            nums[field] = value
            if field in {"net_output_kg", "input_mass_kg"} and value <= 0:
                issue(row_no, batch, field, "nonpositive", "Value must be greater than zero.")
            elif field not in {"net_output_kg", "input_mass_kg"} and value < 0:
                issue(row_no, batch, field, "negative", "Value cannot be negative.")
            if field in PERCENT_FIELDS and value > 100:
                issue(row_no, batch, field, "out_of_range", "Percentage must be between 0 and 100.")
        for field in DATETIME_FIELDS:
            if _blank(row.get(field)):
                continue
            try:
                times[field] = _time(row[field])
            except (TypeError, ValueError, OverflowError):
                issue(row_no, batch, field, "invalid_timestamp", "Use ISO-8601 timestamp with timezone offset.")
        for field, accepted in ENUMS.items():
            value = row.get(field)
            if not _blank(value) and (not isinstance(value, str) or value.strip() not in accepted):
                issue(row_no, batch, field, "invalid_category", f"Accepted values: {', '.join(sorted(accepted))}.")
        for field in BOOL_FIELDS:
            if _blank(row.get(field)):
                continue
            try:
                bools[field] = _bool(row[field])
            except ValueError:
                issue(row_no, batch, field, "invalid_boolean", "Use true or false.")
        for field in STRING_FIELDS:
            value = row.get(field)
            if not _blank(value) and not isinstance(value, str):
                issue(row_no, batch, field, "wrong_type", "Value must be text.")
        if row.get("validation_status") == "validated" and _blank(row.get("validated_at")):
            issue(row_no, batch, "validated_at", "required_for_validation", "Validated records require an approval timestamp.")
        if times.get("record_created_at") and times.get("validated_at") and times["validated_at"] < times["record_created_at"]:
            issue(row_no, batch, "validated_at", "time_order", "Validation cannot precede record creation.")
        if times.get("measurement_at") and times.get("validated_at") and times["validated_at"] < times["measurement_at"]:
            issue(row_no, batch, "validated_at", "time_order", "Validation cannot precede measured net output.")
        if times.get("production_started_at") and times.get("production_ended_at") and times["production_ended_at"] < times["production_started_at"]:
            issue(row_no, batch, "production_ended_at", "time_order", "Production end precedes start.")
        for field in ("measurement_at", "loss_measurement_at"):
            if times.get(field) and times.get("production_started_at") and times[field] < times["production_started_at"]:
                issue(row_no, batch, field, "time_order", "Measurement precedes production start.")
        if times.get("plan_snapshot_at") and times.get("production_started_at") and times["plan_snapshot_at"] > times["production_started_at"]:
            issue(row_no, batch, "plan_snapshot_at", "future_information", "Plan snapshot is after production start.")
        spice_details = None
        if not _blank(row.get("spice_details_json")):
            import json
            try:
                def reject_json_constant(value):
                    raise ValueError(f"Non-finite JSON value: {value}")
                spice_details = json.loads(row["spice_details_json"], parse_constant=reject_json_constant)
                allowed_spice_keys = {"name", "quantity_kg", "unit_price_tl_kg", "cost_tl", "source_reference"}
                if not isinstance(spice_details, list):
                    raise ValueError
                for item in spice_details:
                    if (not isinstance(item, dict) or set(item) - allowed_spice_keys
                            or not isinstance(item.get("name"), str) or not item["name"].strip()):
                        raise ValueError
                    for key in ("quantity_kg", "unit_price_tl_kg", "cost_tl"):
                        if key in item and _number(item[key]) < 0:
                            raise ValueError
                    if all(key in item for key in ("quantity_kg", "unit_price_tl_kg", "cost_tl")):
                        item_cost = _number(item["quantity_kg"]) * _number(item["unit_price_tl_kg"])
                        if abs(item_cost - _number(item["cost_tl"])) > Decimal("0.005"):
                            issue(row_no, batch, "spice_details_json", "spice_item_reconciliation", "A spice item cost differs from quantity × unit price beyond kuruş rounding.")
            except (TypeError, ValueError, InvalidOperation):
                spice_details = None
                issue(row_no, batch, "spice_details_json", "invalid_json", "Expected finite, non-negative, named spice detail objects.")
        if bools.get("spice_details_complete"):
            if not spice_details:
                issue(row_no, batch, "spice_details_json", "incomplete_spice_details", "Complete spice details require at least one item.")
            elif any(not all(key in item for key in ("quantity_kg", "unit_price_tl_kg", "cost_tl")) for item in spice_details):
                issue(row_no, batch, "spice_details_json", "incomplete_spice_details", "Complete spice details require quantity, unit price, and cost for every item.")
            elif "spice_cost_tl" not in nums:
                issue(row_no, batch, "spice_cost_tl", "incomplete_spice_details", "Complete spice detail requires aggregate spice_cost_tl.")
            else:
                item_total = sum((_number(item["cost_tl"]) for item in spice_details), Decimal(0))
                tolerance = Decimal("0.005") * Decimal(len(spice_details) + 1)
                if abs(item_total - nums["spice_cost_tl"]) > tolerance:
                    issue(row_no, batch, "spice_cost_tl", "spice_detail_reconciliation", "Aggregate spice cost differs from item costs beyond kuruş rounding.")

        if bools.get("cost_breakdown_complete"):
            missing = [field for field in COST_COMPONENT_FIELDS if field not in nums]
            for field in missing:
                issue(row_no, batch, field, "incomplete_cost_breakdown", "Complete breakdown needs an explicit value, including zero.")
            if not missing and "total_cost_tl" in nums:
                total_components = sum((nums[field] for field in COST_COMPONENT_FIELDS), Decimal(0))
                tolerance = Decimal("0.005") * Decimal(len(COST_COMPONENT_FIELDS) + 1)
                if abs(nums["total_cost_tl"] - total_components) > tolerance:
                    issue(row_no, batch, "total_cost_tl", "cost_reconciliation", "Total differs from component sum beyond kuruş rounding.")
        elif any(field in nums for field in COST_COMPONENT_FIELDS):
            issue(row_no, batch, "cost_breakdown_complete", "partial_cost_breakdown", "Cost details are partial; total was not reconciled.", "warning")

        loss_fields = ("drying_loss_kg", "sorting_loss_kg", "other_loss_kg")
        present_losses = [field for field in loss_fields if field in nums]
        if bools.get("losses_complete"):
            for field in loss_fields:
                if field not in nums:
                    issue(row_no, batch, field, "incomplete_loss_measurement", "Complete losses need an explicit value, including zero.")
            if _blank(row.get("loss_measurement_at")):
                issue(row_no, batch, "loss_measurement_at", "required_for_mass_balance", "Complete losses need a timestamp.")
            if _blank(row.get("loss_measurement_method")):
                issue(row_no, batch, "loss_measurement_method", "required_for_mass_balance", "Complete losses need a method.")
            if "input_mass_kg" not in nums or "net_output_kg" not in nums:
                issue(row_no, batch, "input_mass_kg", "required_for_mass_balance", "Complete mass balance needs input and net output.")
            elif all(field in nums for field in loss_fields):
                if sum((nums[f] for f in loss_fields), Decimal(0)) > nums["input_mass_kg"]:
                    issue(row_no, batch, "drying_loss_kg", "impossible_mass_balance", "Losses exceed input mass.")
                diff = nums["input_mass_kg"] - nums["net_output_kg"] - sum((nums[f] for f in loss_fields), Decimal(0))
                tolerance = sum((_rounding_uncertainty(nums[f]) for f in ("input_mass_kg", "net_output_kg", *loss_fields)), Decimal(0))
                if abs(diff) > tolerance:
                    issue(row_no, batch, "net_output_kg", "mass_balance_mismatch", "Input minus measured losses differs from net output beyond reported rounding precision.")
        elif present_losses:
            issue(row_no, batch, "losses_complete", "mass_balance_not_assessed", "Partial loss fields do not establish a complete mass balance.", "warning")

        if "input_mass_kg" in nums and "net_output_kg" in nums:
            tolerance = _rounding_uncertainty(nums["input_mass_kg"]) + _rounding_uncertainty(nums["net_output_kg"])
            if nums["net_output_kg"] - nums["input_mass_kg"] > tolerance:
                issue(row_no, batch, "net_output_kg", "input_mass_check", "Net output exceeds recorded input mass; omitted inputs, moisture addition, process boundary, or units must be checked before treating the mass balance as complete.", "warning")
        has_pct = any(field in nums for field in PERCENT_FIELDS)
        if has_pct and _blank(row.get("loss_percentage_basis")):
            issue(row_no, batch, "loss_percentage_basis", "unknown_loss_basis", "Loss percentage denominator is unknown.", "warning")
        if has_pct and not _blank(row.get("loss_measurement_at")):
            issue(row_no, batch, "drying_loss_pct", "postproduction_not_feature", "Loss percentages are excluded from production-before features.", "warning")
        parsed_rows.append((row, nums, times))

    for batch, row_numbers in seen.items():
        if len(row_numbers) > 1:
            for row_no in row_numbers:
                issue(row_no, batch, "batch_id", "duplicate_batch_id", "Batch ID is duplicated in this import.")

    output = []
    for row_no, (row, nums, _) in enumerate(parsed_rows, start=2):
        own = [item for item in issues if item["row_number"] == row_no]
        errors = [item for item in own if item["severity"] == "error"]
        warnings = [item for item in own if item["severity"] == "warning"]
        formula_ok = (
            "total_cost_tl" in nums and "net_output_kg" in nums
            and nums["net_output_kg"] > 0 and nums["total_cost_tl"] >= 0
            and row.get("currency") == "TRY" and row.get("cost_period") == "per_batch"
            and not any(item["field"] in {"total_cost_tl", "net_output_kg", "currency", "cost_period"} for item in errors)
        )
        output.append({
            "row_number": row_no, "batch_id": str(row.get("batch_id")) if row.get("batch_id") is not None else None,
            "is_valid": not errors, "eligible_for_ekp": formula_ok,
            "eligible_for_time_evaluation": not errors and row.get("source_type") == "real" and row.get("validation_status") == "validated",
            "calculated_ekp_tl_kg": str(nums["total_cost_tl"] / nums["net_output_kg"]) if formula_ok else None,
            "errors": errors, "warnings": warnings,
        })
    counts = {}
    for item in issues:
        counts[item["code"]] = counts.get(item["code"], 0) + 1
    return {
        "schema_version": "1.0", "rows": len(rows),
        "valid_rows": sum(item["is_valid"] for item in output),
        "eligible_for_ekp": sum(item["eligible_for_ekp"] for item in output),
        "eligible_for_time_evaluation": sum(item["eligible_for_time_evaluation"] for item in output),
        "error_count": sum(item["severity"] == "error" for item in issues),
        "warning_count": sum(item["severity"] == "warning" for item in issues),
        "issue_counts": counts, "issues": issues, "records": output,
    }


def model1_scenario_a_features(record: Mapping[str, Any]) -> dict[str, Any]:
    """Build the fixed Model1 allow-list only from a timestamped frozen pre-production plan."""
    try:
        started = _time(record.get("production_started_at"))
        planned = _time(record.get("plan_snapshot_at"))
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Timezone-aware production_started_at and plan_snapshot_at are required") from None
    if planned > started:
        raise ValueError("Plan snapshot occurs after production start")
    missing = [field for field in MODEL1_FEATURE_MAP.values() if _blank(record.get(field))]
    if missing:
        raise ValueError(f"Missing production-before features: {', '.join(missing)}")
    result = {}
    for target, source in MODEL1_FEATURE_MAP.items():
        value = record[source]
        if source in NUMERIC_FIELDS:
            try:
                number = _number(value)
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError(f"{source} must be finite numeric data") from None
            if number < 0:
                raise ValueError(f"{source} cannot be negative")
            result[target] = float(number)
        else:
            result[target] = value
    if result["Et_fiyat_TL_kg"] <= 0:
        raise ValueError("Planned meat price must be greater than zero")
    if result["Et_girdi_kg"] <= 0:
        raise ValueError("Planned meat input must be greater than zero")
    for field, valid in (
        ("Bolge", ENUMS["planned_region"]),
        ("Recete_profili", ENUMS["planned_recipe_profile"]),
        ("Isleme_modeli", ENUMS["planned_process_method"]),
    ):
        if result[field] not in valid:
            raise ValueError(f"Invalid planned category for {field}")
    return result

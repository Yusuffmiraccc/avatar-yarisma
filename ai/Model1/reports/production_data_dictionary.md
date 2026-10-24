# Gerçek üretim veri sözlüğü

Bu sözlük boş CSV/XLSX şablonuyla aynı şemayı kullanır. Boş değer bilinmiyor demektir;
eksik ölçümler tahmin edilerek doldurulmaz. CSV/XLSX örnek üretim kaydı içermez.

| Alan | Açıklama | Tip | Birim | Zorunluluk/kullanım | Kabul edilen değerler | Kaynak | Ölçüm zamanı |
|---|---|---|---|---|---|---|---|
| batch_id | batch id — EKP, traceability, time evaluation | string | id | EKP, traceability, time evaluation | Unique non-empty | MES / production order | Assigned before production |
| source_type | source type — Every row | enum | category | Every row | real \| synthetic \| external_benchmark | Dataset owner | Known at ingestion |
| source_system | source system — Real-data provenance | string | text | Real-data provenance | Non-empty for real rows | ERP / MES / scale / accounting | At ingestion |
| source_reference | source reference — Real-data provenance | string | text | Real-data provenance | Traceable record ID; no secrets | Source document/system | At ingestion |
| validation_status | validation status — Evaluation eligibility | enum | category | Evaluation eligibility | pending \| validated \| rejected | Data steward | After review |
| validated_at | validated at — Time-based target availability | datetime | ISO-8601 timezone | Time-based target availability | Timezone offset required for validated rows | Data steward / audit log | After measurement and before the target is used for model training |
| record_created_at | record created at — Required for time-based evaluation availability audit | datetime | ISO-8601 timezone | Required for time-based evaluation availability audit | Timezone offset required | Import/source log | At entry; must precede test-time training cutoff |
| production_started_at | production started at — Chronological evaluation | datetime | ISO-8601 timezone | Chronological evaluation | Timezone offset required | MES / batch sheet | Production start |
| production_ended_at | production ended at — Optional | datetime | ISO-8601 timezone | Optional | Timezone offset required | MES / batch sheet | Production end |
| measurement_at | measurement at — Actual net-output target | datetime | ISO-8601 timezone | Actual net-output target | Timezone offset required | Calibrated scale record | After production start |
| measurement_method | measurement method — Measured net-output provenance | string | text | Measured net-output provenance | Scale/tare/SOP reference | Measurement record | At weighing |
| loss_measurement_at | loss measurement at — Mass balance | datetime | ISO-8601 timezone | Mass balance | Timezone offset required | Scale / process record | At loss measurement |
| loss_measurement_method | loss measurement method — Mass balance | string | text | Mass balance | Method/stage reference | Process SOP | At loss measurement |
| losses_complete | losses complete — Mass balance | boolean | true/false | Mass balance | true \| false | Process owner | After production |
| currency | currency — EKP | enum | ISO code | EKP | TRY only; no implicit FX | Accounting record | Cost period |
| cost_period | cost period — EKP | enum | category | EKP | per_batch only | Accounting policy | Cost period |
| cost_period_start | cost period start — Optional cost audit | datetime | ISO-8601 timezone | Optional cost audit | Timezone offset required | Ledger | Cost period |
| cost_period_end | cost period end — Optional cost audit | datetime | ISO-8601 timezone | Optional cost audit | Timezone offset required | Ledger | Cost period |
| recipe_code | recipe code — Optional context | string | text | Optional context | Source-system value | Approved recipe | Frozen plan |
| recipe_name | recipe name — Optional context | string | text | Optional context | Source-system value | Approved recipe | Frozen plan |
| process_method | process method — Optional context | string | text | Optional context | Source-system value | Production order | Plan or actual; distinguish |
| meat_type | meat type — Optional context | string | text | Optional context | Source-system value | Recipe / purchasing | Frozen plan |
| meat_input_kg | meat input kg — Optional actual input | number | kg | Optional actual input | Finite >= 0 | Batch weighing | Consumption |
| meat_unit_price_tl_kg | meat unit price tl kg — Optional cost detail | number | TL/kg | Optional cost detail | Finite >= 0 | Invoice / ledger | Cost period |
| meat_cost_tl | meat cost tl — Cost breakdown | number | TL/batch | Cost breakdown | Finite >= 0; disjoint | Invoice / ledger | Cost period |
| spice_input_kg | spice input kg — Optional actual input | number | kg | Optional actual input | Finite >= 0 | Batch weighing | Consumption |
| spice_details_json | spice details json — Optional detail | json string | kg, TL/kg, TL | Optional detail | Per-spice quantity × unit price = item cost; aggregate is included once in spice_cost_tl | Recipe / invoice | Plan/actual timing must be explicit |
| spice_details_complete | spice details complete — Spice detail reconciliation | boolean | true/false | Spice detail reconciliation | true requires item quantities, unit prices, costs, and aggregate spice_cost_tl | Recipe / invoice owner | At cost close |
| spice_cost_tl | spice cost tl — Cost breakdown | number | TL/batch | Cost breakdown | Finite >= 0; disjoint | Invoice / ledger | Cost period |
| casing_quantity_m | casing quantity m — Optional actual input | number | m | Optional actual input | Finite >= 0 | Batch sheet | Consumption |
| casing_cost_tl | casing cost tl — Cost breakdown | number | TL/batch | Cost breakdown | Finite >= 0; disjoint | Invoice / ledger | Cost period |
| labor_hours | labor hours — Optional actual consumption | number | hour | Optional actual consumption | Finite >= 0; not a pre-run feature | Timekeeping | After/during production |
| labor_cost_tl | labor cost tl — Cost breakdown | number | TL/batch | Cost breakdown | Finite >= 0; disjoint | Payroll / ledger | Cost period |
| energy_kwh | energy kwh — Optional actual consumption | number | kWh | Optional actual consumption | Finite >= 0; not a pre-run feature | Meter | During/after production |
| energy_cost_tl | energy cost tl — Cost breakdown | number | TL/batch | Cost breakdown | Finite >= 0; disjoint | Utility / ledger | Cost period |
| packaging_cost_tl | packaging cost tl — Cost breakdown | number | TL/batch | Cost breakdown | Finite >= 0; disjoint | Invoice / ledger | Cost period |
| fason_service_cost_tl | fason service cost tl — Cost breakdown | number | TL/batch | Cost breakdown | Finite >= 0; disjoint | Contract / invoice | Cost period |
| inhouse_processing_cost_tl | inhouse processing cost tl — Cost breakdown | number | TL/batch | Cost breakdown | Finite >= 0; disjoint in-house production cost | Internal cost ledger / allocation policy | Cost period |
| overhead_cost_tl | overhead cost tl — Cost breakdown | number | TL/batch | Cost breakdown | Finite >= 0; disjoint allocation | Accounting policy | Cost period |
| other_cost_tl | other cost tl — Cost breakdown | number | TL/batch | Cost breakdown | Finite >= 0; explain; disjoint | Invoice / ledger | Cost period |
| other_cost_description | other cost description — Other cost audit | string | text | Other cost audit | Describe charges not represented by another component | Invoice / ledger | Cost period |
| cost_breakdown_complete | cost breakdown complete — Cost reconciliation | boolean | true/false | Cost reconciliation | true requires every cost field, zero explicit | Accounting owner | After close |
| total_cost_tl | total cost tl — EKP calculation | number | TL/batch | EKP calculation | Finite >= 0; TRY; per_batch | Closed accounting record | After close |
| input_mass_kg | input mass kg — Optional mass balance | number | kg | Optional mass balance | Finite > 0 | Calibrated scale | Production input |
| net_output_kg | net output kg — EKP target/formula | number | kg | EKP target/formula | Finite > 0; measured, not predicted | Calibrated scale | After production |
| drying_loss_kg | drying loss kg — Complete mass balance | number | kg | Complete mass balance | Finite >= 0 | Scale / process | After production |
| sorting_loss_kg | sorting loss kg — Complete mass balance | number | kg | Complete mass balance | Finite >= 0 | Scale / process | After production |
| other_loss_kg | other loss kg — Complete mass balance | number | kg | Complete mass balance | Finite >= 0; do not duplicate | Scale / process | After production |
| drying_loss_pct | drying loss pct — Optional diagnostic | number | % | Optional diagnostic | Finite 0..100; never Scenario A | Process record | Timing must be explicit |
| sorting_loss_pct | sorting loss pct — Optional diagnostic | number | % | Optional diagnostic | Finite 0..100; never Scenario A | Process record | Timing must be explicit |
| loss_percentage_basis | loss percentage basis — If loss percent present | enum | category | If loss percent present | input_mass \| sequential_mass \| unknown | Process definition | Plan vs measured explicit |
| plan_snapshot_at | plan snapshot at — Scenario A feature eligibility | datetime | ISO-8601 timezone | Scenario A feature eligibility | <= production start | Frozen ERP/MES snapshot | Before production |
| planned_meat_input_kg | planned meat input kg — Scenario A input | number | kg | Scenario A input | Finite >= 0 | Frozen order / recipe | Snapshot |
| planned_tail_fat_input_kg | planned tail fat input kg — Scenario A input | number | kg | Scenario A input | Finite >= 0 | Frozen order / recipe | Snapshot |
| planned_spice_input_kg | planned spice input kg — Scenario A input | number | kg | Scenario A input | Finite >= 0 | Frozen order / recipe | Snapshot |
| planned_salt_input_kg | planned salt input kg — Scenario A input | number | kg | Scenario A input | Finite >= 0 | Frozen order / recipe | Snapshot |
| planned_other_inputs_kg | planned other inputs kg — Scenario A input | number | kg | Scenario A input | Finite >= 0 | Frozen order / recipe | Snapshot |
| planned_casing_m | planned casing m — Scenario A input | number | m | Scenario A input | Finite >= 0 | Frozen order / recipe | Snapshot |
| planned_meat_price_tl_kg | planned meat price tl kg — Scenario A input | number | TL/kg | Scenario A input | Finite >= 0 | Frozen quote | Snapshot |
| planned_tail_fat_price_tl_kg | planned tail fat price tl kg — Scenario A input | number | TL/kg | Scenario A input | Finite >= 0 | Frozen quote | Snapshot |
| planned_spice_price_tl_kg | planned spice price tl kg — Scenario A input | number | TL/kg | Scenario A input | Finite >= 0 | Frozen quote | Snapshot |
| planned_salt_price_tl_kg | planned salt price tl kg — Scenario A input | number | TL/kg | Scenario A input | Finite >= 0 | Frozen quote | Snapshot |
| planned_casing_price_tl_m | planned casing price tl m — Scenario A input | number | TL/m | Scenario A input | Finite >= 0 | Frozen quote | Snapshot |
| planned_fason_rate_tl_kg_input | planned fason rate tl kg input — Scenario A input | number | TL/kg input | Scenario A input | Finite >= 0 | Frozen contract | Snapshot |
| planned_labor_rate_tl_hour | planned labor rate tl hour — Scenario A input | number | TL/hour | Scenario A input | Finite >= 0; tariff not actual cost | Frozen rate card | Snapshot |
| planned_electricity_rate_tl_kwh | planned electricity rate tl kwh — Scenario A input | number | TL/kWh | Scenario A input | Finite >= 0; tariff not consumption | Frozen tariff | Snapshot |
| planned_packaging_rate_tl_kg | planned packaging rate tl kg — Scenario A input | number | TL/kg | Scenario A input | Finite >= 0 | Frozen quote | Snapshot |
| planned_region | planned region — Scenario A input | enum | category | Scenario A input | Known Model1 category | Frozen order | Snapshot |
| planned_recipe_profile | planned recipe profile — Scenario A input | enum | category | Scenario A input | ERZURUM_CI \| MEB_STANDART | Frozen order | Snapshot |
| planned_process_method | planned process method — Scenario A input | enum | category | Scenario A input | Fason \| Kurum içi | Frozen order | Snapshot |

Maliyet alanları TRY/batch ve birbirinden ayrık kabul edilir. Aynı fatura kalemini iki alana
yazmayın. Fason hizmeti ve kurum içi işleme ayrı maliyet alanlarıdır. Toplam maliyet, cost_breakdown_complete=true ise tüm on bileşenle
kuruş yuvarlama toleransında mutabık olmalıdır. EKP = toplam parti maliyeti / ölçülmüş net
çıktı (TRY/kg). Harici kur dönüşümü ve aylık maliyet tahsisi bu şemada yapılmaz.

Üretim öncesi özellikler yalnız planned_* alanlarından oluşturulur ve plan_snapshot_at
üretim başlangıcından geç olamaz. Gerçekleşmiş net çıktı, kayıp yüzdesi ve maliyet bileşenleri
sonuç alanlarıdır; Scenario A girdilerinden hariç tutulur.

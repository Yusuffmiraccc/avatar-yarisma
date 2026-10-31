# Gerçek saha verisi toplama şablonu

Bu şablon, bireysel hayvan ölçümlerini kaydetmek içindir. Bilinmeyen değerleri tahmin ederek doldurmayın; boş bırakın. `live_weight_kg` canlı ağırlık, `carcass_weight_kg` karkas ağırlığıdır ve birbirinin yerine kullanılamaz.

- `animal_id`: Aynı hayvan için benzersiz, anonim kimlik.
- `species`, `breed`: Tür ve biliniyorsa ırk.
- `slaughter_date`: Kesim tarihi (YYYY-MM-DD).
- `cutting_method`: Kullanılan parçalama yöntemi/standart.
- Hedef sütunları: Yalnızca fiilen tartılan kategorileri kg cinsinden girin. Kategorilerin sınırlarını ve birbirleriyle örtüşüp örtüşmediğini kayıt altına alın.
- `facility_id`: Gerekliyse anonim işletme kodu.
- `source_type`: Ölçülmüş saha kayıtları için `measured`.
- `measurement_notes`: Tartım aşaması, cihaz veya sıra dışı durumlar.

Gerçek ölçümler toplanmadan modelin gerçek saha performansı doğrulanmış sayılmaz.

## Model B — gerçek saha ölçümü için tamamlayıcı alanlar

CSV şablonundaki temel ölçüm sütunlarını doldururken şu alanları ek sütun olarak kullanın: `carcass_weight_type` (sıcak/soğuk ve kemikli/kemiksiz tanımı), `carcass_weight_timestamp`, `carcass_weight_stage`, `output_measurement_timestamp`, `cutting_standard_id`, `scale_id`, `scale_calibration_date`, `operator_id`, `facility_id`. Ağırlık girdisini kesim başlamadan önce, hedef parçaları işlem sonrası ayrı tartın. `animal_id` anonim olmalı ama aynı bireyi kayıtlarda eşleştirmelidir. Her hedef kategorinin tanımı/örtüşmesi ve kütle dengesi fark açıklaması `measurement_notes` içinde yazılmalıdır. Bu alanlar ölçüm zamanı ve izlenebilirlik için gereklidir; ölçülmemiş alanları tahminle doldurmayın.


## Additional measurement provenance fields

For future measured data, retain the existing blank CSV and add these columns to each row as available: `carcass_weight_type` (hot/cold and bone-in/boneless), `carcass_weight_measured_at`, `cutting_started_at`, `outputs_measured_at`, `cutting_standard_id`, `scale_id`, `scale_calibration_date`, `operator_id`. `live_weight_kg` and `carcass_weight_kg` are distinct quantities. `animal_id` must be anonymized and stable. Record the weight and boundary definition for every target in kg; never fill an unmeasured target with zero. Use `source_type=measured` only for an observed individual record with traceable weighing. The listed timestamp fields are collection requirements, not values asserted for the existing synthetic rows.

Güncel kalıcı iş akışı: `POST /v1/predict/carcass-cuts` başarılı tahminin model/veri sürümü, girdisi, çıktısı ve kimliğini kaydeder. Parçalama sonrası değerleri tahmin ID ve açık saat dilimli `measured_at_utc` ile ayrı `POST /v1/actual/carcass-cuts` endpoint'ine gönderin. `GET /v1/evaluate/carcass-cuts/{prediction_id}` kayıtlı ikisini karşılaştırır; fark `tahmin - gerçekleşen` işaretindedir. Bu endpoint'ler API anahtarı korumasını kullanır. SQLite migration `Model2/sql/001_model_b_audit.sql`; veritabanı `MODEL_B_AUDIT_DB` ile yapılandırılır. Yalnız fiilen tartılmış sonuçları `measured` olarak gönderin. Servis terazi ölçümünü kendisi doğrulayamaz; veri tabanını erişim denetimiyle koruyun ve Git dışında tutun.

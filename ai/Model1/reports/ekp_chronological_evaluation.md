# Gerçek veriyle kronolojik EKP değerlendirmesi

- Durum: **no_real_data**
- Kaynak türü: real production records only
- Değerlendirme: chronological_expanding_window
- Hedef: total_cost_tl / measured net_output_kg; TRY/kg

Gerçek üretim kaydı bulunmadı. Girdi, başlıkları olan boş veri şablonudur.
Model metriği hesaplanmadı; sentetik veriden zaman bazlı gerçek performans üretilmedi.

## Yöntem ve sınırlamalar

- Eğitim minimumu: 50 batch; pencere başına 20 farklı üretim zaman damgası; 3 genişleyen pencere.
- Eğitim hedefleri, her test penceresinin başlangıcında hem kaydedilmiş hem de onaylanmış olmalıdır; sonradan backfill edilen hedefler o fold'un eğitiminden çıkarılır.
- Fark = tahmin − gerçekleşen; pozitif işaret fazla tahmini gösterir.
- Yalnız gerçek, onaylı kayıtlar kullanılır; sentetik/benchmark kayıtlar karıştırılmaz.
- Planlanan girdiler ve fiyatlar ancak timestamp'li, üretim öncesi snapshot ile özellik olur.
- Net çıktı, toplam/gerçekleşen maliyet, gerçekleşmiş kayıplar, gerçekleşen enerji ve işçilik model girdilerinden çıkarılır.
- Tahmini maliyet/tahmini net çıktı yönteminde iki alt model yalnız geçmiş eğitim penceresiyle fit edilir; gerçekleşen test maliyet/çıktısı yalnız hedef/ölçüm içindir.
- Hibrit maliyet formülündeki bilinen alt toplam yalnız plan miktarı/fiyatı ve fason oranından türetilir; muhasebe kapsamının gerçek süreçle eşleşmesi doğrulanmalıdır.
- Ciddi hata oranı ancak iş sahibi TL/kg eşiği verirse hesaplanır.
- Maliyet/yield ve hibrit yaklaşımlarında gerçekleşen test maliyeti/çıktı özellik olarak kullanılmaz.
- Hash kontrolü pickle dosyası içeriğinin sabitlenmiş yerel baytlarla aynı olduğunu gösterir; dijital imza, güvenilir kaynak veya bilimsel doğrulama değildir.
- Veri doğrulama ve satır/alan sorunları JSON raporundadır; hatalı kayıtlar silinmez/düzeltilmez.

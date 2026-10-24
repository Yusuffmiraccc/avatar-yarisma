from pathlib import Path
import csv
from datetime import date

ROOT = Path(__file__).resolve().parent
benchmark_path = ROOT / "data" / "external" / "ekp_published_cost_structure_benchmark.csv"
reports_dir = ROOT / "reports"
reports_dir.mkdir(parents=True, exist_ok=True)

if not benchmark_path.exists():
    raise FileNotFoundError(
        f"Benchmark CSV bulunamadi: {benchmark_path}\n"
        "Once python .\\ekp_external_benchmark.py komutunu calistirin."
    )

with benchmark_path.open("r", encoding="utf-8-sig", newline="") as f:
    benchmark = list(csv.DictReader(f, delimiter=";"))

if not benchmark:
    raise ValueError("Benchmark CSV bos.")

shares = []
for row in benchmark:
    shares.append((row["cost_component"], float(row["share_pct"])))
share_total = sum(value for _, value in shares)

report = []
report += [
    "# EKP Modeli — Değerlendirme ve Harici Benchmark Raporu",
    "",
    f"**Rapor tarihi:** {date.today().isoformat()}",
    "",
    "## 1. Mevcut sentetik test sonuçları",
    "",
    "Aşağıdaki değerler daha önce çalıştırılan `training/validate_models.py` raporundan alınmıştır. "
    "Bunlar sentetik test kümesi sonuçlarıdır; gerçek üretim performansı olarak sunulmamalıdır.",
    "",
    "| EKP yaklaşımı | MAE (TL/kg) | RMSE (TL/kg) | R² | Medyan referansa göre MAE iyileşmesi |",
    "|---|---:|---:|---:|---:|",
    "| Medyan referans, Scenario A | 51.68 | — | — | — |",
    "| Random Forest, Scenario A | 49.87 | 61.22 | 0.1070 | %3.49 |",
    "| Extra Trees, Scenario A | 51.09 | 63.12 | 0.0509 | %1.13 kötüleşme |",
    "| Random Forest, Scenario B* | 12.85 | 16.94 | 0.9316 | %75.14 |",
    "| Extra Trees, Scenario B* | 10.47 | 14.24 | 0.9517 | %79.74 |",
    "",
    "*Scenario B, kuruma kaybı ve ayıklama firesi alanlarını içerir. Bu alanlar gerçekleşmiş/üretim sonrası ölçümlerse üretim öncesi tahminde kullanımları veri sızıntısıdır. Bu yüzden Scenario B skorları üretime hazır model kanıtı değildir.*",
    "",
    "## 2. Harici, tarihsel maliyet yapısı benchmark'ı",
    "",
    "Kaynak dosya: `data/external/ekp_published_cost_structure_benchmark.csv`",
    "",
    "| Maliyet bileşeni | Yayındaki pay |",
    "|---|---:|",
]
for component, share in shares:
    report.append(f"| {component} | %{share:.2f} |")
report += [
    f"| **Toplam** | **%{share_total:.2f}** |",
    "",
    "Bu tablo toplulaştırılmış tarihsel maliyet paylarını içerir; parti bazında toplam maliyet ve net üretim miktarı yoktur. "
    "Bu nedenle buradan EKP MAE/RMSE/R² hesaplanamaz ve bu satırlar eğitim kayıtlarına eklenmemelidir.",
    "",
    "## 3. Karar",
    "",
    "- Mevcut üretim modelleri korunur; bu rapor onları değiştirmez.",
    "- Scenario A, sentetik veride basit medyan referansına karşı yalnızca sınırlı iyileşme göstermiştir.",
    "- Scenario B sonuçları, kayıp değişkenlerinin tahmin anında bilindiği kanıtlanmadan kabul edilmemelidir.",
    "- Harici benchmark yalnızca maliyet bileşenlerinin makullük kontrolüdür; bağımsız tahmin doğrulaması değildir.",
    "",
    "## 4. Gerçek veride test için gereken alanlar",
    "",
    "Her anonimleştirilmiş üretim partisi için asgari alanlar:",
    "",
    "- Parti/lot kimliği ve üretim tarihi",
    "- Tahmin anında bilinen hammadde miktarları, birim fiyatlar ve reçete/proses bilgileri",
    "- Gerçekleşen toplam parti maliyeti (TL)",
    "- Ölçülmüş net sucuk çıktısı (kg)",
    "- Kayıtlı gerçek EKP = toplam maliyet / net çıktı (TL/kg)",
    "",
    "Testte gerçek EKP hedefi, aynı ayrılmış test partileri üzerinde medyan referans ve model tahminleriyle karşılaştırılmalı; MAE, RMSE ve R² raporlanmalıdır. "
    "Aynı partinin türev kayıtları eğitim ve test kümelerine dağıtılmamalıdır.",
    "",
    "## 5. Lot izlenebilirliği ve geri çağırma",
    "",
    "Lot ilişkileri yapay zekâ tahmininden bağımsız kesin kayıtlarla kurulmalıdır: hammadde lotu → üretim partisi → nihai ürün lotu → sevkiyat/müşteri. "
    "Geri çağırma kapsamı bu ilişkilerden sorgulanmalı; model skoru hiçbir zaman lot bağlantısının yerine geçmemelidir.",
    "",
    "**Sonuç:** EKP modeli için sentetik test ve harici maliyet yapısı kontrolü mevcut; gerçek parti bazlı dış doğrulama henüz yoktur.",
    "",
]
out = reports_dir / "ekp_evaluation_and_external_benchmark.md"
out.write_text("\n".join(report), encoding="utf-8")
print("Rapor oluşturuldu:", out)
print("Benchmark maliyet payı toplamı: %.2f%%" % share_total)
print("Üretim model dosyaları değiştirilmedi.")

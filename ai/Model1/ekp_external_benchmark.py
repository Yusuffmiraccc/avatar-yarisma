from pathlib import Path
import csv
from datetime import date

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "external"
REPORTS = ROOT / "reports"
DATA.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

SOURCE = "https://agrifoodscience.com/index.php/TURJAF/article/view/9152"
ROWS = [
    ("Sucuk", "Hammadde", 75.11),
    ("Sucuk", "Yardimci malzemeler", 9.47),
    ("Sucuk", "Iscilik", 5.08),
    ("Sucuk", "Enerji", 2.75),
    ("Sucuk", "Diger giderler", 7.59),
]
fields = ["product", "cost_component", "share_pct", "source_period", "source_sample", "data_type", "source_url"]
with (DATA / "ekp_published_cost_structure_benchmark.csv").open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
    writer.writeheader()
    for product, component, share in ROWS:
        writer.writerow({
            "product": product, "cost_component": component, "share_pct": share,
            "source_period": "2014-2015", "source_sample": "15 enterprises; published aggregate",
            "data_type": "historical aggregate benchmark; not batch-level", "source_url": SOURCE
        })

total = sum(row[2] for row in ROWS)
report = (
    "# EKP — Harici Maliyet Yapısı Kıyaslaması\n\n"
    f"**Tarih:** {date.today().isoformat()}\n\n"
    "## Kaynak\n"
    "Polat, M. & Cevger, Y. (2026), *Analysis of Factors Affecting the Production Costs of Red Meat Products in Türkiye*.\n"
    f"Kaynak: {SOURCE}\n\n"
    "Çalışma, 2014–2015 üretim dönemlerinde 15 işletmeden toplanan verileri inceler.\n\n"
    "| Maliyet bileşeni | Toplam maliyetteki pay |\n|---|---:|\n"
    "| Hammadde | %75,11 |\n| Yardımcı malzemeler | %9,47 |\n"
    "| İşçilik | %5,08 |\n| Enerji | %2,75 |\n| Diğer giderler | %7,59 |\n"
    f"| **Toplam** | **%{total:.2f}** |\n\n"
    "## Yorum ve sınırlılıklar\n"
    "- Bu, tarihsel ve toplulaştırılmış maliyet benchmark'ıdır; parti bazlı eğitim verisi değildir.\n"
    "- Maliyet varsayımlarına yönelik makullük kontrolü olarak kullanılabilir.\n"
    "- Gerçek parti maliyeti ve ölçülmüş net çıktı içermediği için MAE, RMSE veya R² hesaplanamaz.\n"
    "- Güncel TL/kg maliyetini veya bugünkü işletmeleri doğrudan temsil etmez.\n"
    "- Bu satırları sentetik partilere ekleyerek gerçek parti sayısını artırmış gibi göstermeyin.\n\n"
    "## Gerçek EKP doğrulaması\n"
    "Gerçek EKP = gerçek toplam parti maliyeti / ölçülmüş net çıktı (kg). "
    "Anonimleştirilmiş gerçek partilerde girdi miktarları/fiyatları, toplam maliyet ve net çıktı bulunmalıdır. "
    "Medyan referans ve model aynı ayrılmış test kümesinde MAE, RMSE ve R² ile karşılaştırılmalıdır. "
    "Üretim sonu ölçülen fire/kuruma değerleri, üretim öncesi tahminde yalnızca önceden bilinen plan değerleri ise kullanılmalıdır.\n\n"
    "**Durum:** Harici maliyet benchmark'ı hazırlandı; gerçek parti bazlı model doğrulaması değildir. "
    "`models/ekp_model.joblib` ve `models/yield_model.joblib` değiştirilmez.\n"
)
(REPORTS / "ekp_external_benchmark_note.md").write_text(report, encoding="utf-8")
print("Created:", DATA / "ekp_published_cost_structure_benchmark.csv")
print("Created:", REPORTS / "ekp_external_benchmark_note.md")
print("Cost share total:", total)

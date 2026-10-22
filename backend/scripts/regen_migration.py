"""Geliştirme yardımcısı: henüz yayınlanmamış tek 'initial schema' migration'ını modellerden yeniden üretir.

Yalnızca yerel/izole DB'de kullanın. Kullanım: python -m scripts.regen_migration
"""
import glob
import os
import re
import subprocess
import sys

PY = sys.executable
ALEMBIC = [PY, "-m", "alembic"]


def run(*args):
    return subprocess.run([*ALEMBIC, *args], check=True, capture_output=True, text=True)


def main() -> None:
    try:
        run("downgrade", "base")
    except subprocess.CalledProcessError:
        pass
    for f in glob.glob("migrations/versions/*_initial_schema.py"):
        os.remove(f)
    run("revision", "--autogenerate", "-m", "initial schema")
    path = glob.glob("migrations/versions/*_initial_schema.py")[0]
    src = open(path, encoding="utf-8").read()
    head, down = src.split("def downgrade()")
    # MySQL: FK'nin ihtiyaç duyduğu indeks tablodan önce düşürülemez; drop_table indeksleri zaten siler.
    down = re.sub(r"^\s*op\.drop_index\(.*?\)\n", "", down, flags=re.M)
    open(path, "w", encoding="utf-8").write(head + "def downgrade()" + down)
    run("upgrade", "head")
    print("OK", path)


if __name__ == "__main__":
    main()

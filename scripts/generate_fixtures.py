"""Generuje przykładowe dokumenty do folderu ``examples/``.

Przykłady służą do ręcznych testów aplikacji i demonstracji w README:
    python scripts/generate_fixtures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tests import docfactory  # noqa: E402

OUT = REPO_ROOT / "examples"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    docfactory.make_signed_scan().save(OUT / "skan_protokol_podpisany.png")
    docfactory.make_clean_scan().save(OUT / "skan_regulamin_bez_podpisu.jpg", quality=90)
    (OUT / "faktura_bez_podpisu.pdf").write_bytes(docfactory.make_text_pdf())
    (OUT / "umowa_podpis_graficzny.pdf").write_bytes(docfactory.make_pdf_with_signature_image())
    (OUT / "aneks_podpis_cyfrowy_pkcs7.pdf").write_bytes(docfactory.make_digitally_signed_pdf())
    (OUT / "aneks_podpis_cyfrowy_pades.pdf").write_bytes(
        docfactory.make_digitally_signed_pdf(pades=True)
    )
    (OUT / "wniosek_puste_pole_podpisu.pdf").write_bytes(
        docfactory.make_pdf_with_empty_sig_field()
    )
    print(f"Wygenerowano przykłady w {OUT}:")
    for path in sorted(OUT.iterdir()):
        print(f"  {path.name} ({path.stat().st_size} B)")


if __name__ == "__main__":
    main()

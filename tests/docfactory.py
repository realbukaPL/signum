"""Fabryka dokumentów testowych.

Generuje realistyczne dokumenty bez danych osobowych: syntetyczne skany
(podpis odręczny w stylu kursywy, pieczątka), PDF-y tekstowe (reportlab),
PDF z graficznym podpisem oraz PDF-y podpisane cyfrowo naprawdę
(pyhanko + samopodpisany certyfikat). Używana przez testy jednostkowe
i skrypt ``scripts/generate_fixtures.py`` (przykłady do testów ręcznych).
"""

from __future__ import annotations

import datetime
import io
import math
import random
import tempfile
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

SCAN_SIZE = (1000, 1414)  # proporcje A4 w pionie

# Ramki „prawdy” dla syntetycznego skanu (piksele: x0, y0, x1, y1).
SCAN_SIGNATURE_BOX = (600, 1120, 930, 1245)
SCAN_STAMP_BOX = (120, 1100, 340, 1280)


def draw_cursive_signature(
    draw: ImageDraw.ImageDraw,
    x0: float,
    baseline: float,
    width: float,
    seed: int = 7,
    color: tuple[int, int, int] = (15, 15, 100),
) -> None:
    """Rysuje wiarygodny „odręczny” podpis: pętle o zmiennej amplitudzie."""
    rng = random.Random(seed)
    points: list[tuple[float, float]] = []
    x = x0
    n_loops = 9
    for i in range(n_loops):
        amplitude = rng.choice([18, 26, 44, 30, 55])
        loop_width = width / n_loops * rng.uniform(0.7, 1.3)
        for step in range(40):
            t = step / 40
            px = x + t * loop_width + math.sin(t * math.pi * 2) * loop_width * 0.18
            py = baseline - math.sin(t * math.pi * 2 + i) * amplitude - t * 2
            points.append((px, py))
        x += loop_width
    for step in range(60):  # zamaszyste podkreślenie
        t = step / 59
        points.append((x0 + t * width * 1.05, baseline + 14 + math.sin(t * 6) * 5))
    for a, b in pairwise(points):
        if math.dist(a, b) < 40:
            draw.line([a, b], fill=color, width=3)


def _draw_stamp(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    color = (30, 60, 160)
    draw.ellipse(box, outline=color, width=4)
    draw.ellipse((x0 + 18, y0 + 15, x1 - 18, y1 - 15), outline=color, width=2)
    draw.text(((x0 + x1) / 2 - 55, (y0 + y1) / 2 - 20), "URZAD MIASTA", fill=color)
    draw.text(((x0 + x1) / 2 - 45, (y0 + y1) / 2 + 4), "WARSZAWA", fill=color)


def _draw_text_lines(draw: ImageDraw.ImageDraw, seed: int, count: int, y_start: int) -> None:
    rng = random.Random(seed)
    y = y_start
    for _ in range(count):
        draw.line([(80, y), (rng.randint(650, 920), y)], fill=(70, 70, 70), width=3)
        y += 28


def make_signed_scan() -> Image.Image:
    """Skan „protokołu” z podpisem odręcznym i pieczątką."""
    img = Image.new("RGB", SCAN_SIZE, "white")
    d = ImageDraw.Draw(img)
    d.text((80, 60), "PROTOKOL ODBIORU ROBOT BUDOWLANYCH", fill="black")
    d.text((80, 90), "sporzadzony dnia 12.07.2026 r.", fill="black")
    _draw_text_lines(d, seed=1, count=28, y_start=150)
    draw_cursive_signature(d, 610, 1200, 300)
    d.line([(600, 1245), (930, 1245)], fill="black", width=2)
    d.text((700, 1255), "(podpis kierownika)", fill="black")
    _draw_stamp(d, SCAN_STAMP_BOX)
    return img


def make_clean_scan() -> Image.Image:
    """Skan „regulaminu” bez żadnych podpisów (kontrola fałszywych pozytywów)."""
    img = Image.new("RGB", SCAN_SIZE, "white")
    d = ImageDraw.Draw(img)
    d.text((80, 60), "REGULAMIN PRACY ZDALNEJ", fill="black")
    _draw_text_lines(d, seed=3, count=40, y_start=130)
    return img


def make_text_pdf(title: str = "FAKTURA VAT 42/2026", pages: int = 1) -> bytes:
    """Zwykły PDF tekstowy bez podpisów."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for page in range(pages):
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 790, title if page == 0 else f"{title} — strona {page + 1}")
        c.setFont("Helvetica", 11)
        for i in range(30):
            c.drawString(72, 750 - i * 20, f"Pozycja {page * 30 + i + 1}: opis uslugi ...")
        c.showPage()
    c.save()
    return buf.getvalue()


def make_pdf_with_signature_image() -> bytes:
    """PDF z wklejonym graficznym podpisem (jak zeskanowana umowa zapisana do PDF)."""
    sig_img = Image.new("RGBA", (360, 140), (0, 0, 0, 0))
    draw_cursive_signature(ImageDraw.Draw(sig_img), 20, 90, 300, seed=11)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 790, "UMOWA O SWIADCZENIE USLUG")
    c.setFont("Helvetica", 11)
    for i in range(25):
        c.drawString(72, 750 - i * 20, f"Paragraf {i + 1}. Tresc umowy ...")
    c.drawImage(ImageReader(sig_img), 300, 120, width=220, height=85, mask="auto")
    c.line(290, 118, 530, 118)
    c.setFont("Helvetica", 9)
    c.drawString(360, 105, "(podpis zleceniobiorcy)")
    c.showPage()
    c.save()
    return buf.getvalue()


def _self_signed_signer():  # type: ignore[no-untyped-def]
    """Samopodpisany certyfikat + klucz jako pyhanko SimpleSigner (tylko testy)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from pyhanko.sign import signers

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Jan Testowy"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Signum Test"),
        ]
    )
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    # SimpleSigner.load przyjmuje wyłącznie ścieżki plików.
    with tempfile.TemporaryDirectory() as tmp:
        key_path = Path(tmp) / "key.pem"
        cert_path = Path(tmp) / "cert.pem"
        key_path.write_bytes(key_pem)
        cert_path.write_bytes(cert_pem)
        return signers.SimpleSigner.load(
            str(key_path), str(cert_path), key_passphrase=None
        )


def make_digitally_signed_pdf(visible: bool = True, pades: bool = False) -> bytes:
    """PDF podpisany cyfrowo naprawdę (pyhanko, cert samopodpisany).

    Domyślnie CMS/PKCS#7 (``adbe.pkcs7.detached``); ``pades=True`` daje
    podpis PAdES (``ETSI.CAdES.detached``).
    """
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign import signers
    from pyhanko.sign.fields import SigFieldSpec, SigSeedSubFilter

    base = make_text_pdf(title="ANEKS DO UMOWY NR 7/2026")
    writer = IncrementalPdfFileWriter(io.BytesIO(base))
    box = (330, 60, 540, 130) if visible else None
    out = signers.sign_pdf(
        writer,
        signers.PdfSignatureMetadata(
            field_name="Signature1",
            reason="Akceptacja aneksu",
            location="Warszawa",
            subfilter=SigSeedSubFilter.PADES if pades else SigSeedSubFilter.ADOBE_PKCS7_DETACHED,
        ),
        signer=_self_signed_signer(),
        new_field_spec=SigFieldSpec(sig_field_name="Signature1", box=box, on_page=0),
    )
    return out.getvalue()


def make_pdf_with_empty_sig_field() -> bytes:
    """PDF z niewypełnionym polem podpisu (dokument przygotowany do podpisu)."""
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign.fields import SigFieldSpec, append_signature_field

    base = make_text_pdf(title="WNIOSEK URLOPOWY")
    writer = IncrementalPdfFileWriter(io.BytesIO(base))
    append_signature_field(
        writer, SigFieldSpec(sig_field_name="PodpisPracownika", box=(330, 60, 540, 130))
    )
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def image_to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def image_to_jpeg_bytes(image: Image.Image, quality: int = 90) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()

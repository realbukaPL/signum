"""Testy orkiestracji: analiza dokumentu i przetwarzanie partii z atrapą modelu."""

from __future__ import annotations

import json
from pathlib import Path

from signum.ai.base import AIConnectionError, AIResponseError, VisionModel
from signum.core.models import DocumentStatus, SignatureKind
from signum.core.pipeline import BatchResult, CancelToken, DocumentAnalyzer, run_batch
from tests import docfactory


class FakeVisionModel(VisionModel):
    """Deterministyczna atrapa: zawsze zwraca zadany JSON."""

    def __init__(self, response: dict | None = None, fail_with: Exception | None = None):
        self.calls = 0
        self._fail_with = fail_with
        self._response = response or {
            "description": "Umowa testowa",
            "signatures": [
                {"type": "handwritten", "confidence": 92, "box_2d": [800, 600, 880, 900]}
            ],
        }

    @property
    def name(self) -> str:
        return "fake-model"

    def _generate(self, image_jpeg: bytes, prompt: str) -> str:
        self.calls += 1
        if self._fail_with is not None:
            raise self._fail_with
        return json.dumps(self._response)

    def check_connection(self) -> str:
        return "ok"


def _analyzer(model: VisionModel, max_pages: int = 5) -> DocumentAnalyzer:
    return DocumentAnalyzer(model=model, max_pages=max_pages, image_max_side=512)


def _scan_file(tmp_path: Path) -> Path:
    path = tmp_path / "skan.png"
    docfactory.make_signed_scan().save(path)
    return path


class TestDocumentAnalyzer:
    def test_skan_z_podpisem(self, tmp_path: Path) -> None:
        result = _analyzer(FakeVisionModel()).analyze(_scan_file(tmp_path), CancelToken())
        assert result.status is DocumentStatus.OK
        assert result.title == "Umowa testowa"
        assert result.is_signed
        finding = result.findings[0]
        assert finding.kind is SignatureKind.HANDWRITTEN
        assert finding.confidence == 92
        assert finding.crop_png is not None
        assert finding.crop_png.startswith(b"\x89PNG")

    def test_pdf_podpisany_cyfrowo_laczy_zrodla(
        self, tmp_path: Path, signed_pdf_bytes: bytes
    ) -> None:
        pdf = tmp_path / "aneks.pdf"
        pdf.write_bytes(signed_pdf_bytes)
        model = FakeVisionModel(response={"description": "Aneks do umowy", "signatures": []})
        result = _analyzer(model).analyze(pdf, CancelToken())
        assert result.status is DocumentStatus.OK
        kinds = [f.kind for f in result.findings]
        assert kinds == [SignatureKind.DIGITAL]
        assert result.findings[0].confidence == 100
        assert result.findings[0].crop_png is not None  # widoczny widget podpisu

    def test_uszkodzony_plik_to_error_nie_wyjatek(self, tmp_path: Path) -> None:
        bad = tmp_path / "zepsuty.pdf"
        bad.write_bytes(b"nie pdf")
        result = _analyzer(FakeVisionModel()).analyze(bad, CancelToken())
        assert result.status is DocumentStatus.ERROR
        assert result.error

    def test_bledna_odpowiedz_jest_ponawiana(self, tmp_path: Path) -> None:
        model = FakeVisionModel(fail_with=AIResponseError("zly json"))
        result = _analyzer(model).analyze(_scan_file(tmp_path), CancelToken())
        assert result.status is DocumentStatus.ERROR
        assert model.calls == 2  # pierwsza próba + jedno ponowienie

    def test_tytul_z_nazwy_pliku_gdy_brak_opisu(self, tmp_path: Path) -> None:
        model = FakeVisionModel(response={"description": "", "signatures": []})
        result = _analyzer(model).analyze(_scan_file(tmp_path), CancelToken())
        assert result.title == "skan"

    def test_limit_stron(self, tmp_path: Path) -> None:
        pdf = tmp_path / "dlugi.pdf"
        pdf.write_bytes(docfactory.make_text_pdf(pages=4))
        model = FakeVisionModel(response={"description": "Faktura", "signatures": []})
        result = _analyzer(model, max_pages=2).analyze(pdf, CancelToken())
        assert result.page_count == 4
        assert result.pages_analyzed == 2
        assert model.calls == 2


class TestRunBatch:
    def test_blad_pliku_nie_przerywa_partii(self, tmp_path: Path) -> None:
        good = _scan_file(tmp_path)
        bad = tmp_path / "zly.pdf"
        bad.write_bytes(b"x")
        batch = run_batch([bad, good], _analyzer(FakeVisionModel()), CancelToken())
        assert batch.abort_error is None
        assert [r.status for r in batch.results] == [DocumentStatus.ERROR, DocumentStatus.OK]

    def test_blad_polaczenia_przerywa_partie(self, tmp_path: Path) -> None:
        files = [_scan_file(tmp_path), tmp_path / "nast1.png", tmp_path / "nast2.png"]
        docfactory.make_clean_scan().save(files[1])
        docfactory.make_clean_scan().save(files[2])
        model = FakeVisionModel(fail_with=AIConnectionError("brak połączenia"))
        batch = run_batch(files, _analyzer(model), CancelToken())
        assert batch.abort_error is not None
        assert batch.results[0].status is DocumentStatus.ERROR
        assert all(r.status is DocumentStatus.CANCELLED for r in batch.results[1:])
        assert len(batch.results) == 3

    def test_anulowanie_oznacza_pozostale(self, tmp_path: Path) -> None:
        files = [_scan_file(tmp_path)]
        cancel = CancelToken()
        cancel.cancel()
        batch = run_batch(files, _analyzer(FakeVisionModel()), cancel)
        assert [r.status for r in batch.results] == [DocumentStatus.CANCELLED]

    def test_callbacki_i_statystyki(self, tmp_path: Path) -> None:
        started: list[str] = []
        done: list[str] = []
        files = [_scan_file(tmp_path)]
        batch = run_batch(
            files,
            _analyzer(FakeVisionModel()),
            CancelToken(),
            on_file_start=lambda i, n, p: started.append(f"{i + 1}/{n} {p.name}"),
            on_file_done=lambda i, r: done.append(r.title),
        )
        assert started == ["1/1 skan.png"]
        assert done == ["Umowa testowa"]
        assert batch.signed_count == 1
        assert batch.error_count == 0
        assert batch.model_name == "fake-model"
        assert isinstance(batch, BatchResult)

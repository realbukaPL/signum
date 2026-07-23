"""Bezpieczne uruchamianie trybu CLI."""

from __future__ import annotations

from pathlib import Path

import pytest

from signum.cli import build_parser, main


def test_cli_wymaga_jawnego_potwierdzenia(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    document = tmp_path / "skan.png"
    document.write_bytes(b"not-read-before-risk-acknowledgement")

    assert main([str(document)]) == 2
    captured = capsys.readouterr()
    assert "OSTRZEŻENIE PRZED ANALIZĄ" in captured.err
    assert "--acknowledge-risks" in captured.err


@pytest.mark.parametrize("value", ["0", "-1", "501"])
def test_cli_odrzuca_niebezpieczny_limit_stron(value: str) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["dokument.pdf", "--max-pages", value])

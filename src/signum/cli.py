"""Tryb wiersza poleceń: ``signum-cli`` — ta sama analiza co w GUI, bez okna.

Przydatny do automatyzacji (zadania wsadowe, skrypty) i do testów end-to-end.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from signum import __version__
from signum.ai import create_vision_model
from signum.config import AppConfig
from signum.core.discovery import collect_documents
from signum.core.models import DocumentResult, DocumentStatus
from signum.core.pipeline import BatchResult, CancelToken, DocumentAnalyzer, run_batch
from signum.report import write_csv, write_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="signum-cli",
        description="Wykrywa podpisy (odręczne, parafki, pieczątki, cyfrowe) "
        "w dokumentach PDF i skanach.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="pliki i/lub foldery do analizy")
    parser.add_argument("--no-recursive", action="store_true", help="nie schodź do podfolderów")
    parser.add_argument("--html", type=Path, metavar="PLIK", help="zapisz raport HTML")
    parser.add_argument("--csv", type=Path, metavar="PLIK", help="zapisz raport CSV")
    parser.add_argument("--provider", choices=("ollama", "openai", "anthropic"))
    parser.add_argument("--model", help="nazwa modelu (nadpisuje ustawienia)")
    parser.add_argument("--max-pages", type=int, metavar="N", help="limit stron na dokument")
    parser.add_argument("--version", action="version", version=f"signum {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = AppConfig.load()
    if args.provider:
        config.provider = args.provider
    if args.model:
        if config.provider == "ollama":
            config.ollama_model = args.model
        elif config.provider == "openai":
            config.openai_model = args.model
        else:
            config.anthropic_model = args.model
    if args.max_pages:
        config.max_pages_per_doc = args.max_pages

    files = collect_documents(args.paths, recursive=not args.no_recursive)
    if not files:
        print("Nie znaleziono obsługiwanych dokumentów (PDF/JPG/PNG/TIFF/BMP/WEBP).")
        return 2

    model = create_vision_model(config)
    print(f"Model: {model.name}")
    print(f"Plików do analizy: {len(files)}\n")

    analyzer = DocumentAnalyzer(
        model=model,
        max_pages=config.max_pages_per_doc,
        image_max_side=config.model_image_max_side,
    )

    def on_start(index: int, total: int, path: Path) -> None:
        print(f"[{index + 1}/{total}] {path.name} ...", flush=True)

    def on_done(_index: int, result: DocumentResult) -> None:
        print(f"    {_summarize(result)}", flush=True)

    batch = run_batch(files, analyzer, CancelToken(), on_start, on_done)
    _print_summary(batch)

    if args.html:
        write_html(args.html, batch)
        print(f"Raport HTML: {args.html}")
    if args.csv:
        write_csv(args.csv, batch)
        print(f"Raport CSV: {args.csv}")
    return 1 if batch.abort_error else 0


def _summarize(result: DocumentResult) -> str:
    if result.status == DocumentStatus.ERROR:
        return f"BŁĄD: {result.error}"
    if not result.is_signed:
        return f"„{result.title}” — brak podpisów"
    return (
        f"„{result.title}” — PODPISANY: {result.kinds_summary} "
        f"(max pewność {result.max_confidence}%)"
    )


def _print_summary(batch: BatchResult) -> None:
    print(f"\n{'=' * 60}")
    print(
        f"Przetworzono {len(batch.results)} plików w {batch.duration_s:.0f} s — "
        f"z podpisami: {batch.signed_count}, błędy: {batch.error_count}"
    )
    if batch.abort_error:
        print(f"PARTIĘ PRZERWANO: {batch.abort_error}")


if __name__ == "__main__":
    sys.exit(main())

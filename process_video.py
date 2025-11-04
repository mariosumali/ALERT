"""Command line entry point for running the body cam analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from src.platform import VideoAnalysisPipeline


@click.command()
@click.argument("video_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--video-id",
    type=str,
    default=None,
    help="Optional identifier to override the derived video id.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("data/processed/analyses"),
    show_default=True,
    help="Directory where the analysis JSON should be stored.",
)
@click.option(
    "--print-json/--no-print-json",
    default=True,
    help="Print the analysis JSON to stdout after processing.",
)
def main(video_path: Path, video_id: Optional[str], output_dir: Path, print_json: bool) -> None:
    """Analyse ``video_path`` and store the resulting JSON report."""

    pipeline = VideoAnalysisPipeline()
    result = pipeline.process(video_path, video_id=video_id)
    output_file = pipeline.save_result(result, output_dir)

    click.echo(f"Analysis written to: {output_file}")

    if print_json:
        click.echo("\n=== Summary ===")
        click.echo(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()

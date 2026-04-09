"""CLI entry point for data-factory."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from data_factory.core.config import load_config, AppConfig
from data_factory.core.storage import load_json

pass_config = click.make_pass_decorator(AppConfig, ensure=True)


@click.group()
@click.option("--config", "config_path", type=click.Path(exists=True), default=None, help="Path to config.yaml")
@click.option("--verbose", is_flag=True, default=False)
@click.pass_context
def main(ctx, config_path, verbose):
    """data-factory: Multi-platform data scraping tool."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")

    cfg_path = Path(config_path) if config_path else None
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(cfg_path)


def _get_config(ctx) -> AppConfig:
    return ctx.obj["config"]


@main.command()
@click.argument("platform")
@click.argument("query")
@click.option("--limit", default=20, type=int)
@click.option("--fetch", "do_fetch", is_flag=True, default=False, help="Fetch results after search")
@click.pass_context
def search(ctx, platform, query, limit, do_fetch):
    """Search a platform for content."""
    config = _get_config(ctx)
    from data_factory.core.pipeline import get_adapter
    adapter = get_adapter(platform, config)

    urls = adapter.search(query, limit=limit)
    for url in urls:
        click.echo(url)

    if do_fetch:
        from data_factory.core.pipeline import Pipeline
        pipeline = Pipeline(config)
        for url in urls:
            click.echo(f"Fetching: {url}")
            pipeline.run_full(url, platform)


@main.command()
@click.argument("url", required=False)
@click.option("--platform", default=None, help="Platform name (auto-detected from URL if omitted)")
@click.option("--from", "from_file", type=click.Path(exists=True), default=None, help="File with URLs (one per line)")
@click.option("--force", is_flag=True, default=False, help="Force full re-fetch")
@click.pass_context
def fetch(ctx, url, platform, from_file, force):
    """Fetch content from a URL or file of URLs."""
    config = _get_config(ctx)
    from data_factory.core.pipeline import Pipeline
    pipeline = Pipeline(config)

    urls = []
    if from_file:
        with open(from_file, encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    elif url:
        urls = [url]
    else:
        click.echo("Provide a URL or --from file", err=True)
        sys.exit(1)

    for u in urls:
        p = platform
        if not p:
            from data_factory.core.router import resolve_adapter
            adapter = resolve_adapter(u)
            p = adapter.adapter_name

        click.echo(f"[{p}] Fetching: {u}")
        result = pipeline.run_full(u, p)
        if result and result.status == "error":
            click.echo(f"  ERROR: {result.error}", err=True)
        else:
            click.echo(f"  Done.")


@main.command()
@click.option("--platform", default=None)
@click.option("--id", "item_id", default=None)
@click.option("--force", is_flag=True, default=False)
@click.pass_context
def refresh(ctx, platform, item_id, force):
    """Refresh comments for fetched items."""
    config = _get_config(ctx)
    from data_factory.core.pipeline import Pipeline
    pipeline = Pipeline(config)

    if platform and item_id:
        output_dir = config.output_dir / platform / item_id
        meta = load_json(output_dir / "meta.json")
        if meta:
            click.echo(f"Refreshing {platform}/{item_id}")
            pipeline.run_refresh(meta["url"], platform)
        return

    for platform_dir in config.output_dir.iterdir():
        if not platform_dir.is_dir():
            continue
        if platform and platform_dir.name != platform:
            continue
        for item_dir in platform_dir.iterdir():
            meta_path = item_dir / "meta.json"
            meta = load_json(meta_path)
            if not meta:
                continue
            from data_factory.core.refresh import needs_comment_refresh
            if force or needs_comment_refresh(meta):
                click.echo(f"Refreshing {platform_dir.name}/{item_dir.name}")
                pipeline.run_refresh(meta["url"], platform_dir.name)


@main.command()
@click.argument("step")
@click.option("--platform", required=True)
@click.option("--id", "item_id", default=None)
@click.pass_context
def process(ctx, step, platform, item_id):
    """Rerun a processing step (transcribe, images)."""
    config = _get_config(ctx)
    from data_factory.core.pipeline import Pipeline
    pipeline = Pipeline(config)

    if item_id:
        pipeline.run_step(step, platform, item_id)
        return

    platform_dir = config.output_dir / platform
    if not platform_dir.is_dir():
        click.echo(f"No data for platform: {platform}", err=True)
        return
    for item_dir in platform_dir.iterdir():
        if item_dir.is_dir() and (item_dir / "meta.json").exists():
            pipeline.run_step(step, platform, item_dir.name)


@main.group(name="index")
def index_group():
    """Index management commands."""


@index_group.command()
@click.option("--platform", default=None)
@click.pass_context
def status(ctx, platform):
    """Show index status."""
    config = _get_config(ctx)
    gi = load_json(config.output_dir / "global_index.json")

    if not gi:
        click.echo("No index found. Run 'data-factory index rebuild --all' first.")
        return

    click.echo(f"Total: {gi.get('total_count', 0)} items")
    click.echo(f"Updated: {gi.get('updated_at', 'never')}")
    click.echo()

    for pname, pinfo in gi.get("platforms", {}).items():
        if platform and pname != platform:
            continue
        click.echo(f"  {pname}: {pinfo['count']} items (updated {pinfo['last_updated']})")


@index_group.command()
@click.option("--platform", default=None)
@click.option("--all", "rebuild_all", is_flag=True, default=False)
@click.pass_context
def rebuild(ctx, platform, rebuild_all):
    """Rebuild index from disk."""
    config = _get_config(ctx)
    from data_factory.core.indexer import Indexer
    indexer = Indexer(config.output_dir)

    if rebuild_all:
        indexer.rebuild()
        click.echo("All indexes rebuilt.")
    elif platform:
        indexer.rebuild(platform)
        click.echo(f"Index rebuilt for {platform}.")
    else:
        click.echo("Specify --platform or --all", err=True)


@main.command(name="import")
@click.option("--platform", required=True)
@click.argument("source", type=click.Path(exists=True))
@click.pass_context
def import_cmd(ctx, platform, source):
    """Import data from exported files."""
    config = _get_config(ctx)
    from data_factory.core.pipeline import get_adapter
    adapter = get_adapter(platform, config)

    source_path = Path(source)
    if source_path.is_dir():
        files = list(source_path.iterdir())
    else:
        files = [source_path]

    for f in files:
        item_id = f.stem
        output_dir = config.output_dir / platform / item_id
        click.echo(f"Importing: {f.name} -> {platform}/{item_id}")
        try:
            adapter.import_file(f, output_dir)
        except NotImplementedError:
            click.echo(f"  Import not supported for {platform}", err=True)


if __name__ == "__main__":
    main()

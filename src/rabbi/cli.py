from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict
import json
from pathlib import Path
import shlex
import sys

from rabbi.config import (
    FilterConfig,
    ProjectPaths,
    init_project,
    load_project,
    save_project,
    write_json,
)
from rabbi.data.ingest import ingest_local_pgn, ingest_local_pgns
from rabbi.data.split import prepare_training_split
from rabbi.engine.package import EnginePackageConfig, create_engine_package
from rabbi.engine.smoke import smoke_test_engine
from rabbi.maia.converter import ConversionConfig, MaiaDataConverter
from rabbi.maia.trainer import MaiaIndividualTrainer, TrainerConfig
from rabbi.maia.weights import find_latest_weights
from rabbi.sources import (
    LichessDownloadOptions,
    download_chesscom_pgn,
    download_lichess_pgn,
    parse_source,
)
from rabbi.status import collect_status
from rabbi.system import run_doctor


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="rabbi")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check local dependencies.")
    doctor.add_argument("--maia-repo", type=Path)
    doctor.add_argument("--lc0", type=Path)
    doctor.add_argument("--base-model", type=Path)
    doctor.add_argument("--python", type=Path, help="Python executable for Maia scripts.")
    doctor.set_defaults(func=cmd_doctor)

    init = sub.add_parser("init", help="Create a project workspace.")
    init.add_argument("name")
    init.add_argument("--workspace", type=Path, default=Path.cwd())
    init.set_defaults(func=cmd_init)

    status = sub.add_parser("status", help="Show project pipeline status.")
    status.add_argument("--project", required=True, type=Path)
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    resolve = sub.add_parser("resolve", help="Parse source URLs, usernames, or PGN paths.")
    resolve.add_argument("sources", nargs="+")
    resolve.set_defaults(func=cmd_resolve)

    download = sub.add_parser("download", help="Download public games from a profile source.")
    download.add_argument("--project", required=True, type=Path)
    download.add_argument("--source", required=True)
    download.add_argument("--max-games", type=int)
    download.add_argument("--rated-only", action="store_true")
    download.add_argument("--perf-type")
    download.add_argument("--max-archives", type=int)
    download.set_defaults(func=cmd_download)

    ingest = sub.add_parser("ingest", help="Import and filter a local PGN file.")
    ingest.add_argument("--project", required=True, type=Path)
    ingest.add_argument("--pgn", required=True, type=Path, nargs="+")
    ingest.add_argument("--player", required=True)
    ingest.add_argument("--min-ply", type=int, default=10)
    ingest.add_argument("--include-variants", action="store_true")
    ingest.add_argument("--rated-only", action="store_true")
    ingest.set_defaults(func=cmd_ingest)

    convert = sub.add_parser("convert-data", help="Run or print Maia Individual PGN conversion.")
    convert.add_argument("--project", required=True, type=Path)
    convert.add_argument("--maia-repo", required=True, type=Path)
    convert.add_argument("--player", required=True)
    convert.add_argument("--input-pgn", type=Path)
    convert.add_argument("--output-dir", type=Path)
    convert.add_argument("--python", type=Path, help="Python executable for Maia scripts.")
    convert.add_argument("--run", action="store_true", help="Run conversion instead of only writing config.")
    convert.set_defaults(func=cmd_convert_data)

    prepare = sub.add_parser("prepare-train", help="Generate Maia Individual trainer config.")
    prepare.add_argument("--project", required=True, type=Path)
    prepare.add_argument("--maia-repo", required=True, type=Path)
    prepare.add_argument("--base-model", required=True, type=Path)
    prepare.add_argument("--python", type=Path, help="Python executable for Maia scripts.")
    prepare.add_argument("--player", required=True)
    prepare.add_argument("--output-dir", type=Path)
    prepare.add_argument("--dataset-root", type=Path)
    prepare.add_argument("--dataset-name")
    prepare.add_argument("--gpu", type=int, default=0)
    prepare.add_argument("--num-workers", type=int, default=4)
    prepare.add_argument("--batch-size", type=int, default=256)
    prepare.add_argument("--total-steps", type=int, default=150_000)
    prepare.add_argument("--validation-ratio", type=float, default=0.1)
    prepare.add_argument("--skip-pgn-split", action="store_true")
    prepare.add_argument("--run", action="store_true", help="Run training instead of only writing config.")
    prepare.set_defaults(func=cmd_prepare_train)

    package = sub.add_parser("package", help="Create a local UCI engine package.")
    package.add_argument("--project", required=True, type=Path)
    package.add_argument("--name", required=True)
    package.add_argument("--lc0", required=True, type=Path)
    package.add_argument("--weights", type=Path, help="Trained .pb.gz weights. If omitted, newest project model is used.")
    package.add_argument("--output", required=True, type=Path)
    package.add_argument("--style-nodes", type=int, default=1)
    package.add_argument("--analysis-mode", action="store_true")
    package.set_defaults(func=cmd_package)

    smoke = sub.add_parser("smoke-test", help="Verify a UCI engine executable responds correctly.")
    smoke.add_argument("--engine", required=True, type=Path)
    smoke.add_argument("--timeout", type=float, default=10.0)
    smoke.add_argument("--show-output", action="store_true")
    smoke.set_defaults(func=cmd_smoke_test)

    build = sub.add_parser("build", help="Run the end-to-end project workflow.")
    build.add_argument("--name", required=True)
    build.add_argument("--workspace", type=Path, default=Path.cwd())
    build.add_argument("--player", required=True)
    build.add_argument("--source", required=True, action="append")
    build.add_argument("--maia-repo", required=True, type=Path)
    build.add_argument("--base-model", required=True, type=Path)
    build.add_argument("--python", type=Path, help="Python executable for Maia scripts.")
    build.add_argument("--max-games", type=int)
    build.add_argument("--rated-only", action="store_true")
    build.add_argument("--perf-type")
    build.add_argument("--max-archives", type=int)
    build.add_argument("--min-ply", type=int, default=10)
    build.add_argument("--include-variants", action="store_true")
    build.add_argument("--run-convert", action="store_true")
    build.add_argument("--run-train", action="store_true")
    build.add_argument("--package", action="store_true")
    build.add_argument("--lc0", type=Path)
    build.add_argument("--weights", type=Path)
    build.add_argument("--engine-output", type=Path)
    build.set_defaults(func=cmd_build)

    wizard = sub.add_parser("wizard", help="Run a minimal interactive local-PGN workflow.")
    wizard.set_defaults(func=cmd_wizard)

    return parser


def cmd_doctor(args: Namespace) -> int:
    result = run_doctor(
        maia_repo=args.maia_repo,
        lc0_path=args.lc0,
        base_model=args.base_model,
        python_executable=args.python,
    )
    print(f"Python: {result.python_version}")
    for tool in result.tools:
        status = "ok" if tool.found else "missing"
        path = f" ({tool.path})" if tool.path else ""
        required = " required" if tool.required_for_mvp else ""
        detail = f" - {tool.detail}" if tool.detail else ""
        print(f"{tool.name}: {status}{path}{required}{detail}")
    return 0 if result.ok_for_mvp else 1


def cmd_init(args: Namespace) -> int:
    paths = init_project(args.name, args.workspace)
    print(paths.root)
    return 0


def cmd_status(args: Namespace) -> int:
    status = collect_status(args.project)
    if args.json:
        print(json.dumps(status.to_dict(), indent=2, sort_keys=True))
        return 0
    print(f"project: {status.project}")
    print(f"project config: {'ok' if status.has_project_config else 'missing'}")
    print(f"raw PGNs: {status.raw_pgn_count}")
    print(f"cleaned PGN: {status.cleaned_pgn or 'missing'} ({status.cleaned_pgn_bytes} bytes)")
    if status.ingest_report:
        print(
            "ingest: "
            f"{status.ingest_report.get('kept_games', 0)}/"
            f"{status.ingest_report.get('total_games', 0)} games, "
            f"{status.ingest_report.get('target_moves_estimate', 0)} target moves"
        )
    else:
        print("ingest: missing")
    print(f"conversion config: {'ok' if status.has_conversion_config else 'missing'}")
    print(f"training config: {'ok' if status.has_training_config else 'missing'}")
    print(f"latest weights: {status.latest_weights or 'missing'}")
    print(f"logs: {len(status.log_files)}")
    for log in status.log_files:
        print(f"  {log}")
    return 0


def cmd_resolve(args: Namespace) -> int:
    for source in args.sources:
        ref = parse_source(source)
        print(f"{source}\t{ref.kind}\t{ref.username or ''}\t{ref.value}")
    return 0


def cmd_download(args: Namespace) -> int:
    paths = ProjectPaths(args.project)
    ref = parse_source(args.source)
    if ref.kind == "lichess" and ref.username:
        output = paths.raw_dir / f"lichess-{ref.username}.pgn"
        download_lichess_pgn(
            ref.username,
            output,
            LichessDownloadOptions(
                max_games=args.max_games,
                rated=True if args.rated_only else None,
                perf_type=args.perf_type,
            ),
        )
    elif ref.kind == "chesscom" and ref.username:
        output = paths.raw_dir / f"chesscom-{ref.username}.pgn"
        download_chesscom_pgn(ref.username, output, max_archives=args.max_archives)
    else:
        raise ValueError(f"Unsupported downloadable source: {args.source}")
    print(output)
    return 0


def cmd_ingest(args: Namespace) -> int:
    paths = ProjectPaths(args.project)
    filters = FilterConfig(
        target_player=args.player,
        min_ply=args.min_ply,
        standard_only=not args.include_variants,
        rated_only=args.rated_only,
    )
    result = ingest_local_pgns(args.pgn, paths, filters)
    project = load_project(args.project)
    project.filters = filters
    save_project(paths, project)
    for raw_path in result.raw_paths:
        print(f"raw: {raw_path}")
    print(f"cleaned: {result.cleaned_path}")
    print(f"report: {result.report_path}")
    print(f"kept: {result.report.kept_games}/{result.report.total_games}")
    print(f"target move estimate: {result.report.target_moves_estimate}")
    return 0


def cmd_convert_data(args: Namespace) -> int:
    converter = MaiaDataConverter(
        ConversionConfig(
            maia_repo=args.maia_repo,
            project_dir=args.project,
            player_name=args.player,
            input_pgn=args.input_pgn,
            output_dir=args.output_dir,
            python=args.python,
        )
    )
    config_path = converter.write_config()
    command = converter.build_command()
    print(f"config: {config_path}")
    print("command:")
    print(" ".join(shlex.quote(part) for part in command))
    if args.run:
        converter.run(dry_run=False)
    return 0


def cmd_prepare_train(args: Namespace) -> int:
    split = None
    if not args.skip_pgn_split:
        split = prepare_training_split(ProjectPaths(args.project), args.player, validation_ratio=args.validation_ratio)
    output_dir = args.output_dir or (args.project / "models")
    config = TrainerConfig(
        maia_repo=args.maia_repo,
        project_dir=args.project,
        player_name=args.player,
        base_model=args.base_model,
        python=args.python,
        output_dir=output_dir,
        dataset_root=args.dataset_root,
        dataset_name=args.dataset_name,
        gpu=args.gpu,
        num_workers=args.num_workers,
        batch_size=args.batch_size,
        total_steps=args.total_steps,
    )
    trainer = MaiaIndividualTrainer(config)
    json_path = trainer.write_config()
    yaml_path = trainer.write_yaml_config()
    training_data = asdict(config)
    for key in ["maia_repo", "project_dir", "base_model", "python", "output_dir", "dataset_root"]:
        value = training_data.get(key)
        training_data[key] = str(value) if value is not None else None
    training_data.update(
        {
            "output_dir": str(config.resolved_output_dir),
            "dataset_root": str(config.resolved_dataset_root),
            "dataset_name": config.player_slug,
        }
    )
    write_json(ProjectPaths(args.project).training_config, training_data)
    command = trainer.build_command(yaml_path)
    if split is not None:
        print(f"train pgn: {split.train_path}")
        print(f"validate pgn: {split.validate_path}")
    print(f"json: {json_path}")
    print(f"yaml: {yaml_path}")
    print("command:")
    print(" ".join(shlex.quote(part) for part in command))
    if args.run:
        trainer.run(dry_run=False)
    return 0


def cmd_package(args: Namespace) -> int:
    weights = args.weights or find_latest_weights(args.project / "models")
    config = EnginePackageConfig(
        name=args.name,
        lc0_path=args.lc0,
        weights_path=weights,
        output_dir=args.output,
        style_nodes=args.style_nodes,
        analysis_mode=args.analysis_mode,
    )
    wrapper = create_engine_package(config)
    print(wrapper)
    print("Add this path as a local UCI engine in en-croissant.")
    return 0


def cmd_smoke_test(args: Namespace) -> int:
    result = smoke_test_engine(args.engine, timeout=args.timeout)
    print(f"engine: {result.engine}")
    print(f"uci smoke: {'ok' if result.ok else 'failed'}")
    if args.show_output or not result.ok:
        if result.stdout:
            print("stdout:")
            print(result.stdout.rstrip())
        if result.stderr:
            print("stderr:")
            print(result.stderr.rstrip())
    return 0 if result.ok else 1


def cmd_build(args: Namespace) -> int:
    paths = init_project(args.name, args.workspace)
    pgn_paths = _resolve_build_sources(args, paths)
    filters = FilterConfig(
        target_player=args.player,
        min_ply=args.min_ply,
        standard_only=not args.include_variants,
        rated_only=args.rated_only,
    )
    ingest_result = ingest_local_pgns(pgn_paths, paths, filters)

    converter = MaiaDataConverter(
        ConversionConfig(
            maia_repo=args.maia_repo,
            project_dir=paths.root,
            player_name=args.player,
            python=args.python,
        )
    )
    conversion_config = converter.write_config()
    conversion_command = converter.build_command()
    if args.run_convert:
        converter.run(dry_run=False)

    trainer = MaiaIndividualTrainer(
        TrainerConfig(
            maia_repo=args.maia_repo,
            project_dir=paths.root,
            player_name=args.player,
            base_model=args.base_model,
            python=args.python,
        )
    )
    training_json = trainer.write_config()
    training_yaml = trainer.write_yaml_config()
    training_command = trainer.build_command(training_yaml)
    if args.run_train:
        trainer.run(dry_run=False)

    package_path = None
    if args.package:
        if args.lc0 is None:
            raise ValueError("--lc0 is required when --package is set.")
        output = args.engine_output or (args.workspace / "engines" / paths.root.name)
        weights = args.weights or find_latest_weights(paths.root / "models")
        package_path = create_engine_package(
            EnginePackageConfig(
                name=args.name,
                lc0_path=args.lc0,
                weights_path=weights,
                output_dir=output,
            )
        )

    summary_path = paths.config_dir / "build-summary.json"
    write_json(
        summary_path,
        {
            "project": str(paths.root),
            "raw_paths": [str(path) for path in ingest_result.raw_paths],
            "cleaned_pgn": str(ingest_result.cleaned_path),
            "kept_games": ingest_result.report.kept_games,
            "total_games": ingest_result.report.total_games,
            "conversion_config": str(conversion_config),
            "conversion_command": conversion_command,
            "training_json": str(training_json),
            "training_yaml": str(training_yaml),
            "training_command": training_command,
            "package": str(package_path) if package_path else None,
        },
    )

    print(f"project: {paths.root}")
    print(f"cleaned: {ingest_result.cleaned_path}")
    print(f"kept: {ingest_result.report.kept_games}/{ingest_result.report.total_games}")
    print(f"summary: {summary_path}")
    print("conversion command:")
    print(" ".join(shlex.quote(part) for part in conversion_command))
    print("training command:")
    print(" ".join(shlex.quote(part) for part in training_command))
    if package_path:
        print(f"engine: {package_path}")
    return 0


def _resolve_build_sources(args: Namespace, paths: ProjectPaths) -> list[Path]:
    pgn_paths: list[Path] = []
    for source in args.source:
        ref = parse_source(source)
        if ref.kind == "pgn":
            pgn_paths.append(Path(ref.value))
        elif ref.kind == "pgn_dir":
            pgn_paths.extend(sorted(Path(ref.value).glob("*.pgn")))
        elif ref.kind == "lichess" and ref.username:
            output = paths.raw_dir / f"lichess-{ref.username}.pgn"
            download_lichess_pgn(
                ref.username,
                output,
                LichessDownloadOptions(
                    max_games=args.max_games,
                    rated=True if args.rated_only else None,
                    perf_type=args.perf_type,
                ),
            )
            pgn_paths.append(output)
        elif ref.kind == "chesscom" and ref.username:
            output = paths.raw_dir / f"chesscom-{ref.username}.pgn"
            download_chesscom_pgn(ref.username, output, max_archives=args.max_archives)
            pgn_paths.append(output)
        else:
            raise ValueError(f"Unsupported source for build: {source}")
    if not pgn_paths:
        raise ValueError("No PGN files were resolved from sources.")
    return pgn_paths


def cmd_wizard(_: Namespace) -> int:
    print("Rabbi minimal local-PGN wizard")
    name = input("Project name: ").strip()
    workspace = Path(input("Workspace directory [.]: ").strip() or ".").expanduser()
    pgn = Path(input("PGN file: ").strip()).expanduser()
    player = input("Target player name: ").strip()
    paths = init_project(name, workspace)
    result = ingest_local_pgn(pgn, paths, FilterConfig(target_player=player))
    print(f"Created project: {paths.root}")
    print(f"Filtered games: {result.report.kept_games}/{result.report.total_games}")
    print("Next: run prepare-train with your Maia Individual repo and base model paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

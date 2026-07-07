from pathlib import Path

from personal_maia.system.doctor import run_doctor


def test_doctor_checks_maia_repo_paths(tmp_path: Path):
    repo = tmp_path / "maia-individual"
    (repo / "1-data_generation").mkdir(parents=True)
    (repo / "2-training").mkdir(parents=True)
    (repo / "1-data_generation" / "9-pgn_to_training_data.sh").write_text("", encoding="utf-8")
    (repo / "2-training" / "train_transfer.py").write_text("", encoding="utf-8")
    base_model = tmp_path / "maia-1900"
    base_model.mkdir()

    result = run_doctor(maia_repo=repo, base_model=base_model)
    checks = {tool.name: tool.found for tool in result.tools}

    assert checks["maia repo"]
    assert checks["maia conversion script"]
    assert checks["maia training script"]
    assert checks["base model"]


def test_doctor_respects_explicit_missing_lc0_path(tmp_path: Path):
    result = run_doctor(lc0_path=tmp_path / "missing-lc0")
    checks = {tool.name: tool for tool in result.tools}

    assert not checks["lc0"].found
    assert checks["lc0"].path == str(tmp_path / "missing-lc0")


def test_doctor_reports_missing_maia_python(tmp_path: Path):
    result = run_doctor(python_executable=tmp_path / "missing-python")
    checks = {tool.name: tool for tool in result.tools}

    assert not checks["maia python"].found
    assert checks["maia python"].required_for_mvp
    assert not result.ok_for_mvp

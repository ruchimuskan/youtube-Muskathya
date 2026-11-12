from pathlib import Path

from app.config import get_settings
from app.database import Repository, session_scope


def test_settings_dirs_created(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'data' / 't.db'}")
    get_settings.cache_clear()
    s = get_settings()
    assert Path(s.data_dir).exists()


def test_init_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    with session_scope() as session:
        Repository(session).init_db()
    assert db.exists()

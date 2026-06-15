import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / f"dnd_dm_agent_test_{os.getpid()}.db"
TEST_DB.unlink(missing_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["DATA_DIR"] = str(Path(__file__).parents[2] / "data")
os.environ["EMBEDDING_BACKEND"] = "disabled"

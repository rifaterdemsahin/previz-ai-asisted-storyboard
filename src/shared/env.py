from pathlib import Path

def load_env(filepath: str = "config/.env") -> dict[str, str]:
    """Load KEY=VALUE pairs from a .env file (no external dependencies)."""
    env: dict[str, str] = {}
    path = Path(filepath)
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env

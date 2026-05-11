#!/usr/bin/env python3
"""Wake Hermes only when an Obsidian inbox file matches this cost tier.

Install into `~/.hermes/scripts/` and attach it to a Hermes cron job with
`--script hermes-obsidian-gate.py`. The last stdout line is a Hermes wake gate:
`{"wakeAgent": false}` means the scheduler skips the LLM entirely.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_VAULT = "~/Documents/Obsidian Vault"
VAULT = Path(os.getenv("OBSIDIAN_VAULT_PATH", DEFAULT_VAULT)).expanduser()
def detect_agent() -> str:
    explicit = os.getenv("OBSIDIAN_AGENT_NAME", "").strip()
    if explicit:
        return explicit
    env_checks = (
        ("HERMES_CONFIG", "hermes"),
        ("HERMES_HOME", "hermes"),
        ("OPENCLAW_CONFIG", "openclaw"),
        ("CODEX", "codex"),
        ("ANTHROPIC_API_KEY", "claude"),
    )
    for key, name in env_checks:
        if os.getenv(key):
            return name
    for command, name in (("hermes", "hermes"), ("openclaw", "openclaw"), ("codex", "codex"), ("claude", "claude")):
        if shutil.which(command):
            return name
    for path, name in (("~/.hermes", "hermes"), ("~/.openclaw", "openclaw"), ("~/.claude", "claude")):
        if Path(path).expanduser().is_dir():
            return name
    return "agent"


AGENT_NAME = detect_agent()
DEFAULT_INBOX = str(VAULT / "00-Inbox" / "for-agent")
INBOX = Path(os.getenv("OBSIDIAN_AGENT_INBOX", DEFAULT_INBOX)).expanduser()
PROCESSED_DIR = Path(
    os.getenv("OBSIDIAN_AGENT_PROCESSED", str(VAULT / "00-Inbox" / "processed"))
).expanduser()
OUTPUT_DIR = Path(
    os.getenv("OBSIDIAN_AGENT_OUTPUT", str(VAULT / "80-Outputs" / f"{AGENT_NAME}-response"))
).expanduser()
INDEX_FILE = Path(
    os.getenv("OBSIDIAN_AGENT_INDEX", str(OUTPUT_DIR / "_index.md"))
).expanduser()
ERROR_LOG = Path(os.getenv("HERMES_ERROR_LOG", "~/.hermes/logs/errors.log")).expanduser()
HERMES_HOME = Path(os.getenv("HERMES_HOME", "~/.hermes")).expanduser()
JOBS_FILE = Path(os.getenv("HERMES_CRON_JOBS_FILE", str(HERMES_HOME / "cron" / "jobs.json"))).expanduser()
STATE_FILE = Path(
    os.getenv("OBSIDIAN_GATE_STATE", str(HERMES_HOME / "cron" / "obsidian_gate_state.json"))
).expanduser()
SMB_URL = os.getenv("OBSIDIAN_SMB_URL", "").strip()
FATAL_THRESHOLD = int(os.getenv("OBSIDIAN_PROVIDER_FATAL_THRESHOLD", "3"))
SCRIPT_NAME = Path(sys.argv[0]).name
TIER = "strong" if "strong" in SCRIPT_NAME else os.getenv("OBSIDIAN_AGENT_TIER", "cheap")
FATAL_PATTERNS = ("Arrearage", "Invalid token", "Access denied")
STRONG_VALUES = {"strong", "deep", "plus", "large", "advanced", "深度", "强模型", "大模型"}
STRONG_KEYWORDS = ("model: strong", "model: deep", "深度分析", "复杂推理", "跨多篇", "强模型", "大模型")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    meta: dict[str, str] = {}
    for raw in text[4:end].splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        meta[key.strip().lower()] = value.strip().strip("\"'")
    return meta


def is_strong_task(path: Path) -> tuple[bool, dict[str, str], str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False, {}, ""
    head = text[:12000]
    meta = parse_frontmatter(head)
    values = {
        meta.get("model", "").lower(),
        meta.get("type", "").lower(),
        meta.get("priority", "").lower(),
    }
    strong = bool(values & STRONG_VALUES) or any(keyword in head for keyword in STRONG_KEYWORDS)
    preview = re.sub(r"\s+", " ", head).strip()[:500]
    return strong, meta, preview


def recent_provider_fatal(minutes: int = 30) -> str | None:
    if not ERROR_LOG.exists():
        return None
    cutoff = datetime.now() - timedelta(minutes=minutes)
    try:
        lines = ERROR_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-240:]
    except OSError:
        return None
    for line in reversed(lines):
        if not any(pattern in line for pattern in FATAL_PATTERNS):
            continue
        try:
            ts = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return line[:240]
        if ts >= cutoff:
            return line[:240]
    return None


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=STATE_FILE.parent, delete=False) as tmp:
        json.dump(state, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(STATE_FILE)


def pause_matching_jobs(reason: str) -> list[str]:
    if not JOBS_FILE.exists():
        return []
    try:
        data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    paused: list[str] = []
    now = datetime.now().astimezone().isoformat()
    script_names = {SCRIPT_NAME}
    if TIER == "strong":
        tier_markers = ("strong", "深度", "强模型")
    else:
        tier_markers = ("cheap", "普通", "省钱")
    for job in data.get("jobs", []):
        script = str(job.get("script") or "")
        name = str(job.get("name") or "")
        if Path(script).name not in script_names:
            continue
        if not any(marker in name for marker in tier_markers):
            continue
        if not job.get("enabled", True):
            continue
        job["enabled"] = False
        job["state"] = "paused"
        job["paused_at"] = now
        job["paused_reason"] = reason
        paused.append(str(job.get("id") or name or script))
    if paused:
        data["updated_at"] = now
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=JOBS_FILE.parent, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(JOBS_FILE)
    return paused


def note_provider_fatal(fatal: str) -> dict:
    state = load_state()
    key = f"{AGENT_NAME}:{TIER}"
    entry = state.get(key, {})
    entry["fatal_count"] = int(entry.get("fatal_count") or 0) + 1
    entry["last_fatal"] = fatal
    entry["last_fatal_at"] = datetime.now().astimezone().isoformat()
    paused: list[str] = []
    if entry["fatal_count"] >= FATAL_THRESHOLD:
        paused = pause_matching_jobs(f"provider fatal threshold reached: {fatal[:160]}")
        entry["paused_jobs"] = paused
    state[key] = entry
    save_state(state)
    return entry


def reset_provider_fatal() -> None:
    state = load_state()
    key = f"{AGENT_NAME}:{TIER}"
    if key in state and state[key].get("fatal_count"):
        state[key]["fatal_count"] = 0
        state[key]["last_ok_at"] = datetime.now().astimezone().isoformat()
        save_state(state)


def ensure_vault_available() -> bool:
    if VAULT.exists():
        return True
    if not SMB_URL:
        return False
    try:
        subprocess.run(
            ["osascript", "-e", f'mount volume "{SMB_URL}"'],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return VAULT.exists()


def emit_skip(reason: str, **extra: object) -> None:
    payload = {"wakeAgent": False, "tier": TIER, "reason": reason}
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False))


def main() -> None:
    if not ensure_vault_available():
        emit_skip("vault_unavailable", vault=str(VAULT), smb_configured=bool(SMB_URL))
        return

    pending = sorted(
        (p for p in INBOX.glob("*.md") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
    ) if INBOX.exists() else []

    if not pending:
        emit_skip("no_pending_markdown")
        return

    candidates = []
    for path in pending:
        strong, meta, preview = is_strong_task(path)
        if (TIER == "strong" and strong) or (TIER == "cheap" and not strong):
            candidates.append((path, strong, meta, preview))

    if not candidates:
        emit_skip("no_matching_tier_task", pending_count=len(pending))
        return

    fatal = recent_provider_fatal()
    if fatal:
        entry = note_provider_fatal(fatal)
        emit_skip(
            "provider_circuit_open",
            pending_count=len(pending),
            fatal=fatal,
            fatal_count=entry.get("fatal_count", 0),
            paused_jobs=entry.get("paused_jobs", []),
        )
        return

    reset_provider_fatal()
    target, strong, meta, preview = candidates[0]
    print(f"Pending Obsidian instruction count: {len(pending)}")
    print(f"Selected tier: {TIER}")
    print(f"Selected file: {target}")
    print(f"Processed dir: {PROCESSED_DIR}")
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"Index file: {INDEX_FILE}")
    if meta:
        print(f"Frontmatter: {json.dumps(meta, ensure_ascii=False, sort_keys=True)}")
    if preview:
        print(f"Preview: {preview}")
    print(json.dumps({
        "wakeAgent": True,
        "tier": TIER,
        "target_file": str(target),
        "strong_task": strong,
        "pending_count": len(pending),
        "processed_dir": str(PROCESSED_DIR),
        "output_dir": str(OUTPUT_DIR),
        "index_file": str(INDEX_FILE),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

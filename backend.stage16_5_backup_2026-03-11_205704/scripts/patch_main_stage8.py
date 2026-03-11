from pathlib import Path

main_path = Path("app/main.py")
if not main_path.exists():
    raise SystemExit("ERROR: app/main.py not found")

text = main_path.read_text(encoding="utf-8")
original = text

imports_to_add = [
    "from app.api.dashboard import router as dashboard_router",
    "from app.ui_dashboard import router as ui_dashboard_router",
]

for import_line in imports_to_add:
    if import_line not in text:
        lines = text.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_at = i + 1
        lines.insert(insert_at, import_line)
        text = "\n".join(lines) + "\n"

includes_to_add = [
    "app.include_router(dashboard_router)",
    "app.include_router(ui_dashboard_router)",
]

for include_line in includes_to_add:
    if include_line not in text:
        lines = text.splitlines()
        insert_at = None
        for i, line in enumerate(lines):
            if "app.include_router(" in line:
                insert_at = i + 1
        if insert_at is None:
            for i, line in enumerate(lines):
                if "app = FastAPI" in line or "FastAPI(" in line:
                    insert_at = i + 1
                    break
        if insert_at is None:
            raise SystemExit("ERROR: could not find FastAPI app in app/main.py")
        lines.insert(insert_at, include_line)
        text = "\n".join(lines) + "\n"

if text != original:
    backup = main_path.with_suffix(".py.bak_stage8")
    backup.write_text(original, encoding="utf-8")
    main_path.write_text(text, encoding="utf-8")
    print(f"OK: patched {main_path}, backup: {backup}")
else:
    print("OK: main.py already patched")

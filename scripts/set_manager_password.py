from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/itcs/itcs_mvp_stage4/backend")

from app.auth_manager import hash_password

if len(sys.argv) != 3:
    print("usage: python3 set_manager_password.py <email> <password>")
    raise SystemExit(1)

email = sys.argv[1].strip()
password = sys.argv[2].strip()

print(hash_password(password))

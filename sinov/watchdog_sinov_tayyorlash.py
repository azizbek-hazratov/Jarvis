from datetime import datetime, timedelta
from pathlib import Path

eski = (datetime.now() - timedelta(minutes=3)).strftime("%H:%M:%S.%f")[:-3]
yol = Path(__file__).parent / "diagnostika_sinov.log"
with open(yol, "w", encoding="utf-8") as f:
    f.write(f"[{eski}] tirikman\n")
print("yaratildi:", yol, "vaqt:", eski)

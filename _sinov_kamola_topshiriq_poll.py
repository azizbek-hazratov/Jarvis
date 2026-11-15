import json
import time
import urllib.request

TOKEN = "20f5af27e7f989a8e73fb99e67c58e2a9b6ca757dbb0a615"
TASK_ID = "31909444f3"
URL = "http://localhost:8090/jamoa"


def olish():
    req = urllib.request.Request(URL, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


boshlandi = time.monotonic()
while time.monotonic() - boshlandi < 140:
    data = olish()
    for t in data["topshiriqlar_tarixi"]:
        if t["id"] == TASK_ID:
            if t["holat"] in ("tayyor", "xato"):
                print(json.dumps(t, ensure_ascii=False, indent=2))
                raise SystemExit(0)
            else:
                print(f"... holat: {t['holat']} ({time.monotonic()-boshlandi:.0f}s)")
    time.sleep(3)
print("TIMEOUT — 140 soniyada tugamadi")

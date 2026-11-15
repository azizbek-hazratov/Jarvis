"""
AI Javob Bridge — Azizbekning shaxsiy Instagram/Telegram akkauntlariga kelgan
xabarlarga TO'LIQ AVTOMATIK (AI/Claude orqali, inson qatnashuvisiz) javob
generatsiya qiladigan markaziy server.

Nega kerak (2026-09-14, Azizbek ovozli xabar bilan so'ragan): mijozga (JetCafe)
"Instagram/Telegram o'zi mijozga javob beradigan" botni ko'rsatish uchun, avval
Azizbek O'Z shaxsiy Instagram/Telegram akkauntini shu holatga o'tkazmoqchi —
namoyish sifatida.

Arxitektura — bitta "miya", ikkita kanal:
- userbot/monitor.py (Telegram, Telethon, Azizbekning shaxsiy akkaunti) HTTP orqali
  shu serverga murojaat qiladi.
- instagram-server/index.js (Instagram DM webhook, Node.js) ham xuddi shu
  serverga HTTP orqali murojaat qiladi.

Xavfsizlik: bu suhbat-sessiya HECH QANDAY vositaga (fayl/Bash/internet) kirish
huquqiga ega emas (`can_use_tool` orqali hammasi rad etiladi) — faqat matn
yozadi, xuddi ai_expert_bot/core.py'dagi kabi.

Ishga tushirish: python ai_javob_bridge.py  (port 4031, faqat 127.0.0.1)
"""

import asyncio
import re
import sys
import threading
import warnings
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

warnings.filterwarnings("ignore", message=".*can_use_tool.*")

# --- Claude CLI child-process'ini Windows'da yashirin ishga tushirish ---
# `jarvis_core.py`dagi bilan AYNAN bir xil tuzatish (2026-09-18) — konsolsiz
# (pythonw.exe/Task Scheduler) fon jarayonidan claude_agent_sdk CLI
# subprocess'i chaqirilsa Windows avtomatik ko'rinadigan konsol oynasi ochib
# yuboradi, uzoq umrli sessiyalar to'planib ko'p oyna hosil bo'lishiga
# olib keladi.
if sys.platform == "win32":
    import subprocess as _subprocess

    import anyio as _anyio

    _original_anyio_open_process = _anyio.open_process

    async def _hidden_anyio_open_process(*args, **kwargs):
        kwargs.setdefault("creationflags", _subprocess.CREATE_NO_WINDOW)
        return await _original_anyio_open_process(*args, **kwargs)

    _anyio.open_process = _hidden_anyio_open_process

import requests
from flask import Flask, jsonify, request
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    PermissionResultDeny,
)

import config

BASE = Path(__file__).parent
LOG_FILE = BASE / "ai_javob_bridge.log"
LEADS_FILE = BASE / "ai_javob_leads.txt"
LEAD_RE = re.compile(r"\[\[\s*LEAD\s*:\s*(.+?)\s*\]\]")


def log(msg: str):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def build_system_prompt() -> str:
    bugun = f"{datetime.now():%Y-%m-%d, %A}"
    return f"""Sening isming yo'q — sen Azizbekning nomidan Instagram/Telegram DM'ga
javob yozayotgan virtual yordamchisan. Odam buni sezmasligi kerak, tabiiy
yoz — o'zingni "bot"/"AI" deb atama, robot kabi gapirma.
Bugun: {bugun}.

KIM BU AZIZBEK
Bizneslar uchun AI agent (mijozlar bilan avtomatik gaplashadigan, savollarga
javob beradigan, buyurtma/lead yig'adigan tizim) quradigan mutaxassis.
Instagram: @azizbekhazratov.ai. Telegram kanal: t.me/azizbek_ai_agent.

VAZIFANG
1. Yozgan odamning savoliga AI agent xizmati haqida tushunarli, samimiy javob ber
   (nima qiladi, qanday foyda beradi, umumiy tarzda — texnik jargon ishlatma).
2. Aniq narx AYTMA — "har loyiha individual, Azizbek siz bilan bog'lanib aniq
   taklif tayyorlaydi" deb tushuntir.
3. Qiziqqan bo'lsa ISM va TELEFON RAQAM so'ra (bu — MIJOZNING raqami, pastdagi
   4-band esa Azizbekning O'Z raqami haqida, ikkalasini aralashtirma).
4. TELEFON RAQAMINGIZNI ({config.EGASI_TELEFON}, qo'ng'iroq yoki Telegram)
   FAQAT quyidagi holatlarda ayt: odam NARX/TARIF so'rasa, TAKLIF/xizmat
   qanday ishlashini so'rasa, BOG'LANISH yo'lini so'rasa, yoki "QANDAY
   BOSHLAYMIZ"/"qayerdan boshlaylik" desa. Boshqa HAR QANDAY holatda
   (masalan oddiy salom, umumiy tanishuv savoli) bu raqamni TILGA OLMA —
   faqat aniq shu 4 mavzuda so'ralganda ayt.
5. Ism VA telefon (mijozniki) ikkalasi ham aniq bo'lgach, javobing OXIRIGA
   ANIQ shu formatda maxsus belgi qo'sh (odamga bu qism umuman
   ko'rsatilmaydi, faqat tizim uchun, faqat BIR MARTA qo'y):
   [[LEAD: Ism | Telefon | qisqa izoh]]

USLUB
- O'zbek tilida (odam boshqa tilda yozsa o'sha tilda) javob ber.
- QISQA — Instagram/Telegram DM uslubi, 2-4 gap yetarli, ortiqcha cho'zma.
- Mavzuga aloqasi yo'q so'rov kelsa (masalan boshqa mavzu haqida gap) — qisqa
  javob berib, muloyimlik bilan AI agent mavzusiga qaytar.
"""


async def _deny_all(tool_name, input_data, context):
    return PermissionResultDeny(message="Bu suhbat faqat matn uchun, vosita ishlatmaydi.")


class Suhbat:
    """Bitta yozishuvchi uchun bitta Claude sessiyasi (xotira sessiya davomida saqlanadi)."""

    def __init__(self, tarix: str = ""):
        sp = build_system_prompt()
        if tarix:
            sp += (
                "\n\nOLDINGI SUHBAT TARIXI (bu odam bilan avval gaplashilgan, "
                "sessiya 30 daqiqa jim turgani uchun yopilib, endi qayta ochildi — "
                "quyidagi tarixni o'qib kontekstni tikla, lekin buni odamga qayta "
                "aytib berma, faqat javobingda hisobga ol):\n" + tarix
            )
        self._options = ClaudeAgentOptions(
            system_prompt=sp,
            model="sonnet",
            allowed_tools=[],
            can_use_tool=_deny_all,
            permission_mode="default",
        )
        self._client = None

    async def ulan(self):
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.connect()

    async def ask(self, text: str) -> str:
        parts = []
        await self._client.query(text)
        async for message in self._client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
        return "".join(parts)

    async def yop(self):
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception as e:
                log(f"sessiyani yopishda xato: {e}")


SESSIYALAR: dict[str, Suhbat] = {}
OXIRGI_FAOL: dict[str, datetime] = {}
SESSIYA_TIMEOUT_DAQIQA = 30  # jim tursa shuncha daqiqadan keyin sessiya avtomatik yopiladi

# --- alohida oqim (thread) ichida doimiy ishlaydigan asyncio loop ---
_loop = asyncio.new_event_loop()


def _loop_ishga_tushir():
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


threading.Thread(target=_loop_ishga_tushir, daemon=True).start()


def oldingi_tarixni_olish(kalit: str, limit: int = 6) -> str:
    """LOG_FILE'dan shu kalit uchun oxirgi savol/javob yozuvlarini o'qiydi --
    sessiya jimlik sabab yopilib, keyin xabar kelganda kontekstni tiklash uchun."""
    if not LOG_FILE.exists():
        return ""
    izlash = f"JAVOB [{kalit}]:"
    qatorlar = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if izlash in line:
                    qatorlar.append(line.strip())
    except Exception as e:
        log(f"oldingi tarixni o'qishda xato [{kalit}]: {e}")
        return ""
    return "\n".join(qatorlar[-limit:])


def _eskirgan_sessiyalarni_tozala():
    """Har 5 daqiqada ishga tushadi -- 30 daqiqa jim turgan sessiyalarni yopadi."""
    try:
        chegara = datetime.now() - timedelta(minutes=SESSIYA_TIMEOUT_DAQIQA)
        eskirgan = [k for k, t in list(OXIRGI_FAOL.items()) if t < chegara]
        for k in eskirgan:
            suhbat = SESSIYALAR.pop(k, None)
            OXIRGI_FAOL.pop(k, None)
            if suhbat is not None:
                try:
                    fut = asyncio.run_coroutine_threadsafe(suhbat.yop(), _loop)
                    fut.result(timeout=10)
                except Exception as e:
                    log(f"sessiya yopishda xato [{k}]: {e}")
            log(f"SESSIYA AVTOMATIK YOPILDI (30 daqiqa jim turgani uchun): {k}")
    except Exception as e:
        log(f"tozalash tsiklida xato: {e}")
    finally:
        threading.Timer(300, _eskirgan_sessiyalarni_tozala).start()


threading.Timer(300, _eskirgan_sessiyalarni_tozala).start()


def notify_owner(text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": config.OWNER_ID, "text": text},
            timeout=10,
        )
    except Exception as e:
        log(f"notify_owner xato: {e}")


def log_lead(kalit: str, raw: str):
    with open(LEADS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M} | {kalit} | {raw}\n")
    notify_owner(f"🎯 Yangi LEAD (AI avto-javob, {kalit}):\n{raw}")


async def _javob_ol_async(kalit: str, matn: str) -> str:
    if kalit not in SESSIYALAR:
        tarix = oldingi_tarixni_olish(kalit)
        s = Suhbat(tarix=tarix)
        await s.ulan()
        SESSIYALAR[kalit] = s
    OXIRGI_FAOL[kalit] = datetime.now()
    suhbat = SESSIYALAR[kalit]
    javob = await suhbat.ask(matn)
    lead = LEAD_RE.search(javob)
    toza = LEAD_RE.sub("", javob).strip()
    if lead:
        log_lead(kalit, lead.group(1))
    return toza


def javob_ol(kalit: str, matn: str, timeout: int = 60) -> str:
    fut = asyncio.run_coroutine_threadsafe(_javob_ol_async(kalit, matn), _loop)
    return fut.result(timeout=timeout)


app = Flask(__name__)


@app.route("/javob", methods=["POST"])
def http_javob():
    data = request.get_json(force=True, silent=True) or {}
    kalit = str(data.get("kalit", "")).strip()
    matn = str(data.get("matn", "")).strip()
    if not kalit or not matn:
        return jsonify({"xato": "kalit va matn shart"}), 400
    try:
        javob = javob_ol(kalit, matn)
        log(f"JAVOB [{kalit}]: savol={matn[:150]!r} -> javob={javob[:150]!r}")
        return jsonify({"javob": javob})
    except Exception as e:
        log(f"XATO [{kalit}]: {e}")
        return jsonify({"xato": str(e)}), 500


@app.route("/", methods=["GET"])
def health():
    return "AI Javob Bridge ishlayapti. Faol sessiyalar: %d" % len(SESSIYALAR)


if __name__ == "__main__":
    log("AI Javob Bridge ishga tushdi (port 4031)")
    app.run(host="127.0.0.1", port=4031, threaded=True, debug=False)

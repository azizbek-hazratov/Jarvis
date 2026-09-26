"""
JARVIS — yadro (core)
Barcha rejimlar (terminal, ovoz, Telegram) shu fayldan foydalanadi.

Xotira tuzilishi (2026-09-12'da qayta qurildi — har safar to'liq yuklanadigan
qismi endi kichik, batafsil loyiha holati alohida fayllarda, faqat kerak
bo'lganda Read bilan o'qiladi):
    xotira/profil.md          — Azizbek haqida (har safar to'liq yuklanadi)
    xotira/indeks.md          — loyihalar/*.md fayllarining bir qatorlik ro'yxati (har safar to'liq yuklanadi)
    xotira/vazifalar.md       — bajarilishi kerak bo'lgan ishlar, QISQA (har safar to'liq yuklanadi)
    xotira/eslatmalar.md      — boshqa muhim narsalar (tail bilan kesiladi)
    xotira/loyihalar/<nom>.md — har loyiha/soha uchun ALOHIDA, batafsil fayl —
                                 PROMPTGA AVTOMATIK YUKLANMAYDI, faqat Read bilan
                                 talab bo'yicha o'qiladi (hajmiga cheklov yo'q)
    suhbatlar/YYYY-MM-DD.md   — har kunning to'liq yozuvi (avtomatik)
"""

import asyncio
import re
import sys
import warnings
from datetime import datetime
from pathlib import Path

# SDK'ning "can_use_tool ro'yxatdagi vositalar uchun chaqirilmaydi" ogohlantirishi
# — bu bizning ataylab qilgan sozlamamiz, shuning uchun ko'rsatmaymiz.
warnings.filterwarnings("ignore", message=".*can_use_tool.*")

# --- Claude CLI child-process'ini Windows'da yashirin ishga tushirish ---
# claude_agent_sdk o'zining "claude" CLI jarayonini anyio.open_process()
# orqali ishga tushiradi. Jarvis konsolsiz (pythonw/Task Scheduler) holda
# ishlaganda, Windows console-app uchun avtomatik YANGI KONSOL OYNASI ochib
# yuboradi — bu oyna ekranga chiqib, tasodifan yopilsa butun bot to'xtab
# qoladi (aynan shu sabab bilan bot bir marta qulagan edi). Buning oldini
# olish uchun anyio.open_process()ni o'raymiz va Windows'da har doim
# CREATE_NO_WINDOW bayrog'ini qo'shamiz — natijada CLI hech qanday ko'zga
# ko'ringan oyna ochmasdan, fonda ishlaydi.
if sys.platform == "win32":
    import subprocess as _subprocess

    import anyio as _anyio

    _original_anyio_open_process = _anyio.open_process

    async def _hidden_anyio_open_process(*args, **kwargs):
        kwargs.setdefault("creationflags", _subprocess.CREATE_NO_WINDOW)
        return await _original_anyio_open_process(*args, **kwargs)

    _anyio.open_process = _hidden_anyio_open_process

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    PermissionResultAllow,
    PermissionResultDeny,
)

import jarvis_fon_ishlar as _fon_ishlar

BASE_DIR = Path(__file__).parent
MEM_DIR = BASE_DIR / "xotira"
LOG_DIR = BASE_DIR / "suhbatlar"

MEM_FILES = {
    "profil.md": (
        "# Profil\n\n"
        "Azizbek haqida uzoq muddat o'zgarmaydigan ma'lumotlar:\n"
        "kim, nima bilan shug'ullanadi, qanday ishlashni yoqtiradi.\n\n"
    ),
    "indeks.md": (
        "# Loyihalar indeksi\n\n"
        "Har birining to'liq holati xotira/loyihalar/<nom>.md faylida. Bu yerda\n"
        "faqat bir qatorlik tavsif — kerakli fayl nomini shu ro'yxatdan top, keyin\n"
        "Read bilan o'sha faylni TO'LIQ o'qi.\n\n"
    ),
    "vazifalar.md": (
        "# Vazifalar\n\n"
        "Bajarilishi kerak bo'lgan ishlar. Bajarilgani `[x]` bilan belgilanadi.\n\n"
    ),
    "eslatmalar.md": (
        "# Eslatmalar\n\n"
        "Yuqoridagilarga kirmaydigan, lekin eslab qolish kerak bo'lgan narsalar.\n\n"
    ),
}

# Har loyiha/soha uchun alohida, batafsil xotira fayllari — prompt ichiga
# AVTOMATIK yuklanmaydi (indeks.md orqali topilib, kerak bo'lganda Read bilan
# o'qiladi). Shuning uchun MEM_BUDGET/_tail() cheklovi bularga aloqador emas.
LOYIHALAR_DIR = MEM_DIR / "loyihalar"

# --- Tashqi integratsiyalar: Gmail / Google Drive / Google Calendar / Canva ---
# 2026-09-12, Azizbek tasdiqladi: o'qish ham, YOZISH/YUBORISH/O'CHIRISH
# amallari ham so'ramasdan avtomatik ruxsat etilsin (alohida tasdiqlash
# shart emas). Bu vositalar Claude Code CLI'ning claude.ai konnektorlari
# sifatida shu Windows profilida hisob darajasida ulangan (OAuth allaqachon
# qilingan) — jarvis_core.py'da alohida mcp_servers sozlash shart emas,
# faqat quyidagi aniq vosita nomlarini SAFE_TOOLS'ga (auto-approve)
# qo'shish yetarli. Yozish toifasidagi HAR BIR chaqiruv pastdagi
# auto_approve() orqali xotira/integratsiya_log.md fayliga yoziladi —
# xato bo'lsa orqaga qaytarish/tekshirish uchun.
GMAIL_OQISH = [
    "mcp__claude_ai_Gmail__get_draft",
    "mcp__claude_ai_Gmail__get_message",
    "mcp__claude_ai_Gmail__get_thread",
    "mcp__claude_ai_Gmail__list_drafts",
    "mcp__claude_ai_Gmail__list_labels",
    "mcp__claude_ai_Gmail__search_threads",
]
GMAIL_YOZISH = [
    "mcp__claude_ai_Gmail__apply_sensitive_message_label",
    "mcp__claude_ai_Gmail__apply_sensitive_thread_label",
    "mcp__claude_ai_Gmail__create_draft",
    "mcp__claude_ai_Gmail__create_label",
    "mcp__claude_ai_Gmail__delete_label",
    "mcp__claude_ai_Gmail__forward",
    "mcp__claude_ai_Gmail__label_message",
    "mcp__claude_ai_Gmail__label_thread",
    "mcp__claude_ai_Gmail__mark_message_spam",
    "mcp__claude_ai_Gmail__mark_thread_spam",
    "mcp__claude_ai_Gmail__reply",
    "mcp__claude_ai_Gmail__send_message",
    "mcp__claude_ai_Gmail__trash_message",
    "mcp__claude_ai_Gmail__trash_thread",
    "mcp__claude_ai_Gmail__unlabel_message",
    "mcp__claude_ai_Gmail__unlabel_thread",
    "mcp__claude_ai_Gmail__unmark_message_spam",
    "mcp__claude_ai_Gmail__unmark_thread_spam",
    "mcp__claude_ai_Gmail__untrash_message",
    "mcp__claude_ai_Gmail__untrash_thread",
    "mcp__claude_ai_Gmail__update_draft",
    "mcp__claude_ai_Gmail__update_label",
    "mcp__claude_ai_Gmail__update_message_labels",
]
KALENDAR_OQISH = [
    "mcp__claude_ai_Google_Calendar__get_event",
    "mcp__claude_ai_Google_Calendar__list_calendars",
    "mcp__claude_ai_Google_Calendar__list_events",
    "mcp__claude_ai_Google_Calendar__search_events",
    "mcp__claude_ai_Google_Calendar__suggest_time",
]
KALENDAR_YOZISH = [
    "mcp__claude_ai_Google_Calendar__create_event",
    "mcp__claude_ai_Google_Calendar__delete_event",
    "mcp__claude_ai_Google_Calendar__respond_to_event",
    "mcp__claude_ai_Google_Calendar__update_event",
]
DRIVE_OQISH = [
    "mcp__claude_ai_Google_Drive__download_file_content",
    "mcp__claude_ai_Google_Drive__get_file_metadata",
    "mcp__claude_ai_Google_Drive__get_file_permissions",
    "mcp__claude_ai_Google_Drive__list_recent_files",
    "mcp__claude_ai_Google_Drive__read_file_content",
    "mcp__claude_ai_Google_Drive__search_files",
]
DRIVE_YOZISH = [
    "mcp__claude_ai_Google_Drive__copy_file",
    "mcp__claude_ai_Google_Drive__create_file",
    "mcp__claude_ai_Google_Drive__share_file",
    "mcp__claude_ai_Google_Drive__trash_file",
    "mcp__claude_ai_Google_Drive__update_file",
]
CANVA_OQISH = [
    "mcp__claude_ai_Canva__export-design",
    "mcp__claude_ai_Canva__get-assets",
    "mcp__claude_ai_Canva__get-brand-template-dataset",
    "mcp__claude_ai_Canva__get-design-candidates",
    "mcp__claude_ai_Canva__get-design-dataset",
    "mcp__claude_ai_Canva__get-design-pages",
    "mcp__claude_ai_Canva__get-export-formats",
    "mcp__claude_ai_Canva__help",
    "mcp__claude_ai_Canva__list-brand-kits",
    "mcp__claude_ai_Canva__list-comments",
    "mcp__claude_ai_Canva__list-folder-items",
    "mcp__claude_ai_Canva__list-replies",
    "mcp__claude_ai_Canva__read-design",
    "mcp__claude_ai_Canva__resolve-shortlink",
    "mcp__claude_ai_Canva__search-brand-templates",
    "mcp__claude_ai_Canva__search-designs",
    "mcp__claude_ai_Canva__search-folders",
]
CANVA_YOZISH = [
    "mcp__claude_ai_Canva__comment-on-design",
    "mcp__claude_ai_Canva__copy-design",
    "mcp__claude_ai_Canva__create-brand-template-draft",
    "mcp__claude_ai_Canva__create-design-from-brand-template",
    "mcp__claude_ai_Canva__create-design-from-candidate",
    "mcp__claude_ai_Canva__create-folder",
    "mcp__claude_ai_Canva__edit-design",
    "mcp__claude_ai_Canva__generate-design",
    "mcp__claude_ai_Canva__generate-design-structured",
    "mcp__claude_ai_Canva__import-design-from-url",
    "mcp__claude_ai_Canva__merge-designs",
    "mcp__claude_ai_Canva__move-item-to-folder",
    "mcp__claude_ai_Canva__publish-brand-template",
    "mcp__claude_ai_Canva__reply-to-comment",
    "mcp__claude_ai_Canva__request-outline-review",
    "mcp__claude_ai_Canva__resize-design",
    "mcp__claude_ai_Canva__upload-asset-from-url",
]

INTEGRATSIYA_OQISH = GMAIL_OQISH + KALENDAR_OQISH + DRIVE_OQISH + CANVA_OQISH
INTEGRATSIYA_YOZISH = GMAIL_YOZISH + KALENDAR_YOZISH + DRIVE_YOZISH + CANVA_YOZISH

# So'ramasdan ishlatiladigan vositalar
# MUHIM (2026-09-12, haqiqiy sinovda topilgan xato): `allowed_tools`ga
# (SAFE_TOOLS) kiritilgan vositalar SDK darajasida can_use_tool/auto_approve
# chaqiruvini BUTUNLAY chetlab o'tadi — ya'ni shu ro'yxatga tushgan vosita
# uchun pastdagi auto_approve() funksiyasi HECH QACHON ishlamaydi. Shuning
# uchun INTEGRATSIYA_YOZISH (Gmail/Drive/Calendar/Canva'ning
# yozish/yuborish/o'chirish amallari) ATAYLAB bu ro'yxatga QO'SHILMAYDI —
# xuddi Bash kabi, ular auto_approve() orqali o'tadi (u yerda so'ramasdan
# Allow qilinadi VA integratsiya_log.md'ga yoziladi). Faqat o'qish
# (INTEGRATSIYA_OQISH) shu yerga qo'shilgan, chunki uni loglash shart emas.
SAFE_TOOLS = [
    "Read", "Glob", "Grep",
    "Write", "Edit",
    "WebSearch", "WebFetch",
    "TodoWrite",
] + INTEGRATSIYA_OQISH

INTEGRATSIYA_LOG = MEM_DIR / "integratsiya_log.md"


def _integratsiya_obyekt(input_data: dict) -> str:
    """Log yozuvi uchun input_data'dan eng ma'noli maydonni ajratib oladi
    (aniq schema har vosita uchun boshqacha bo'lgani uchun eng ko'p
    ishlatiladigan kalitlarni sinab ko'ramiz, topilmasa butun inputni
    qisqartirib qaytaramiz)."""
    for kalit in (
        "to", "subject", "recipient", "fileId", "file_id", "name",
        "title", "summary", "eventId", "event_id", "designId", "design_id",
        "query", "labelId", "label_id", "folderId", "folder_id",
    ):
        qiymat = input_data.get(kalit) if isinstance(input_data, dict) else None
        if qiymat:
            return f"{kalit}={qiymat!r}"
    return str(input_data)[:200]


def _integratsiya_logga_yoz(tool_name: str, input_data: dict):
    """Gmail/Drive/Calendar/Canva'dagi YOZISH/YUBORISH/O'CHIRISH amalini
    xotira/integratsiya_log.md fayliga yozadi — xato bo'lsa orqaga
    qaytarish/tekshirish uchun. Log yozish muvaffaqiyatsiz bo'lsa ham
    asosiy amal to'xtamasligi kerak, shuning uchun xatoni yutamiz."""
    try:
        MEM_DIR.mkdir(exist_ok=True)
        yangi = not INTEGRATSIYA_LOG.exists()
        vaqt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        obyekt = _integratsiya_obyekt(input_data)
        with open(INTEGRATSIYA_LOG, "a", encoding="utf-8") as f:
            if yangi:
                f.write(
                    "# Integratsiya logi — Gmail/Drive/Calendar/Canva "
                    "yozish/yuborish/o'chirish amallari\n\n"
                    "Har yozuv: vaqt | vosita nomi | obyekt. Bu amallar "
                    "so'ramasdan avtomatik ruxsat etilgan (2026-09-12, "
                    "Azizbek tasdig'i) — shuning uchun bu log orqaga "
                    "qaytarish/tekshirish uchun yagona iz.\n\n"
                )
            f.write(f"- {vaqt} | {tool_name} | {obyekt}\n")
    except Exception:
        pass


# ---------------- Xotira fayllari ----------------

def _ensure_dirs():
    MEM_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    LOYIHALAR_DIR.mkdir(exist_ok=True)
    for name, boshlangich in MEM_FILES.items():
        f = MEM_DIR / name
        if not f.exists():
            f.write_text(boshlangich, encoding="utf-8")


# Windows'da buyruq qatori 32767 belgidan oshsa, jarayon umuman ishga
# tushmaydi ([WinError 206] "Imya fayla ... slishkom bolshuyu dlinu").
# SDK tizim ko'rsatmasini aynan buyruq qatori orqali uzatadi, shuning uchun
# xotira fayllari cheksiz o'sib ketsa Jarvis butunlay ishga tushmay qoladi.
# Shu sabab prompt ichiga qo'yiladigan xotiraga qattiq chegara qo'yamiz.
MEM_BUDGET = 12000        # xotira bloklari uchun umumiy belgi chegarasi
PROMPT_LIMIT = 24000      # butun tizim ko'rsatmasi uchun xavfsiz chegara

# Bu fayllar to'liq qo'yiladi (kichik va har doim kerak)
MEM_FULL = ["profil.md", "indeks.md", "vazifalar.md"]

# 2026-09-26 TUZATISH (AzizEdu production hodisasi — batafsil izoh
# _reset_client()da): avval bitta qattiq ASK_TIMEOUT_S=600 bor edi, va
# tugaganda FAQAT "bekor qildim" deb aytib, Python-tarafdagi kutishni
# bekor qilardi — TASHQI claude.exe/tool-jarayonlar esa hech qanday signal
# olmay ISHLASHDA DAVOM ETARDI. Endi ikki qatlam:
# - HEARTBEAT_INTERVAL_S: ish davom etayotganda shuncha soniyada bir marta
#   "hali ishlayapman, oxirgi qadam: ..." signali beriladi.
# - MAX_ASK_TIMEOUT_S: FAQAT abadiy osilib qolishning oldini oluvchi ZAXIRA
#   chegara (haqiqiy uzoq production ishlar soatlab davom etishi mumkin
#   bo'lgani uchun ataylab juda katta). Bu yerga yetilganda endi HAQIQATDA
#   to'xtatiladi (`_majburan_toxtat()` — interrupt() + kerak bo'lsa
#   process-daraxtini taskkill bilan o'ldirish), shunchaki aytib qo'yilmaydi.
HEARTBEAT_INTERVAL_S = 150  # 2.5 daqiqa
MAX_ASK_TIMEOUT_S = 7200  # 2 soat — zaxira, oddiy holatda yetilmasligi kerak

# Fon-agent/uzoq-ish "holat so'rovi" heuristikasi — lock band bo'lganda
# kelgan xabar shu kalit so'zlardan birini o'z ichiga olsa, navbatga
# qo'yilmasdan DARHOL joriy holat bilan javob beriladi (2026-09-26).
HOLAT_SOROVI_KALIT_SOZLAR = (
    "holat", "tugadi", "tugatding", "tugatdim", "qanday ketyapti",
    "hali tugamadi", "band mi", "bandmi", "ishlayapsanmi", "nima bo'lyapti",
)


def holat_sorovimi(text: str) -> bool:
    """Xabar 'holat/tugatdingmi' kabi so'rovmi — shunday bo'lsa navbatga
    qo'yilmasdan darhol joriy holat bilan javob beriladi."""
    past = (text or "").strip().lower()
    return any(kalit in past for kalit in HOLAT_SOROVI_KALIT_SOZLAR)


def _tool_qadam_matni(block: "ToolUseBlock") -> str:
    """Heartbeat/holat xabari uchun: oxirgi ishlatilgan vositaning qisqa,
    o'qish mumkin bo'lgan tavsifi (masalan 'Bash — npm test', 'Read —
    D:\\...\\server.js')."""
    nomi = getattr(block, "name", "vosita")
    kirish = getattr(block, "input", None) or {}
    tafsilot = ""
    try:
        if isinstance(kirish, dict):
            for kalit in ("command", "file_path", "pattern", "description", "prompt", "query"):
                if kirish.get(kalit):
                    tafsilot = str(kirish[kalit])
                    break
    except Exception:
        pass
    tafsilot = tafsilot.replace("\n", " ").strip()
    if len(tafsilot) > 100:
        tafsilot = tafsilot[:100] + "…"
    return f"{nomi}" + (f" — {tafsilot}" if tafsilot else "")


async def _eski_jarayonni_tekshir_va_ozdir(pid, kutish_s: int = 10) -> bool:
    """interrupt()+disconnect()dan keyin, eski claude.exe jarayoni (PID)
    hali ham Windows jarayonlar ro'yxatida tursa, `kutish_s` soniya kutadi,
    keyin ham tirik bo'lsa `taskkill /PID <pid> /T /F` bilan BUTUN jarayon
    daraxtini (bola-jarayonlar — masalan uzoq Bash/SSH — bilan birga)
    majburan o'ldiradi. Faqat Windows'da ishlaydi. True qaytarsa — majburan
    o'ldirish HAQIQATDA kerak bo'ldi (halol hisobot uchun muhim)."""
    if not pid or sys.platform != "win32":
        return False
    loop = asyncio.get_event_loop()
    for _ in range(kutish_s):
        await asyncio.sleep(1)
        try:
            natija = await loop.run_in_executor(
                None,
                lambda: _subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True, text=True,
                    creationflags=_subprocess.CREATE_NO_WINDOW,
                ),
            )
            if str(pid) not in natija.stdout:
                return False  # o'z-o'zidan tugadi, majburiylik kerak emas
        except Exception:
            return False
    diag(f"PID {pid} {kutish_s}s dan keyin ham tirik — taskkill /T /F")
    try:
        await loop.run_in_executor(
            None,
            lambda: _subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True, creationflags=_subprocess.CREATE_NO_WINDOW,
            ),
        )
    except Exception:
        pass
    return True


def _tail(matn: str, limit: int) -> str:
    """Uzun matnning faqat oxirgi (eng yangi) qismini qaytaradi."""
    if len(matn) <= limit:
        return matn
    kesilgan = matn[-limit:]
    # yarim qolgan qatorni tashlab yuboramiz
    if "\n" in kesilgan:
        kesilgan = kesilgan.split("\n", 1)[1]
    return "…(eski qismi kesildi — kerak bo'lsa Read bilan to'liq o'qi)…\n" + kesilgan


def _read_memory(budget: int = MEM_BUDGET) -> str:
    _ensure_dirs()
    xom = {}
    for name in MEM_FILES:
        xom[name] = (MEM_DIR / name).read_text(encoding="utf-8").strip()

    # avval to'liq qo'yiladiganlar, qolgan joyni boshqalarga bo'lamiz
    band = sum(len(xom[n]) for n in MEM_FULL if n in xom)
    qolgan_fayllar = [n for n in MEM_FILES if n not in MEM_FULL]
    ulush = max(1000, (budget - band) // max(1, len(qolgan_fayllar)))

    bloklar = []
    for name in MEM_FILES:
        matn = xom[name]
        if name not in MEM_FULL:
            matn = _tail(matn, ulush)
        bloklar.append(f"### xotira/{name}\n{matn}")
    return "\n\n".join(bloklar)


def _recent_days(n: int = 5) -> str:
    """Oxirgi kunlardagi suhbat fayllari ro'yxati."""
    _ensure_dirs()
    fayllar = sorted(LOG_DIR.glob("*.md"), reverse=True)[:n]
    if not fayllar:
        return "(hali suhbat yozuvi yo'q)"
    return ", ".join(f.name for f in fayllar)


DIAG_LOG = BASE_DIR / "diagnostika.log"


def diag(bosqich: str):
    """Diagnostika/heartbeat logi — har bir yozuv aniq vaqt bilan (soat:daqiqa:
    soniya.millisekund). Maqsad: dastur biror joyda qotib qolsa, shu faylga
    qarab AYNAN qaysi bosqichda to'xtab qolganini bilish (2026-09-05,
    ishonchlilikni oshirish bo'yicha 1-qadam)."""
    vaqt = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    try:
        with open(DIAG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{vaqt}] {bosqich}\n")
    except Exception:
        pass


def log_exchange(savol: str, javob: str):
    """Har bir savol-javobni kunlik faylga yozadi."""
    _ensure_dirs()
    fayl = LOG_DIR / f"{datetime.now():%Y-%m-%d}.md"
    vaqt = f"{datetime.now():%H:%M}"
    with fayl.open("a", encoding="utf-8") as f:
        f.write(f"\n## {vaqt}\n\n**Azizbek:** {savol}\n\n**Jarvis:** {javob}\n")


# ---------------- Tizim ko'rsatmasi ----------------

def build_system_prompt(extra: str = "") -> str:
    bugun = f"{datetime.now():%Y-%m-%d, %A}"
    return f"""Sening isming Jarvis. Sen Azizbekning shaxsiy AI yordamchisisan.
Uning Windows kompyuterida ishlaysan. Bugun: {bugun}.

MULOQOT
- O'zbek tilida javob ber (u boshqa tilda yozsa, o'sha tilda).
- Qisqa va aniq. Ortiqcha muqaddima, takrorlash va maqtov yo'q.
- Bilmasang "bilmayman" de. Hech qachon o'ylab topma.

ISH BAJARISH — bu eng muhimi
- Sendan ish so'ralsa, BAJAR. Ruxsat so'rama, "xohlaysizmi" dema,
  rejani sanab o'tirma — ishni qilib, natijani ayt.
- "Qila olmayman" deyishdan oldin ROSTDAN urinib ko'r. Bir vosita
  ishlamasa, boshqasini sina. Faqat 2-3 urinishdan keyin ham chiqmasa,
  nima urinib ko'rganingni aniq aytib, muqobil taklif qil.

KIRUVCHI XABAR — HECH QACHON E'TIBORSIZ QOLDIRMA (2026-09-05 da real xato
sodir bo'lgan, qattiq qoida sifatida yozilgan)
Azizbek katta biznesmenlar bilan ishlaydi — mijoz oldida senga yozganda
javobing eskirgan yoki mavzudan tashqari chiqsa, bu uning obro'siga zarar.
Real misol: fonda uzoq ishlagan test (masalan Whisper tezlik testi)
tugagach, Azizbek AYNAN O'SHA daqiqada "Ha, Google STT'ga o't..." deb
aniq javob yozgan bo'lsa ham, javob o'rniga fon testi haqida xabar berib,
oxirida "hali javobingizni kutyapman" deb ALLAQACHON BERILGAN javobni
qayta so'rab yuborilgan — bu MUTLAQO TAKRORLANMASLIGI kerak.
Shuning uchun har safar javob yozishdan oldin:
1. ENG AVVAL kiruvchi xabarning o'zini diqqat bilan o'qi va unga
   TO'G'RIDAN-TO'G'RI javob ber. Agar bu xabar avval sen bergan savolga
   javob bo'lsa ("ha", "mayli", "o't", "qil", "yo'q" va h.k.) — o'sha
   savolni SHU ZAHOTI yopilgan deb hisobla va aytilgan amalni bajar.
2. Fon vazifasi (background bash/test) tugagani haqida ma'lumot xabaringga
   aralashsa: avval Azizbekning YANGI xabariga to'liq javob ber, fon
   vazifa natijasini FAQAT shundan keyin, agar hali kerak bo'lsa, qisqa
   qo'shimcha sifatida yoz. Agar Azizbek o'sha oraliqda allaqachon boshqa
   qaror qabul qilgan bo'lsa, fon vazifa haqida umuman eslatmasa ham
   bo'ladi — asosiysi, ESKI SAVOLNI QAYTA SO'RAMA.
3. Bitta suhbatda ketma-ket kelgan har bir xabar alohida ko'rib chiqilishi
   va navbat bilan javob olishi shart — birontasi ham "band edim" deb
   tushib qolmasligi yoki javobsiz qolmasligi kerak.

SENDA NIMA BOR (aniq ro'yxat — bundan tashqarisini da'vo qilma)
- Read / Write / Edit — kompyuterdagi istalgan faylni o'qish va yozish
- Glob / Grep — fayl va matn qidirish
- Bash — Windows buyruqlarini bajarish (dastur o'rnatish, pip install,
  papka yaratish, fayl ko'chirish, dastur ishga tushirish). Bu ISHLAYDI,
  har uchala rejimda ham. Faqat halokatli buyruqlar (disk formatlash,
  tizimni o'chirish) bloklangan.
- WebSearch / WebFetch — internetdan qidirish va sahifa o'qish
- Gmail (mcp__claude_ai_Gmail__*) — xat o'qish/qidirish VA yuborish/javob
  berish/forward/draft/label/spam/trash — hammasi SO'RAMASDAN avtomatik
  ishlaydi (2026-09-12, Azizbek tasdig'i). Har bir yozish/yuborish/o'chirish
  amali xotira/integratsiya_log.md fayliga avtomatik yoziladi.
- Google Calendar (mcp__claude_ai_Google_Calendar__*) — voqealarni
  ko'rish/qidirish VA yaratish/yangilash/o'chirish/javob berish — hammasi
  so'ramasdan ishlaydi, yozish amallari integratsiya_log.md'ga yoziladi.
- Google Drive (mcp__claude_ai_Google_Drive__*) — fayl o'qish/qidirish VA
  yaratish/yangilash/nusxalash/ulashish/o'chirish (trash) — hammasi
  so'ramasdan ishlaydi, yozish amallari integratsiya_log.md'ga yoziladi.
- Canva (mcp__claude_ai_Canva__*) — dizayn qidirish/o'qish VA
  yaratish/tahrirlash/eksport/nashr qilish — hammasi so'ramasdan ishlaydi,
  yozish amallari integratsiya_log.md'ga yoziladi.
  MUHIM: bularning barchasi HAQIQIY hisobga (Azizbekning Gmail/Drive/
  Calendar/Canva'siga) ta'sir qiladi — email haqiqatan yuboriladi, fayl
  haqiqatan o'chadi/o'zgaradi. Ehtiyotkorlik BUYRUQ ANIQLIGIDA bo'lsin
  (kimga/nima/qaysi fayl ekanini aniq bilib bajar), lekin tasdiqlash
  SO'RAMA — Azizbek buni oldindan tasdiqlagan.

SENDA NIMA YO'Q
- Rasm yarata olmaysan, ovoz fayl yarata olmaysan.
- Yuqorida sanalganlardan tashqari boshqa tashqi xizmatga (masalan
  Shopify, Microsoft 365 — bular hali ulanmagan/needs-auth) ulanmagansan.
- Bularni bor deb aytma. Kerak bo'lsa, Bash orqali kerakli dasturni
  o'rnatib, o'zing hal qil.

FAYL FORMATLARI
Read vositasi faqat oddiy matn va rasm fayllarini ocha oladi.
Boshqa formatlar uchun Bash orqali python ishlat:
- .xlsx / .xls  -> openpyxl yoki pandas
- .docx         -> python-docx
- .pdf          -> pdfplumber yoki pypdf
- .pptx         -> python-pptx
Kutubxona o'rnatilmagan bo'lsa, avval `pip install <nom>` qil, keyin o'qi.
"O'qiy olmayman" dema — o'rnat va o'qi.

IJTIMOIY TARMOQLAR VA BRAUZER
Ikkita tayyor asbobing bor, ikkalasi ham PAROLSIZ ishlaydi:

1) Post qo'yish — Buffer (asosiy yo'l):
   python jarvis_buffer.py kanallar
   python jarvis_buffer.py post "matn" --kanal <ID> --rejim addToQueue
   (--rejim: addToQueue / shareNext / shareNow)
   BUFFER_TOKEN config.py da bo'lishi kerak. Yo'q bo'lsa, Azizbekdan
   kalitni so'ra: https://publish.buffer.com/settings/api

2) Sayt bilan ishlash — o'z brauzer profiling:
   python jarvis_brauzer.py holat <url>
   Murakkabroq ish uchun jarvis_brauzer.ochish() ni import qilib,
   o'zing Playwright skripti yoz. Profil allaqachon login qilingan.
   Agar sayt "kiring" desa — Azizbekdan `python jarvis_brauzer.py login <url>`
   ni bir marta qo'lda bajarishini so'ra.
   MUHIM: sahifaning to'liq HTML/matnini hech qachon print() qilma —
   juda katta bo'lib xatoga olib keladi. page.inner_text()/content() dan
   kerakli qismini ([:1500] kabi) kesib olib chiqar, qolganini kerak
   bo'lsa faylga yoz.

PAROL QOIDASI — buzilmaydi
Hech qachon parol so'rama, olma, saqlama, skriptga yozma.
Azizbek parol yuborsa: uni ISHLATMA, faylga yozma, va darhol ayt —
"parolni yubormang, buni almashtiring, bizda parolsiz yo'l bor".
Sayt parol so'rasa, javob: brauzer profiliga bir marta o'zi kirsin.
Bu cheklov emas — parol bilan avtomatik kirish hisobni bloklattiradi.

WINDOWS KODIROVKASI — muhim
Windows konsoli o'zbekcha/kirill harflarni buzadi. Shuning uchun:
- Python skriptda faylga yozganda har doim encoding="utf-8" qo'sh.
- Uzun yoki o'zbekcha natijani print() qilma — faylga yoz, keyin o'qi.
- Kerak bo'lsa skript boshida: sys.stdout.reconfigure(encoding="utf-8")
"Kodirovka xatosi" chiqsa, bu to'siq emas — yuqoridagi yo'l bilan aylanib o't.

MUAMMOGA UCHRASANG
Kutubxona yetishmasa — `pip install` qilib ol.
Dastur yo'q bo'lsa — `winget install` bilan o'rnat.
Fayl formatini o'qiy olmasang — o'qiy oladigan kutubxonani o'rnat.
Azizbekdan so'rash oxirgi chora, birinchi emas.

XOTIRA — bu senga tegishli, o'zing boshqarasan
Papka: {MEM_DIR}
- xotira/profil.md          — Azizbek kim, nima bilan shug'ullanadi, qanday ishlaydi
- xotira/indeks.md          — loyihalar/*.md fayllarining bir qatorlik ro'yxati
- xotira/vazifalar.md       — bajarilishi kerak bo'lgan ishlar, QISQA shaklda
- xotira/eslatmalar.md      — qolgan muhim narsalar
- xotira/loyihalar/<nom>.md — har loyiha/soha uchun ALOHIDA, BATAFSIL fayl
  (masalan loyihalar/jetcafe.md, loyihalar/nishon.md) — bular pastdagi
  "HOZIRGI XOTIRANG" bo'limiga AVTOMATIK YUKLANMAYDI, faqat kerak bo'lganda
  Read bilan o'qiladi. Shuning uchun bu fayllarni istalgancha batafsil
  yozish mumkin — hajm cheklovi YO'Q.

Loyiha fayllari bilan ishlash tartibi (MUHIM, har safar shunday qil):
- Agar suhbat biror loyiha/soha haqida bo'lsa — AVVAL xotira/indeks.mddan
  tegishli fayl nomini top, keyin Read bilan o'sha xotira/loyihalar/<nom>.md
  faylni TO'LIQ o'qi. Taxmin qilma, indeks.md'dagi bir qatorga ishonib
  javob berma — batafsili doim loyiha faylida.
- Yangi fakt bilsang — o'sha AYNAN loyihaning faylini Edit bilan yangila,
  umumiy fayllarga (profil/vazifalar/eslatmalar) loyiha tafsilotini yozma.
- Yangi loyiha/mijoz boshlansa — xotira/loyihalar/ ichida yangi fayl yarat
  VA xotira/indeks.mdga bitta qator qo'sh.

Umumiy qoidalar:
1. Yangi muhim narsa bilsang — SHU ZAHOTI tegishli faylni Edit bilan yangila.
   So'rashini kutma. "Eslab qol" deyishini ham kutma.
2. Ish yakunlansa yoki holat o'zgarsa — tegishli loyiha faylini va (qisqa
   holatda) vazifalar.md ni yangila.
3. Har bir faktni faqat BITTA joyga yoz. Takrorlama.
4. Maydakash narsalarni yozma (bir martalik savollar, o'tkinchi tafsilotlar).
5. Eskirgan ma'lumotni o'chirib, yangisini yoz.
6. MUHIM: profil.md/indeks.md/vazifalar.md/eslatmalar.md HAR BIRI 15 000
   belgidan oshmasin (bular prompt ichiga to'liq/deyarli to'liq yuklanadi).
   Oshsa, eski/tugagan yozuvlarni qisqartirib birlashtir. xotira/loyihalar/
   ichidagi fayllarga bu cheklov TEGISHLI EMAS — ular avtomatik yuklanmaydi.
   Sabab: umumiy fayllar juda kattalashsa Jarvis umuman ishga tushmaydi.

Pastdagi "HOZIRGI XOTIRANG" bo'limi joy tejash uchun QISQARTIRILGAN bo'lishi
mumkin ("…eski qismi kesildi…" belgisi bo'lsa — bu faqat eslatmalar.md kabi
tail bilan kesiladigan fayllarga tegishli). Eski ma'lumot kerak bo'lsa —
tegishli xotira faylini Read bilan to'liq o'qi, taxmin qilma.

ESKI SUHBATLAR
Papka: {LOG_DIR}
Har kunning to'liq yozuvi `YYYY-MM-DD.md` shaklida avtomatik saqlanadi.
Oxirgi kunlar: {_recent_days()}
Azizbek o'tgan suhbat haqida so'rasa ("kecha nima gaplashgandik", "falon
narsani qachon aytgandim") — Grep vositasi bilan shu papkani qidir, keyin
Read bilan kerakli joyini o'qi. Taxmin qilma, qidirib top.

HOZIRGI XOTIRANG
{_read_memory()}
{extra}
"""


REMEMBER_PROMPT = """[tizim] Suhbat tugadi. Endi xotirangni yangila:
1. Shu suhbatda Azizbek haqida bilgan yangi narsalarni tegishli xotira
   fayliga yoz — loyihaga oid batafsil narsa xotira/loyihalar/<nom>.md ga
   (indeks.md orqali toping, yangi loyiha bo'lsa yangi fayl+indeks qatori
   yarating), umumiy narsa profil/vazifalar/eslatmalarga.
2. Holati o'zgargan ishlarni yangila, bajarilgan vazifalarni belgila
   (vazifalar.mdda QISQA, batafsili loyiha faylida).
3. Yangi bilgan narsa bo'lmasa, hech narsa o'zgartirma.
Ishni bajarib bo'lgach, faqat "xotira yangilandi" deb javob ber."""


# Hech qachon bajarilmaydigan buyruqlar (qaytarib bo'lmaydigan zarar)
XAVFLI_BUYRUQLAR = [
    r"rm\s+-rf",
    r"\brmdir\s+/s",
    r"\bdel\s+/[qsf]",
    r"\bformat\s+[a-z]:",
    r"\bdiskpart\b",
    r"\bshutdown\b",
    r"\bbcdedit\b",
    r"\breg\s+delete\b",
    r"Remove-Item[^|]*-Recurse[^|]*-Force",
    r"\btakeown\b",
    r"\bcipher\s+/w",
    r"\bmkfs\b",
    r"\bnet\s+user\b",
    # Faqat HAQIQIY qurilma fayllariga yozishni bloklaydi (masalan
    # `dd if=... of=/dev/sda`) — `/dev/null`, `/dev/zero` va h.k. psevdo-
    # qurilmalarga yozish (masalan juda keng tarqalgan `2>/dev/null`) esa
    # butunlay zararsiz va bloklanmasligi kerak edi. 2026-09-18: bu haddan
    # tashqari keng naqsh sabab bir nechta zararsiz buyruq (`du`, `grep -oP`,
    # `pip list`, `python -c` va h.k. — barchasi oxirida shunchaki
    # `2>/dev/null` bilan tugagan) noto'g'ri "xavfli" deb bloklangani
    # Azizbek bilan ishlashda real aniqlandi.
    r">\s*/dev/(?!null\b|zero\b|full\b|random\b|urandom\b|stdin\b|stdout\b|stderr\b|fd/)",
]


async def auto_approve(tool_name, input_data, context):
    """Buyruqlarni o'zi bajaradi, faqat halokatli buyruqlarni rad etadi."""
    if tool_name == "Bash":
        cmd = input_data.get("command", "")
        for naqsh in XAVFLI_BUYRUQLAR:
            if re.search(naqsh, cmd, re.IGNORECASE):
                return PermissionResultDeny(
                    message=(
                        "Bu buyruq xavfli deb belgilangan va bajarilmadi. "
                        "Azizbekdan o'zi bajarishini so'ra."
                    )
                )
        # ILDIZ SABABNI KOD ORQALI YO'QOTISH (2026-09-05): Bash'ning
        # run_in_background=true rejimi joriy suhbat turi (ask() chaqiruvi)
        # tugagandan KEYIN ham fonda davom etib, natijasi keyingi (bog'liqsiz)
        # ask() chaqiruvi ichiga tasodifiy vaqtda aralashib kirishiga sabab
        # bo'lardi — aynan shu orqali "eski savolni qayta so'rash" xatosi
        # yuzaga kelgan (tasdiqlangan: real sinovda repro qilindi). Telegram
        # tarafida xabarlar allaqachon lock bilan ketma-ket (serial) ishlanadi,
        # shuning uchun fon vazifaga hojat yo'q — uni majburan sinxron
        # (bloklovchi) rejimga o'tkazamiz: shu ask() chaqiruvi butun buyruq
        # tugaguncha kutadi, natija AYNAN shu turdagi javobga kiradi, hech
        # qanday keyingi turga "sizib chiqmaydi".
        with open(BASE_DIR / "_diag_bash.log", "a", encoding="utf-8") as _f:
            _f.write(f"{datetime.now()} INPUT_DATA={input_data!r}\n")
        if input_data.get("run_in_background"):
            input_data = dict(input_data)
            input_data["run_in_background"] = False
    elif tool_name in INTEGRATSIYA_YOZISH:
        _integratsiya_logga_yoz(tool_name, input_data)
    return PermissionResultAllow(updated_input=input_data)


async def _confirm_deny(tool_name, input_data, context):
    return PermissionResultDeny(
        message="Bu vositani ishlatish uchun ruxsat yo'q."
    )


# ---------------- Ochiq savol holati (kod darajasidagi tekshiruv) ----------------
# Muammo: fon vazifasi (masalan uzoq Bash test) tugagani haqidagi xabar SDK
# tomonidan navbatdagi ask() chaqiruvi ichiga aralashtirilib yuborilishi mumkin
# (bitta ClaudeSDKClient ulanishi barcha xabarlar uchun qayta ishlatiladi).
# Natijada model ba'zan Azizbekning YANGI xabariga javob berish o'rniga fon
# vazifa haqida gapirib, oldin bergan (va Azizbek allaqachon javob bergan)
# savolni qayta so'rab yuboradi (2026-09-05 da real sodir bo'lgan xato).
# Bunga faqat tizim ko'rsatmasidagi matnga ("yodda tut" qoidasi) ishonib
# bo'lmaydi — shuning uchun holatni KOD orqali ham kuzatamiz: Jarvis oxirgi
# javobida ochiq savol qoldirgan bo'lsa, keyingi ask() chaqiruvida shu savol
# aniq eslatib, "bu allaqachon javob olingan bo'lishi mumkin" deb ogohlantirib
# qo'shiladi — modelning o'zi eslab qolishiga qoldirilmaydi.
_SAVOL_QATOR_RE = re.compile(r"[^\n]*\?\s*$")


def _extract_pending_question(javob: str) -> str | None:
    """Javob ochiq savol bilan tugagan bo'lsa (masalan "...qilaymi?"), o'sha
    oxirgi savol qatorini qaytaradi. Bo'lmasa None."""
    if not javob:
        return None
    oxirgi_abzas = javob.strip().splitlines()[-1] if javob.strip() else ""
    m = _SAVOL_QATOR_RE.match(oxirgi_abzas.strip())
    if m:
        return oxirgi_abzas.strip()
    return None


class Jarvis:
    """
    async with Jarvis() as j:
        javob = await j.ask("Salom")
    """

    def __init__(
        self,
        confirm_fn=None,
        extra_prompt: str = "",
        model: str = "sonnet",
        log: bool = True,
    ):
        self._log = log

        # Oxirgi himoya: prompt baribir juda uzun bo'lib qolsa, Windows
        # jarayonni ishga tushira olmaydi. Shuning uchun qattiq kesamiz —
        # Jarvis ishlamay qolgandan ko'ra, xotiraning bir qismi kesilgani yaxshi.
        prompt = build_system_prompt(extra_prompt)
        if len(prompt) > PROMPT_LIMIT:
            prompt = prompt[:PROMPT_LIMIT] + (
                "\n…(tizim ko'rsatmasi uzunligi chegarasi sabab kesildi — "
                "to'liq ma'lumot uchun xotira fayllarini Read bilan o'qi)…\n"
            )

        options_kwargs = dict(
            system_prompt=prompt,
            model=model,
            allowed_tools=SAFE_TOOLS,
            can_use_tool=confirm_fn or _confirm_deny,
            cwd=str(BASE_DIR),
            permission_mode="default",
            # Standart 1MB bufer katta sahifa matni/HTML uchun yetmaydi
            # ("JSON message exceeded maximum buffer size" xatosi) — kattalashtiramiz.
            max_buffer_size=25 * 1024 * 1024,
        )
        self._options = ClaudeAgentOptions(**options_kwargs)
        self._client = None
        # Kod darajasidagi holat: Jarvisning oxirgi javobida ochiq qolgan
        # savol (bo'lsa). Quyida ask() ichida tekshiriladi.
        self._pending_question: str | None = None
        # ILDIZ SABAB #2 (2026-09-05, real sinovda ISBOTLANDI): bitta
        # ClaudeSDKClient ulanishi orqali IKKITA ask() BIR VAQTDA (parallel)
        # chaqirilsa, ikkalasi ham bitta umumiy javob oqimini (receive_response)
        # o'qiydi — natijada javoblar bir-biriga ARALASHIB ketadi (sinovda:
        # bitta so'rov ikkinchisining matnini ham yutib oldi, ikkinchisi bo'sh
        # qoldi). Avval bu faqat tashqarida (jarvis_telegram.py'dagi global
        # `lock`) oldi olingan edi — ya'ni HAR BIR chaqiruvchi shu tartibga
        # rioya qilishni ESLAB QOLISHI kerak edi. Endi klassning o'zi
        # kafolatlaydi: qaysi tashqi kod chaqirmasin, bir vaqtning o'zida
        # faqat bitta ask() ishlaydi, qolganlari navbatda kutadi.
        self._lock = asyncio.Lock()

        # 2026-09-26 qo'shilgan holat (heartbeat/dublikat-bloklash/`/stop`
        # uchun) — barchasi FAQAT `self._lock` band bo'lganda mazmunli,
        # bo'sh bo'lsa None/bo'sh qiymatlarda turadi.
        self._current_task: asyncio.Task | None = None
        self._current_request_text: str | None = None
        self._request_started_at: datetime | None = None
        self._last_step: str | None = None
        self._partial_parts: list[str] = []
        self._fon_ish_id: str | None = None

    @property
    def is_busy(self) -> bool:
        return self._lock.locked()

    @property
    def current_request_text(self) -> str | None:
        """Hozir bajarilayotgan so'rov matni (bo'sh bo'lsa None) — dublikat
        aniqlash uchun tashqi kod (jarvis_telegram.py) shu bilan solishtiradi."""
        return self._current_request_text

    def holat_matni(self) -> str:
        """'/holat', 'tugatdingmi' kabi so'rovlarga darhol (navbatsiz)
        beriladigan javob matni."""
        if not self.is_busy:
            return "Hozir bo'sh — hech narsa bajarilmayapti."
        elapsed = 0.0
        if self._request_started_at:
            elapsed = (datetime.now() - self._request_started_at).total_seconds()
        daq, son = divmod(int(elapsed), 60)
        qadam = self._last_step or "boshlanmoqda"
        soragi = (self._current_request_text or "")[:200]
        return (
            f"⏳ Band — {daq}:{son:02d} davomida ishlayapman.\n"
            f"So'rov: {soragi}\n"
            f"Oxirgi qadam: {qadam}\n\n"
            "Yakunlashni istasangiz /stop yozing."
        )

    async def __aenter__(self):
        _ensure_dirs()
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.connect()
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.disconnect()

    async def _reset_client(self, sabab: str = "timeout") -> bool:
        """Uzoq/osilib qolgan so'rovdan keyin ulanishni butunlay yangilaydi.

        2026-09-26 TUZATISH — ILDIZ SABAB (AzizEdu production hodisasi,
        Azizbek payqagan): avval bu funksiya FAQAT `disconnect()` chaqirardi
        — bu esa faqat Python-tarafdagi ulanishni uzardi. Tashqi `claude.exe`
        CLI jarayoni (va uning ichida ishga tushirilgan Bash/SSH kabi tool-
        jarayonlar) hech qanday to'xtatish signali OLMAY, ishlashda DAVOM
        ETARDI — shuning uchun "bekor qildim" degan xabar productionda
        30+ daqiqa davomida yolg'on bo'lib chiqdi (kod hali yozilar, backup
        olinar, deploy qilinar edi, Azizbek buni keyinroq zaxira fayl
        vaqtlaridan payqab qoldi).

        Endi 3 bosqich:
        (1) HAQIQIY `interrupt()` — SDK'ning rasmiy streaming-to'xtatish
            signali, CLI o'zining ichki tool-jarayonlarini ham tozalashi
            kutiladi (bu — asosiy, "yumshoq" tuzatish).
        (2) `disconnect()` — Python-tarafdagi ulanishni yopadi (SDK o'zi
            ham terminate/kill eskalatsiyasini ichida qiladi, lekin FAQAT
            bevosita bola-jarayon uchun).
        (3) Ehtiyot chorasi (Azizbek aniq so'ragan): agar eski claude.exe
            PID'i 10 soniyada o'z-o'zidan tugamasa, `taskkill /T /F` bilan
            BUTUN jarayon daraxti (nabira-jarayonlar bilan birga) majburan
            o'ldiriladi. Natija chaqiruvchiga halol aytiladi (True = majburan
            o'ldirishga to'g'ri keldi).
        """
        eski_pid = None
        try:
            eski_pid = self._client._transport._process.pid
        except Exception:
            pass

        try:
            await asyncio.wait_for(self._client.interrupt(), timeout=10)
            diag(f"interrupt() yuborildi (sabab: {sabab})")
        except Exception as e:
            diag(f"interrupt() muvaffaqiyatsiz/timeout (sabab: {sabab}): {e}")

        try:
            await asyncio.wait_for(self._client.disconnect(), timeout=15)
        except Exception as e:
            diag(f"disconnect() muvaffaqiyatsiz/timeout: {e}")

        majburan_oldirildi = await _eski_jarayonni_tekshir_va_ozdir(eski_pid)
        if majburan_oldirildi:
            diag(f"PID {eski_pid} taskkill /T /F bilan majburan o'ldirildi")

        self._client = ClaudeSDKClient(options=self._options)
        await self._client.connect()
        return majburan_oldirildi

    async def _run(self, text: str, on_chunk=None) -> str:
        parts: list[str] = []
        self._partial_parts = parts
        await self._client.query(text)
        async for message in self._client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
                        if on_chunk:
                            on_chunk(block.text)
                    elif isinstance(block, ToolUseBlock):
                        self._last_step = _tool_qadam_matni(block)
        return "".join(parts)

    async def _heartbeat_sikli(self, on_heartbeat) -> None:
        """Ish davom etayotganda har HEARTBEAT_INTERVAL_S soniyada bir marta
        `on_heartbeat(oxirgi_qadam)` chaqiradi. `ask()` bu vazifani asosiy ish
        bilan BIR VAQTDA ishga tushiradi va tugagach cancel qiladi."""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL_S)
            if on_heartbeat:
                try:
                    qadam = self._last_step or "ishlayapman..."
                    on_heartbeat(qadam)
                except Exception:
                    pass

    async def _majburan_toxtat(self, run_task: asyncio.Task, sabab: str) -> str:
        """MAX_ASK_TIMEOUT_S zaxira chegarasiga yetilganda (yoki `/stop`
        buyrug'ida) chaqiriladi — endi shunchaki "bekor qildim" deb
        AYTIB QO'YISH emas, HAQIQATDA to'xtatadi va halol hisobot beradi."""
        diag(f"majburan to'xtatish boshlandi (sabab: {sabab})")
        majburan_oldirildi = await self._reset_client(sabab=sabab)

        if not run_task.done():
            run_task.cancel()
            try:
                await run_task
            except (asyncio.CancelledError, Exception):
                pass

        yigilgan = "".join(self._partial_parts).strip() if self._partial_parts else ""
        xabar = f"So'rov to'xtatildi ({sabab})."
        if self._last_step:
            xabar += f"\nOxirgi qadam: {self._last_step}"
        if yigilgan:
            xabar += f"\n\nShu paytgacha bajarilganlar:\n{_tail(yigilgan, 1500)}"
        if majburan_oldirildi:
            xabar += (
                "\n\n(Eslatma: eski jarayon o'z-o'zidan tugamadi — "
                "MAJBURAN to'xtatildi, taskkill /T /F bilan.)"
            )
        return xabar

    async def stop(self) -> str:
        """`/stop` buyrug'i uchun: HOZIR bajarilayotgan so'rovni haqiqatan
        to'xtatadi (interrupt + kerak bo'lsa majburan o'ldirish) va shu
        paytgacha bajarilganlar haqida hisobot qaytaradi. Hech narsa
        ishlamayotgan bo'lsa, shunchaki shuni aytadi (navbatga TEGMAYDI —
        navbatdagi keyingi xabarlar o'z tartibida davom etadi)."""
        if not self.is_busy or not self._current_task:
            return "Hozir hech narsa bajarilmayapti — to'xtatadigan narsa yo'q."
        return await self._majburan_toxtat(self._current_task, sabab="/stop buyrug'i")

    async def ask(self, text: str, on_chunk=None, on_heartbeat=None) -> str:
        # self._lock: shu Jarvis ulanishida bir vaqtning o'zida faqat BITTA
        # so'rov ishlashini kafolatlaydi (ILDIZ SABAB #2 tuzatishi — yuqoridagi
        # izohga qara). Tashqi chaqiruvchi o'z lock'ini unutgan taqdirda ham,
        # bu yerda avtomatik navbatga turadi, javoblar aralashmaydi.
        diag("lock kutilmoqda")
        async with self._lock:
            diag("lock olindi")
            # KOD DARAJASIDAGI TEKSHIRUV (system-prompt matniga qo'shimcha,
            # unga ishonib qolmaslik uchun): agar oldingi javobda ochiq savol
            # qolgan bo'lsa, uni bu safargi so'rovga aniq eslatma sifatida
            # qo'shib yuboramiz — fon vazifa xabari orasiga tushib ketmasin.
            if self._pending_question:
                text = (
                    "[KOD ESLATMASI — avtomatik qo'shildi: sening oldingi javobing "
                    f"ochiq savol bilan tugagan edi: \"{self._pending_question}\". "
                    "Quyidagi Azizbekning YANGI xabari ko'pincha aynan shu savolga "
                    "javobdir (masalan \"ha\", \"mayli\", \"yo'q\", \"o't\", \"qil\" "
                    "va h.k.). Agar shunday bo'lsa, savolni ALLAQACHON YOPILGAN deb "
                    "hisobla, uni qayta so'rama va aytilgan amalni to'g'ridan-to'g'ri "
                    "bajar. Fon vazifa haqida biror xabar bo'lsa ham, avval shu yangi "
                    "xabarga javob ber.]\n\n" + text
                )
                self._pending_question = None

            self._current_request_text = text
            self._request_started_at = datetime.now()
            self._last_step = None
            self._partial_parts = []
            self._fon_ish_id = _fon_ishlar.royxatga_ol("telegram", text, str(BASE_DIR))

            heartbeat_task = None
            if on_heartbeat:
                heartbeat_task = asyncio.create_task(self._heartbeat_sikli(on_heartbeat))

            diag("Claude'ga so'rov yuborildi")
            run_task = asyncio.create_task(self._run(text, on_chunk))
            self._current_task = run_task
            try:
                javob = await asyncio.wait_for(run_task, timeout=MAX_ASK_TIMEOUT_S)
            except asyncio.TimeoutError:
                diag(f"{MAX_ASK_TIMEOUT_S}s zaxira chegarasiga yetdi")
                javob = await self._majburan_toxtat(
                    run_task, sabab=f"{MAX_ASK_TIMEOUT_S}s zaxira chegarasi"
                )
                self._pending_question = None
            except asyncio.CancelledError:
                # `/stop` orqali `stop()` o'zi run_task'ni allaqachon boshqargan —
                # bu yerga faqat run_task tashqaridan cancel qilingan holatda kelamiz.
                javob = "To'xtatildi."
                self._pending_question = None
            else:
                diag("Claude'dan javob keldi")
                self._pending_question = _extract_pending_question(javob)
            finally:
                if heartbeat_task:
                    heartbeat_task.cancel()
                if self._fon_ish_id:
                    _fon_ishlar.royxatdan_ochir(self._fon_ish_id)
                self._current_task = None
                self._current_request_text = None
                self._request_started_at = None
                self._last_step = None
                self._fon_ish_id = None
            if self._log:
                log_exchange(text, javob)
            return javob

    @property
    def pending_question(self) -> str | None:
        """Tashqi kod uchun: oxirgi javobda ochiq qolgan savol bormi, tashqaridan
        o'qish uchun. Faqat o'qish — o'zgartirish shu klass ichida ask() orqali
        boshqariladi."""
        return self._pending_question

    async def remember(self):
        """Suhbat oxirida xotirani yangilaydi (javobi ko'rsatilmaydi)."""
        try:
            async with self._lock:
                run_task = asyncio.create_task(self._run(REMEMBER_PROMPT))
                self._current_task = run_task
                try:
                    await asyncio.wait_for(run_task, timeout=MAX_ASK_TIMEOUT_S)
                except asyncio.TimeoutError:
                    await self._majburan_toxtat(run_task, sabab="remember() zaxira chegarasi")
                finally:
                    self._current_task = None
            return True
        except Exception:
            return False

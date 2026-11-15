"""
JARVIS PROAKTIV — 2-qadam: Telegram xabar yuborish qo'shildi (2026-09-12).

Bu fayl jarvis_core.py'dan va jarvis_telegram.py'dan MUSTAQIL, alohida
skript — ularga HECH QANDAY aloqasi yo'q, ularni buzmaydi. Hozircha
Task Scheduler ULANMAGAN, qo'lda ishga tushiriladi:
    python jarvis_proaktiv.py

1-qadam (bor): nishonsport.uz domenining Cloudflare'dagi holatini
(NS yozuvlari orqali) tekshiradigan `domen_cloudflare_holati()` funksiyasi.

2-qadam (YANGI, shu faylda qo'shilgan):
    - `telegram_xabar_yubor(matn)` — mavjud bot token/OWNER_ID (config.py)
      orqali, jarvis_telegram.py'ga UMUMAN tegmasdan, to'g'ridan-to'g'ri
      Telegram Bot API'ga (https://api.telegram.org/bot<TOKEN>/sendMessage)
      oddiy HTTP so'rov yuboradi (urllib, tashqi kutubxona shart emas).
    - xotira/kuzatuv.md — har bir kuzatuv bandi ("nishon_domen_active" kabi)
      uchun holat saqlanadi. Band "hal_qilingan" yoki "xabar_yuborilgan"
      deb belgilangan bo'lsa, shu band uchun Telegram xabar QAYTA
      YUBORILMAYDI. `nishon_domen_active` banди Azizbek SSL'ni qo'lda
      o'rnatgani uchun ATAYLAB "hal_qilingan" deb oldindan belgilangan —
      funksiya (`nishon_domen_kuzatuvi`) o'chirilmagan, kelajakdagi boshqa
      kuzatuvlar uchun NAMUNA bo'lib qoladi, lekin bu band uchun endi
      hech qachon xabar yubormaydi.

3-qadam (BAJARILDI, 2026-09-12): Windows Task Scheduler ulandi — "Jarvis
Proaktiv Tekshiruv" vazifasi har 30 daqiqada shu faylni (pythonw.exe orqali,
oynasiz) ishga tushiradi. Yuqoridagi eski izoh ("hozircha YO'Q") ESKIRGAN,
shu sabab shu yerda tuzatildi.

4-qadam (2026-09-13, QISQA VAQT shu yerga ulangan edi, keyin ALOHIDA
vazifaga ko'chirildi): AI yangiliklar kuzatuvi (`ai_yangiliklar.py`) avval
shu faylga ulangan edi, lekin Azizbek darhol/tez-tez (bir necha daqiqada)
reaksiya kerakligini aytgach, 30 daqiqalik tsikl juda sekin bo'lib qoldi —
shuning uchun ALOHIDA Task Scheduler vazifasiga ("Jarvis AI Yangiliklar",
har 3 daqiqa) ko'chirildi, bu yerdan OLIB TASHLANDI. Tafsilot:
`xotira/loyihalar/jarvis_ichki.md`.
"""

import html as _html
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import config  # TELEGRAM_TOKEN, OWNER_ID — mavjud bot bilan bir xil (config.py)

try:
    # roadmap #9 MVP (2026-09-21) — ixtiyoriy, alohida modul. Topilmasa ham
    # (masalan fayl ko'chirilgan/o'chirilgan bo'lsa) bu skriptning asosiy
    # vazifasi (Telegram xabar yuborish) BUZILMASLIGI kerak — shu sabab
    # import xatosi jim yutiladi.
    import jarvis_bildirishnoma as _hud_bildirishnoma
except Exception:
    _hud_bildirishnoma = None

BASE_DIR = Path(__file__).parent
MEM_DIR = BASE_DIR / "xotira"
KUZATUV_FILE = MEM_DIR / "kuzatuv.md"
LOG_FILE = BASE_DIR / "jarvis_proaktiv.log"

DOMEN = "nishonsport.uz"
CLOUDFLARE_NS_BELGISI = "ns.cloudflare.com"
OMMAVIY_RESOLVERLAR = ["1.1.1.1", "8.8.8.8"]

# Bu kuzatuv bandi uchun "hal_qilingan" holati oldindan xotira/kuzatuv.md
# fayliga yozilgan (Azizbek SSL'ni 2026-09-12 kuni qo'lda o'rnatdi) — shu
# sababli quyidagi kod hech qachon Telegram xabar yubormaydi, lekin
# NAMUNA sifatida qoldirilgan.
NISHON_KUZATUV_KODI = "nishon_domen_active"


def _logga_yoz(matn: str):
    """Har ishga tushishni jarvis_proaktiv.log fayliga yozadi."""
    vaqt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{vaqt}] {matn}\n")
    except Exception:
        pass  # Log yozilmasa ham asosiy mantiq to'xtamasin


def _ns_yozuvlari(domain: str, resolver: str) -> str:
    """Berilgan ommaviy resolver orqali domenning NS yozuvlarini so'raydi
    (nslookup orqali — tashqi kutubxona kerak emas). Xato/timeout bo'lsa
    bo'sh satr qaytaradi."""
    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        natija = subprocess.run(
            ["nslookup", "-type=NS", domain, resolver],
            capture_output=True,
            text=True,
            timeout=15,
            **kwargs,
        )
        return natija.stdout or ""
    except Exception as e:
        _logga_yoz(f"NS so'rovida xato ({resolver}): {e!r}")
        return ""


def domen_cloudflare_holati(domain: str) -> str:
    """Domenning Cloudflare'dagi holatini aniqlaydi.

    Ikkala mustaqil ommaviy resolver (1.1.1.1 va 8.8.8.8) ham domen NS
    yozuvlarida Cloudflare nomeserverini ko'rsatsa "Active" qaytaradi
    (delegatsiya global miqyosda tarqalgan), aks holda "Pending"
    qaytaradi.
    """
    natijalar = {}
    for resolver in OMMAVIY_RESOLVERLAR:
        matn = _ns_yozuvlari(domain, resolver)
        natijalar[resolver] = CLOUDFLARE_NS_BELGISI in matn.lower()
    _logga_yoz(f"NS tekshiruvi natijasi: {natijalar}")

    if natijalar and all(natijalar.values()):
        return "Active"
    return "Pending"


# 2026-09-27 (Azizbek topdi): telegram_xabar_yubor() eskidan parse_mode
# UMUMAN belgilamas edi — Jarvis javoblarida odatiy bo'lgan "**qalin**"
# uslubi Telegram'da xom "**qalin**" holida ko'rinar edi. Endi matn HTML'ga
# o'tkaziladi (faqat **qalin**/__qalin__ va `kod` qo'llab-quvvatlanadi,
# qolgan hamma narsa xavfsiz escape qilinadi) va parse_mode="HTML" bilan
# yuboriladi. Shuningdek Telegram'ning 4096-belgi chegarasidan uzun xabar
# endi TASHLAB YUBORILMAYDI/qirqilmaydi — mos bo'laklarga bo'lib, alohida-
# alohida xabar sifatida ketma-ket yuboriladi.
TELEGRAM_XABAR_LIMIT = 4096


def _markdown_html_ga(matn: str) -> str:
    """`**qalin**`/`__qalin__` -> `<b>`, `` `kod` `` -> `<code>`, qolgan
    hamma narsa (shu jumladan Jarvis javobida kelishi mumkin bo'lgan xom
    `<`/`&` belgilari) HTML uchun xavfsiz escape qilinadi -- shuning uchun
    avval ESCAPE qilinadi, keyin markdown belgilari HTML teglariga
    almashtiriladi (aks holda o'zimiz qo'shgan teglar ham escape bo'lib
    qolar edi)."""
    xavfsiz = _html.escape(matn, quote=False)
    xavfsiz = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", xavfsiz, flags=re.DOTALL)
    xavfsiz = re.sub(r"__(.+?)__", r"<b>\1</b>", xavfsiz, flags=re.DOTALL)
    xavfsiz = re.sub(r"`([^`]+?)`", r"<code>\1</code>", xavfsiz)
    return xavfsiz


def _matnni_boklarga_bol(matn: str, maks: int = TELEGRAM_XABAR_LIMIT) -> list:
    """Uzun (asl, HAM markdown belgili) matnni Telegram chegarasidan oldin
    xavfsiz bo'laklarga bo'ladi -- imkon qadar paragraf ("\n\n") yoki qator
    ("\n") chegarasida, shunda bitta `**...**` juftligi ikki bo'lakka
    bo'linib qolib, HTML tegi "ochiq" qolib ketmaydi (har bo'lak keyin
    ALOHIDA `_markdown_html_ga()` orqali o'tadi)."""
    if len(matn) <= maks:
        return [matn]
    boklar = []
    qoldiq = matn
    while len(qoldiq) > maks:
        chegara = qoldiq.rfind("\n\n", 0, maks)
        if chegara < maks * 0.4:
            chegara = qoldiq.rfind("\n", 0, maks)
        if chegara < maks * 0.4:
            chegara = maks
        boklar.append(qoldiq[:chegara])
        qoldiq = qoldiq[chegara:].lstrip("\n")
    if qoldiq:
        boklar.append(qoldiq)
    return boklar


def _bitta_xabar_yubor(matn_html: str) -> bool:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"

    def _post(payload: dict) -> tuple:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read()

    try:
        status, _body = _post({"chat_id": config.OWNER_ID, "text": matn_html, "parse_mode": "HTML"})
        if 200 <= status < 300:
            return True
        _logga_yoz(f"Telegram (HTML) javobi kutilmagan status: {status}")
    except Exception as e:
        _logga_yoz(f"Telegram (HTML) yuborishda xato, oddiy matnga qaytilmoqda: {e!r}")

    # HTML tarkibi biror sababdan noto'g'ri chiqib qolgan bo'lsa ham (masalan
    # kutilmagan tenglashmagan teg) xabar HECH QACHON yo'qolib qolmasin --
    # zaxira sifatida oddiy (formatlashsiz) matn bilan qayta urinamiz.
    try:
        oddiy = re.sub(r"<[^>]+>", "", matn_html)
        oddiy = _html.unescape(oddiy)
        status, _body = _post({"chat_id": config.OWNER_ID, "text": oddiy})
        return 200 <= status < 300
    except Exception as e:
        _logga_yoz(f"Telegram (zaxira, oddiy matn) yuborishda ham xato: {e!r}")
        return False


def telegram_xabar_yubor(matn: str) -> bool:
    """Mavjud bot token/OWNER_ID (config.py) orqali, jarvis_telegram.py'ga
    umuman tegmasdan, to'g'ridan-to'g'ri Telegram Bot API'ga oddiy HTTP
    POST so'rov bilan xabar yuboradi. Muvaffaqiyatli bo'lsa True qaytaradi.
    Uzun matn avtomatik bo'laklarga bo'linib, ketma-ket yuboriladi.
    """
    boklar = _matnni_boklarga_bol(matn)
    hammasi_ok = True
    for bok in boklar:
        if not _bitta_xabar_yubor(_markdown_html_ga(bok)):
            hammasi_ok = False

    if hammasi_ok and _hud_bildirishnoma:
        # roadmap #9 MVP (2026-09-21): Telegram bilan BIR VAQTDA HUD
        # bildirishnoma navbatiga ham yoziladi — HUD ochiq bo'lsa,
        # shu xabar u yerda ham (toast) ko'rinadi. Xato bo'lsa ham
        # (funksiyaning o'zi hech qachon ko'tarmaydi) Telegram
        # yuborilgani asosiy natija — shu SHART. Asl (markdown) matn
        # yoziladi -- HUD toast'ga HTML teg kerak emas.
        _hud_bildirishnoma.bildirishnoma_yoz(matn, manba="proaktiv")
    elif not hammasi_ok:
        _logga_yoz("Telegram xabar yuborishda xato (yuqoriga qarang).")
    return hammasi_ok


def _kuzatuv_holati(kod: str) -> str | None:
    """xotira/kuzatuv.md faylidan berilgan kuzatuv kodi uchun holatni
    o'qiydi (masalan "hal_qilingan", "xabar_yuborilgan"). Topilmasa None
    qaytaradi — bu "hali hech narsa qilinmagan" deb talqin qilinadi."""
    if not KUZATUV_FILE.exists():
        return None
    for qator in KUZATUV_FILE.read_text(encoding="utf-8").splitlines():
        qator = qator.strip()
        if qator.startswith(f"- {kod}:"):
            qolgan = qator.split(":", 1)[1].strip()
            holat = qolgan.split("|")[0].strip()
            return holat
    return None


def _kuzatuv_belgila(kod: str, holat: str, izoh: str):
    """xotira/kuzatuv.md fayliga yangi kuzatuv qatorini qo'shadi (mavjud
    qatorlarni o'zgartirmaydi, faqat yangi band qo'shadi)."""
    MEM_DIR.mkdir(exist_ok=True)
    vaqt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    yangi_fayl = not KUZATUV_FILE.exists()
    with open(KUZATUV_FILE, "a", encoding="utf-8") as f:
        if yangi_fayl:
            f.write(
                "# Kuzatuv — Jarvis proaktiv skriptlari kuzatib turgan "
                "bandlar holati\n\n"
                "Har bir band uchun holat shu yerda saqlanadi. Agar band "
                "\"hal_qilingan\" yoki \"xabar_yuborilgan\" deb "
                "belgilangan bo'lsa, proaktiv skript shu band uchun QAYTA "
                "Telegram xabar YUBORMAYDI. Format:\n"
                "`- <kod>: <holat> | <izoh> | <vaqt>`\n\n"
            )
        f.write(f"- {kod}: {holat} | {izoh} | {vaqt}\n")


def nishon_domen_kuzatuvi():
    """NAMUNA funksiya: domen holatini tekshiradi, "Active" bo'lsa VA
    kuzatuv.md'da bu band hali "hal_qilingan"/"xabar_yuborilgan" deb
    belgilanmagan bo'lsa — Telegram xabar yuboradi va belgilaydi.

    Hozircha xotira/kuzatuv.md faylida "nishon_domen_active" bandi
    ATAYLAB "hal_qilingan" deb oldindan yozilgan (Azizbek SSL'ni qo'lda
    o'rnatdi, 2026-09-12) — shuning uchun bu funksiya ishga tushsa ham
    endi hech qachon xabar yubormaydi. Kelajakda boshqa kuzatuv
    bandlari uchun shu naqshni nusxalash mumkin.
    """
    joriy_holat = _kuzatuv_holati(NISHON_KUZATUV_KODI)
    if joriy_holat in ("hal_qilingan", "xabar_yuborilgan"):
        _logga_yoz(
            f"'{NISHON_KUZATUV_KODI}' band allaqachon '{joriy_holat}' deb "
            "belgilangan — hech narsa qilinmaydi."
        )
        return

    holat = domen_cloudflare_holati(DOMEN)
    if holat == "Active":
        matn = (
            "Nishon domeni Cloudflare'da Active bo'ldi, "
            "nginx+SSL sozlashga tayyor."
        )
        if telegram_xabar_yubor(matn):
            _kuzatuv_belgila(
                NISHON_KUZATUV_KODI, "xabar_yuborilgan", "Proaktiv skript orqali"
            )
            _logga_yoz("Xabar muvaffaqiyatli yuborildi va kuzatuv.md'ga belgilandi.")
        else:
            _logga_yoz(
                "Active aniqlandi, LEKIN Telegram xabar yuborish "
                "MUVAFFAQIYATSIZ bo'ldi — belgi qo'yilmadi."
            )
    else:
        _logga_yoz("Hali kutilmoqda (Cloudflare NS to'liq tarqalmagan) — xabar yuborilmadi.")


if __name__ == "__main__":
    _logga_yoz("Ishga tushdi.")
    nishon_domen_kuzatuvi()

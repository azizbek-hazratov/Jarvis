"""
JARVIS OS -- har xodim uchun "tanbeh xotirasi" (2026-09-28, Azizbek "1-bosqich"
vazifasi, band 2).

G'OYA: Azizbek Telegramda "Nozima, bundan keyin ..." yoki "Samandar, bunday
qilma" desa, bu qoida `D:\\jarvis-os\\agentlar\\<xodim>_qoidalar.md` fayliga
yoziladi (vaqt bilan). Xodim "Tushundim, bundan keyin ..." deb tasdiqlaydi.

BU FAYL o'sha xodim uchun ERKIN SAVOL AI'ga yuborilishidan OLDIN o'qiladi va
promptga qo'shiladi -- shunday qilib AI xodim rolini o'ynaganda Azizbekning
oldingi tanbehlarini hisobga oladi. Deterministik (SQL/shablon asosidagi)
javoblar uchun bu fayl HAR JAVOBDAN OLDIN baribir o'qiladi (audit/kelajakda
kengaytirish uchun), lekin shablon javob matniga avtomatik aralashtirilmaydi
-- sabab: shablon javoblar (masalan Nozimaning to'lov ro'yxati) qattiq SQL
natijasi, erkin matn emas, "qoida"ni ularga aralashtirish noto'g'ri/chalkash
natija berishi mumkin edi. Bu cheklov ATAYLAB va ochiq aytiladi (loyihalar/
jarvis_os.md'da yozilgan).
"""

import re
from datetime import datetime
from pathlib import Path

QOIDALAR_DIR = Path(r"D:\jarvis-os\agentlar")

_TANBEH_KALIT = re.compile(
    r"bundan\s*(keyin|buyon)|endi\s*(doim|har\s*doim|shunday)|hech\s*qachon|"
    r"bunday\s*qilma|bundoq\s*qilma|shunday\s*qil\w*|qoida\s*[:\-]|eslab\s*qol|"
    r"^har\s*doim|har\s*safar|to'xtat\w*\s*buni|buni\s*to'xtat",
    re.IGNORECASE,
)

# 2026-09-28 (Azizbek tuzatishi, imtihon bandi): "... hech qachon uzilib
# qolganmi?" kabi ODDIY SAVOL "hech qachon" so'zi tufayli QOIDA deb
# xato tanilib qolmasligi kerak -- savol belgisi ANIQ signal.
_SAVOL_BELGISI = re.compile(r"\?\s*$")

# Qoida MAZMUNI xavfsizlik/tasdiq mexanizmini chetlab o'tishga urinsa --
# bunday "qoida" HECH QACHON saqlanmaydi (masalan "tasdiqsiz yubor").
_XAVFSIZ_EMAS_KALIT = re.compile(
    r"tasdiqsiz|tasdiqlamasdan|so'ramasdan\s*yubor|ruxsatsiz\s*yubor|"
    r"nazoratsiz|cheklovsiz|tekshirmasdan\s*yubor|"
    r"sinov_rejim\w*\s*(o'chir|off|yo'q\s*qil)|"
    r"limitni\s*(chetlab|bypas|oshir)|xavfsizlikni\s*o'chir|"
    r"qoidani\s*(buz|chetlab)",
    re.IGNORECASE,
)

_ROYXAT_SOROVI_KALIT = re.compile(
    r"qoidala\w*\s*(ko'rsat|royxat\w*|nima)|qanday\s*qoidala\w*",
    re.IGNORECASE,
)
_OCHIRISH_SOROVI_KALIT = re.compile(
    r"(\d+)\s*[-\s]*qoida\w*\s*(ni)?\s*o'chir",
    re.IGNORECASE,
)


def qoidalar_fayli(xodim_id: str) -> Path:
    return QOIDALAR_DIR / f"{xodim_id}_qoidalar.md"


def tanbehmi(matn: str) -> bool:
    """Azizbekning xabari yangi QOIDA/tanbehmi (savol/topshiriq emas).
    2026-09-28: "?" bilan tugagan SAVOL hech qachon qoida deb tanilmaydi,
    hatto "hech qachon" kabi kalit so'zlar bo'lsa ham."""
    matn = matn or ""
    if _SAVOL_BELGISI.search(matn.strip()):
        return False
    return bool(_TANBEH_KALIT.search(matn))


def xavfsiz_qoidami(matn: str) -> bool:
    """Qoidaning MAZMUNI xavfsizlik/tasdiq mexanizmini chetlab o'tishga
    urinmayaptimi (masalan "tasdiqsiz yubor"). True = xavfsiz, saqlash mumkin."""
    return not _XAVFSIZ_EMAS_KALIT.search(matn or "")


def royxat_sorovimi(matn: str) -> bool:
    """Azizbek "qoidalaringni ko'rsat" kabi ro'yxatni so'rayaptimi."""
    return bool(_ROYXAT_SOROVI_KALIT.search(matn or ""))


def ochirish_sorovimi(matn: str):
    """"2-qoidani o'chir" kabi so'rovda qoida raqamini (1-based) qaytaradi,
    mos kelmasa None."""
    m = _OCHIRISH_SOROVI_KALIT.search(matn or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None


def qoidalar_royxati(xodim_id: str) -> list:
    """Faylda saqlangan qoidalarni (har biri "- [vaqt] matn" qatori)
    RO'YXAT sifatida qaytaradi -- sarlavha/bo'sh qatorlarsiz."""
    matn = qoidalarni_oqi(xodim_id)
    qatorlar = []
    for satr in matn.splitlines():
        satr = satr.strip()
        if satr.startswith("- ["):
            qatorlar.append(satr[2:])  # "- " ni olib tashlab, "[vaqt] matn" qoladi
    return qatorlar


def qoida_ochir(xodim_id: str, raqam: int) -> str:
    """`raqam`-chi (1-based, `qoidalar_royxati()` tartibida) qoidani
    o'chiradi. Muvaffaqiyatli bo'lsa "ok", aks holda xato matni."""
    royxat = qoidalar_royxati(xodim_id)
    if raqam < 1 or raqam > len(royxat):
        return f"xato: {raqam}-qoida topilmadi (jami {len(royxat)} ta qoida bor)"
    try:
        p = qoidalar_fayli(xodim_id)
        yangi_royxat = royxat[: raqam - 1] + royxat[raqam:]
        sarlavha = (
            f"# {xodim_id} -- Azizbekning qoida/tanbehlari\n\n"
            "Har bir erkin (AI) javobdan oldin shu fayl o'qiladi va "
            "hisobga olinadi.\n\n"
        )
        matn = sarlavha + "".join(f"- {q}\n" for q in yangi_royxat)
        p.write_text(matn, encoding="utf-8")
        return "ok"
    except Exception as e:
        return f"xato: {e}"


def qoidalarni_oqi(xodim_id: str) -> str:
    """Har javobdan OLDIN chaqiriladi -- fayl yo'q/bo'sh bo'lsa "" qaytadi
    (xato ko'tarilmaydi, chaqiruvchi vazifasi buzilmasin)."""
    try:
        p = qoidalar_fayli(xodim_id)
        if p.exists():
            return p.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""


def qoida_qoshish(xodim_id: str, matn: str) -> str:
    """Yangi qoidani faylga qo'shadi (vaqt bilan), fayl yo'q bo'lsa sarlavha
    bilan yaratadi. Xato bo'lsa ham chaqiruvchiga aniq xabar qaytaradi."""
    p = qoidalar_fayli(xodim_id)
    vaqt = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            mavjud = p.read_text(encoding="utf-8")
        else:
            mavjud = (
                f"# {xodim_id} -- Azizbekning qoida/tanbehlari\n\n"
                "Har bir erkin (AI) javobdan oldin shu fayl o'qiladi va "
                "hisobga olinadi.\n\n"
            )
        if not mavjud.endswith("\n"):
            mavjud += "\n"
        mavjud += f"- [{vaqt}] {matn.strip()}\n"
        p.write_text(mavjud, encoding="utf-8")
        return "ok"
    except Exception as e:
        return f"xato: {e}"


def ai_prompt_uchun_qoshimcha(xodim_id: str) -> str:
    """AI promptiga qo'shiladigan blok -- qoidalar bo'lmasa bo'sh string
    (promptni keraksiz uzaytirmaslik uchun)."""
    matn = qoidalarni_oqi(xodim_id)
    if not matn.strip():
        return ""
    return (
        "\n\n[Azizbekning oldingi qoida/tanbehlari -- bularga AMAL QIL:]\n"
        + matn.strip() + "\n"
    )

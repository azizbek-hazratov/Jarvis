"""
JARVIS OS -- Avtomatik imtihon, 30 savol (2026-09-28, "1-bosqich" band 4,
Azizbek talabi: kechagi 12 savolni 30 taga yetkazish, har xodimga kamida
4 ta, shu jumladan boshqa xodimga yo'naltirish/"ma'lumot yo'q"/tasdiq
talab qiladigan holatlar).

TEZKOR va ISHONCHLI bo'lishi uchun brauzer (Playwright) EMAS -- to'g'ridan-
to'g'ri bridge (`/jamoa/savol`, HUD panel bilan bir xil funksiya) orqali
ishlaydi, shuning uchun HAR O'ZGARISHDAN KEYIN bir necha soniyada ishga
tushirish mumkin ("har o'zgarishdan keyin imtihonni ishga tushir" talabiga
mos). "Yozish" turidagi savollar yaratgan kutish-navbatdagi topshiriqlar
DARHOL avtomatik bekor qilinadi (real hech narsa bajarilmaydi/yuborilmaydi).

Ishlatish:
    python jarvis_imtihon.py            -> to'liq 30 ta savol, natija chop etiladi
    (dastur ichida) natija = ishga_tushir() -> {"jami":30,"otdi":N,"muvaffaqiyatsiz":[...]}
Chiqish kodi: 0 = barchasi o'tdi, 1 = kamida bittasi muvaffaqiyatsiz (chaqiruvchi
o'zgarishni QAYTARISHI kerak -- Azizbek qoidasi).
"""

import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE / "jarvis_hud"))
sys.path.insert(0, str(BASE))

import jarvis_xodim_telegram as jxt  # noqa: E402


# (xodim, matn, kutilgan_turi, kutilgan_egasi_yoki_None)
# kutilgan_turi: "oqish" | "malumot_yoq" | "yonaltirildi" | "yozish"
# kutilgan_egasi -- faqat "yonaltirildi" uchun (kim haqiqatda javob berishi kerak)
SAVOLLAR = [
    # ---- SAMANDAR (sotuvchi -- lid/qiziquvchi) ----
    ("samandar", "bugun nechta lid keldi?", "oqish", None),
    ("samandar", "yangi qiziquvchilar bormi?", "oqish", None),
    ("nozima", "bugun nechta lid keldi?", "yonaltirildi", "samandar"),
    ("samandar", "bugun qancha tushum bo'ldi?", "malumot_yoq", None),
    ("samandar", "SINOV_ Orzu ota-onalariga eslatma yubor", "yozish", None),

    # ---- MALIKA (mijoz operatori -- restoran/jetcafe, avval "Dasturxon") ----
    ("malika", "mijozlar nima so'radi?", "oqish", None),
    ("malika", "restoran haqida savol bo'ldimi?", "oqish", None),
    ("sardor", "jetcafe mijozlari nima so'radi?", "yonaltirildi", "malika"),
    ("malika", "bugun qancha taom sotildi?", "malumot_yoq", None),
    ("malika", "SINOV_ mijozga buyurtma tayyor deb xabar ber", "yozish", None),

    # ---- SARDOR (nazoratchi -- zaxira/xavfsizlik) ----
    ("sardor", "zaxira nusxa holati qanday?", "oqish", None),
    ("sardor", "server xavfsizligi qanday?", "oqish", None),
    ("bekzod", "zaxira nusxa qanday holatda?", "yonaltirildi", "sardor"),
    ("sardor", "bugungi xarajat qancha bo'ldi?", "malumot_yoq", None),
    ("sardor", "SINOV_ bu haqida menga alohida email jo'nat", "yozish", None),

    # ---- BEKZOD (tizim muhandisi -- botlar/watchdog, avval "Doktor") ----
    ("bekzod", "hamma ishlayaptimi?", "oqish", None),
    ("bekzod", "botlar holati qanday?", "oqish", None),
    ("nozima", "watchdog ishlayaptimi?", "yonaltirildi", "bekzod"),
    ("bekzod", "ombordagi mahsulot yetarlimi?", "malumot_yoq", None),
    ("bekzod", "SINOV_ bu haqida menga email jo'nat", "yozish", None),

    # ---- NOZIMA (buxgalter -- to'lov/qarzdor) ----
    ("nozima", "Orzu'da kim to'lamagan?", "oqish", None),
    ("nozima", "Grampus'da nechta faol sportchi bor?", "oqish", None),
    ("samandar", "kim to'lamagan?", "yonaltirildi", "nozima"),
    ("nozima", "bugun qancha foyda bo'ldi?", "malumot_yoq", None),
    ("nozima", "SINOV_ hisobotni menga alohida jo'nat", "yozish", None),

    # ---- KAMOLA (marketolog -- post/kontent/reja) ----
    ("kamola", "bu hafta nima post qilamiz?", "oqish", None),
    ("kamola", "marketing rejasi qanday?", "oqish", None),
    ("sardor", "bu haftagi kontent rejasi qanday?", "yonaltirildi", "kamola"),
    ("kamola", "bugungi xarajat qancha bo'ldi?", "malumot_yoq", None),
    ("kamola", "SINOV_ rejani menga alohida jo'nat", "yozish", None),
]

assert len(SAVOLLAR) == 30, f"30 ta bo'lishi kerak, hozir {len(SAVOLLAR)}"


def ishga_tushir(ovoz_sinovisiz: bool = True) -> dict:
    muvaffaqiyatsiz = []
    for xodim, matn, kutilgan_turi, kutilgan_egasi in SAVOLLAR:
        try:
            data = jxt.bridge_savol(xodim, matn)
        except Exception as e:
            muvaffaqiyatsiz.append({
                "xodim": xodim, "matn": matn, "kutilgan": kutilgan_turi,
                "olindi": f"BRIDGE XATO: {e}",
            })
            continue

        turi = data.get("turi")
        ok = turi == kutilgan_turi
        if ok and kutilgan_turi == "yonaltirildi":
            egasi = (data.get("yonaltirilgan") or {}).get("xodim")
            ok = egasi == kutilgan_egasi
            if not ok:
                muvaffaqiyatsiz.append({
                    "xodim": xodim, "matn": matn, "kutilgan": f"yonaltirildi->{kutilgan_egasi}",
                    "olindi": f"yonaltirildi->{egasi}",
                })
                continue
        if ok and turi == "yozish":
            # tasdiq talab qilingani tasdiqlandi -- DARHOL bekor qilamiz
            # (haqiqiy bajarish yo'q, faqat turi to'g'riligini tekshiramiz).
            task_id = data.get("id")
            if task_id:
                jxt.bridge_bekor_qilish(task_id)
        if not ok:
            muvaffaqiyatsiz.append({
                "xodim": xodim, "matn": matn, "kutilgan": kutilgan_turi, "olindi": turi,
            })

    natija = {
        "jami": len(SAVOLLAR),
        "otdi": len(SAVOLLAR) - len(muvaffaqiyatsiz),
        "muvaffaqiyatsiz": muvaffaqiyatsiz,
    }
    return natija


def main():
    natija = ishga_tushir()
    print(f"Jami: {natija['jami']}, o'tdi: {natija['otdi']}, muvaffaqiyatsiz: {len(natija['muvaffaqiyatsiz'])}")
    for m in natija["muvaffaqiyatsiz"]:
        print(f"  ❌ [{m['xodim']}] {m['matn']!r} -- kutilgan={m['kutilgan']!r}, olindi={m['olindi']!r}")
    sys.exit(0 if not natija["muvaffaqiyatsiz"] else 1)


if __name__ == "__main__":
    main()

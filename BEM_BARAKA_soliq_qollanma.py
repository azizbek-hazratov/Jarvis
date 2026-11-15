# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()

# Style
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)

def h1(text):
    p = doc.add_heading(text, level=1)
    return p

def h2(text):
    p = doc.add_heading(text, level=2)
    return p

def para(text, bold=False, italic=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    return p

def bullet(text):
    doc.add_paragraph(text, style='List Bullet')

def add_table(headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Light Grid Accent 1'
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    doc.add_paragraph("")

# TITLE
title = doc.add_heading("BEM BARAKA — Buxgalteriya va Soliq bo'yicha Professional Qo'llanma", level=0)

para("Tayyorlandi: Bosh buxgalter maslahati (AI, O'zbekiston Respublikasi Soliq kodeksi asosida)", italic=True)
para("Sana: 2026-09-01", italic=True)
para("Muhim eslatma: Quyidagi ma'lumotlar Soliq kodeksining umumiy tartib-qoidalariga asoslangan. Har yili stavkalar o'zgarishi mumkin — amaliy ish oldidan soliq.uz shaxsiy kabinetida joriy stavkalarni tekshirib oling.", bold=True)

doc.add_paragraph("")

# 0. Umumiy tushuntirish
h1("0. Soliq rejimi bo'yicha umumiy tushuntirish")
para("Diqqat: QQS (qo'shilgan qiymat solig'i) va Aylanma solig'i — bir korxona uchun bir vaqtda qo'llanilmaydi, ular alternativ soliq rejimlaridir (Soliq kodeksi 461-modda).")
bullet("Agar BEM BARAKA QQS to'lovchisi bo'lsa — umumbelgilangan tartibda ishlaydi: QQS (standart stavka 12%) + Foyda solig'i (15%, chakana savdo uchun ba'zan 20%).")
bullet("Agar yillik aylanma 1 mlrd so'mdan kam bo'lsa va QQS to'lovchisi sifatida ro'yxatdan o'tmagan bo'lsa — Aylanma solig'ini to'laydi (savdo faoliyati uchun standart stavka 4%, mahalliy kengash tomonidan tuzatilishi mumkin).")
bullet("Ijtimoiy soliq, JSHDS, Mol-mulk solig'i va Yer solig'i — soliq rejimidan qat'i nazar, barcha yuridik shaxslar uchun umumiy asosda amal qiladi (agar tegishli obyekt — xodim, mulk, yer mavjud bo'lsa).")
para("Amaliy tavsiya: Agar BEM BARAKA aniq qaysi rejimda ekanligini (QQS yoki aylanma) aniqlab bersangiz, keyingi hisob-kitoblar faqat o'sha rejim bo'yicha to'g'ri chiqadi. Quyida ikkala variant ham ko'rsatilgan.")

doc.add_paragraph("")

# 1. Tovar sotib olindi
h1("1. Operatsiya: Tovar sotib olindi (yetkazib beruvchidan)")
h2("1.1 Huquqiy-buxgalteriya bahosi")
para("Tovar BHMS 4-son (Moddiy-ishlab chiqarish zaxiralari) asosida sotib olish tannarxida hisobga olinadi. QQS to'lovchi bo'lsa, yetkazib beruvchi taqdim etgan QQS summasi hisob-kitob (offset) qilinadi — ya'ni tovar tannarxiga kiritilmaydi, alohida hisobga olinadi (Soliq kodeksi 266-modda, QQSni hisobga olish huquqi).")

h2("1.2 1C Provodkalar")
add_table(
    ["Dt", "Kt", "Mazmuni"],
    [
        ["2910", "6010", "Tovar sotib olindi (QQS'siz tannarx)"],
        ["4410", "6010", "Yetkazib beruvchidan olingan QQS summasi (hisobga olinadigan)"],
        ["6010", "5110", "Yetkazib beruvchiga to'lov o'tkazildi"],
    ]
)
para("Eslatma: Agar aylanma soliq to'lovchi bo'lsa, QQS hisobga olinmaydi — 4410-schyot ishlatilmaydi, QQS summasi ham tovar tannarxiga qo'shiladi (Dt 2910 to'liq summaga).")

h2("1.3 Hujjatlashtirish (Didox / Soliq.uz)")
bullet("Yetkazib beruvchidan Elektron schyot-faktura (ЭСФ/EAVF) Didox tizimida qabul qilinadi va tasdiqlanadi.")
bullet("Tovar-transport xatnomasi (agar yetkazib berish bo'lsa) elektron shaklda rasmiylashtiriladi.")
bullet("Shartnoma asosida — ombor kirim order (M-4 shakli yoki ichki forma) tuziladi.")

h2("1.4 Soliq oqibatlari")
para("QQS to'lovchi uchun: kiruvchi QQS keyingi davrda chiquvchi QQS'dan chegirib tashlanadi (offset), soliq yukini kamaytiradi. Aylanma soliq to'lovchi uchun: qo'shimcha soliq yuki yo'q, lekin QQS ham qaytarilmaydi.")

doc.add_paragraph("")

# 2. Tovar sotildi
h1("2. Operatsiya: Tovar (mol) sotildi (chakana/ulgurji)")
h2("2.1 Baho")
para("Sotishdan tushum BHMS 4-son bo'yicha tan olinadi. QQS to'lovchi bo'lsa sotish narxiga 12% QQS qo'shib hisoblanadi. Aylanma soliq to'lovchi bo'lsa, umumiy tushumdan 4% aylanma solig'i hisoblanadi (QQS ajratilmaydi).")

h2("2.2 1C Provodkalar (QQS rejimi)")
add_table(
    ["Dt", "Kt", "Mazmuni"],
    [
        ["4010", "9010", "Tovar sotishdan tushum (QQS bilan)"],
        ["9010", "6410", "Sotishdan QQS hisoblandi (12%)"],
        ["9110", "2910", "Sotilgan tovar tannarxi hisobdan chiqarildi"],
        ["5110", "4010", "Xaridordan pul tushdi"],
    ]
)

h2("2.3 1C Provodkalar (Aylanma soliq rejimi)")
add_table(
    ["Dt", "Kt", "Mazmuni"],
    [
        ["4010", "9010", "Tovar sotishdan tushum"],
        ["9110", "2910", "Sotilgan tovar tannarxi hisobdan chiqarildi"],
        ["5110", "4010", "Xaridordan pul tushdi"],
        ["9410", "6410", "Aylanma solig'i hisoblandi (davr yakunida, 4%)"],
    ]
)

h2("2.4 Hujjatlashtirish")
bullet("Xaridorga (yuridik shaxs bo'lsa) Didox orqali ЭСФ chiqariladi.")
bullet("Chakana savdo uchun onlayn-nazorat kassa mashinasi (ONKM) orqali fiskal chek beriladi, ma'lumot Soliq.uz ga avtomatik uzatiladi.")

h2("2.5 Soliq oqibati")
para("QQS deklaratsiyasi va/yoki Aylanma soliq hisob-kitobi har oy Soliq.uz shaxsiy kabineti orqali elektron taqdim etiladi (keyingi oyning 15-kunigacha).")

doc.add_paragraph("")

# 3. Xarajat
h1("3. Operatsiya: Xarajat qilindi (masalan: ijara, kommunal, xizmat)")
h2("3.1 Baho")
para("Xarajatlar BHMS 4-son (harajatlar) asosida davr xarajati sifatida tan olinadi. QQS to'lovchi bo'lsa, xizmat ko'rsatuvchi QQS to'lovchisi bo'lgan taqdirda kiruvchi QQS hisobga olinadi.")

h2("3.2 1C Provodkalar")
add_table(
    ["Dt", "Kt", "Mazmuni"],
    [
        ["9420", "6010", "Xarajat qabul qilindi (ijara/xizmat, QQS'siz)"],
        ["4410", "6010", "Xizmatga to'g'ri keluvchi QQS (agar QQS to'lovchi bo'lsa)"],
        ["6010", "5110", "Xizmat ko'rsatuvchiga to'lov o'tkazildi"],
    ]
)

h2("3.3 Hujjatlashtirish")
bullet("Ijara/xizmat shartnomasi, bajarilgan ishlar dalolatnomasi (Akt).")
bullet("Didox orqali ЭСФ (agar QQS to'lovchi kontragent bo'lsa) yoki elektron akt-dalolatnoma.")

h2("3.4 Soliq oqibati")
para("Xarajat foyda solig'i bazasini kamaytiradi (agar hujjatlashtirilgan va ishlab chiqarish faoliyati bilan bog'liq bo'lsa — Soliq kodeksi 305-modda, chegirib tashlanadigan xarajatlar).")

doc.add_paragraph("")

# 4. Ish haqi
h1("4. Operatsiya: Ish haqi hisoblandi va to'landi")
h2("4.1 Baho")
para("Ish haqi fondidan ikki turdagi soliq/to'lov yuzaga keladi: JSHDS (jismoniy shaxslardan daromad solig'i, 12% flat stavka, xodim daromadidan ushlab qolinadi) va Ijtimoiy soliq (ish beruvchi hisobidan, standart stavka 12%, ish haqi fondiga qo'shimcha sifatida to'lanadi).")

h2("4.2 1C Provodkalar")
add_table(
    ["Dt", "Kt", "Mazmuni"],
    [
        ["9420/2010", "6710", "Ish haqi hisoblandi (to'liq summa)"],
        ["6710", "6410", "JSHDS ushlab qolindi (12%)"],
        ["9420", "6520", "Ijtimoiy soliq hisoblandi (ish beruvchi hisobidan, 12%)"],
        ["6710", "5110", "Ish haqi xodimga to'landi (JSHDS chegirilgandan keyin)"],
        ["6410", "5110", "JSHDS byudjetga o'tkazildi"],
        ["6520", "5110", "Ijtimoiy soliq byudjetga o'tkazildi"],
    ]
)

h2("4.3 Hujjatlashtirish")
bullet("Ish haqi tarqatma vedomosti (1C ichida shakllanadi).")
bullet("Har oy JSHDS va Ijtimoiy soliq bo'yicha hisob-kitob Soliq.uz shaxsiy kabineti orqali elektron taqdim etiladi (keyingi oyning 15-kunigacha).")
bullet("Xodimlar bo'yicha shaxsiy hisobga olish (individual ma'lumotlar) IIV/DIM ma'lumotlar bazasiga muvofiqlashtiriladi.")

h2("4.4 Soliq oqibati")
para("JSHDS xodim zimmasida, Ijtimoiy soliq esa korxona xarajati sifatida foyda solig'i bazasini kamaytiradi.")

doc.add_paragraph("")

# 5. Asosiy vosita
h1("5. Operatsiya: Asosiy vosita sotib olindi (masalan: muzlatgich, savdo jihozi)")
h2("5.1 Baho")
para("BHMS 5-son (Asosiy vositalar) asosida boshlang'ich qiymatda hisobga olinadi (sotib olish narxi + yetkazish/o'rnatish xarajatlari, QQS'siz agar hisobga olinsa).")

h2("5.2 1C Provodkalar")
add_table(
    ["Dt", "Kt", "Mazmuni"],
    [
        ["0820", "6010", "Asosiy vosita sotib olindi (QQS'siz qiymat)"],
        ["4410", "6010", "QQS summasi (hisobga olinadigan, agar QQS to'lovchi bo'lsa)"],
        ["0120", "0820", "Foydalanishga topshirildi"],
        ["6010", "5110", "Yetkazib beruvchiga to'lov o'tkazildi"],
        ["9420", "0220", "Har oy amortizatsiya hisoblanadi (foydalanish muddati bo'yicha)"],
    ]
)

h2("5.3 Hujjatlashtirish")
bullet("Yetkazib beruvchidan ЭСФ (Didox).")
bullet("Asosiy vositani qabul qilish-topshirish dalolatnomasi (OS-1 shakli).")
bullet("Inventar kartochka ochiladi (1C avtomatik).")

h2("5.4 Soliq oqibati")
para("Asosiy vosita mol-mulk solig'i bazasiga qo'shiladi (agar ko'chmas mulk yoki soliq kodeksida belgilangan boshqa toifadagi vosita bo'lsa) — quyidagi 6-bo'limga qarang.")

doc.add_paragraph("")

# 6. Mol-mulk solig'i
h1("6. Mol-mulk solig'i")
para("Yuridik shaxslar uchun mol-mulk solig'i asosiy vositalar (bino, inshoot va boshqa ko'chmas mulk) o'rtacha yillik qoldiq qiymatidan hisoblanadi.")
bullet("Standart stavka: 1,5% (mahalliy kengash qarori bilan 3%gacha oshirilishi mumkin).")
bullet("Soliq davri — kalendar yil, har chorakda avans to'lovlari amalga oshiriladi.")
bullet("Hisob-kitob Soliq.uz orqali yillik deklaratsiya va choraklik avans hisob-kitoblari shaklida taqdim etiladi.")
para("1C provodka: Dt 9430 — Kt 6410 (mol-mulk solig'i hisoblandi, chorak yakunida).")

doc.add_paragraph("")

# 7. Yer solig'i
h1("7. Yer solig'i")
para("Agar BEM BARAKA do'kon binosi ostidagi yoki qo'shimcha foydalanishdagi yer uchastkasiga egalik huquqi yoki foydalanish huquqiga ega bo'lsa, yer solig'i to'lanadi.")
bullet("Stavka hududiy joylashuv va yer toifasiga qarab mahalliy hokimiyat tomonidan belgilanadi (1 kv.m uchun belgilangan summa asosida).")
bullet("Soliq davri — kalendar yil, choraklik avans to'lovlari bilan.")
para("1C provodka: Dt 9430 — Kt 6410 (yer solig'i hisoblandi, chorak yakunida).")

doc.add_paragraph("")

# Yakuniy xulosa
h1("Yakuniy tavsiyalar")
bullet("BEM BARAKA aniq qaysi soliq rejimida (QQS yoki aylanma) ishlashini rasman aniqlang — bu barcha keyingi hisob-kitoblarga ta'sir qiladi.")
bullet("Har bir operatsiya bo'yicha elektron hujjat (ЭСФ, akt) Didox orqali o'z vaqtida rasmiylashtirilishi shart — aks holda xarajat/QQS chegirmasi rad etilishi mumkin.")
bullet("Barcha soliq hisobotlari muddatida (odatda keyingi oy/chorakning 15-20 kunigacha) Soliq.uz shaxsiy kabineti orqali topshirilsin.")
bullet("Joriy yil uchun aniq stavkalarni (QQS, aylanma, ijtimoiy soliq, mol-mulk, yer) soliq.uz saytida yoki Soliq kodeksining amaldagi tahririda tasdiqlab oling — stavkalar yillik davlat byudjeti to'g'risidagi qonun bilan yangilanishi mumkin.")

doc.save(r"C:\Users\Dell\jarvis\BEM_BARAKA_soliq_qollanma.docx")
print("OK")

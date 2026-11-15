# -*- coding: utf-8 -*-
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from datetime import date

wb = openpyxl.Workbook()

thin = Side(style="thin", color="999999")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
header_fill = PatternFill("solid", fgColor="1F4E78")
header_font = Font(bold=True, color="FFFFFF")
title_font = Font(bold=True, size=14)
sub_font = Font(bold=True, size=11)
money_fmt = '#,##0 "so\'m"'

def set_col_widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

# ============================================================
# SHEET 1: HISOB-FAKTURA NAMUNASI (bitta hujjat shakli)
# ============================================================
ws1 = wb.active
ws1.title = "Hisob-faktura namuna"
set_col_widths(ws1, [4, 28, 14, 12, 14, 14, 16])

ws1.merge_cells("A1:G1")
ws1["A1"] = "HISOB-FAKTURA № 000045"
ws1["A1"].font = title_font
ws1["A1"].alignment = Alignment(horizontal="center")

ws1.merge_cells("A2:G2")
ws1["A2"] = "Sana: 2026-yil 12-avgust"
ws1["A2"].alignment = Alignment(horizontal="center")

ws1["A4"] = "Sotuvchi:"
ws1["A4"].font = sub_font
ws1["B4"] = "\"BEM BARAKA\" MChJ"
ws1["A5"] = "STIR:"
ws1["B5"] = "301234567"
ws1["A6"] = "Manzil:"
ws1["B6"] = "Toshkent sh., Chilonzor tumani"
ws1["A7"] = "H/r:"
ws1["B7"] = "20208000123456789001"
ws1["A8"] = "Bank:"
ws1["B8"] = "\"Ipoteka bank\" ATB Chilonzor filiali, MFO 00445"

ws1["D4"] = "Xaridor:"
ws1["D4"].font = sub_font
ws1["E4"] = "\"Sifat Savdo\" XK"
ws1["D5"] = "STIR:"
ws1["E5"] = "305678912"
ws1["D6"] = "Manzil:"
ws1["E6"] = "Toshkent sh., Yunusobod tumani"

headers = ["№", "Mahsulot / xizmat nomi", "O'lchov birligi", "Miqdori", "Narxi (so'm)", "Summa (QQS'siz)", "QQS (12%)"]
row0 = 10
for i, h in enumerate(headers, start=1):
    c = ws1.cell(row=row0, column=i, value=h)
    c.font = header_font
    c.fill = header_fill
    c.alignment = Alignment(horizontal="center", wrap_text=True)
    c.border = border

items = [
    ("Kir yuvish kukuni \"Ariel\" 3kg", "dona", 40, 85000),
    ("O'simlik yog'i \"Oltin dala\" 5L", "dona", 25, 95000),
    ("Guruch \"Lazer\" 1-nav", "kg", 300, 12000),
]

r = row0 + 1
total_wo_vat = 0
total_vat = 0
for idx, (name, unit, qty, price) in enumerate(items, start=1):
    summa = qty * price
    vat = round(summa * 0.12)
    total_wo_vat += summa
    total_vat += vat
    vals = [idx, name, unit, qty, price, summa, vat]
    for ci, v in enumerate(vals, start=1):
        c = ws1.cell(row=r, column=ci, value=v)
        c.border = border
        if ci in (5, 6, 7):
            c.number_format = money_fmt
    r += 1

ws1.merge_cells(f"A{r}:E{r}")
ws1.cell(row=r, column=1, value="JAMI:").font = sub_font
ws1.cell(row=r, column=1).alignment = Alignment(horizontal="right")
ws1.cell(row=r, column=6, value=total_wo_vat).number_format = money_fmt
ws1.cell(row=r, column=7, value=total_vat).number_format = money_fmt
for ci in (1, 6, 7):
    ws1.cell(row=r, column=ci).border = border
r += 1
ws1.merge_cells(f"A{r}:F{r}")
ws1.cell(row=r, column=1, value="JAMI TO'LASH SUMMASI (QQS bilan):").font = sub_font
ws1.cell(row=r, column=1).alignment = Alignment(horizontal="right")
ws1.cell(row=r, column=7, value=total_wo_vat + total_vat).number_format = money_fmt
ws1.cell(row=r, column=7).font = sub_font

r += 3
ws1.cell(row=r, column=1, value="Sotuvchi (imzo): _______________")
ws1.cell(row=r+1, column=1, value="Xaridor (imzo): _______________")
r += 3
ws1.cell(row=r, column=1, value="Eslatma: bu — namuna hujjat. Haqiqiy hisob-faktura Didox tizimida elektron shaklda (ЭСФ) rasmiylashtiriladi.").font = Font(italic=True, size=9, color="777777")

# ============================================================
# SHEET 2: HISOB-FAKTURALAR REESTRI (1 oylik ro'yxat)
# ============================================================
ws2 = wb.create_sheet("Hisob-fakturalar reestri")
set_col_widths(ws2, [5, 12, 14, 26, 14, 16, 14, 16, 14])

ws2.merge_cells("A1:I1")
ws2["A1"] = "\"BEM BARAKA\" MChJ — 2026-yil avgust oyi uchun chiqarilgan hisob-fakturalar reestri"
ws2["A1"].font = title_font

headers2 = ["№", "Sana", "Hisob-faktura №", "Xaridor nomi", "STIR", "Summa (QQS'siz)", "QQS (12%)", "Jami (QQS bilan)", "To'lov holati"]
row0 = 3
for i, h in enumerate(headers2, start=1):
    c = ws2.cell(row=row0, column=i, value=h)
    c.font = header_font
    c.fill = header_fill
    c.alignment = Alignment(horizontal="center", wrap_text=True)
    c.border = border

reestr_data = [
    ("2026-08-03", "000041", "\"Aziz Trade\" XK", "304551122", 12500000, "To'langan"),
    ("2026-08-05", "000042", "\"Yunusobod Savdo\" MChJ", "302334455", 8300000, "To'langan"),
    ("2026-08-08", "000043", "Jismoniy shaxs (chek)", "-", 1450000, "To'langan"),
    ("2026-08-12", "000044", "\"Sifat Savdo\" XK", "305678912", 9700000, "To'langan"),
    ("2026-08-12", "000045", "\"Sifat Savdo\" XK", "305678912", 6950000, "Kutilmoqda"),
    ("2026-08-16", "000046", "\"Chilonzor Market\" MChJ", "301122334", 15200000, "To'langan"),
    ("2026-08-20", "000047", "Jismoniy shaxs (chek)", "-", 980000, "To'langan"),
    ("2026-08-23", "000048", "\"Baraka Optom\" XK", "306789123", 22300000, "Qisman to'langan"),
    ("2026-08-27", "000049", "\"Yunusobod Savdo\" MChJ", "302334455", 5100000, "To'langan"),
    ("2026-08-30", "000050", "\"Aziz Trade\" XK", "304551122", 11800000, "Kutilmoqda"),
]

r = row0 + 1
sum_wo, sum_vat = 0, 0
for idx, (sana, num, nomi, stir, summa_total_with_vat, holat) in enumerate(reestr_data, start=1):
    summa_wo_vat = round(summa_total_with_vat / 1.12)
    vat = summa_total_with_vat - summa_wo_vat
    sum_wo += summa_wo_vat
    sum_vat += vat
    vals = [idx, sana, num, nomi, stir, summa_wo_vat, vat, summa_total_with_vat, holat]
    for ci, v in enumerate(vals, start=1):
        c = ws2.cell(row=r, column=ci, value=v)
        c.border = border
        if ci in (6, 7, 8):
            c.number_format = money_fmt
        if ci == 2:
            c.alignment = Alignment(horizontal="center")
    r += 1

ws2.merge_cells(f"A{r}:E{r}")
ws2.cell(row=r, column=1, value="JAMI (oy uchun):").font = sub_font
ws2.cell(row=r, column=1).alignment = Alignment(horizontal="right")
ws2.cell(row=r, column=6, value=sum_wo).number_format = money_fmt
ws2.cell(row=r, column=7, value=sum_vat).number_format = money_fmt
ws2.cell(row=r, column=8, value=sum_wo + sum_vat).number_format = money_fmt
for ci in range(1, 9):
    ws2.cell(row=r, column=ci).font = sub_font
    ws2.cell(row=r, column=ci).border = border

# ============================================================
# SHEET 3: BANK KO'CHIRMASI (1 oylik)
# ============================================================
ws3 = wb.create_sheet("Bank ko'chirmasi")
set_col_widths(ws3, [5, 12, 16, 28, 30, 16, 16, 18])

ws3.merge_cells("A1:H1")
ws3["A1"] = "\"BEM BARAKA\" MChJ — H/r 20208000123456789001 bo'yicha 2026-yil avgust oyi bank ko'chirmasi"
ws3["A1"].font = title_font

headers3 = ["№", "Sana", "Hujjat №", "Kontragent", "Operatsiya tavsifi", "Kirim (kredit)", "Chiqim (debet)", "Qoldiq"]
row0 = 3
for i, h in enumerate(headers3, start=1):
    c = ws3.cell(row=row0, column=i, value=h)
    c.font = header_font
    c.fill = header_fill
    c.alignment = Alignment(horizontal="center", wrap_text=True)
    c.border = border

balance = 18500000
ops = [
    ("2026-08-01", "-", "-", "Oy boshiga qoldiq", 0, 0),
    ("2026-08-03", "П-118", "\"Aziz Trade\" XK", "Hisob-faktura №000041 uchun tushum", 12500000, 0),
    ("2026-08-04", "П-119", "\"Elektr tarmoqlari\" AJ", "Elektr energiyasi uchun to'lov", 0, 1850000),
    ("2026-08-05", "П-120", "\"Yunusobod Savdo\" MChJ", "Hisob-faktura №000042 uchun tushum", 8300000, 0),
    ("2026-08-06", "П-121", "\"Aloqa Ijara\" MChJ", "Do'kon ijarasi uchun to'lov (avgust)", 0, 6000000),
    ("2026-08-10", "П-122", "\"MegaFood Distribution\" XK", "Tovar sotib olish uchun to'lov", 0, 15400000),
    ("2026-08-12", "П-123", "\"Sifat Savdo\" XK", "Hisob-faktura №000044 uchun tushum", 9700000, 0),
    ("2026-08-15", "П-124", "Xodimlar (ish haqi ro'yxati)", "Iyul oyi uchun ish haqi to'lovi", 0, 24000000),
    ("2026-08-15", "П-125", "Davlat soliq xizmati", "JSHDS va Ijtimoiy soliq o'tkazmasi", 0, 4680000),
    ("2026-08-16", "П-126", "\"Chilonzor Market\" MChJ", "Hisob-faktura №000046 uchun tushum", 15200000, 0),
    ("2026-08-18", "П-127", "Davlat soliq xizmati", "QQS bo'yicha oylik to'lov", 0, 3200000),
    ("2026-08-23", "П-128", "\"Baraka Optom\" XK", "Hisob-faktura №000048 (qisman to'lov)", 10000000, 0),
    ("2026-08-27", "П-129", "\"Yunusobod Savdo\" MChJ", "Hisob-faktura №000049 uchun tushum", 5100000, 0),
    ("2026-08-28", "П-130", "Kommunal xizmatlar", "Suv va gaz uchun to'lov", 0, 620000),
]

r = row0 + 1
for idx, (sana, hujjat, kontragent, tavsif, kirim, chiqim) in enumerate(ops, start=1):
    if idx == 1:
        balance = balance  # oy boshi
    else:
        balance = balance + kirim - chiqim
    vals = [idx, sana, hujjat, kontragent, tavsif, kirim if kirim else None, chiqim if chiqim else None, balance]
    for ci, v in enumerate(vals, start=1):
        c = ws3.cell(row=r, column=ci, value=v)
        c.border = border
        if ci in (6, 7, 8):
            c.number_format = money_fmt
        if ci == 2:
            c.alignment = Alignment(horizontal="center")
    r += 1

ws3.merge_cells(f"A{r}:E{r}")
ws3.cell(row=r, column=1, value="JAMI (oy uchun) / Oy oxiriga qoldiq:").font = sub_font
ws3.cell(row=r, column=1).alignment = Alignment(horizontal="right")
total_kirim = sum(o[4] for o in ops)
total_chiqim = sum(o[5] for o in ops)
ws3.cell(row=r, column=6, value=total_kirim).number_format = money_fmt
ws3.cell(row=r, column=7, value=total_chiqim).number_format = money_fmt
ws3.cell(row=r, column=8, value=balance).number_format = money_fmt
for ci in range(1, 9):
    ws3.cell(row=r, column=ci).font = sub_font
    ws3.cell(row=r, column=ci).border = border

wb.save(r"C:\Users\Dell\jarvis\BEM_BARAKA_hisobfaktura_bank_namuna.xlsx")
print("OK")

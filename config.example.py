# Jarvis sozlamalari
#
# DIQQAT: bu faylga PAROL yozmang. Faqat token va kalitlar.

# Telegram вЂ” @BotFather -> /revoke bilan almashtiriladi
TELEGRAM_TOKEN = "BU_YERGA_QIYMAT_YOZING"
OWNER_ID = 7999087214

# Azizbekning shaxsiy/biznes telefon raqami (2026-09-27) вЂ” Lead-bot
# (ai_javob_bridge.py + userbot/faq.json, Instagram va Telegram) shu YAGONA
# o'zgaruvchidan foydalanadi, faqat narx/taklif/bog'lanish/"qanday
# boshlaymiz" savollarida ko'rsatadi (har xabarda emas).
EGASI_TELEFON = "BU_YERGA_QIYMAT_YOZING"

# Buffer API kaliti вЂ” publish.buffer.com/settings/api
# Amal qilish muddati: 2027-yil 2-sentabr
BUFFER_TOKEN = "BU_YERGA_QIYMAT_YOZING"

# Instagram Graph API access token вЂ” akkaunt: azizbekhazratov.ai
# Meta app: "Azizbek AI Mutaxassis-IG" (developers.facebook.com/apps/1096152019653495)
# Olingan sana: 2026-09-06. Bu qisqa muddatli (short-lived, ~1 soat) token вЂ”
# doimiy ishlatish uchun long-lived token'ga almashtirish kerak bo'ladi.
INSTAGRAM_ACCESS_TOKEN = "BU_YERGA_QIYMAT_YOZING"
INSTAGRAM_ACCOUNT_ID = "BU_YERGA_QIYMAT_YOZING"
INSTAGRAM_APP_ID = "BU_YERGA_QIYMAT_YOZING"
INSTAGRAM_APP_SECRET = "BU_YERGA_QIYMAT_YOZING"

# Cloudflare API token вЂ” FAQAT nishonsport.uz zonasi, FAQAT DNS-edit huquqi (2026-09-16, Azizbekdan)
# Zone ID (nishonsport.uz): be63655c835eea3100ecdf42521413cd
CLOUDFLARE_API_TOKEN = "BU_YERGA_QIYMAT_YOZING"
CLOUDFLARE_ZONE_ID_NISHONSPORT = "BU_YERGA_QIYMAT_YOZING"

# Hetzner "nishon-server" (49.12.111.53) вЂ” nishon-platform + oquv-markaz ikkalasi ham shu yerda.
# SSH orqali kirish uchun (deploy/kuzatuv skriptlari uchun umumiy).
HETZNER_NISHON_SERVER_IP = "BU_YERGA_QIYMAT_YOZING"
HETZNER_NISHON_SERVER_SSH_KEY = r"C:\Users\Dell\.ssh\nishon_hetzner_ed25519"

# Jarvis Biznes Kuzatuv (2026-09-21) вЂ” proaktiv kunlik hisobot/anomaliya kuzatuvi uchun
# FAQAT O'QISH huquqli Postgres rol (INSERT/UPDATE/DELETE fizik jihatdan mumkin emas вЂ”
# default_transaction_read_only=on VA yozish uchun GRANT yo'q, ikkalasi ham sinovda tasdiqlangan).
AZIZEDU_DB_HOST = "BU_YERGA_QIYMAT_YOZING"  # server ICHIDA (SSH orqali kirilgach) вЂ” Postgres tashqariga ochiq emas
AZIZEDU_DB_NAME = "BU_YERGA_QIYMAT_YOZING"
AZIZEDU_DB_USER = "BU_YERGA_QIYMAT_YOZING"
AZIZEDU_DB_PASSWORD = "BU_YERGA_QIYMAT_YOZING"
AZIZEDU_ORG_ID = "BU_YERGA_QIYMAT_YOZING"  # "Orzu Akademy" вЂ” yagona REAL tashkilot (134 o'quvchi)

# Grampus Junior FC (Nishon platform) вЂ” xuddi shu server, xuddi shu jarvis_readonly
# rol (Postgres rollari klaster darajasida umumiy), lekin BOSHQA baza (`nishon`).
GRAMPUS_DB_HOST = "BU_YERGA_QIYMAT_YOZING"
GRAMPUS_DB_NAME = "BU_YERGA_QIYMAT_YOZING"
GRAMPUS_DB_USER = "BU_YERGA_QIYMAT_YOZING"
GRAMPUS_DB_PASSWORD = "BU_YERGA_QIYMAT_YOZING"  # xuddi shu rol/parol, ikkala bazaga GRANT qilingan
GRAMPUS_ORG_ID = "BU_YERGA_QIYMAT_YOZING"  # Grampus Junior FC вЂ” yagona REAL tashkilot

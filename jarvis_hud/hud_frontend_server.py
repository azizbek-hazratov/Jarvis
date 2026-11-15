"""
Jarvis HUD static frontend server (index.html, port 8080).
pythonw.exe orqali (konsolsiz) ishga tushirilganda sys.stdout/sys.stderr
None bo'lib qoladi -- stdlib http.server har bir so'rovda
sys.stderr.write(...) chaqirgani uchun (log_message -> send_response
ICHIDA, javob yuborilishidan OLDIN chaqiriladi) bu har bir so'rovni
xatoga uchratib, mijozga BO'SH javob (connection reset) qaytarardi.
Yechim: ishga tushishdan OLDIN stdout/stderr'ni log faylga yo'naltiramiz.

2026-09-29 XAVFSIZLIK TUZATISHI (Azizbek): avval bu server ("", PORT) --
butun tarmoqqa ochiq edi VA jarvis_hud papkasidagi HAR QANDAY faylni
(shu jumladan .py, .session, hud_token.py, log/jsonl fayllarni) berardi.
Endi: (1) FAQAT 127.0.0.1 ga bog'lanadi (mahalliy kompyuterdan tashqari
hech kim ulana olmaydi), (2) faqat frontend uchun zarur kengaytmalar
(.html/.css/.js/.png/.jpg/.jpeg/.webp/.svg/.mp4/.mp3/.woff2/.woff/.ico)
va "vendor/", "portretlar/" papkalaridagi fayllar beriladi -- qolgan
hammasi (.py, .session, .json, .jsonl, .log, .xml, .bat, .txt va h.k.)
404 qaytaradi.
"""
import os
import sys

PAPKA = os.path.dirname(os.path.abspath(__file__))
os.chdir(PAPKA)

log_fayl = open(os.path.join(PAPKA, "hud_frontend_task.log"), "a", buffering=1, encoding="utf-8")
sys.stdout = log_fayl
sys.stderr = log_fayl

import http.server
import socketserver

PORT = 8080
BIND_HOST = "127.0.0.1"

RUXSAT_ETILGAN_KENGAYTMALAR = {
    ".html", ".css", ".js", ".mjs",
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico",
    ".mp4", ".mp3", ".ogg", ".wav",
    ".woff", ".woff2", ".ttf",
}
RUXSAT_ETILGAN_PAPKALAR = ("vendor/", "portretlar/")


def _yol_ruxsat_etilganmi(path: str) -> bool:
    # path -- URL-dekodlanmagan, lekin kengaytma/papka tekshiruvi uchun yetarli.
    toza = path.split("?", 1)[0].split("#", 1)[0].lstrip("/")
    if toza == "" or toza.endswith("/"):
        return True  # katalog so'rovi -- SimpleHTTPRequestHandler index.html'ni o'zi hal qiladi
    for papka in RUXSAT_ETILGAN_PAPKALAR:
        if toza.startswith(papka):
            return True
    _, ext = os.path.splitext(toza)
    return ext.lower() in RUXSAT_ETILGAN_KENGAYTMALAR


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))

    def do_GET(self):
        if not _yol_ruxsat_etilganmi(self.path):
            self.send_error(404, "Not Found")
            return
        super().do_GET()

    def do_HEAD(self):
        if not _yol_ruxsat_etilganmi(self.path):
            self.send_error(404, "Not Found")
            return
        super().do_HEAD()


if __name__ == "__main__":
    with socketserver.ThreadingTCPServer((BIND_HOST, PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        print(f"Jarvis HUD frontend http://{BIND_HOST}:{PORT} da ishga tushdi (pythonw, log fayl orqali, faqat mahalliy)")
        httpd.serve_forever()

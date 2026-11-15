"""
JARVIS — Buffer (ijtimoiy tarmoqlarga post qo'yish)

Parol kerak emas — faqat API kaliti.
Kalitni olish: https://publish.buffer.com/settings/api
Keyin config.py ga BUFFER_TOKEN = "..." deb yozing.

Ishlatish (Jarvis buni Bash orqali chaqiradi):
    python jarvis_buffer.py kanallar
    python jarvis_buffer.py post "Salom dunyo" --kanal <ID>
    python jarvis_buffer.py post "Matn" --kanal <ID> --rejim shareNow
    python jarvis_buffer.py gql "query { account { id } }"

--rejim variantlari:
    addToQueue  (standart) — navbatga qo'shadi, Buffer o'zi vaqtini tanlaydi
    shareNext              — navbatning boshiga qo'yadi
    shareNow               — hoziroq e'lon qiladi
"""

import argparse
import json
import sys

import httpx

try:
    from config import BUFFER_TOKEN
except ImportError:
    BUFFER_TOKEN = ""

ENDPOINT = "https://api.buffer.com"


def gql(query: str, variables: dict | None = None) -> dict:
    if not BUFFER_TOKEN:
        raise SystemExit(
            "BUFFER_TOKEN yo'q. config.py ga qo'shing.\n"
            "Kalitni olish: https://publish.buffer.com/settings/api"
        )
    r = httpx.post(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {BUFFER_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": variables or {}},
        timeout=60,
    )
    try:
        data = r.json()
    except Exception:
        raise SystemExit(f"Javob JSON emas ({r.status_code}): {r.text[:500]}")
    if "errors" in data:
        raise SystemExit("Buffer xatosi:\n" + json.dumps(data["errors"], indent=2, ensure_ascii=False))
    return data.get("data", {})


TASHKILOT_QUERY = """
query {
  account {
    organizations {
      id
      name
    }
  }
}
"""

KANAL_QUERY = """
query($orgId: OrganizationId!) {
  channels(input: { organizationId: $orgId }) {
    id
    name
    service
  }
}
"""

POST_MUTATION = """
mutation($text: String!, $channelId: ChannelId!, $mode: ShareMode!) {
  createPost(input: {
    text: $text,
    channelId: $channelId,
    schedulingType: automatic,
    mode: $mode
  }) {
    ... on PostActionSuccess {
      post { id text }
    }
    ... on MutationError {
      message
    }
  }
}
"""

# Rasm(lar) bilan post (masalan Instagram — matn-only postga ruxsat bermaydi, rasm shart;
# bir nechta rasm bo'lsa — karusel/albom sifatida qo'yiladi).
# Buffer'ning GraphQL API'si faylni to'g'ridan-to'g'ri yuklashni qo'llab-quvvatlamaydi — faqat
# ochiq (public) URL qabul qiladi, shuning uchun rasm avval biror ochiq hostga yuklanadi (masalan
# catbox.moe), keyin o'sha URL shu yerga beriladi.
POST_MUTATION_RASM = """
mutation($text: String!, $channelId: ChannelId!, $mode: ShareMode!, $assets: [AssetInput!]!, $metadata: PostInputMetaData) {
  createPost(input: {
    text: $text,
    channelId: $channelId,
    schedulingType: automatic,
    mode: $mode,
    assets: $assets,
    metadata: $metadata
  }) {
    ... on PostActionSuccess {
      post { id text }
    }
    ... on MutationError {
      message
    }
  }
}
"""


def kanallar():
    data = gql(TASHKILOT_QUERY)
    orgs = data.get("account", {}).get("organizations", [])
    if not orgs:
        print("Tashkilot topilmadi. Buffer'da kanal ulaganmisiz?")
        return
    for org in orgs:
        print(f"\nTashkilot: {org.get('name')}  ({org.get('id')})")
        kdata = gql(KANAL_QUERY, {"orgId": org.get("id")})
        kans = kdata.get("channels") or []
        if not kans:
            print("  (kanal ulanmagan)")
        for k in kans:
            print(f"  {k.get('service'):<12} {k.get('name'):<25} ID: {k.get('id')}")


VIDEO_KENGAYTMALAR = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}


def fayl_video_mi(fayl_yoli: str) -> bool:
    return ("." + fayl_yoli.rsplit(".", 1)[-1].lower()) in VIDEO_KENGAYTMALAR if "." in fayl_yoli else False


def post(
    matn: str,
    kanal: str,
    rejim: str,
    rasm_urllar: list[str] | None = None,
    ig_turi: str | None = None,
    fb_turi: str | None = None,
):
    if rasm_urllar:
        assets = [
            {"video": {"url": u}} if fayl_video_mi(u) else {"image": {"url": u}}
            for u in rasm_urllar
        ]
        variables = {"text": matn, "channelId": kanal, "mode": rejim, "assets": assets}
        metadata = {}
        if ig_turi:
            metadata["instagram"] = {"type": ig_turi, "shouldShareToFeed": True}
        if fb_turi:
            metadata["facebook"] = {"type": fb_turi}
        if metadata:
            variables["metadata"] = metadata
        data = gql(POST_MUTATION_RASM, variables)
    else:
        data = gql(POST_MUTATION, {"text": matn, "channelId": kanal, "mode": rejim})
    natija = data.get("createPost", {})
    if "message" in natija:
        raise SystemExit(f"Post qo'yilmadi: {natija['message']}")
    p = natija.get("post", {})
    print(f"Post qo'yildi. ID: {p.get('id')}")
    print(f"Matn: {p.get('text')}")


def rasm_yukla(fayl_yoli: str) -> str:
    """Lokal rasm/videoni ochiq (public) hostga (catbox.moe) yuklab, URL qaytaradi — Buffer shu URL
    orqali oladi. Fayl nomi (kengaytmasi bilan) saqlanib yuboriladi, shuning uchun qaytgan URL ham
    o'sha kengaytmani saqlaydi (video/rasm turini keyin aniqlash uchun shu muhim)."""
    import mimetypes
    import httpx as _httpx

    nomi = fayl_yoli.split("/")[-1].split("\\")[-1]
    turi = mimetypes.guess_type(nomi)[0] or "application/octet-stream"
    with open(fayl_yoli, "rb") as f:
        r = _httpx.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (nomi, f, turi)},
            timeout=180,
        )
    r.raise_for_status()
    url = r.text.strip()
    if not url.startswith("http"):
        raise SystemExit(f"Fayl yuklashda xato: {url}")
    return url


def main():
    ap = argparse.ArgumentParser(description="Buffer orqali post qo'yish")
    sub = ap.add_subparsers(dest="buyruq", required=True)

    sub.add_parser("kanallar", help="Ulangan kanallar ro'yxati")

    p = sub.add_parser("post", help="Post qo'yish")
    p.add_argument("matn")
    p.add_argument("--kanal", required=True)
    p.add_argument(
        "--rejim",
        default="addToQueue",
        choices=["addToQueue", "shareNext", "shareNow"],
    )
    p.add_argument(
        "--rasm",
        action="append",
        help="Lokal rasm YOKI video fayl yo'li (Instagram uchun majburiy) — avtomatik ochiq hostga "
        "yuklanadi (kengaytmadan avtomatik aniqlanadi: .mp4/.mov/.m4v/.avi/.mkv/.webm -> video, "
        "aks holda rasm). Video uchun --ig-turi reel bering. Bir nechta marta berilsa "
        "(--rasm a.png --rasm b.png) karusel/albom bo'lib qo'yiladi.",
    )
    p.add_argument(
        "--ig-turi",
        choices=["post", "carousel", "story", "reel"],
        help="Instagram uchun post turi (Instagram kanaliga rasm bilan post qilinganda majburiy)",
    )
    p.add_argument(
        "--fb-turi",
        choices=["post", "story", "reel"],
        help="Facebook uchun post turi (Facebook kanaliga rasm bilan post qilinganda majburiy)",
    )

    g = sub.add_parser("gql", help="Ixtiyoriy GraphQL so'rov (schema o'rganish uchun)")
    g.add_argument("query")

    a = ap.parse_args()

    if a.buyruq == "kanallar":
        kanallar()
    elif a.buyruq == "post":
        rasm_urllar = None
        if a.rasm:
            rasm_urllar = []
            for yol in a.rasm:
                u = rasm_yukla(yol)
                print(f"Rasm yuklandi: {yol} -> {u}")
                rasm_urllar.append(u)
        post(a.matn, a.kanal, a.rejim, rasm_urllar, a.ig_turi, a.fb_turi)
    elif a.buyruq == "gql":
        print(json.dumps(gql(a.query), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

#!/usr/bin/env python3
"""삿포로 플랜 장소 보강 - 구글 Places(New)로 주소·영업시간·좌표·지도링크·사진 1장.
tokyo-plan/scripts/enrich.py 와 같은 방식. 결과는 places.json, 사진은 photos/<id>.jpg
이미 받은 사진은 다시 받지 않는다. 키 파일은 tokyo-food 와 공유 (내용을 출력하지 않는다).
"""
import json, pathlib, re, sys, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "places.json"
PHOTOS = ROOT / "photos"
KEY = (pathlib.Path.home() / ".config/tokyo-food/google_places.key").read_text().strip()
FIELDS = ",".join(["places.displayName", "places.formattedAddress", "places.location",
                   "places.regularOpeningHours.weekdayDescriptions", "places.googleMapsUri", "places.photos"])
DAY_KO = {"月曜日": "월", "火曜日": "화", "水曜日": "수", "木曜日": "목", "金曜日": "금", "土曜日": "토", "日曜日": "일"}
ORDER = ["월", "화", "수", "목", "금", "토", "일"]
SAPPORO, OTARU = (43.0687, 141.3508), (43.1977, 141.0010)

# id: (검색어, 위치 기준)
Q = {
  "airport": ("新千歳空港", None),
  "hotel": ("SAPPORO HOTEL by GRANBELL 札幌市東区北6条東2丁目", SAPPORO),
  "daimaru": ("大丸札幌店", SAPPORO),
  "hands": ("ハンズ札幌店", SAPPORO),
  "akarenga": ("北海道庁旧本庁舎 赤れんが庁舎", SAPPORO),
  "tokeidai": ("札幌市時計台", SAPPORO),
  "odori": ("さっぽろテレビ塔", SAPPORO),
  "t38": ("JRタワー展望室 T38", SAPPORO),
  "patchwork": ("パッチワークの路 美瑛", None),
  "sevenstar": ("セブンスターの木 美瑛", None),
  "aoiike": ("白金青い池", None),
  "shirahige": ("白ひげの滝", None),
  "takushinkan": ("拓真館 美瑛", None),
  "shikisai": ("展望花畑 四季彩の丘", None),
  "nijo": ("二条市場", SAPPORO),
  "orgel": ("小樽オルゴール堂 本館", OTARU),
  "letao": ("ルタオ本店 小樽", OTARU),
  "kitaichi": ("北一硝子 三号館", OTARU),
  "unga": ("小樽運河", OTARU),
  "takino": ("真駒内滝野霊園 頭大仏", SAPPORO),
  "jigokudani": ("登別地獄谷", None),
  "silo": ("サイロ展望台 洞爺湖", None),
  "nakayama": ("道の駅 望羊中山", None),
  # 관광지 탭 (일정에 안 넣은 곳)
  "hokudai": ("北海道大学 クラーク像", SAPPORO),
  "icho": ("北海道大学 イチョウ並木", SAPPORO),
  "jingu": ("北海道神宮", SAPPORO),
  "moiwa": ("札幌もいわ山ロープウェイ", SAPPORO),
  "beermuseum": ("サッポロビール博物館", SAPPORO),
  "factory": ("サッポロファクトリー", SAPPORO),
  "tanuki": ("狸小路商店街", SAPPORO),
  "susukino": ("すすきの交差点 ニッカウヰスキー看板", SAPPORO),
  "hoheikan": ("豊平館 中島公園", SAPPORO),
  "shiroi": ("白い恋人パーク", SAPPORO),
  "okurayama": ("大倉山展望台", SAPPORO),
  # 먹을 곳
  "king": ("スープカレーKING セントラル 札幌", SAPPORO),
  "ichiryu": ("ラーメン札幌 一粒庵", SAPPORO),
  "haruka": ("札幌ラーメン 悠 元祖さっぽろラーメン横丁", SAPPORO),
  "yukikaze": ("麺屋 雪風 すすきの店", SAPPORO),
  "karaichi": ("札幌ラーメン 辛いち すすきの店", SAPPORO),
  "deno": ("175°DENO担担麺 札幌北口店", SAPPORO),
  "matsuo": ("松尾ジンギスカン 札幌駅前店", SAPPORO),
  "daruma": ("成吉思汗だるま 本店", SAPPORO),
  "daruma44": ("成吉思汗だるま 4・4店", SAPPORO),
  "beerkan": ("サッポロビール園 ポプラ館", SAPPORO),
  "oiso": ("二条市場 大磯", SAPPORO),
  "donburi": ("二条市場 どんぶり茶屋", SAPPORO),
  "tatsumi": ("おたる巽鮨 堺町店", OTARU),
  "kani": ("すすきの蟹一", SAPPORO),
  "sato_daimaru": ("パフェ、珈琲、酒、佐藤 大丸札幌店", SAPPORO),
  "sato": ("パフェ、珈琲、酒、佐藤 札幌", SAPPORO),
  "pal": ("夜パフェ専門店 Parfaiteria PaL", SAPPORO),
  "miru": ("夜パフェ専門店 Parfaiteria miru", SAPPORO),
}


def search(q, center):
    body = {"textQuery": q, "languageCode": "ja", "regionCode": "JP", "maxResultCount": 1}
    if center:
        body["locationBias"] = {"circle": {"center": {"latitude": center[0], "longitude": center[1]}, "radius": 5000.0}}
    req = urllib.request.Request("https://places.googleapis.com/v1/places:searchText", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY, "X-Goog-FieldMask": FIELDS})
    for a in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                p = json.load(r).get("places", [])
                return p[0] if p else None
        except urllib.error.HTTPError as e:
            if e.code == 429 and a < 2:
                time.sleep(3); continue
            print("  ! HTTP", e.code, e.read()[:150]); return None
        except Exception as e:
            print("  ! err", e); return None


def hours(descs):
    rows = {}
    for d in descs or []:
        day, _, t = d.partition(": ")
        t = t.replace("24 時間営業", "24시간").replace("～", "~").replace("–", "~").replace("時", ":").replace("分", "").replace("定休日", "휴무").replace("24 時間営業", "24시간").strip()
        rows[DAY_KO.get(day.strip(), day.strip())] = t
    return [{"day": d, "time": rows[d], **({"off": True} if "휴무" in rows[d] else {})} for d in ORDER if d in rows] or None


def photo(place, pid):
    have = list(PHOTOS.glob(pid + ".*"))
    if have:
        return "photos/" + have[0].name
    ph = place.get("photos") or []
    if not ph:
        return None
    url = f"https://places.googleapis.com/v1/{ph[0]['name']}/media?maxWidthPx=800&key={KEY}"
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            (PHOTOS / (pid + ".jpg")).write_bytes(r.read())
            return f"photos/{pid}.jpg"
    except Exception as e:
        print("  ! photo", e); return None


def main(only):
    PHOTOS.mkdir(exist_ok=True)
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    for pid, (q, c) in Q.items():
        if only and pid not in only:
            continue
        p = search(q, c)
        if not p:
            print("MISS", pid, q); continue
        loc = p.get("location") or {}
        out[pid] = {k: v for k, v in {
            "gname": (p.get("displayName") or {}).get("text"),
            "addr": re.sub(r"^〒\d{3}-\d{4}\s*", "", (p.get("formattedAddress") or "").replace("日本、", "")),
            "hours": hours((p.get("regularOpeningHours") or {}).get("weekdayDescriptions")),
            "lat": loc.get("latitude"), "lng": loc.get("longitude"),
            "map": p.get("googleMapsUri"), "photo": photo(p, pid)}.items() if v}
        print("ok ", pid, "->", out[pid].get("gname"), "|", out[pid].get("addr", "")[:40])
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (ROOT / "places.js").write_text("window.PLACES = " + json.dumps(out, ensure_ascii=False) + ";\n")   # file:// 에서도 열리게


if __name__ == "__main__":
    main(set(sys.argv[1:]))

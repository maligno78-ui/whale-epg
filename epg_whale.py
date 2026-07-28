"""
Genera EPG XMLTV para Whale TV+ desde la API oficial de rlaxx.zeasn.tv.
Ejecutar una vez al dia para mantener la guia actualizada (7 dias).
"""
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta, timezone
import concurrent.futures
import uuid
import os

API_TOKEN = "4ef13b5f3d2744e3b0a569feb8dde298"
AUTH_URL = "https://rlaxx.zeasn.tv/livetv/api/v1/auth/access"
CHANNELS_URL = "https://rlaxx.zeasn.tv/livetv/api/device/browser/v1/category/channels"
EPG_URL = "https://rlaxx.zeasn.tv/livetv/api/device/browser/v1/epg"
LOGO_BASE = "https://d3b6luslimvglo.cloudfront.net/images/79/rlaxximages/channels-rescaled/icon-white/{}_white.png"
OUTPUT_FILE = "epg.xml"
DAYS = 7
EPG_BATCH_SIZE = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://watch.whaletvplus.com",
    "Referer": "https://watch.whaletvplus.com/",
}

_session = None

def get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        device_id = str(uuid.uuid4())
        resp = _session.get(AUTH_URL, params={"apiToken": API_TOKEN, "uuid": device_id}, timeout=10)
        resp.raise_for_status()
        data = resp.json()["data"]
        token = data["subjectToken"]
        _session.headers["Authorization"] = f"Bearer {token}"
        print(f"Token obtenido: {token[:20]}...")
    return _session

def fetch_channels():
    """Obtiene todos los canales disponibles."""
    session = get_session()
    resp = session.get(CHANNELS_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    channels = {}
    seen = set()
    categories = data.get("data", [])
    skip = {"All", "Featured all other countries"}

    for cat in categories:
        cat_name = cat.get("categoryName", "")
        if cat_name in skip:
            continue
        for ch in cat.get("channelList", []):
            chl_id = ch.get("chlId")
            if chl_id and chl_id not in seen:
                seen.add(chl_id)
                channels[chl_id] = {
                    "id": chl_id,
                    "name": ch.get("chlName", ""),
                    "logo": LOGO_BASE.format(ch.get("imageIdentifier", "")),
                    "lang": (ch.get("chlLangCode", "es") or "es").split("-")[0],
                }
    print(f"Canales obtenidos: {len(channels)}")
    return channels

def fetch_epg_batch(channel_ids, start_ms, end_ms):
    """Obtiene EPG para un lote de canales."""
    session = get_session()
    params = {
        "channelIds": ",".join(channel_ids),
        "startTime": start_ms,
        "endTime": end_ms,
    }
    try:
        resp = session.get(EPG_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception as e:
        print(f"  Error EPG batch: {e}")
        return []

def build_xmltv(channels, epg_data):
    """Construye el XMLTV."""
    root = ET.Element("tv")
    root.set("generator-info-name", "WhaleTV-EPG")
    root.set("generator-info-url", "https://github.com/maligno78-ui/whale-epg")

    for ch in channels.values():
        channel = ET.SubElement(root, "channel", id=ch["id"])
        ET.SubElement(channel, "display-name", lang=ch["lang"]).text = ch["name"]
        if ch["logo"]:
            ET.SubElement(channel, "icon", src=ch["logo"])

    count = 0
    for entry in epg_data:
        chl_id = entry.get("chlId")
        for prog in entry.get("ptList", []):
            programme = ET.SubElement(root, "programme", {
                "channel": chl_id,
                "start": _fmt_time(prog.get("prgStm", 0)),
                "stop": _fmt_time(prog.get("prgEtm", 0)),
            })
            title = prog.get("prgTitle", "") or "Sin titulo"
            ET.SubElement(programme, "title", lang="es").text = title
            if prog.get("prgDesc"):
                ET.SubElement(programme, "desc", lang="es").text = prog["prgDesc"]
            count += 1

    print(f"Programas en EPG: {count}")
    return root

def _fmt_time(ms):
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S %z")

def main():
    print("=== Whale TV+ EPG Generator ===\n")
    channels = fetch_channels()

    now = datetime.now(timezone.utc)
    start_ms = int(now.timestamp() * 1000)
    end_ms = int((now + timedelta(days=DAYS)).timestamp() * 1000)

    chl_ids = list(channels.keys())
    epg_data = []

    print(f"Descargando EPG ({len(chl_ids)} canales, {DAYS} dias)...")
    for i in range(0, len(chl_ids), EPG_BATCH_SIZE):
        batch = chl_ids[i : i + EPG_BATCH_SIZE]
        result = fetch_epg_batch(batch, start_ms, end_ms)
        epg_data.extend(result)
        if (i // EPG_BATCH_SIZE + 1) % 5 == 0:
            print(f"  {min(i + EPG_BATCH_SIZE, len(chl_ids))}/{len(chl_ids)} lotes...")

    print("Generando XMLTV...")
    root = build_xmltv(channels, epg_data)

    xml_str = minidom.parseString(ET.tostring(root, encoding="utf-8")).toprettyxml(indent="  ", encoding="utf-8")
    with open(OUTPUT_FILE, "wb") as f:
        f.write(xml_str)

    size_mb = os.path.getsize(OUTPUT_FILE) / 1024 / 1024
    print(f"\nEPG generado: {OUTPUT_FILE} ({size_mb:.1f} MB)")
    print("Listo.")

if __name__ == "__main__":
    main()

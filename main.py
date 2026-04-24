import numpy as np
import requests
import pandas as pd
import math
import os
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO
import folium
from branca.element import Template, MacroElement

def get_latest_radar_rgb(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        gif = Image.open(BytesIO(res.content))
        frames = []
        try:
            while True:
                frames.append(gif.copy())
                gif.seek(gif.tell() + 1)
        except EOFError: pass
        return np.array(frames[-1].convert('RGB'))
    except: return None

def rgb_to_dbz(r, g, b):
    r, g, b = int(r), int(g), int(b)
    rain_colors = [((255, 0, 255), 60.0), ((255, 0, 0), 50.0), ((255, 128, 0), 45.0),
                   ((255, 255, 0), 35.0), ((0, 255, 0), 20.0), ((0, 200, 0), 15.0)]
    for target, dbz in rain_colors:
        tr, tg, tb = int(target[0]), int(target[1]), int(target[2])
        dist = math.sqrt((r - tr)**2 + (g - tg)**2 + (b - tb)**2)
        if dist < 55: return dbz
    return 0

def get_dbz_color(dbz):
    colors = {60: '#FF00FF', 50: '#FF0000', 40: '#FF8000', 30: '#FFFF00', 20: '#00FF00'}
    for threshold, color in colors.items():
        if dbz >= threshold: return color
    return '#008000'

# ตั้งค่าสถานี
configs = {
    "Nong Chok": {"url": "https://weather.bangkok.go.th/Images/Radar/radar.gif", "lat": 13.861, "lon": 100.862},
    "Nong Khaem": {"url": "https://weather.bangkok.go.th/Images/Radar/nkradar.gif", "lat": 13.701, "lon": 100.338}
}

all_rain_data = []
for name, conf in configs.items():
    img = get_latest_radar_rgb(conf["url"])
    if img is not None:
        px_per_km = 300.0 / 60.0
        grid = np.arange(-60.0, 60.0 + 0.4, 0.4)
        for y_km in grid:
            for x_km in grid:
                if math.sqrt(x_km**2 + y_km**2) > 60.0: continue
                px, py = int(425 + (x_km * px_per_km)), int(380 - (y_km * px_per_km))
                if 0 <= px < img.shape[1] and 0 <= py < img.shape[0]:
                    dbz = rgb_to_dbz(*img[py, px])
                    if dbz > 0:
                        all_rain_data.append([conf["lat"] + (y_km/111.0), 
                                            conf["lon"] + (x_km/(111.0*math.cos(math.radians(conf["lat"])))), 
                                            dbz])

# สร้างแผนที่
m = folium.Map(location=[13.75, 100.5], zoom_start=11, tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', attr='©CartoDB')
for p in all_rain_data:
    folium.CircleMarker(location=[p[0], p[1]], radius=2.5, color=get_dbz_color(p[2]), fill=True, weight=0, fill_opacity=0.75).add_to(m)

# บันทึกเป็น index.html (เพื่อให้แสดงผลหน้าเว็บได้เลย)
m.save("index.html")
print(f"Done! Found {len(all_rain_data)} points.")

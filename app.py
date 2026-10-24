import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, date
import calendar
import html
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components
import re
import unicodedata
import os
import glob
import random
import requests
from geopy.geocoders import Nominatim

# Initialisation du géolocaliseur de secours
geolocator = Nominatim(user_agent="raids_dingues_app_85")

# Compteur de visiteurs uniques (IP)
@st.cache_resource
def get_ip_tracker():
    return set()

ip_set = get_ip_tracker()
try:
    headers = st.context.headers
    ip_client = headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if ip_client:
        ip_set.add(ip_client)
except Exception:
    pass

# Chargement sécurisé du GeoJSON des départements via CDN
@st.cache_data(ttl=3600)
def load_geojson_depts():
    urls = [
        "https://cdn.jsdelivr.net/gh/gregoiredA/france-geojson@master/departements-version-simplifiee.geojson",
        "https://france-geojson.gregoiredavid.fr/repo/departements-version-simplifiee.geojson",
        "https://raw.githubusercontent.com/gregoiredA/france-geojson/master/departements-version-simplifiee.geojson"
    ]
    req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for u in urls:
        try:
            r = requests.get(u, headers=req_headers, timeout=6)
            if r.status_code == 200:
                data = r.json()
                if "features" in data:
                    return data
        except Exception:
            continue
    raise RuntimeError("Données GeoJSON inaccessibles")

DEPTS_NAMES = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence", "05": "Hautes-Alpes",
    "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes", "09": "Ariège", "10": "Aube",
    "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône", "14": "Calvados", "15": "Cantal",
    "16": "Charente", "17": "Charente-Maritime", "18": "Cher", "19": "Corrèze", "2A": "Corse-du-Sud",
    "2B": "Haute-Corse", "21": "Côte-d'Or", "22": "Côtes-d'Armor", "23": "Creuse", "24": "Dordogne",
    "25": "Doubs", "26": "Drôme", "27": "Eure", "28": "Eure-et-Loir", "29": "Finistère",
    "30": "Gard", "31": "Haute-Garonne", "32": "Gers", "33": "Gironde", "34": "Hérault",
    "35": "Ille-et-Vilaine", "36": "Indre", "37": "Indre-et-Loire", "38": "Isère", "39": "Jura",
    "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire", "44": "Loire-Atlantique",
    "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne", "48": "Lozère", "49": "Maine-et-Loire",
    "50": "Manche", "51": "Marne", "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle",
    "55": "Meuse", "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord",
    "60": "Oise", "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin", "68": "Haut-Rhin", "69": "Rhône",
    "70": "Haute-Saône", "71": "Saône-et-Loire", "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie",
    "75": "Paris", "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines", "79": "Deux-Sèvres",
    "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne", "83": "Var", "84": "Vaucluse",
    "85": "Vendée", "86": "Vienne",
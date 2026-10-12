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

# Chargement sécurisé du GeoJSON des départements
@st.cache_data(ttl=3600)
def load_geojson_depts():
    url = "https://raw.githubusercontent.com/gregoiredA/france-geojson/master/departements-version-simplifiee.geojson"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

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
    "85": "Vendée", "86": "Vienne", "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne",
    "90": "Territoire de Belfort", "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne", "95": "Val-d'Oise", "971": "Guadeloupe", "972": "Martinique", "973": "Guyane",
    "974": "La Réunion", "976": "Mayotte"
}

MOIS_TEXTE = {
    "janvier": 1, "janv": 1, "février": 2, "fevrier": 2, "févr": 2, "fevr": 2, "mars": 3,
    "avril": 4, "avr": 4, "mai": 5, "juin": 6, "juillet": 7, "juil": 7, "août": 8, "aout": 8,
    "septembre": 9, "sept": 9, "octobre": 10, "oct": 10, "novembre": 11, "nov": 11, "décembre": 12, "decembre": 12, "déc": 12, "dec": 12
}

def strip_accents(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.strip().upper()

def clean_course_key(text):
    if not isinstance(text, str): return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-zA-Z0-9]', '', text).upper()

def normalize_lieu(lieu):
    if not lieu or pd.isna(lieu):
        return ""
    text = str(lieu).split('(')[0]
    text = text.replace('\xa0', ' ').replace('-', ' ')
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', text).strip().upper()

def extract_dept(lieu_str):
    if pd.isna(lieu_str):
        return None
    match = re.search(r'\((\d{2,3}\vert{}2A\vert{}2B)\)', str(lieu_str))
    return match.group(1) if match else None

def parse_course_date(d_str):
    if pd.isna(d_str):
        return pd.NaT
    d_str = str(d_str).strip().lower()
    
    match_chiffres = re.findall(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', d_str)
    if match_chiffres:
        day, month, year = match_chiffres[-1]
        year_int = int(year) + 2000 if len(year) == 2 else int(year)
        try:
            return pd.Timestamp(year=year_int, month=int(month), day=int(day))
        except Exception:
            pass
            
    for m_nom, m_num in MOIS_TEXTE.items():
        if m_nom in d_str:
            jours = re.findall(r'\b\d{1,2}\b', d_str)
            annees = re.findall(r'\b20\d{2}\b', d_str)
            if jours:
                day_val = int(jours[-1])
                year_val = int(annees[0]) if annees else 2026
                try:
                    return pd.Timestamp(year=year_val, month=m_num, day=day_val)
                except Exception:
                    pass
    return pd.NaT

def get_rank_number(res_str):
    if pd.isna(res_str) or not str(res_str).strip():
        return None
    match = re.search(r'^\s*(\d+)', str(res_str).strip())
    return int(match.group(1)) if match else None

def format_resultat_avec_emoji(res_str):
    if pd.isna(res_str) or not str(res_str).strip():
        return ""
    val = str(res_str).strip()
    rank = get_rank_number(val)
    if rank == 1:
        return f"🥇 {val}"
    elif rank == 2:
        return f"🥈 {val}"
    elif rank == 3:
        return f"🥉 {val}"
    elif rank == 4:
        return f"🍫 {val}"
    return val

# 1. Configuration de la page
st.set_page_config(page_title="Raids Dingues 85", page_icon="🏃‍♂️", layout="wide")

# Affichage du compteur dans la barre latérale
st.sidebar.title("📊 Statistiques")
st.sidebar.metric("🌐 Visiteurs uniques (IP)", len(ip_set))
st.sidebar.divider()

st.title("🏃‍♂️ Raids Dingues 85")
st.write("Saison 2026 — Calendrier, Carte & Suivi des membres")

# 2. Connexion au Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

df_courses = conn.read(worksheet="BDD 2026", header=5, ttl=10)
df_participations = conn.read(worksheet="PARTICIPATIONS", ttl=10)

# Sécurisation des types (Anti-crash PyArrow)
for col in df_participations.columns:
    if col != 'Km_Calc':
        df_participations[col] = df_participations[col].fillna("").astype(str)

for col in df_courses.columns:
    df_courses[col] = df_courses[col].fillna("").astype(str)

# Lecture de l'onglet MEMBRES
df_membres_clean = pd.DataFrame()
try:
    df_membres = conn.read(worksheet="MEMBRES", ttl=10)
    df_membres['Nom_Complet'] = df_membres['NOM'].astype(str).str.strip() + " " + df_membres['Prénom'].astype(str).str.strip()
    df_membres['Sexe_Clean'] = df_membres['Sexe'].astype(str).str.strip().str.upper()
    df_membres['Key_Match'] = df_membres['Nom_Complet'].apply(strip_accents)
    
    df_membres_clean = df_membres[['Key_Match', 'Sexe_Clean']].drop_duplicates().copy()
    liste_membres = sorted(df_membres['Nom_Complet'].dropna().unique().tolist())
except Exception:
    liste_membres = sorted(df_participations["Nom_Membre"].dropna().unique().tolist()) if "Nom_Membre" in df_participations.columns else []

# Correction automatique des colonnes
rename_cols = {}
for c in df_participations.columns:
    if "sultat" in str(c).lower():
        rename_cols[c] = "Resultat"
    elif str(c).lower() in ["nom_prenom", "prenom_nom"]:
        rename_cols[c] = "Nom_Membre"
    elif str(c).lower() == "distance_choisie":
        rename_cols[c] = "Distance"

if rename_cols:
    df_participations = df_participations.rename(columns=rename_cols)

# Normalisation des chaînes & Clé sans ponctuation
df_courses = df_courses[df_courses["Nom de la course"] != ""].copy()
df_courses['Course_Key'] = df_courses['Nom de la course'].apply(clean_course_key)
df_participations['Course_Key'] = df_participations['Nom_Course'].apply(clean_course_key)

# Conversion intelligente des dates et extraction des départements
df_courses['Date_dt'] = df_courses['Date'].apply(parse_course_date)
df_courses = df_courses.sort_values(by='Date_dt')
df_courses['Dept_Code'] = df_courses['Lieu'].apply(extract_dept)

MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
    7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

# Base de coordonnées GPS ultra-complète (Niveau 1)
COORDS_VILLES_RAW = {
    "FOURAS": (45.9875, -1.0936), "MAILLEZAIS": (46.3725, -0.7383), "LA ROCHELLE": (46.1603, -1.1511),
    "LES MATHES": (45.7183, -1.1472), "BRESSUIRE": (46.8406, -0.4939), "POUFFONDS": (46.1736, -0.1558),
    "ST LAURENT SUR SEVRE": (46.9583, -0.8931), "PARIS": (48.8566, 2.3522), "LUCS SUR BOULOGNE": (46.8439, -1.4939),
    "LES LUCS SUR BOULOGNE": (46.8439, -1.4939), "NUEIL LES AUBIERS": (46.9372, -0.5897),
    "LA CHAPELLE DES POTS": (45.7608, -0.5408), "AIGONNAY": (46.3411, -0.2447), "FONTENAY LE COMTE": (46.4667, -0.8000),
    "SAIVRES": (46.4250, -0.2319), "SAINTE SOULLE": (46.1856, -1.0117), "CUGAND": (47.0628, -1.2542),
    "ST MAIXENT L'ECOLE": (46.4117, -0.2078), "CHAPELLE ST LAURENT": (46.8147, -0.4786),
    "ARCHINGEAY": (45.9328, -0.6558), "MERVENT": (46.5228, -0.7553), "VALLET": (47.1611, -1.2658),
    "AIGONDIGNE": (46.3486, -0.2883), "BOURNEZEAU": (46.6358, -1.1689), "VINCENNES": (48.8475, 2.4392),
    "ISSY LES MOULINEAUX": (48.8239, 2.2703), "CHAMPDENIERS": (46.4842, -0.4028), "CHAUCHE": (46.8308, -1.2694),
    "CHARENTON LE PONT": (48.8222, 2.4144), "AIGREFEUILLE D'AUNIS": (46.1181, -0.9328),
    "BOISSIERE DE MONTAIGU": (46.9806, -1.1917), "VOLVIC": (45.8711, 3.0372), "ST JEAN DE MONTS": (46.7922, -2.0603),
    "MORTAGNE / SEVRE": (46.9931, -0.9542), "MORTAGNE SUR SEVRE": (46.9931, -0.9542), "ROCHEFORT": (45.9428, -0.9631),
    "ST MARTIN DES NOYERS": (46.7239, -1.1783), "LONGEVILLE SUR MER": (46.4239, -1.4889),
    "LA GAUBRETIERE": (46.9458, -1.0664), "BEAULIEU SOUS LA ROCHE": (46.6764, -1.6094), "SAUMUR": (47.2603, -0.0769),
    "L'OIE": (46.7981, -1.1325), "ST HILAIRE DE RIEZ": (46.7214, -1.9453), "POUZAUGES": (46.7833, -0.8333),
    "VENAUSAULT": (46.6858, -1.5125), "VENANSAULT": (46.6858, -1.5125), "NIORT": (46.3237, -0.4648), "LUCON": (46.4550, -1.1664),
    "LA TRANCHE / MER": (46.3439, -1.4389), "LA TRANCHE SUR MER": (46.3439, -1.4389), "NOIRMOUTIER": (47.0003, -2.2417),
    "LES SABLES D'OLONNES": (46.4972, -1.7833), "LES SABLES D'OLONNE": (46.4972, -1.7833), "PARTHENAY": (46.6486, -0.2483),
    "LA ROCHE SUR YON": (46.6705, -1.4265), "CHATELAILLON-PLAGE": (46.0728, -1.0881), "CHATELAILLON": (46.0728, -1.0881),
    "LES HERBIERS": (46.8681, -1.0094), "NANTES": (47.2181, -1.5536), "CHANTONNAY": (46.6881, -1.0506),
    "MONTAIGU": (46.9739, -1.3125), "AIRVAULT": (46.8267, -0.1389), "TALMONT ST HILAIRE": (46.4683, -1.6186),
    "SAINTE NEOMAYE": (46.3719, -0.2589), "MAGNÉ": (46.3153, -0.5461), "CROZON": (48.2464, -4.4894),
    "CARCANS": (45.0783, -1.0456), "TIFFAUGES": (47.0142, -1.1114), "MAULEON": (46.9213, -0.7497),
    "LE POIRE SUR VIE": (46.7672, -1.5017), "VIX": (46.3631, -0.8542), "SAINTE FOY": (46.5372, -1.5647),
    "STE FOY": (46.5372, -1.5647), "COURS": (46.7328, -0.4967), "VIEILLE AURE": (42.8286, 0.3242),
    "VIELLE AURE": (42.8286, 0.3242), "LAVELANET": (42.9300, 1.8492), "CHEFFOIS": (46.6692, -0.7892),
    "FUTUROSCOPE": (46.6700, 0.3600), "SAINT MALO": (48.6493, -2.0257), "BARBATRE": (46.9450, -2.1810),
    "POULDREUZIC": (47.9525, -4.3606), "PORNIC": (47.1147, -2.1031), "CHAVAGNES EN PAILLERS": (46.8925, -1.2514),
    "LE CHATEAU D'OLERON": (45.8858, -1.1947), "CHATEAU D'OLERON": (45.8858, -1.1947)
}

COORDS_VILLES = {normalize_lieu(k): v for k, v in COORDS_VILLES_RAW.items()}

# Cache mémoire pour éviter les requêtes API redondantes
@st.cache_resource
def get_runtime_geo_cache():
    return {}

runtime_geo_cache = get_runtime_geo_cache()

def get_coords_expert(lieu_str):
    if not lieu_str or pd.isna(lieu_str):
        return None, None
    
    key = normalize_lieu(lieu_str)
    if not key or key.startswith('?') or key.startswith('#'):
        return None, None
    
    # 1. Base locale prioritaire
    if key in COORDS_VILLES:
        return COORDS_VILLES[key]
    
    # 2. Cache de session
    if key in runtime_geo_cache:
        return runtime_geo_cache[key]
    
    ville_clean = str(lieu_str).split('(')[0].replace('\xa0', ' ').strip()
    dept = extract_dept(lieu_str) or ""
    
    # 3. API Adresse de l'État français (BAN)
    try:
        query_ban = f"{ville_clean} {dept}".strip()
        resp = requests.get(
            "https://api-adresse.data.gouv.fr/search/",
            params={"q": query_ban, "type": "municipality", "limit": 1},
            timeout=2
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("features"):
                lon, lat = data["features"][0]["geometry"]["coordinates"]
                runtime_geo_cache[key] = (lat, lon)
                return lat, lon
    except Exception:
        pass
    
    # 4. Secours OpenStreetMap Nominatim
    try:
        dept_nom = DEPTS_NAMES.get(dept, "")
        query_osm = f"{ville_clean}, {dept_nom}, France" if dept_nom else f"{ville_clean}, France"
        loc = geolocator.geocode(query_osm, timeout=2)
        if loc:
            runtime_geo_cache[key] = (loc.latitude, loc.longitude)
            return loc.latitude, loc.longitude
    except Exception:
        pass
        
    return None, None

def categorize_course(type_course):
    t = str(type_course).upper()
    if "ORIENTATION" in t or "CO " in t or "CVO" in t or "RAID" in t: return "Orientation / Raid"
    elif "TRAIL" in t or "NATURE" in t or "BACKYARD" in t: return "Trail / Nature"
    elif "ROUTE" in t or "MARATHON" in t or "10 KM" in t or "SEMI" in t: return "Course sur route"
    elif "TRIATHLON" in t or "SWIMRUN" in t or "BIATHLON" in t or "BIKE" in t: return "Multisport (Tri, Swimrun...)"
    elif "RANDO" in t or "MARCHE" in t: return "Randonnée / Marche"
    else: return "Autres"

def get_icon_details(cat_course):
    if cat_course == "Orientation / Raid": return "compass", "fa"
    elif cat_course == "Trail / Nature": return "tree", "fa"
    elif cat_course == "Course sur route": return "road", "fa"
    elif cat_course == "Multisport (Tri, Swimrun...)": return "bicycle", "fa"
    elif cat_course == "Randonnée / Marche": return "blind", "fa"
    else: return "flag", "fa"

df_courses['Catégorie'] = df_courses['Type de course'].apply(categorize_course)

def extraire_km(distance_str):
    if pd.isna(distance_str): return 0.0
    val = str(distance_str).replace(',', '.').lower().replace('km', '').strip()
    match = re.search(r"(\d+(\.\d+)?)", val)
    if match: return float(match.group(1))
    return 0.0

df_participations['Km_Calc'] = df_participations['Distance'].apply(extraire_km)

liste_courses = df_courses["Nom de la course"].dropna().unique()
course_url = st.query_params.get("course", None)
default_idx = list(liste_courses).index(course_url) if course_url and course_url in liste_courses else 0

# --- FILTRAGE STRICT À DATE & AVEC INSCRITS ---
today = datetime.now()
courses_avec_inscrits = df_participations['Course_Key'].dropna().unique()

df_courses_a_date = df_courses[
    (df_courses['Course_Key'].isin(courses_avec_inscrits)) &
    (df_courses['Date_dt'].notna()) &
    (df_courses['Date_dt'] <= today)
].copy()

df_participations_a_date = df_participations[
    df_participations['Course_Key'].isin(df_courses_a_date['Course_Key'])
].copy()

# --- BANDEAU D'INDICATEURS CLÉS ---
kpi_events = df_courses_a_date["Nom de la course"].nunique()
kpi_inscriptions = len(df_participations_a_date)
kpi_depts = df_courses_a_date["Dept_Code"].dropna().nunique()

col_k1, col_k2, col_k3 = st.columns(3)
with col_k1:
    st.metric("📅 Événements courus à date", kpi_events)
with col_k2:
    st.metric("✍️ Inscriptions à date", kpi_inscriptions)
with col_k3:
    st.metric("🗺️ Départements parcourus à date", kpi_depts)

st.divider()

# 4. Organisation en onglets
tab_fiche, tab_cal, tab_carte, tab_membre, tab_stats_km, tab_stats_glob = st.tabs([
    "📋 Fiche & Inscription", 
    "📅 Calendrier Visuel", 
    "🗺️ Carte des courses", 
    "👤 Fiche Membre", 
    "🏆 Classement Kilométrique",
    "📊 Statistiques Globales"
])

# --- TAB 1 : FICHE & INSCRIPTION ---
with tab_fiche:
    st.subheader("📅 Sélectionner une course")
    course_choisie = st.selectbox("Quelle course t'intéresse ?", liste_courses, index=default_idx)

    if course_choisie:
        infos = df_courses[df_courses["Nom de la course"] == course_choisie].iloc[0]
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"📍 **Lieu :** {infos['Lieu']}")
            st.write(f"🗓 **Date :** {infos['Date']}")
            st.write(f"🏃 **Type :** {infos['Type de course']} ({infos['Détail']})")
            
            lien_raw = str(infos.get('Lien', '')).strip()
            match_lien = re.search(r'https?://[^\s\)\(\"\']+', lien_raw)             if match_lien:                 st.write(f"🔗 [Lien d'inscription]({match_lien.group(0)})")             elif lien_raw and lien_raw.lower() not in ["clos", "nan", "none", "lien d'inscription"]:                 st.write(f"🔗 **Lien :** {lien_raw}")         with col2:             img_col = 'Visuel' if 'Visuel' in infos else ('Lien_Image' if 'Lien_Image' in infos else None)             if img_col and pd.notna(infos[img_col]):                 raw_img = str(infos[img_col]).strip()                 match_img_url = re.search(r'https?://[^\s\)\(\"\']+', raw_img)
                if match_img_url:
                    st.image(match_img_url.group(0), width=300)

        st.divider()
        st.subheader("👥 Déjà inscrits :")
        c_key_choisie = clean_course_key(course_choisie)
        inscrits = df_participations[df_participations["Course_Key"] == c_key_choisie]
        
        if inscrits.empty:
            st.info("Aucun Raid Dingue n'est encore inscrit. Sois le premier !")
        else:
            disp_cols = [c for c in ["Nom_Membre", "Distance", "Statut", "Resultat"] if c in inscrits.columns]
            st.dataframe(inscrits[disp_cols].astype(str), hide_index=True)
            
        st.divider()
        st.subheader("✍️ M'inscrire à cette course")
        with st.form("form_inscription"):
            nom = st.selectbox("Sélectionne ton Nom / Prénom", liste_membres) if liste_membres else st.text_input("Ton Prénom et Nom")
            distance = st.text_
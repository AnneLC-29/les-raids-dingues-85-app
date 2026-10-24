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
    match = re.search(r'\((\d{2,3}|2A|2B)\)', str(lieu_str))
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

def extract_year_safely(d_str, date_dt):
    if pd.notna(date_dt):
        return int(date_dt.year)
    match = re.search(r'\b(202\d)\b', str(d_str))
    return int(match.group(1)) if match else 2026

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

# 2. Connexion au Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

def read_bdd_sheet(sheet_name):
    for h in [5, 0, 1, 4]:
        try:
            df = conn.read(worksheet=sheet_name, header=h, ttl=10)
            for c in df.columns:
                if "nom" in str(c).lower() and "course" in str(c).lower():
                    df = df.rename(columns={c: "Nom de la course"})
                    return df
        except Exception:
            continue
    return pd.DataFrame()

df_2026 = read_bdd_sheet("BDD 2026")
df_2027 = read_bdd_sheet("BDD 2027")
if df_2027.empty:
    df_2027 = read_bdd_sheet("2027")

df_courses_raw = pd.concat([df_2026, df_2027], ignore_index=True)

df_participations_raw = conn.read(worksheet="PARTICIPATIONS", ttl=10)

# Sécurisation des types
for col in df_participations_raw.columns:
    df_participations_raw[col] = df_participations_raw[col].fillna("").astype(str)

for col in df_courses_raw.columns:
    df_courses_raw[col] = df_courses_raw[col].fillna("").astype(str)

# Correction automatique des colonnes PARTICIPATIONS
rename_cols = {}
for c in df_participations_raw.columns:
    if "sultat" in str(c).lower():
        rename_cols[c] = "Resultat"
    elif str(c).lower() in ["nom_prenom", "prenom_nom"]:
        rename_cols[c] = "Nom_Membre"
    elif str(c).lower() == "distance_choisie":
        rename_cols[c] = "Distance"

if rename_cols:
    df_participations_raw = df_participations_raw.rename(columns=rename_cols)

# Traitement des dates et extraction des années
df_courses_raw = df_courses_raw[df_courses_raw["Nom de la course"].str.strip() != ""].copy()
df_courses_raw['Date_dt'] = df_courses_raw['Date'].apply(parse_course_date)
df_courses_raw['Annee'] = df_courses_raw.apply(lambda r: extract_year_safely(r['Date'], r['Date_dt']), axis=1)
df_courses_raw['Course_Key'] = df_courses_raw['Nom de la course'].apply(clean_course_key)
df_courses_raw['Dept_Code'] = df_courses_raw['Lieu'].apply(extract_dept)
df_courses_raw['Label_Unique'] = df_courses_raw.apply(lambda r: f"{r['Nom de la course']} ({r['Annee']})", axis=1)

df_participations_raw['Date_dt'] = df_participations_raw['Date'].apply(parse_course_date)
df_participations_raw['Annee'] = df_participations_raw.apply(lambda r: extract_year_safely(r['Date'], r['Date_dt']), axis=1)
df_participations_raw['Course_Key'] = df_participations_raw['Nom_Course'].apply(clean_course_key)

def extraire_km(distance_str):
    if pd.isna(distance_str): return 0.0
    val = str(distance_str).replace(',', '.').lower().replace('km', '').strip()
    match = re.search(r"(\d+(\.\d+)?)", val)
    if match: return float(match.group(1))
    return 0.0

df_participations_raw['Km_Calc'] = df_participations_raw['Distance'].apply(extraire_km)

# ================= MENU LATÉRAL : SÉLECTEUR DE SAISON =================
st.sidebar.title("⚙️ Paramètres")
saisons_disponibles = sorted(list(set(df_courses_raw['Annee'].dropna().astype(int).tolist() + [2026])))
saisons_selectionnees = st.sidebar.multiselect(
    "Saisons à afficher :",
    options=saisons_disponibles,
    default=saisons_disponibles
)

if not saisons_selectionnees:
    saisons_selectionnees = saisons_disponibles

st.sidebar.divider()
st.sidebar.title("📊 Statistiques")
st.sidebar.metric("🌐 Visiteurs uniques (IP)", len(ip_set))
st.sidebar.divider()

titre_annees = " & ".join(map(str, sorted(saisons_selectionnees)))
st.title("🏃‍♂️ Raids Dingues 85")
st.write(f"Saison {titre_annees} — Calendrier, Carte & Suivi des membres")

# Filtrage global selon la ou les saisons sélectionnées
df_courses = df_courses_raw[df_courses_raw['Annee'].isin(saisons_selectionnees)].sort_values(by='Date_dt').copy()
df_participations = df_participations_raw[df_participations_raw['Annee'].isin(saisons_selectionnees)].copy()

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

MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
    7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

# Base complète de coordonnées GPS (Niveau 1)
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
    "LE CHATEAU D'OLERON": (45.8858, -1.1947), "CHATEAU D'OLERON": (45.8858, -1.1947),
    "ARGENTON LES VALLEES": (46.9850, -0.4492), "ARGENTON-LES-VALLEES": (46.9850, -0.4492),
    "ARGENTONNAY": (46.9850, -0.4492)
}

COORDS_VILLES = {normalize_lieu(k): v for k, v in COORDS_VILLES_RAW.items()}

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
    
    if key in COORDS_VILLES:
        return COORDS_VILLES[key]
    
    if key in runtime_geo_cache:
        return runtime_geo_cache[key]
    
    ville_clean = str(lieu_str).split('(')[0].replace('\xa0', ' ').strip()
    dept = extract_dept(lieu_str) or ""
    
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

liste_courses_labels = df_courses["Label_Unique"].dropna().unique()
course_url = st.query_params.get("course", None)
default_idx = list(liste_courses_labels).index(course_url) if course_url and course_url in liste_courses_labels else 0

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
kpi_events = df_courses_a_date["Label_Unique"].nunique()
kpi_inscriptions = len(df_participations_a_date)
kpi_depts = df_courses_a_date["Dept_Code"].dropna().nunique()

col_k1, col_k2, col_k3 = st.columns(3)
with col_k1:
    st.metric(f"📅 Événements courus ({titre_annees})", kpi_events)
with col_k2:
    st.metric(f"✍️ Inscriptions à date ({titre_annees})", kpi_inscriptions)
with col_k3:
    st.metric("🗺️ Départements parcourus", kpi_depts)

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
    if len(liste_courses_labels) == 0:
        st.info("Aucune course disponible pour la sélection en cours.")
    else:
        course_choisie = st.selectbox("Quelle course t'intéresse ?", liste_courses_labels, index=default_idx)

        if course_choisie:
            infos = df_courses[df_courses["Label_Unique"] == course_choisie].iloc[0]
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"📍 **Lieu :** {infos['Lieu']}")
                st.write(f"🗓 **Date :** {infos['Date']}")
                st.write(f"🏃 **Type :** {infos['Type de course']} ({infos['Détail']})")
                
                lien_raw = str(infos.get('Lien', '')).strip()
                match_lien = re.search(r'https?://[^\s\)\(\"\']+', lien_raw)
                if match_lien:
                    st.write(f"🔗 [Lien d'inscription]({match_lien.group(0)})")
                elif lien_raw and lien_raw.lower() not in ["clos", "nan", "none", "lien d'inscription"]:
                    st.write(f"🔗 **Lien :** {lien_raw}")
            with col2:
                img_col = 'Visuel' if 'Visuel' in infos else ('Lien_Image' if 'Lien_Image' in infos else None)
                if img_col and pd.notna(infos[img_col]):
                    raw_img = str(infos[img_col]).strip()
                    match_img_url = re.search(r'https?://[^\s\)\(\"\']+', raw_img)
                    if match_img_url:
                        st.image(match_img_url.group(0), width=300)

            st.divider()
            st.subheader("👥 Déjà inscrits :")
            c_key_choisie = clean_course_key(infos["Nom de la course"])
            inscrits = df_participations[
                (df_participations["Course_Key"] == c_key_choisie) &
                (df_participations["Annee"] == infos["Annee"])
            ]
            
            if inscrits.empty:
                st.info("Aucun Raid Dingue n'est encore inscrit. Sois le premier !")
            else:
                disp_cols = [c for c in ["Nom_Membre", "Distance", "Statut", "Resultat"] if c in inscrits.columns]
                st.dataframe(inscrits[disp_cols].astype(str), hide_index=True)
                
            st.divider()
            st.subheader("✍️ M'inscrire à cette course")
            with st.form("form_inscription"):
                nom = st.selectbox("Sélectionne ton Nom / Prénom", liste_membres) if liste_membres else st.text_input("Ton Prénom et Nom")
                distance = st.text_input("Distance choisie (ex : 12 km)")
                submit = st.form_submit_button("Je participe !")
                
                if submit and nom:
                    nouvelle_inscription = pd.DataFrame([{
                        "Horodatage": datetime.now().strftime("%d/%m/%Y %H:%M"), "Date": str(infos['Date']), "Lieu": str(infos['Lieu']),            
                        "Nom_Membre": str(nom), "Nom_Course": str(infos['Nom de la course']), "Distance": str(distance), "Statut": "Inscrit", "Resultat": ""
                    }])
                    df_updated = pd.concat([df_participations_raw, nouvelle_inscription], ignore_index=True)
                    cols_to_drop = [c for c in ['Km_Calc', 'Course_Key', 'Date_dt', 'Annee'] if c in df_updated.columns]
                    if cols_to_drop: df_updated = df_updated.drop(columns=cols_to_drop)
                    conn.update(worksheet="PARTICIPATIONS", data=df_updated)
                    st.success(f"Bravo {nom} ! Ton inscription a été enregistrée.")
                    st.rerun()

# --- TAB 2 : CALENDRIER VISUEL ---
with tab_cal:
    st.subheader(f"📅 Vue Calendrier Mensuel ({titre_annees})")
    col_y, col_m, col_f1, col_f2 = st.columns([1, 1, 2, 2])
    with col_y:
        annee_cal = st.selectbox("Année :", sorted(saisons_selectionnees), key="sel_annee_cal")
    with col_m:
        mois_selectionne = st.selectbox("Mois :", range(1, 13), index=0, format_func=lambda m: f"{MOIS_FR[m]} {annee_cal}", key="sel_mois_cal")
    with col_f1:
        cat_choices_cal = ["Toutes les courses"] + sorted(df_courses['Catégorie'].unique().tolist())
        filtre_type_cal = st.selectbox("🎯 Filtrer par discipline :", cat_choices_cal, key="cal_type")
    with col_f2:
        st.write(""); st.write("")
        filtre_inscrits_cal = st.checkbox("🚩 Courses avec RD inscrits uniquement", key="cal_rd")

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(annee_cal, mois_selectionne)

    html_code = f"""<!DOCTYPE html>
<html><head><style>
    body {{ margin: 0; padding-top: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    .cal-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    .cal-th {{ background-color: #0066cc; color: white; text-align: center; padding: 10px; font-size: 13px; font-weight: bold; border: 1px solid #0055b3; }}
    .cal-td {{ border: 1px solid #ddd; vertical-align: top; height: 110px; padding: 5px; background-color: #ffffff; position: relative; }}
    .cal-empty {{ background-color: #f8f9fa; }}
    .day-num {{ font-weight: bold; font-size: 12px; color: #444; margin-bottom: 4px; }}
    .event-card {{ position: relative; padding: 4px 6px; margin-bottom: 4px; border-radius: 4px; font-size: 11px; cursor: pointer; }}
    .event-red {{ background-color: #ffe6e6; color: #cc0000; border-left: 3px solid #cc0000; font-weight: bold; }}
    .event-blue {{ background-color: #e6f0ff; color: #004085; border-left: 3px solid #0066cc; }}
    .tooltip-content {{ visibility: hidden; width: 210px; background-color: #1e293b; color: #ffffff; text-align: left; border-radius: 6px; padding: 8px 10px; position: absolute; z-index: 999; bottom: 100%; left: 50%; transform: translateX(-50%); box-shadow: 0px 4px 12px rgba(0,0,0,0.3); font-size: 11px; line-height: 1.4; white-space: normal; opacity: 0; transition: opacity 0.15s ease-in-out; margin-bottom: 6px; pointer-events: none; }}
    .tooltip-content::after {{ content: ""; position: absolute; top: 100%; left: 50%; margin-left: -5px; border-width: 5px; border-style: solid; border-color: #1e293b transparent transparent transparent; }}
    .event-card:hover .tooltip-content {{ visibility: visible; opacity: 1; }}
</style>
<script>
    function navToCourse(courseName) {{
        try {{ var parentUrl = new URL(window.parent.location.href); parentUrl.searchParams.set('course', courseName); window.parent.location.href = parentUrl.toString();
        }} catch(e) {{ window.top.location.search = '?course=' + encodeURIComponent(courseName); }}
    }}
</script></head><body>
<table class="cal-table"><thead><tr><th class="cal-th">LUNDI</th><th class="cal-th">MARDI</th><th class="cal-th">MERCREDI</th><th class="cal-th">JEUDI</th><th class="cal-th">VENDREDI</th><th class="cal-th">SAMEDI</th><th class="cal-th">DIMANCHE</th></tr></thead><tbody>"""

    for week in month_days:
        html_code += "<tr>"
        for day in week:
            if day == 0: html_code += '<td class="cal-td cal-empty"></td>'
            else:
                date_target = pd.Timestamp(year=annee_cal, month=mois_selectionne, day=day)
                courses_jour = df_courses[df_courses['Date_dt'] == date_target]
                cell_content = f'<div class="day-num">{day}</div>'
                
                for _, row in courses_jour.iterrows():
                    nom_raw = str(row['Nom de la course'])
                    c_key = str(row['Course_Key'])
                    
                    if filtre_type_cal != "Toutes les courses" and row['Catégorie'] != filtre_type_cal: continue
                    
                    inscrits_df = df_participations[
                        (df_participations['Course_Key'] == c_key) &
                        (df_participations['Annee'] == annee_cal)
                    ]
                    inscrits_liste = inscrits_df['Nom_Membre'].tolist()
                    nb_inscrits = len(inscrits_liste)
                    
                    if filtre_inscrits_cal and nb_inscrits == 0: continue
                        
                    nom_c = html.escape(nom_raw)
                    inscrits_html = f"<br><b>👥 Inscrits ({nb_inscrits}) :</b><br>" + ", ".join([html.escape(m) for m in inscrits_liste]) if nb_inscrits > 0 else "<br><i>Aucun membre inscrit</i>"
                    tooltip_body = f"<b>{nom_c}</b><br>📍 {html.escape(str(row['Lieu']))}<br>🏃 {html.escape(str(row['Type de course']))} ({html.escape(str(row['Détail']))}){inscrits_html}<br><br><span style='color: #38bdf8; font-weight: bold;'>👉 Clic pour m'inscrire</span>"
                    click_action = f"navToCourse('{str(row['Label_Unique']).replace('`', '').replace('\"', '').replace('+', '')}')"
                    
                    if nb_inscrits > 0: cell_content += f'<div class="event-card event-red" onclick="{click_action}">🔴 {nom_c} ({nb_inscrits})<div class="tooltip-content">{tooltip_body}</div></div>'
                    else: cell_content += f'<div class="event-card event-blue" onclick="{click_action}">🏃 {nom_c}<div class="tooltip-content">{tooltip_body}</div></div>'
                        
                html_code += f'<td class="cal-td">{cell_content}</td>'
        html_code += "</tr>"

    html_code += "</tbody></table></body></html>"
    components.html(html_code, height=680, scrolling=True)

# --- TAB 3 : CARTE INTERACTIVE & PANNEAU DROIT ---
with tab_carte:
    st.subheader("🗺️ Localisation des courses & Détails")
    
    col_c1, col_c2, col_c3 = st.columns([2, 2, 2])
    
    with col_c1:
        cat_choices = ["Toutes les courses"] + sorted(df_courses['Catégorie'].unique().tolist())
        filtre_type = st.selectbox("🎯 Filtrer par discipline :", cat_choices)
        
    dates_valides = df_courses['Date_dt'].dropna()
    min_d = dates_valides.min().date() if not dates_valides.empty else date(min(saisons_selectionnees), 1, 1)
    max_d = dates_valides.max().date() if not dates_valides.empty else date(max(saisons_selectionnees), 12, 31)
    
    with col_c2:
        plage_dates = st.date_input("🗓️ Plage de dates :", value=(min_d, max_d), min_value=min_d, max_value=max_d)
        
    with col_c3:
        st.write(""); st.write("")
        filtre_inscrits = st.checkbox("🚩 Courses avec Raids Dingues uniquement", value=False)
        
    if isinstance(plage_dates, (tuple, list)) and len(plage_dates) == 2:
        start_date, end_date = plage_dates[0], plage_dates[1]
    elif isinstance(plage_dates, (tuple, list)) and len(plage_dates) == 1:
        start_date = end_date = plage_dates[0]
    else:
        start_date, end_date = min_d, max_d
    
    col_map, col_details = st.columns([2, 1])
    
    with col_map:
        m = folium.Map(location=[46.67, -1.42], zoom_start=8, tiles="OpenStreetMap")
        for _, row in df_courses.iterrows():
            if filtre_type != "Toutes les courses" and row['Catégorie'] != filtre_type: continue
            if pd.isna(row['Date_dt']): continue
                
            course_d = row['Date_dt'].date()
            if not (start_date <= course_d <= end_date): continue
            
            nom_c = str(row['Nom de la course'])
            c_key = str(row['Course_Key'])
            
            inscrits_df = df_participations[
                (df_participations['Course_Key'] == c_key) &
                (df_participations['Annee'] == row['Annee'])
            ]
            nb_inscrits = len(inscrits_df)
            
            if filtre_inscrits and nb_inscrits == 0: continue
                
            lat, lon = get_coords_expert(row['Lieu'])
            if lat and lon:
                rng = random.Random(str(row['Label_Unique']))
                lat += rng.uniform(-0.004, 0.004)
                lon += rng.uniform(-0.004, 0.004)

                icon_color = "red" if nb_inscrits > 0 else "blue"
                icon_name, icon_prefix = get_icon_details(row['Catégorie'])
                
                popup_html = f"<div style='font-family: sans-serif; width: 180px;'><b>{html.escape(nom_c)}</b><br>📅 {row['Date']}<br>📍 {row['Lieu']}<br>🏃 {row['Type de course']}<br><small>{row['Détail']}</small><br><b>👥 Inscrits : {nb_inscrits}</b></div>"
                
                folium.Marker(
                    location=[lat, lon], popup=folium.Popup(popup_html, max_width=220),
                    tooltip=f"{row['Label_Unique']} ({row['Date']})", name=str(row['Label_Unique']),
                    icon=folium.Icon(color=icon_color, icon=icon_name, prefix=icon_prefix)
                ).add_to(m)
                
        map_data = st_folium(m, width="100%", height=600, key="map_courses_v5", returned_objects=["last_object_clicked_tooltip"])
    
    with col_details:
        st.write("### 📜 Palmarès de la course")
        course_cliquee_label = None
        if map_data
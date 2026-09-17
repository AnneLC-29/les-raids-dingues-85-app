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
from geopy.geocoders import Nominatim

# Initialisation du géolocaliseur
geolocator = Nominatim(user_agent="raids_dingues_app_85")

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
    if not isinstance(text, str): return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.strip().upper()

def extract_dept(lieu_str):
    if pd.isna(lieu_str): return None
    match = re.search(r'\((\d{2,3}|2A|2B)\)', str(lieu_str))
    return match.group(1) if match else None

def parse_course_date(d_str):
    if pd.isna(d_str): return pd.NaT
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

# 1. Configuration de la page
st.set_page_config(page_title="Raids Dingues 85", page_icon="🏃‍♂️", layout="wide")

# ================= MENU LATÉRAL (FILTRE ANNÉES) =================
st.sidebar.header("⚙️ Paramètres")
st.sidebar.markdown("Coche les années que tu souhaites afficher sur l'application :")

annees_disponibles = [2026, 2027]
annees_selectionnees = st.sidebar.multiselect(
    "Sélectionner la / les saison(s) :", 
    options=annees_disponibles, 
    default=[2026]
)

if not annees_selectionnees:
    st.warning("⚠️ Veuillez sélectionner au moins une année dans le menu de gauche.")
    st.stop()

annees_str = " & ".join(map(str, sorted(annees_selectionnees)))
st.title("🏃‍♂️ Raids Dingues 85")
st.write(f"Saison {annees_str} — Calendrier, Carte & Suivi des membres")

# 2. Connexion au Google Sheet
conn = st.connection("gsheets", type=GSheetsConnection)

# Lecture multi-onglets (2026 avec header=5, 2027 avec header=0 sur ligne 1)
try:
    df_2026 = conn.read(worksheet="BDD 2026", header=5, ttl=10)
except Exception:
    df_2026 = pd.DataFrame()

try:
    df_2027 = conn.read(worksheet="BDD 2027", header=0, ttl=10)
except Exception:
    df_2027 = pd.DataFrame()

df_courses = pd.concat([df_2026, df_2027], ignore_index=True)
if "Nom de la course" in df_courses.columns:
    df_courses = df_courses.dropna(subset=["Nom de la course"])
else:
    st.error("L'onglet BDD semble vide ou mal formaté.")
    st.stop()

df_participations = conn.read(worksheet="PARTICIPATIONS", ttl=10)

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

# Correction colonnes participations
rename_cols = {}
for c in df_participations.columns:
    if "sultat" in str(c).lower(): rename_cols[c] = "Resultat"
    elif str(c).lower() in ["nom_prenom", "prenom_nom"]: rename_cols[c] = "Nom_Membre"
    elif str(c).lower() == "distance_choisie": rename_cols[c] = "Distance"
if rename_cols:
    df_participations = df_participations.rename(columns=rename_cols)

# Traitement des DATES et ANNÉES pour df_courses
df_courses['Date_dt'] = df_courses['Date'].apply(parse_course_date)
df_courses['Annee'] = df_courses['Date_dt'].dt.year
df_courses = df_courses[df_courses['Annee'].isin(annees_selectionnees)].sort_values(by='Date_dt')
df_courses['Dept_Code'] = df_courses['Lieu'].apply(extract_dept)

# Création d'un Label Unique pour ne pas mélanger 2026 et 2027
def create_label(row):
    annee = str(int(row['Annee'])) if pd.notna(row['Annee']) else "Inconnue"
    return f"{row['Nom de la course']} ({annee})"
df_courses['Label_Unique'] = df_courses.apply(create_label, axis=1)

# Traitement des DATES et ANNÉES pour df_participations
df_participations['Date_dt'] = df_participations['Date'].apply(parse_course_date)
df_participations['Annee'] = df_participations['Date_dt'].dt.year

# On garde les participations liées aux années sélectionnées (ou sans date précise pour ne pas les perdre)
df_participations = df_participations[
    df_participations['Annee'].isin(annees_selectionnees) | df_participations['Annee'].isna()
].copy()

MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
    7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}

# Base de coordonnées GPS enrichie
COORDS_VILLES = {
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
    "VENAUSAULT": (46.6858, -1.5125), "NIORT": (46.3237, -0.4648), "LUCON": (46.4550, -1.1664),
    "LA TRANCHE / MER": (46.3439, -1.4389), "LA TRANCHE SUR MER": (46.3439, -1.4389), "NOIRMOUTIER": (47.0003, -2.2417),
    "LES SABLES D'OLONNES": (46.4972, -1.7833), "LES SABLES D'OLONNE": (46.4972, -1.7833), "PARTHENAY": (46.6486, -0.2483),
    "LA ROCHE SUR YON": (46.6705, -1.4265), "CHATELAILLON-PLAGE": (46.0728, -1.0881), "CHATELAILLON": (46.0728, -1.0881),
    "LES HERBIERS": (46.8681, -1.0094), "NANTES": (47.2181, -1.5536), "CHANTONNAY": (46.6881, -1.0506),
    "MONTAIGU": (46.9739, -1.3125), "AIRVAULT": (46.8267, -0.1389), "TALMONT ST HILAIRE": (46.4683, -1.6186),
    "SAINTE NEOMAYE": (46.3719, -0.2589), "MAGNÉ": (46.3153, -0.5461), "CROZON": (48.2464, -4.4894),
    "CARCANS": (45.0783, -1.0456), "TIFFAUGES": (47.0142, -1.1114), "MAULEON": (46.9213, -0.7497),
    "LE POIRE SUR VIE": (46.7672, -1.5017), "LE POIRÉ SUR VIE": (46.7672, -1.5017), "LE POIRE-SUR-VIE": (46.7672, -1.5017)
}

@st.cache_data
def get_coords_smart(lieu_str):
    if not lieu_str or pd.isna(lieu_str): return None, None
    ville = str(lieu_str).split('(')[0].strip().upper()
    if ville in COORDS_VILLES: return COORDS_VILLES[ville]
    try:
        match = re.search(r"\((.*?)\)", str(lieu_str))
        dept = match.group(1) if match else ""
        query = f"{ville} {dept}, France" if dept else f"{ville}, France"
        loc = geolocator.geocode(query, timeout=4)
        if loc: return loc.latitude, loc.longitude
    except Exception: pass
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

liste_courses_labels = df_courses["Label_Unique"].dropna().unique()
course_url = st.query_params.get("course", None)
default_idx = list(liste_courses_labels).index(course_url) if course_url and course_url in liste_courses_labels else 0

# --- FILTRAGE STRICT À DATE ---
today = datetime.now()
df_courses_a_date = df_courses[(df_courses['Date_dt'].notna()) & (df_courses['Date_dt'] <= today)].copy()

# Participations reliées à ces événements passés
df_participations_a_date = df_participations[
    (df_participations['Nom_Course'].isin(df_courses_a_date['Nom de la course'])) & 
    (df_participations['Date'].isin(df_courses_a_date['Date']))
].copy()

# --- BANDEAU D'INDICATEURS CLÉS ---
kpi_events = df_courses_a_date["Label_Unique"].nunique()
kpi_inscriptions = len(df_participations_a_date)
kpi_depts = df_courses_a_date["Dept_Code"].dropna().nunique()

col_k1, col_k2, col_k3 = st.columns(3)
with col_k1: st.metric("📅 Événements courus à date", kpi_events)
with col_k2: st.metric("✍️ Inscriptions à date", kpi_inscriptions)
with col_k3: st.metric("🗺️ Départements parcourus à date", kpi_depts)

st.divider()

# 4. Organisation en onglets
tab_fiche, tab_cal, tab_carte, tab_membre, tab_stats_km, tab_stats_glob = st.tabs([
    "📋 Fiche & Inscription", "📅 Calendrier Visuel", "🗺️ Carte des courses", 
    "👤 Fiche Membre", "🏆 Classement Kilométrique", "📊 Statistiques Globales"
])

# --- TAB 1 : FICHE & INSCRIPTION ---
with tab_fiche:
    st.subheader("📅 Sélectionner une course")
    course_choisie = st.selectbox("Quelle course t'intéresse ?", liste_courses_labels, index=default_idx)

    if course_choisie:
        infos = df_courses[df_courses["Label_Unique"] == course_choisie].iloc[0]
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write(f"📍 **Lieu :** {infos['Lieu']}")
            st.write(f"🗓 **Date :** {infos['Date']}")
            st.write(f"🏃 **Type :** {infos['Type de course']} ({infos['Détail']})")
            if pd.notna(infos.get('Lien')) and infos.get('Lien') != "Clos":
                st.write(f"🔗 [Lien d'inscription]({infos['Lien']})")
        with col2:
            if 'Lien_Image' in infos and pd.notna(infos['Lien_Image']):
                st.image(infos['Lien_Image'], width=300)

        st.divider()
        st.subheader("👥 Déjà inscrits :")
        inscrits = df_participations[(df_participations["Nom_Course"] == infos["Nom de la course"]) & (df_participations["Date"] == infos["Date"])]
        
        if inscrits.empty:
            st.info("Aucun Raid Dingue n'est encore inscrit. Sois le premier !")
        else:
            disp_cols = [c for c in ["Nom_Membre", "Distance", "Statut", "Resultat"] if c in inscrits.columns]
            st.dataframe(inscrits[disp_cols], hide_index=True)
            
        st.divider()
        st.subheader("✍️ M'inscrire à cette course")
        with st.form("form_inscription"):
            nom = st.selectbox("Sélectionne ton Nom / Prénom", liste_membres) if liste_membres else st.text_input("Ton Prénom et Nom")
            distance = st.text_input("Distance choisie (ex : 12 km)")
            submit = st.form_submit_button("Je participe !")
            
            if submit and nom:
                nouvelle_inscription = pd.DataFrame([{
                    "Horodatage": datetime.now().strftime("%d/%m/%Y %H:%M"), "Date": infos['Date'], "Lieu": infos['Lieu'],            
                    "Nom_Membre": nom, "Nom_Course": infos['Nom de la course'], "Distance": distance, "Statut": "Inscrit", "Resultat": ""
                }])
                df_updated = pd.concat([df_participations, nouvelle_inscription], ignore_index=True)
                if 'Km_Calc' in df_updated.columns: df_updated = df_updated.drop(columns=['Km_Calc'])
                if 'Date_dt' in df_updated.columns: df_updated = df_updated.drop(columns=['Date_dt'])
                if 'Annee' in df_updated.columns: df_updated = df_updated.drop(columns=['Annee'])
                conn.update(worksheet="PARTICIPATIONS", data=df_updated)
                st.success(f"Bravo {nom} ! Ton inscription a été enregistrée.")
                st.rerun()

# --- TAB 2 : CALENDRIER VISUEL ---
with tab_cal:
    st.subheader(f"📅 Vue Calendrier Mensuel ({annees_str})")
    col_m0, col_m, col_f1, col_f2 = st.columns([1, 1, 2, 2])
    with col_m0:
        annee_cal = st.selectbox("Année :", sorted(annees_selectionnees))
    with col_m:
        mois_selectionne = st.selectbox("Mois :", range(1, 13), index=0, format_func=lambda m: MOIS_FR[m])
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
    function navToCourse(courseLabel) {{
        try {{ var parentUrl = new URL(window.parent.location.href); parentUrl.searchParams.set('course', courseLabel); window.parent.location.href = parentUrl.toString();
        }} catch(e) {{ window.top.location.search = '?course=' + encodeURIComponent(courseLabel); }}
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
                    if filtre_type_cal != "Toutes les courses" and row['Catégorie'] != filtre_type_cal: continue
                    
                    inscrits_df = df_participations[(df_participations['Nom_Course'] == nom_raw) & (df_participations['Date'] == row['Date'])]
                    inscrits_liste = inscrits_df['Nom_Membre'].tolist()
                    nb_inscrits = len(inscrits_liste)
                    
                    if filtre_inscrits_cal and nb_inscrits == 0: continue
                        
                    nom_c = html.escape(nom_raw)
                    inscrits_html = f"<br><b>👥 Inscrits ({nb_inscrits}) :</b><br>" + ", ".join([html.escape(m) for m in inscrits_liste]) if nb_inscrits > 0 else "<br><i>Aucun membre inscrit</i>"
                    tooltip_body = f"<b>{nom_c}</b><br>📍 {html.escape(str(row['Lieu']))}<br>🏃 {html.escape(str(row['Type de course']))} ({html.escape(str(row.get('Détail', '')))}){inscrits_html}<br><br><span style='color: #38bdf8; font-weight: bold;'>👉 Clic pour m'inscrire</span>"
                    click_action = f"navToCourse('{row['Label_Unique'].replace('`', '').replace('\"', '').replace('+', '')}')"
                    
                    if nb_inscrits > 0: cell_content += f'<div class="event-card event-red" onclick="{click_action}">🔴 {nom_c} ({nb_inscrits})<div class="tooltip-content">{tooltip_body}</div></div>'
                    else: cell_content += f'<div class="event-card event-blue" onclick="{click_action}">🏃 {nom_c}<div class="tooltip-content">{tooltip_body}</div></div>'
                        
                html_code += f'<td class="cal-td">{cell_content}</td>'
        html_code += "</tr>"

    html_code += "</tbody></table></body></html>"
    components.html(html_code, height=680, scrolling=True)

# --- TAB 3 : CARTE INTERACTIVE ---
with tab_carte:
    st.subheader("🗺️ Localisation des courses & Détails")
    
    col_c1, col_c2, col_c3 = st.columns([2, 2, 2])
    
    with col_c1:
        cat_choices = ["Toutes les courses"] + sorted(df_courses['Catégorie'].unique().tolist())
        filtre_type = st.selectbox("🎯 Filtrer par discipline :", cat_choices)
        
    dates_valides = df_courses['Date_dt'].dropna()
    min_d = dates_valides.min().date() if not dates_valides.empty else date(min(annees_selectionnees), 1, 1)
    max_d = dates_valides.max().date() if not dates_valides.empty else date(max(annees_selectionnees), 12, 31)
    
    with col_c2:
        plage_dates = st.date_input("🗓️ Plage de dates :", value=(min_d, max_d), min_value=min_d, max_value=max_d)
        
    with col_c3:
        st.write(""); st.write("")
        filtre_inscrits = st.checkbox("🚩 Courses avec Raids Dingues uniquement", value=False)
        
    if isinstance(plage_dates, (tuple, list)) and len(plage_dates) == 2: start_date, end_date = plage_dates[0], plage_dates[1]
    elif isinstance(plage_dates, (tuple, list)) and len(plage_dates) == 1: start_date = end_date = plage_dates[0]
    else: start_date, end_date = min_d, max_d
    
    col_map, col_details = st.columns([2, 1])
    
    with col_map:
        m = folium.Map(location=[46.67, -1.42], zoom_start=8, tiles="OpenStreetMap")
        for _, row in df_courses.iterrows():
            if filtre_type != "Toutes les courses" and row['Catégorie'] != filtre_type: continue
            if pd.isna(row['Date_dt']): continue
                
            course_d = row['Date_dt'].date()
            if not (start_date <= course_d <= end_date): continue
            
            inscrits_df = df_participations[(df_participations['Nom_Course'] == row['Nom de la course']) & (df_participations['Date'] == row['Date'])]
            nb_inscrits = len(inscrits_df)
            
            if filtre_inscrits and nb_inscrits == 0: continue
                
            lat, lon = get_coords_smart(row['Lieu'])
            if lat and lon:
                icon_color = "red" if nb_inscrits > 0 else "blue"
                icon_name, icon_prefix = get_icon_details(row['Catégorie'])
                
                popup_html = f"<div style='font-family: sans-serif; width: 180px;'><b>{html.escape(str(row['Nom de la course']))}</b><br>📅 {row['Date']}<br>📍 {row['Lieu']}<br>🏃 {row['Type de course']}<br><small>{row.get('Détail', '')}</small><br><b>👥 Inscrits : {nb_inscrits}</b></div>"
                
                folium.Marker(
                    location=[lat, lon], popup=folium.Popup(popup_html, max_width=220),
                    tooltip=row['Label_Unique'], name=row['Label_Unique'],
                    icon=folium.Icon(color=icon_color, icon=icon_name, prefix=icon_prefix)
                ).add_to(m)
                
        map_data = st_folium(m, width="100%", height=600, returned_objects=["last_object_clicked_tooltip"])
    
    with col_details:
        st.write("### 📜 Palmarès de la course")
        course_cliquee_label = map_data.get("last_object_clicked_tooltip") if map_data else None
        
        if not course_cliquee_label:
            st.info("👈 Clique sur un marqueur de la carte pour afficher la liste des participants.")
        else:
            try:
                infos_cliquee = df_courses[df_courses["Label_Unique"] == course_cliquee_label].iloc[0]
                st.markdown(f"**Événement :** {infos_cliquee['Nom de la course']}")
                inscrits_course = df_participations[(df_participations["Nom_Course"] == infos_cliquee['Nom de la course']) & (df_participations["Date"] == infos_cliquee['Date'])]
                
                if inscrits_course.empty:
                    st.warning("Aucun Raid Dingue n'est encore inscrit pour cette course.")
                    st.write(f"🔗 [M'inscrire à {infos_cliquee['Nom de la course']}](?course={infos_cliquee['Label_Unique']})")
                else:
                    st.success(f"👥 {len(inscrits_course)} participant(s)")
                    inscrits_course = inscrits_course.sort_values(by="Km_Calc", ascending=False)
                    disp_cols_c = [c for c in ["Nom_Membre", "Distance", "Resultat"] if c in inscrits_course.columns]
                    st.dataframe(inscrits_course[disp_cols_c], hide_index=True, use_container_width=True)
            except IndexError:
                st.info("Données de course introuvables.")

# --- TAB 4 : FICHE MEMBRE ---
with tab_membre:
    st.subheader("👤 Suivi individuel des membres")
    membres_dispos = liste_membres if liste_membres else sorted(df_participations["Nom_Membre"].dropna().unique().tolist())
    
    if not membres_dispos: st.info("Aucun membre disponible.")
    else:
        membre_choisi = st.selectbox("Sélectionner un membre des Raids Dingues :", membres_dispos)
        if membre_choisi:
            p_membre = df_participations[df_participations["Nom_Membre"].apply(strip_accents) == strip_accents(membre_choisi)] if not df_participations.empty else pd.DataFrame()
            if p_membre.empty: st.info(f"{membre_choisi} n'a aucune inscription sur la saison {annees_str}.")
            else:
                st.metric(f"Total d'inscriptions ({annees_str})", len(p_membre))
                details_membre = p_membre.merge(df_courses[["Nom de la course", "Date", "Type de course"]], left_on=["Nom_Course", "Date"], right_on=["Nom de la course", "Date"], how="left")
                disp_cols_m = [c for c in ["Date", "Nom_Course", "Lieu", "Type de course", "Distance", "Statut", "Resultat"] if c in details_membre.columns]
                st.dataframe(details_membre[disp_cols_m], hide_index=True, use_container_width=True)

# --- TAB 5 : CLASSEMENT KILOMETRIQUE ---
with tab_stats_km:
    col_km_title, col_km_metric = st.columns([2, 1])
    
    mots_valides = ['terminé', 'termine', 'finisher']
    df_finishers = df_participations[df_participations['Statut'].astype(str).str.strip().str.lower().isin(mots_valides)]
    total_km_club = df_finishers['Km_Calc'].sum() if not df_finishers.empty else 0.0

    with col_km_title:
        st.subheader(f"🏆 Classement Kilométrique du Club ({annees_str})")
    with col_km_metric:
        st.metric("Total kilomètres parcourus", f"{total_km_club:.1f} km")
    
    if df_finishers.empty: 
        st.info("Aucun kilomètre validé sur la période sélectionnée.")
    else:
        stats_membres = df_finishers.groupby("Nom_Membre").agg(Courses_Totales=('Nom_Course', 'count'), Km_Parcourus=('Km_Calc', 'sum')).reset_index()
        stats_membres['Key_Match'] = stats_membres['Nom_Membre'].apply(strip_accents)
        
        if not df_membres_clean.empty:
            stats_membres = stats_membres.merge(df_membres_clean, on='Key_Match', how='left')
            stats_membres['Sexe'] = stats_membres['Sexe_Clean'].map({'H': '👨 Homme', 'F': '👩 Femme'}).fillna('❓ Non renseigné')
            stats_membres = stats_membres.drop(columns=['Key_Match', 'Sexe_Clean'])
        else:
            stats_membres['Sexe'] = '❓ Non renseigné'
            
        stats_membres = stats_membres.sort_values(by=['Km_Parcourus', 'Nom_Membre'], ascending=[False, True])
        stats_display = stats_membres.rename(columns={'Nom_Membre': 'Membre', 'Courses_Totales': 'Nb Courses Terminées', 'Km_Parcourus': 'Distance Totale (km)'})[['Membre', 'Sexe', 'Nb Courses Terminées', 'Distance Totale (km)']]
        stats_display['Distance Totale (km)'] = stats_display['Distance Totale (km)'].round(1)
        
        def style_rows(row): return ['background-color: #fef9c3; color: #1e293b; font-weight: 500;'] * len(row) if 'Femme' in str(row['Sexe']) else [''] * len(row)
        st.dataframe(stats_display.style.apply(style_rows, axis=1).format({'Distance Totale (km)': '{:.1f} km'}), use_container_width=True, hide_index=True)

# --- TAB 6 : STATISTIQUES GLOBALES ---
with tab_stats_glob:
    st.subheader(f"📊 Statistiques Récapitulatives ({annees_str})")
    
    if df_courses_a_date.empty:
        st.info("Aucun événement couru avec des inscrits à ce jour pour l'année sélectionnée.")
    else:
        col_s_left, col_s_right = st.columns([1, 1])
        
        with col_s_left:
            col_m_title, col_m_metric = st.columns([2, 1])
            counts_by_month = []
            for m_num in range(1, 13):
                nb_m = len(df_courses_a_date[df_courses_a_date['Date_dt'].dt.month == m_num])
                counts_by_month.append({"Mois": MOIS_FR[m_num], "Nombre de manifestations": nb_m})
                
            df_month_stats = pd.DataFrame(counts_by_month)
            total_manifestations = df_month_stats["Nombre de manifestations"].sum()
            
            with col_m_title: st.write("#### 📅 Manifestations par mois")
            with col_m_metric: st.metric("Total événements", total_manifestations)
            
            df_month_stats_total = pd.concat([df_month_stats, pd.DataFrame([{"Mois": "TOTAL", "Nombre de manifestations": total_manifestations}])], ignore_index=True)
            st.dataframe(df_month_stats_total, hide_index=True, use_container_width=True)
            st.write("")
            
            df_depts = df_courses_a_date['Dept_Code'].dropna().value_counts().reset_index()
            df_depts.columns = ['Code_Dept', 'Nombre de courses']
            df_depts['Lieu des courses'] = df_depts['Code_Dept'].apply(lambda code: f"{code} - {DEPTS_NAMES.get(code, 'Inconnu')}")
            df_depts = df_depts.sort_values(by='Code_Dept')[['Lieu des courses', 'Nombre de courses']]
            
            col_d_title, col_d_metric = st.columns([2, 1])
            with col_d_title: st.write("#### 🗺️ Départements courus")
            with col_d_metric: st.metric("Départements distincts", len(df_depts))
            st.dataframe(df_depts, hide_index=True, use_container_width=True)

        with col_s_right:
            st.write("#### 👥 Participants par manifestation")
            st.metric("Total de participants à date", len(df_participations_a_date))
            
            if df_participations_a_date.empty:
                st.info("Aucune participation enregistrée à date.")
            else:
                # Groupby Name AND Date to avoid merging homonymous races
                df_part_course = df_participations_a_date.groupby(["Nom_Course", "Date"]).size().reset_index(name="Nombre de participants")
                # Create the Label_Unique for display
                df_part_course['Annee'] = pd.to_datetime(df_part_course['Date'], format='%d/%m/%Y', errors='coerce').dt.year
                df_part_course['Manifestation'] = df_part_course.apply(lambda row: f"{row['Nom_Course']} ({int(row['Annee']) if pd.notna(row['Annee']) else 'Inconnue'})", axis=1)
                
                df_part_course = df_part_course.sort_values(by="Nombre de participants", ascending=False)
                df_part_display = df_part_course[['Manifestation', 'Nombre de participants']]
                st.dataframe(df_part_display, hide_index=True, use_container_width=True)
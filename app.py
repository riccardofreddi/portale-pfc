import streamlit as st
import os
import json
import shutil
from datetime import datetime
import hashlib

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Portale studiocommercialepfc", layout="wide", page_icon="🏢")

# --- FUNZIONI DI SICUREZZA ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verifica_password(password_inserita, password_db):
    return hash_password(password_inserita) == password_db

# --- DATABASE E GESTIONE STATO ---
DB_FILE = "utenti_db.json"
DOCS_DIR = "documenti"
if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)

def carica_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"credentials": {"usernames": {"admin": {"name": "Titolare", "password": hash_password('admin')}}}}

def salva_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f, indent=4)
    st.session_state['db'] = db # Aggiorna lo stato globale immediatamente

# --- CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    [data-testid="stSidebar"] { background-color: #1e1e2f !important; color: white !important; }
    .status-badge { padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.2); background-color: #ff4b4b; color: white; }
    .stButton > button { border-radius: 5px; font-weight: bold; width: 100%; transition: 0.3s; }
    button[data-testid="baseButton-primary"] { background-color: #28a745 !important; color: white !important; border: none !important; }
    .stSidebar .stButton > button { background-color: #ff4b4b !important; color: white !important; border: 1px solid white; }
    .folder-detail { font-size: 0.9em; color: #555; padding-left: 10px; font-weight: bold; margin-top: 5px; }
    .file-list { font-size: 0.85em; color: #777; padding-left: 25px; font-style: italic; }
    </style>
""", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE STATO ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'confirm_delete_user' not in st.session_state: st.session_state['confirm_delete_user'] = None
if 'db' not in st.session_state: st.session_state['db'] = carica_db()
if 'msg_success' not in st.session_state: st.session_state['msg_success'] = None

db = st.session_state['db']

# --- LOGIN ---
if not st.session_state['logged_in']:
    st.title("🏢 Accesso Portale PFC")
    with st.form("login_form"):
        u = st.text_input("Username").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("ACCEDI"):
            users = db['credentials']['usernames']
            if u in users and verifica_password(p, users[u]['password']):
                st.session_state.update({'logged_in': True, 'username': u, 'name': users[u]['name']})
                st.rerun()
            else: st.error("Credenziali errate")

# --- AREA RISERVATA ---
else:
    with st.sidebar:
        if st.session_state['username'] == "admin":
            st.markdown('<div class="status-badge">🛡️ AMMINISTRATORE</div>', unsafe_allow_html=True)
        st.write(f"Benvenuto, **{st.session_state['name']}**")
        if st.button("ESCI"):
            st.session_state.clear()
            st.rerun()

    if st.session_state['username'] == "admin":
        st.title("🖥️ Console di Controllo")
        
        # TAB PRINCIPALI
        tab1, tab2, tab3 = st.tabs(["📤 Invio Documenti", "👤 Gestione Clienti", "📊 Resoconto File"])

        with tab1:
            clienti_dict = {u: d for u, d in db['credentials']['usernames'].items() if u != 'admin'}
            st.subheader("Caricamento File")
            if not clienti_dict:
                st.info("Nessun cliente censito.")
            else:
                with st.form(key="form_invio", clear_on_submit=True):
                    scelta = st.selectbox("Seleziona destinatario", list(clienti_dict.keys()), format_func=lambda x: clienti_dict[x]['name'])
                    c1, c2 = st.columns(2)
                    anno = c1.text_input("Anno", value=str(datetime.now().year))
                    cartella = c2.text_input("Cartella (es. DICHIARAZIONI, FATTURE)")
                    file = st.file_uploader("Scegli file")
                    if st.form_submit_button("INVIA DOCUMENTO", type="primary"):
                        if cartella and file:
                            path = os.path.join(DOCS_DIR, scelta, anno, cartella)
                            os.makedirs(path, exist_ok=True)
                            with open(os.path.join(path, file.name), "wb") as f:
                                f.write(file.getbuffer())
                            st.session_state['msg_success'] = f"✅ File '{file.name}' inviato correttamente!"
                            st.rerun()
                        else: st.warning("⚠️ Compila tutti i campi.")
                
                # Messaggio di successo sotto il form invio
                if st.session_state['msg_success'] and "File" in st.session_state['msg_success']:
                    st.success(st.session_state['msg_success'])
                    st.session_state['msg_success'] = None

        with tab2:
            st.subheader("Gestione Anagrafica")
            col_add, col_del = st.columns(2)
            
            with col_add:
                st.markdown("**Aggiungi nuovo cliente**")
                with st.form("form_aggiunta", clear_on_submit=True):
                    n = st.text_input("Ragione Sociale")
                    u_n = st.text_input("User")
                    p_w = st.text_input("Password", type="password")
                    if st.form_submit_button("REGISTRA CLIENTE"):
                        if n and u_n and p_w:
                            db['credentials']['usernames'][u_n.lower()] = {"name": n, "password": hash_password(p_w)}
                            salva_db(db)
                            st.session_state['msg_success'] = f"✅ Cliente '{n}' registrato con successo!"
                            st.rerun()
                
                # Messaggio di successo sotto il pulsante registra
                if st.session_state['msg_success'] and "registrato" in st.session_state['msg_success']:
                    st.success(st.session_state['msg_success'])
                    st.session_state['msg_success'] = None
            
            with col_del:
                st.markdown("**Elimina cliente**")
                target = st.selectbox("Seleziona cliente", ["Seleziona..."] + list(clienti_dict.keys()), format_func=lambda x: clienti_dict[x]['name'] if x != "Seleziona..." else x)
                if target != "Seleziona...":
                    if st.button("ELIMINA CLIENTE"):
                        st.session_state.confirm_delete_user = target
                    if st.session_state.confirm_delete_user == target:
                        st.warning(f"Eliminare definitivamente {clienti_dict[target]['name']}?")
                        if st.button("SÌ, CONFERMO"):
                            user_path = os.path.join(DOCS_DIR, target)
                            if os.path.exists(user_path): shutil.rmtree(user_path)
                            del db['credentials']['usernames'][target]
                            salva_db(db)
                            st.session_state.confirm_delete_user = None
                            st.session_state['msg_success'] = "🗑️ Cliente eliminato correttamente."
                            st.rerun()
                
                # Messaggio sotto eliminazione
                if st.session_state['msg_success'] and "eliminato" in st.session_state['msg_success']:
                    st.info(st.session_state['msg_success'])
                    st.session_state['msg_success'] = None
            
            st.markdown("---")
            st.markdown("### 📋 Lista Clienti Attivi")
            for uid, info in clienti_dict.items():
                st.text(f"• {info['name']} (Username: {uid})")

        with tab3:
            st.subheader("📊 Archivio")
            for u_id, info in clienti_dict.items():
                with st.expander(f"👤 {info['name'].upper()}"):
                    u_path = os.path.join(DOCS_DIR, u_id)
                    if os.path.exists(u_path) and os.listdir(u_path):
                        for a in sorted(os.listdir(u_path), reverse=True):
                            st.markdown(f"**Anno {a}**")
                            a_path = os.path.join(u_path, a)
                            for fld in sorted(os.listdir(a_path)):
                                f_path = os.path.join(a_path, fld)
                                files = os.listdir(f_path)
                                st.markdown(f'<div class="folder-detail">📂 {fld.upper()}:</div>', unsafe_allow_html=True)
                                for fn in files:
                                    st.markdown(f'<div class="file-list">📄 {fn}</div>', unsafe_allow_html=True)
                    else: st.write("Archivio vuoto.")

    else: # LATO CLIENTE
        st.title(f"📄 Archivio: {st.session_state['name']}")
        u_path = os.path.join(DOCS_DIR, st.session_state["username"])
        if os.path.exists(u_path) and os.listdir(u_path):
            for anno in sorted(os.listdir(u_path), reverse=True):
                st.markdown(f"#### 📅 {anno}")
                p_anno = os.path.join(u_path, anno)
                for fld in sorted(os.listdir(p_anno)):
                    with st.expander(f"📁 {fld.upper()}", expanded=True):
                        p_f = os.path.join(p_anno, fld)
                        for file in sorted(os.listdir(p_f)):
                            with open(os.path.join(p_f, file), "rb") as d:
                                st.download_button(label=f"📥 Scarica {file}", data=d, file_name=file, key=f"dl_{anno}_{fld}_{file}", use_container_width=True)
        else: st.info("Nessun documento presente.")
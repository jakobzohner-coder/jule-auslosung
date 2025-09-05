import streamlit as st
import pandas as pd
import random
from collections import defaultdict
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import tempfile
from PIL import Image as PILImage

st.set_page_config(page_title="Jule Turnier Planer", layout="wide")
st.title("🎲 Jule Turnier Auslosung")

# --- Datei Upload ---
uploaded_file = st.file_uploader("Teilnehmerliste hochladen (CSV)", type="csv")

# Lokale Bilddatei für PDF (hochauflösend)
logo_path = st.file_uploader("Logo für PDF hochladen (PNG/JPG)", type=["png", "jpg", "jpeg"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if not {"Name", "Team"}.issubset(df.columns):
        st.error("CSV muss die Spalten 'Name' und 'Team' enthalten!")
    else:
        st.success(f"{len(df)} Teilnehmer erfolgreich geladen.")
        teilnehmer = df.to_dict(orient="records")

        def create_rounds(players, num_rounds=3, max_attempts=50):
            rounds = []
            opponents = defaultdict(set)

            for r in range(num_rounds):
                success = False
                attempt = 0
                while not success and attempt < max_attempts:
                    attempt += 1
                    available = players.copy()
                    random.shuffle(available)
                    tische = []
                    valid = True
                    while len(available) > 0:
                        if len(available) >= 4:
                            group = available[:4]
                            del available[:4]
                        elif len(available) == 3:
                            group = available[:3]
                            del available[:3]
                        else:
                            if tische and len(tische[-1]) == 4:
                                group = available[:1] + tische[-1][:3]
                                available = []
                                tische[-1] = tische[-1][3:]
                            else:
                                group = available
                                available = []
                        teams = [p["Team"] for p in group]
                        if len(set(teams)) < len(teams):
                            valid = False
                            break
                        for i in range(len(group)):
                            for j in range(i+1, len(group)):
                                if group[j]["Name"] in opponents[group[i]["Name"]]:
                                    valid = False
                                    break
                            if not valid:
                                break
                        if not valid:
                            break
                        tische.append(group)
                    if valid:
                        for group in tische:
                            for i in range(len(group)):
                                for j in range(i+1, len(group)):
                                    opponents[group[i]["Name"]].add(group[j]["Name"])
                                    opponents[group[j]["Name"]].add(group[i]["Name"])
                        rounds.append(tische)
                        success = True
                if not success:
                    available = players.copy()
                    random.shuffle(available)
                    tische = []
                    while len(available) > 0:
                        if len(available) >= 4:
                            group = available[:4]
                            del available[:4]
                        else:
                            group = available[:3]
                            del available[:3]
                        tische.append(group)
                    rounds.append(tische)
            return rounds

        def export_round_pdf(round_index, tische, logo_path):
            styles = getSampleStyleSheet()
            tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=f"_runde{round_index}.pdf")
            doc = SimpleDocTemplate(tmpfile.name, pagesize=A4)
            elements = []

            if logo_path is not None:
                pil_image = PILImage.open(logo_path)
                img_width, img_height = pil_image.size
                elements.append(Image(logo_path, width=img_width, height=img_height))
                elements.append(Spacer(1, 12))

            elements.append(Paragraph(f"Jule Turnier - Runde {round_index}", styles['Title']))
            elements.append(Spacer(1, 12))

            for i, group in enumerate(tische):
                data = [["Name", "Team"]] + [[p["Name"], p["Team"]] for p in group]
                table = Table(data, hAlign='LEFT')
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.grey),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN',(0,0),(-1,-1),'CENTER'),
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                ]))
                elements.append(KeepTogether([Paragraph(f"Tisch {i+1}", styles['Heading3']), table, Spacer(1,12)]))

            doc.build(elements)
            return tmpfile.name

        if st.button("Turnier auslosen"):
            st.session_state["result"] = create_rounds(teilnehmer)

        if "result" in st.session_state:
            result = st.session_state["result"]

            for r, tische in enumerate(result, start=1):
                st.subheader(f"Runde {r}")
                cols = st.columns(len(tische))
                for i, group in enumerate(tische):
                    with cols[i]:
                        st.markdown(f"**Tisch {i+1}**")
                        table = pd.DataFrame(group)
                        st.table(table)

            for r, tische in enumerate(result, start=1):
                pdf_path = export_round_pdf(r, tische, logo_path)
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label=f"📥 Runde {r} als PDF herunterladen",
                        data=pdf_file,
                        file_name=f"jule_turnier_runde{r}.pdf",
                        mime="application/pdf"
                    )

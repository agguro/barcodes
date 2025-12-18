#!/usr/bin/env python3
import sqlite3
import pandas as pd
import os
from barcode import Code128
from barcode.writer import ImageWriter

# ReportLab imports voor de PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

# --- CONFIGURATIE ---
DB_FILE = "inventaris.sqlite"
PDF_FILENAME = "inventaris_barcodes.pdf"
TEMP_IMG_DIR = "temp_barcodes"  # Tijdelijke map voor plaatjes

def get_data_from_db():
    """Haalt serial en device_name op uit de database."""
    if not os.path.exists(DB_FILE):
        print(f"❌ Database '{DB_FILE}' niet gevonden.")
        return pd.DataFrame()

    conn = sqlite3.connect(DB_FILE)
    # We selecteren serial én device_name
    query = "SELECT serial, device_name FROM laptops WHERE serial IS NOT NULL AND serial != ''"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def generate_temp_barcode(serial, outdir):
    """Genereert een tijdelijk PNG bestand voor de PDF."""
    # Bestandsnaam veilig maken
    safe_sn = "".join([c if c.isalnum() else '_' for c in str(serial)])
    file_path = os.path.join(outdir, safe_sn)
    
    # Barcode opties (tekst onder barcode)
    options = {
        'write_text': True,
        'font_size': 8,
        'module_height': 10.0, 
        'quiet_zone': 1.0,
    }
    
    # ImageWriter voegt zelf .png toe, dus file_path zonder extensie
    writer = ImageWriter()
    code = Code128(str(serial), writer=writer)
    saved_path = code.save(file_path, options=options)
    return saved_path

def create_pdf(df):
    print(f"[INFO] PDF genereren: {PDF_FILENAME}...")
    
    # 1. Maak document setup (A4)
    doc = SimpleDocTemplate(PDF_FILENAME, pagesize=A4,
                            rightMargin=10*mm, leftMargin=10*mm,
                            topMargin=10*mm, bottomMargin=10*mm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom stijl voor de device_name tekst (gecentreerd)
    device_style = ParagraphStyle(
        'DeviceName',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1, # 0=Left, 1=Center, 2=Right
        spaceBefore=2,
        spaceAfter=10
    )

    # 2. Maak de tijdelijke map aan
    os.makedirs(TEMP_IMG_DIR, exist_ok=True)

    # 3. Data voorbereiden voor de tabel
    # We willen een structuur: [[Cel1, Cel2], [Cel3, Cel4], ...]
    table_data = []
    row = []

    for index, item in df.iterrows():
        serial = item['serial']
        d_name = item['device_name'] if item['device_name'] else "Onbekend device"

        # A. Genereer barcode plaatje
        img_path = generate_temp_barcode(serial, TEMP_IMG_DIR)
        
        # B. Maak ReportLab elementen
        # Afbeelding: width aanpassen aan kolom, aspect ratio behouden
        img = Image(img_path)
        img.drawHeight = 25*mm # Hoogte forceren
        img.drawWidth = 50*mm  # Breedte forceren (of weglaten voor auto)
        
        # Tekst: Device naam
        p_text = Paragraph(f"<b>{d_name}</b>", device_style)

        # C. Stop ze in een lijstje (dit is 1 celinhoud)
        cell_content = [img, p_text]
        
        row.append(cell_content)

        # Als de rij 2 items heeft, voeg toe aan tabel en begin nieuwe rij
        if len(row) == 2:
            table_data.append(row)
            row = []

    # Als er nog 1 item over is (oneven aantal), voeg die toe als laatste rij
    if row:
        row.append([]) # Lege cel toevoegen voor de rechterkolom
        table_data.append(row)

    # 4. Tabel opmaken
    # colWidths verdeelt de pagina (A4 breedte is ong 210mm, min marges = ~190mm)
    col_width = 90*mm
    t = Table(table_data, colWidths=[col_width, col_width])

    # Styling van de tabel (lijnen, uitlijning)
    t.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),    # Alles centreren
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),   # Verticaal in het midden
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey), # Rasterlijnen (optioneel)
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))

    elements.append(t)

    # 5. PDF Bouwen
    try:
        doc.build(elements)
        print(f"✅ Succes! PDF staat in: {os.path.abspath(PDF_FILENAME)}")
    except Exception as e:
        print(f"❌ Fout bij maken PDF: {e}")

    # (Optioneel) Opruimen van tijdelijke plaatjes
    # import shutil
    # shutil.rmtree(TEMP_IMG_DIR)

def main():
    df = get_data_from_db()
    print(f"Records gevonden: {len(df)}")
    
    if not df.empty:
        create_pdf(df)
    else:
        print("Geen data om te verwerken.")

if __name__ == "__main__":
    main()

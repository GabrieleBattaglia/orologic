import os
import io
import datetime
import re
import chess
import chess.svg
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Flowable
from reportlab.lib.styles import getSampleStyleSheet
from GBUtils import dgt, Acusticator
from .. import config
from .. import storage
from ..config import _

class DrawingFlowable(Flowable):
    def __init__(self, drawing, width, height, scale=1.0):
        Flowable.__init__(self)
        self.drawing = drawing
        self.orig_width = width
        self.orig_height = height
        self.scale = scale
        self.width = width * scale
        self.height = height * scale

    def draw(self):
        available_width = self._frame.width if hasattr(self, '_frame') else self.width
        offset = (available_width - self.width) / 2 if available_width > self.width else 0
        
        self.canv.saveState()
        self.canv.translate(offset, 0)
        self.canv.scale(self.scale, self.scale)
        renderPDF.draw(self.drawing, self.canv, 0, 0)
        self.canv.restoreState()

def rgb_from_percent(r_perc, g_perc, b_perc):
    """Converte percentuali RGB (0-100) in stringa hex #RRGGBB."""
    r = int(max(0, min(100, r_perc)) * 2.55)
    g = int(max(0, min(100, g_perc)) * 2.55)
    b = int(max(0, min(100, b_perc)) * 2.55)
    return "#{:02x}{:02x}{:02x}".format(r, g, b)

def get_image_settings():
    db = storage.LoadDB()
    # Se le impostazioni non esistono nel DB, usiamo questi nuovi valori di default
    settings = db.get("image_settings", {
        "square_light": [94, 85, 71],        # Case chiare (crema/beige)
        "square_dark": [36, 25, 20],         # Case scure (marrone scuro)
        "pieces_white": [96, 96, 94],        # Pezzi bianchi (bianco sporco)
        "pieces_white_stroke": [0, 21, 14],  # Bordo pezzi bianchi (verde scuro)
        "pieces_black": [3, 3, 3],           # Pezzi neri (grigio scurissimo/nero)
        "pieces_black_stroke": [100, 100, 90],# Bordo pezzi neri (giallino/avorio)
        "margin": [12, 12, 20],              # Sfondo coordinate (blu notte)
        "coord": [98, 98, 34],               # Testo coordinate (giallo)
        "inner_border": [100, 100, 0],       # Bordo interno scacchiera (giallo acceso)
        "outer_border": [0, 0, 6],           # Bordo esterno (blu molto scuro)
        "last_move_light": [50, 90, 15],     # Ultima mossa su casa chiara (verde chiaro)
        "last_move_dark": [70, 40, 40],      # Ultima mossa su casa scura (rosso/mattone)
        "check_color": [100, 0, 0],          # Colore scacco (rosso puro)
        "piece_stroke_width": 1.4,           # Spessore bordo bilanciato (float)
        "shadow": True,                      # Ombreggiatura attiva
        "size": 600                          # Dimensione standard in pixel
    })
    return settings
def save_image_settings(settings):
    db = storage.LoadDB()
    db["image_settings"] = settings
    storage.SaveDB(db)

def ask_rgb(label, defaults):
    print(_("\nImpostazione colore per: {l}").format(l=label))
    r = dgt(prompt=_("  Rosso % [{d}]: ").format(d=defaults[0]), kind="i", imin=0, imax=100, default=defaults[0])
    Acusticator(["c4", 0.05, 0, config.VOLUME])
    g = dgt(prompt=_("  Verde % [{d}]: ").format(d=defaults[1]), kind="i", imin=0, imax=100, default=defaults[1])
    Acusticator(["e4", 0.05, 0, config.VOLUME])
    b = dgt(prompt=_("  Blu % [{d}]: ").format(d=defaults[2]), kind="i", imin=0, imax=100, default=defaults[2])
    Acusticator(["g4", 0.05, 0, config.VOLUME])
    return [r, g, b]

def image_settings_menu():
    settings = get_image_settings()
    Acusticator(["c5", 0.1, 0, config.VOLUME])
    
    settings["square_light"] = ask_rgb(_("Case Chiare"), settings["square_light"])
    settings["square_dark"] = ask_rgb(_("Case Scure"), settings["square_dark"])
    
    settings["pieces_white"] = ask_rgb(_("Pezzi Bianchi (Riempimento)"), settings["pieces_white"])
    settings["pieces_white_stroke"] = ask_rgb(_("Pezzi Bianchi (Bordi/Rifiniture)"), settings.get("pieces_white_stroke", [0, 0, 0]))
    
    settings["pieces_black"] = ask_rgb(_("Pezzi Neri (Riempimento)"), settings["pieces_black"])
    settings["pieces_black_stroke"] = ask_rgb(_("Pezzi Neri (Bordi/Rifiniture)"), settings.get("pieces_black_stroke", [100, 100, 100]))
    
    settings["margin"] = ask_rgb(_("Sfondo Margine (Coordinate)"), settings.get("margin", [20, 20, 20]))
    settings["coord"] = ask_rgb(_("Testo Coordinate"), settings.get("coord", [90, 90, 90]))
    settings["inner_border"] = ask_rgb(_("Bordo Interno"), settings.get("inner_border", [100, 100, 100]))
    settings["outer_border"] = ask_rgb(_("Bordo Esterno"), settings.get("outer_border", [0, 0, 0]))
    
    settings["last_move_light"] = ask_rgb(_("Evidenzia Ultima Mossa (Casa Chiara)"), settings.get("last_move_light", [100, 100, 0]))
    settings["last_move_dark"] = ask_rgb(_("Evidenzia Ultima Mossa (Casa Scura)"), settings.get("last_move_dark", [80, 80, 0]))
    settings["check_color"] = ask_rgb(_("Colore Scacco Re"), settings.get("check_color", [100, 0, 0]))
    
    settings["piece_stroke_width"] = dgt(prompt=_("\nSpessore bordo pezzi (pixel) [{d}]: ").format(d=settings.get("piece_stroke_width", 1)), kind="f", fmin=0.0, fmax=5.0, default=settings.get("piece_stroke_width", 1.3))
    
    shadow_choice = dgt(prompt=_("Attivare ombreggiatura pezzi? (S/N) [S]: "), kind="s", default="S").strip().upper()
    settings["shadow"] = (shadow_choice == "S")
    
    settings["size"] = dgt(prompt=_("\nDimensione immagine in pixel [{d}]: ").format(d=settings["size"]), kind="i", imin=100, imax=1200, default=settings["size"])
    Acusticator(["c6", 0.1, 0, config.VOLUME])
    
    save_image_settings(settings)
    print(_("\nImpostazioni immagine salvate correttamente."))
    Acusticator(["c5", 0.1, 0, config.VOLUME, "e5", 0.1, 0, config.VOLUME, "g5", 0.2, 0, config.VOLUME], kind=1)

def export_board_pdf(board, node=None):
    settings = get_image_settings()
    now = datetime.datetime.now()
    
    Acusticator(["g5", 0.05, 0, config.VOLUME])
    user_filename = dgt(prompt=_("\nInserisci un nome per il file (max 50 car.): "), kind="s", smax=50, default="").strip()
    
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    if not user_filename:
        base_name = board.fen().replace("/", "-")
        filename_pdf = f"board_{base_name}_{timestamp_str}.pdf"
    else:
        clean_user_name = config.sanitize_filename(user_filename)
        filename_pdf = f"{clean_user_name}_{timestamp_str}.pdf"

    Acusticator(["a5", 0.05, 0, config.VOLUME])
    user_comment = dgt(prompt=_("\nInserisci un commento per il PDF (max 1500 car.): "), kind="s", smax=1500, default="").strip()
    
    footer_text = _("Generata con Orologic v.{v}, {a}, il {d}").format(
        v=config.VERSION, a=config.version.PROGRAMMER, d=now.strftime('%d/%m/%Y %H:%M:%S')
    )
    
    img_dir = config.percorso_salvataggio("images")
    if not os.path.exists(img_dir): 
        os.makedirs(img_dir, exist_ok=True)
    full_path = os.path.join(img_dir, filename_pdf)
    
    # Preleviamo tutti i colori
    sl = rgb_from_percent(*settings["square_light"])
    sd = rgb_from_percent(*settings["square_dark"])
    
    pw = rgb_from_percent(*settings["pieces_white"])
    pws = rgb_from_percent(*settings.get("pieces_white_stroke", [0, 0, 0])) # Bordo bianco
    
    pb = rgb_from_percent(*settings["pieces_black"])
    pbs = rgb_from_percent(*settings.get("pieces_black_stroke", [100, 100, 100])) # Bordo nero
    
    mrg = rgb_from_percent(*settings["margin"])
    crd = rgb_from_percent(*settings["coord"])
    ib = rgb_from_percent(*settings["inner_border"])
    ob = rgb_from_percent(*settings["outer_border"])
    lml = rgb_from_percent(*settings["last_move_light"])
    lmd = rgb_from_percent(*settings["last_move_dark"])
    chk = rgb_from_percent(*settings["check_color"])
    psw = settings.get("piece_stroke_width", 1)
    
    # Ricolorazione Nativa Case
    square_fills = {}
    for sq in chess.SQUARES:
        color = sl if (chess.square_file(sq) + chess.square_rank(sq)) % 2 != 0 else sd
        square_fills[sq] = color

    svg_size = settings["size"]
    
    svg_data = chess.svg.board(
        board=board, size=svg_size, fill=square_fills,
        colors={
            "margin": mrg, "coord": crd, "inner border": ib, "outer border": ob,
            "square light lastmove": lml, "square dark lastmove": lmd, "check": chk
        },
        borders=True, orientation=board.turn
    )
    
    # --- NUOVA MANOVRA CHIRURGICA ---
    # 1. Coordinate
    svg_data = re.sub(r'(<text [^>]*?class="coord"[^>]*?)>', f'\\1 fill="{crd}" style="fill:{crd};">', svg_data)
    
    # 2. Funzioni mirate per colorare i pezzi senza distruggere i dettagli interni
# 2. Funzioni mirate per colorare i pezzi senza distruggere i dettagli interni
    def colorize_white(match):
        """Sostituisce i colori standard del pezzo bianco con quelli scelti dall'utente."""
        text = match.group(0)
        # Sostituisce il corpo (che di default è bianco)
        text = text.replace('fill="#fff"', f'fill="{pw}"').replace('fill="#ffffff"', f'fill="{pw}"')
        # Sostituisce i bordi e dettagli (che di default sono neri)
        text = text.replace('stroke="#000"', f'stroke="{pws}"').replace('stroke="#000000"', f'stroke="{pws}"')
        return text

    def colorize_black(match):
        """Sostituisce i colori standard del pezzo nero con quelli scelti dall'utente."""
        text = match.group(0)
        # Sostituisce il corpo (che di default è nero)
        text = text.replace('fill="#000"', f'fill="{pb}"').replace('fill="#000000"', f'fill="{pb}"')
        
        # IL FIX È QUI: Sostituisce i bordi ESTERNI (che di default sono neri)
        text = text.replace('stroke="#000"', f'stroke="{pbs}"').replace('stroke="#000000"', f'stroke="{pbs}"')
        
        # Sostituisce le rifiniture INTERNE (che di default sono bianche)
        text = text.replace('stroke="#fff"', f'stroke="{pbs}"').replace('stroke="#ffffff"', f'stroke="{pbs}"')
        # Per sicurezza, se ci fossero riempimenti bianchi nei pezzi neri
        text = text.replace('fill="#fff"', f'fill="{pbs}"').replace('fill="#ffffff"', f'fill="{pbs}"')
        
        text = text.replace('currentColor', pb) 
        return text

    # Applichiamo le funzioni SOLO all'interno della definizione dei singoli pezzi (<g id="...">)
    # re.DOTALL permette al "." di matchare anche i ritorni a capo all'interno del blocco del pezzo.
    svg_data = re.sub(r'<g id="white-[^"]+".*?</g>', colorize_white, svg_data, flags=re.DOTALL)
    svg_data = re.sub(r'<g id="black-[^"]+".*?</g>', colorize_black, svg_data, flags=re.DOTALL)

    # 3. Impostazione Spessore Bordo (Stroke Width) sui pezzi
    svg_data = svg_data.replace('stroke-width="1.5"', f'stroke-width="{psw}"')

    # 4. Bordi e Margini 
    svg_data = re.sub(r'class="square light"', f'class="square light" fill="{sl}"', svg_data)
    svg_data = re.sub(r'class="square dark"', f'class="square dark" fill="{sd}"', svg_data)
    svg_data = svg_data.replace('class="margin"', f'class="margin" fill="{mrg}"')
    svg_data = svg_data.replace('class="inner-border"', f'class="inner-border" stroke="{ib}"')
    svg_data = svg_data.replace('class="outer-border"', f'class="outer-border" stroke="{ob}"')

    try:
        drawing = svg2rlg(io.BytesIO(svg_data.encode('utf-8')))
        doc = SimpleDocTemplate(full_path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        available_width = A4[0] - 4*cm
        scale_factor = available_width / svg_size if svg_size > available_width else 1.0
        
        styles = getSampleStyleSheet()
        comment_style = styles["Normal"]
        comment_style.fontSize = 11; comment_style.leading = 14
        footer_style = styles["Italic"]
        footer_style.fontSize = 9; footer_style.alignment = 2
        
        moves_text = ""
        if node is not None:
            line = []
            curr = node
            while curr.parent is not None:
                line.insert(0, curr)
                curr = curr.parent
            if line:
                moves_text = curr.board().variation_san(line)
        if not moves_text:
            moves_text = "FEN: " + board.fen()
        
        story = [DrawingFlowable(drawing, svg_size, svg_size, scale=scale_factor), Spacer(1, 1*cm)]
        if user_comment: story.extend([Paragraph(user_comment, comment_style), Spacer(1, 0.5*cm)])
        story.extend([Paragraph(moves_text, comment_style), Spacer(1, 1*cm)])
        story.append(Paragraph(footer_text, footer_style))
        doc.build(story)
        
        print(_("\nDocumento PDF salvato in: {p}").format(p=full_path))
        Acusticator(["g5", 0.1, 0, config.VOLUME, "b5", 0.1, 0, config.VOLUME, "d6", 0.2, 0, config.VOLUME], kind=1)
    except Exception as e:
        print(_("\nErrore durante la creazione del PDF: {e}").format(e=e))
        Acusticator(["c3", 0.3, 0, config.VOLUME], kind=2)
import re
import chess
from GBUtils import dgt, Acusticator
from .. import config
from ..config import _, L10N

MNDRAWING = {
    "A": _("Aggiungi una forma (freccia o cerchio)"),
    "L": _("Lista tutte le forme di questa mossa"),
    "C": _("Cancella tutte le forme di questa mossa"),
    "P": _("Pulisci tutte le forme dell'intero PGN"),
    ".": _("Torna al menu principale"),
}


def get_drawings_from_node(node):
    if not node or not node.comment:
        return [], []

    cal_match = re.search(r"\[%cal (.*?)\]", node.comment)
    csl_match = re.search(r"\[%csl (.*?)\]", node.comment)

    arrows = cal_match.group(1).split(",") if cal_match else []
    circles = csl_match.group(1).split(",") if csl_match else []

    arrows = [a.strip() for a in arrows if a.strip()]
    circles = [c.strip() for c in circles if c.strip()]

    return arrows, circles


def set_drawings_to_node(node, arrows, circles):
    if not node:
        return

    comment = node.comment if node.comment else ""
    comment = re.sub(r"\[%cal .*?\]", "", comment)
    comment = re.sub(r"\[%csl .*?\]", "", comment)

    tags = []
    if arrows:
        tags.append(f"[%cal {','.join(arrows)}]")
    if circles:
        tags.append(f"[%csl {','.join(circles)}]")

    if tags:
        comment = comment.strip() + " " + "".join(tags)

    node.comment = comment.strip()


def verbalize_square(sq_str):
    if len(sq_str) == 2:
        col = sq_str[0]
        row = sq_str[1]
        col_name = L10N["columns"].get(col, col)
        return f"{col_name} {row}"
    return sq_str


def verbalize_color(color_code):
    colors = {"G": _("verde"), "R": _("rosso"), "B": _("blu"), "Y": _("giallo")}
    return colors.get(color_code, _("sconosciuto"))


def verbalize_drawings(node):
    arrows, circles = get_drawings_from_node(node)
    if not arrows and not circles:
        return ""

    lines = []
    for a in arrows:
        if len(a) >= 5:
            color = a[0]
            sq1 = a[1:3]
            sq2 = a[3:5]
            lines.append(
                _("Freccia da {sq1} ad {sq2} ({col})").format(
                    sq1=verbalize_square(sq1),
                    sq2=verbalize_square(sq2),
                    col=verbalize_color(color),
                )
            )
    for c in circles:
        if len(c) >= 3:
            color = c[0]
            sq1 = c[1:3]
            lines.append(
                _("Cerchio su {sq} ({col})").format(
                    sq=verbalize_square(sq1), col=verbalize_color(color)
                )
            )
    return ", ".join(lines)


def clear_all_drawings(curr_node):
    c = 0
    a, c_sq = get_drawings_from_node(curr_node)
    if a or c_sq:
        set_drawings_to_node(curr_node, [], [])
        c += 1
    for var in curr_node.variations:
        c += clear_all_drawings(var)
    return c


def drawing_menu(game, node):
    is_modified = False
    while True:
        Acusticator(["c5", 0.05, 0, config.VOLUME, "e5", 0.05, 0, config.VOLUME])
        choice = (
            dgt(
                prompt=_(
                    "\nMenu Disegno (.d): [A]ggiungi, [L]ista, [C]ancella da questa mossa, [P]ulisci tutto, [.] Esci: "
                ),
                kind="s",
                default=".",
            )
            .upper()
            .strip()
        )

        if choice == ".":
            break

        elif choice == "A":
            target = (
                dgt(
                    prompt=_(
                        "Inserisci casa (es. e4 per cerchio) o case (es. e4.f6 per freccia): "
                    ),
                    kind="s",
                    default="",
                )
                .lower()
                .strip()
            )
            if not target:
                continue

            parts = target.split(".")
            if len(parts) not in [1, 2]:
                print(_("Formato non valido. Usa e4 oppure e4.f6"))
                continue

            col_choice = (
                dgt(
                    prompt=_("Scegli colore: [V]erde, [R]osso, [B]lu, [G]iallo: "),
                    kind="s",
                    default="V",
                )
                .upper()
                .strip()
            )
            color_map = {"V": "G", "R": "R", "B": "B", "G": "Y"}
            if col_choice not in color_map:
                print(_("Colore non valido. Usato Verde come default."))
                col_choice = "V"

            color_code = color_map[col_choice]

            arrows, circles = get_drawings_from_node(node)

            if len(parts) == 1:
                sq = parts[0]
                try:
                    chess.parse_square(sq)
                except ValueError:
                    print(_("Casa non valida."))
                    continue
                circles.append(f"{color_code}{sq}")
                print(
                    _("Hai impostato un cerchio su {sq} di colore {col}.").format(
                        sq=verbalize_square(sq), col=verbalize_color(color_code)
                    )
                )
            else:
                sq1, sq2 = parts[0], parts[1]
                try:
                    chess.parse_square(sq1)
                    chess.parse_square(sq2)
                except ValueError:
                    print(_("Case non valide."))
                    continue
                arrows.append(f"{color_code}{sq1}{sq2}")
                print(
                    _(
                        "Hai impostato la freccia che parte da {sq1}, punta a {sq2} ed è di colore {col}."
                    ).format(
                        sq1=verbalize_square(sq1),
                        sq2=verbalize_square(sq2),
                        col=verbalize_color(color_code),
                    )
                )

            set_drawings_to_node(node, arrows, circles)
            is_modified = True
            Acusticator(
                ["c5", 0.1, 0, config.VOLUME, "e5", 0.1, 0, config.VOLUME], kind=1
            )

        elif choice == "L":
            arrows, circles = get_drawings_from_node(node)
            if not arrows and not circles:
                print(_("Nessun disegno presente in questa mossa."))
            else:
                lines = verbalize_drawings(node).split(", ")
                for l in lines:
                    print(l)

        elif choice == "C":
            set_drawings_to_node(node, [], [])
            is_modified = True
            print(_("Tutti i disegni di questa mossa sono stati cancellati."))
            Acusticator(["g4", 0.1, 0, config.VOLUME], kind=1)

        elif choice == "P":
            conf = (
                dgt(
                    prompt=_(
                        "Sei sicuro di voler cancellare TUTTI i disegni dell'intero PGN? (S/N): "
                    ),
                    kind="s",
                    default="N",
                )
                .upper()
                .strip()
            )
            if conf == "S":
                count = clear_all_drawings(game)
                is_modified = True
                print(
                    _("Pulizia completata. Cancellati disegni in {n} mosse.").format(
                        n=count
                    )
                )
                Acusticator(
                    ["g4", 0.1, 0, config.VOLUME, "c4", 0.2, 0, config.VOLUME], kind=1
                )

        else:
            print(_("Scelta non valida."))

    return is_modified

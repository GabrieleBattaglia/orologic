# Orologic, sottopacchetto easyfish: statistiche di analisi del motore.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).

from ..config import _


def ShowStats(board, info):
    """Mostra le statistiche dell'analisi."""
    wdl = info.get("wdl")  # Fix: uso get per evitare KeyError
    depth = info.get("depth", 0)
    seldepth = info.get("seldepth", 0)
    nps = info.get("nps", 0)
    pv = info.get("pv", [])
    hashfull = info.get("hashfull", 0)

    debug_string = info.get("string", "N/A")
    tbhits = info.get("tbhits", 0)
    time_val = info.get("time", 0)

    print(
        _("Results: time {time}, Hash {hash}, TB {tb}, Dibug: {dbg}").format(
            time=time_val, hash=hashfull, tb=tbhits, dbg=debug_string
        )
    )

    score_obj = info.get("score")
    score = score_obj.white().score(mate_score=10000) / 100 if score_obj else 0.0

    wdl_str = ""
    if wdl:
        wdl_str = _(", WDL: {w:.1f}%/{d_:.1f}%/{l:.1f}%").format(
            w=wdl[0] / 10, d_=wdl[1] / 10, l=wdl[2] / 10
        )

    best_move = board.san(pv[0]) if pv else "N/A"
    print(
        _(
            "Depth {d}/{sd}, best {best}, score {sc:+.2f}{wdl}, node {n}, NPS {nps}"
        ).format(
            d=depth,
            sd=seldepth,
            best=best_move,
            sc=score,
            wdl=wdl_str,
            n=info.get("nodes", 0),
            nps=nps,
        )
    )

    temp_board = board.copy()
    san_moves = ""
    for move in pv:
        san_move = temp_board.san(move)
        san_moves += san_move + " "
        temp_board.push(move)
    print(_("Line:") + " " + san_moves)

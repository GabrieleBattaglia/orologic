import chess
import chess.engine
from ..config import _

def GetPrincipalVariationSan(board, pv):
    """Restituisce una lista di mosse SAN a partire da una variante principale (PV)."""
    temp_board = board.copy()
    san_moves = []
    for move in pv:
        try:
            san_moves.append(temp_board.san(move))
            temp_board.push(move)
        except: break 
    return san_moves

def FormatAnalysisInfo(board, info):
    """Formatta un singolo dizionario di info analisi in una stringa leggibile."""
    pv = info.get("pv", [])
    if not pv: return None
    
    score_val = info.get('score').pov(board.turn)
    if score_val.is_mate():
        eval_str = "M{m}".format(m=abs(score_val.mate()))
    else:
        eval_str = "{cp:+.2f}".format(cp=score_val.score(mate_score=10000)/100)
        
    wdl = info.get("wdl")
    wdl_str = "WDL: {:.0f}/{:.0f}/{:.0f} ".format(wdl[0]/10, wdl[1]/10, wdl[2]/10) if wdl else ""
    
    line_san = ' '.join(GetPrincipalVariationSan(board, pv))
    return f"CP: {eval_str} {wdl_str}PV: {line_san}"

def RunAnalysis(board, engine, time_limit, multipv_count):
    """
    Esegue un'analisi della posizione corrente.
    Restituisce una lista di stringhe formattate.
    """
    if not engine:
        return [_("Motore non disponibile.")]

    results = []
    try:
        limit = chess.engine.Limit(time=time_limit)
        info_list = engine.analyse(board, limit, multipv=multipv_count)
        
        if isinstance(info_list, dict): info_list = [info_list]
        elif not isinstance(info_list, list): info_list = [info_list]

        for i, info in enumerate(info_list):
            formatted = FormatAnalysisInfo(board, info)
            if formatted:
                results.append(f"{i+1}. {formatted}")
            
    except Exception as e:
        results.append(_("Analisi fallita: {e}").format(e=e))
        
    return results

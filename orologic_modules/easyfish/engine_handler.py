import os
import json
import multiprocessing
import chess.engine
from GBUtils import dgt
from .constants import CONFIG_FILE
from ..config import _

def GetEngineSet():
    """Carica o crea la configurazione del motore scacchistico."""
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "r",encoding="utf-8") as f:
            config = json.load(f)
            path = config.get("path")
            filename = config.get("filename")
            engine_path = os.path.join(path, filename)
            if os.path.isfile(engine_path):
                return engine_path, config
            else:
                print(_("The file specified in the configuration does not exist."))
    
    print(_("Hi, I'm Easyfish. I didn't find your configuration file, so I have some questions for you.\\nReady? Let's begin.\\n"))
    path = dgt(prompt=_("Give me the path location where your UCI engine is saved: "),kind="s",smin=3,smax=256)
    filename = dgt(prompt=_("Now tell me the exact name of the UCI engine's executable (like, stockfish_15_x64_popcnt.exe): "),kind="s",smin=5,smax=64)
    engine_path = os.path.join(path, filename)
    
    if os.path.isfile(engine_path):
        # UCI parameters configuration
        hash_size = dgt(prompt=_("Enter the size of the hash table (min: 1, max: 4096 MB): "),kind="i",imin=1,imax=4096)
        max_cores = multiprocessing.cpu_count()
        num_cores = dgt(prompt=_("Enter the number of cores to use (min: 1, max: {max_cores}): ").format(max_cores=max_cores),kind="i",imin=1,imax=max_cores,default=4)
        skill_level = dgt(prompt=_("Enter the skill level (min: 0, max: 20): "),kind="i",imin=0,imax=20)
        move_overhead = dgt(prompt=_("Enter the move overhead in milliseconds (min: 0, max: 500): "),kind="i",imin=0,imax=500,default=0)
        wdl_switch=True
        
        config = {
            "path": path,
            "filename": filename,
            "hash_size": hash_size,
            "num_cores": num_cores,
            "skill_level": skill_level,
            "move_overhead": move_overhead,
            "wdl_switch": wdl_switch}
            
        with open(CONFIG_FILE, "w",encoding="utf-8") as f:
            json.dump(config, f)
        return engine_path, config
    else:
        print(_("The specified file does not exist. Check the path and executable name."))
        return None, None

def InitEngine():
    """Inizializza il motore scacchistico usando la configurazione."""
    engine_path, config = GetEngineSet()
    if engine_path:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        engine.configure({"Hash": config["hash_size"]})
        engine.configure({"Threads": config["num_cores"]})
        engine.configure({"Skill Level": config["skill_level"]})
        engine.configure({"Move Overhead": config["move_overhead"]})
        engine.configure({"UCI_ShowWDL": config["wdl_switch"]})
        return engine, config
    return None, None

def ShowStats(board, info):
    """Mostra le statistiche dell'analisi."""
    wdl = info.get("wdl") # Fix: uso get per evitare KeyError
    depth = info.get("depth", 0)
    seldepth = info.get("seldepth", 0)
    nps = info.get("nps", 0)
    pv = info.get("pv", [])
    hashfull = info.get("hashfull", 0)
    
    debug_string = info.get("string", "N/A")
    tbhits = info.get("tbhits", 0)
    time_val = info.get("time", 0)
    
    print(_("Results: time {time}, Hash {hash}, TB {tb}, Dibug: {dbg}").format(time=time_val, hash=hashfull, tb=tbhits, dbg=debug_string))
    
    score_obj = info.get('score')
    score = score_obj.white().score(mate_score=10000)/100 if score_obj else 0.0
    
    wdl_str = ""
    if wdl:
        wdl_str = _(", WDL: {w:.1f}%/{d_:.1f}%/{l:.1f}%").format(w=wdl[0]/10, d_=wdl[1]/10, l=wdl[2]/10)
    
    best_move = board.san(pv[0]) if pv else "N/A"
    print(_("Depth {d}/{sd}, best {best}, score {sc:+.2f}{wdl}, node {n}, NPS {nps}").format(d=depth, sd=seldepth, best=best_move, sc=score, wdl=wdl_str, n=info.get('nodes', 0), nps=nps))
    
    temp_board = board.copy()
    san_moves = ''
    for move in pv:
        san_move = temp_board.san(move)
        san_moves += san_move+" "
        temp_board.push(move)
    print(_("Line:")+" "+san_moves)
    return

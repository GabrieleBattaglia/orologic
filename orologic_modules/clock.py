import time
import os
import json
from . import config
from . import storage
from . import board_utils
from GBUtils import dgt, menu, Acusticator, key, polipo

lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

# Volume gestito via config.VOLUME

def generate_time_control_string(clock_config):
	phases = clock_config["phases"]; tc_list = []
	for phase in phases:
		moves = phase["moves"]
		base_time = int(phase["white_time"]); inc = int(phase["white_inc"])
		if moves == 0: tc = "{base}+{inc}".format(base=base_time, inc=inc) if inc > 0 else "{base}".format(base=base_time)
		else: tc = "{moves}/{base}+{inc}".format(moves=moves, base=base_time, inc=inc) if inc > 0 else "{moves}/{base}".format(moves=moves, base=base_time)
		tc_list.append(tc)
	return ", ".join(tc_list)

class ClockConfig:
	def __init__(self,name,same_time,phases,alarms,note):
		self.name=name; self.same_time=same_time; self.phases=phases; self.alarms=alarms; self.note=note
	def to_dict(self): return {"name":self.name,"same_time":self.same_time,"phases":self.phases,"alarms":self.alarms,"note":self.note}
	@staticmethod
	def from_dict(d): return ClockConfig(d["name"],d["same_time"],d["phases"],d.get("alarms",[]),d.get("note",""))

def CreateClock():
	print(_("\nCreazione orologi\n"))
	name=dgt(_("Nome dell'orologio: "),kind="s")
	Acusticator(["f7", .09, 0, config.VOLUME,"d4", .07, 0, config.VOLUME],sync=True)
	db=storage.LoadDB()
	if any(c["name"]==name for c in db.get("clocks", [])):
		print(_("Un orologio con questo nome esiste gia'.")); Acusticator(["a3",1,0,config.VOLUME],kind=2); return
	same=dgt(_("Bianco e Nero partono con lo stesso tempo? (Invio per si', 'n' per no): "),kind="s")
	Acusticator(["f7", .09, 0, config.VOLUME,"d4", .07, 0, config.VOLUME])
	same_time=True if same=="" else False
	phases=[]; phase_count=0
	while phase_count<4:
		phase={}
		if same_time:
			total_seconds=board_utils.ParseTime(_("Tempo (hh:mm:ss) per fase {num}: ").format(num=phase_count+1))
			inc=dgt(_("Incremento in secondi per fase {num}: ").format(num=phase_count+1),kind="i")
			phase["white_time"]=phase["black_time"]=total_seconds; phase["white_inc"]=phase["black_inc"]=inc
		else:
			total_seconds_w=board_utils.ParseTime(_("Tempo per il bianco (hh:mm:ss) fase {num}: ").format(num=phase_count+1))
			inc_w=dgt(_("Incremento per il bianco fase {num}: ").format(num=phase_count+1),kind="i")
			total_seconds_b=board_utils.ParseTime(_("Tempo per il nero (hh:mm:ss) fase {num}: ").format(num=phase_count+1))
			inc_b=dgt(_("Incremento per il nero fase {num}: ").format(num=phase_count+1),kind="i")
			phase["white_time"]=total_seconds_w; phase["black_time"]=total_seconds_b; phase["white_inc"]=inc_w; phase["black_inc"]=inc_b
		Acusticator(["f7", .09, 0, config.VOLUME,"d4", .07, 0, config.VOLUME])
		moves=dgt(_("Numero di mosse per fase {num} (0 per terminare): ").format(num=phase_count+1),kind="i")
		phase["moves"]=moves; phases.append(phase)
		if moves==0: break
		phase_count+=1
	alarms=[]; num_alarms=dgt(_("Numero di allarmi da inserire (max 5, 0 per nessuno): "),kind="i",imax=5,default=0)
	for i in range(num_alarms):
		alarm_input = dgt(_("Inserisci il tempo (mm:ss) per l'allarme {num}: ").format(num=i+1), kind="s")
		alarms.append(board_utils.parse_mmss_to_seconds(alarm_input))
		Acusticator(["f7", .09, 0, config.VOLUME,"d4", .07, 0, config.VOLUME])
	note=dgt(_("Inserisci una nota per l'orologio (opzionale): "),kind="s",default="")
	Acusticator(["f7", .09, 0, config.VOLUME,"d5", .07, 0, config.VOLUME,"p",.1,0,0,"d5", .07, 0, config.VOLUME,"f7", .09, 0, config.VOLUME])
	new_clock=ClockConfig(name,same_time,phases,alarms,note)
	if "clocks" not in db: db["clocks"] = []
	db["clocks"].append(new_clock.to_dict()); storage.SaveDB(db)
	print(_("\nOrologio creato e salvato."))

def ViewClocks():
	print(_("\nVisualizzazione orologi\n"))
	db = storage.LoadDB()
	if not db.get("clocks"): print(_("Nessun orologio salvato.")); return
	choices = {}
	STILE_MENU_NUMERICO = db.get("menu_numerati", False)
	for c in db["clocks"]:
		indicatore = "B=N" if c["same_time"] else "B/N"
		fasi = "".join([" F{n}:{t}+{i}".format(n=j+1, t=board_utils.SecondsToHMS(p["white_time"]), i=p['white_inc']) for j, p in enumerate(c["phases"])])
		details = "{indicator}{phases}. Allarmi: ({num})".format(indicator=indicatore, phases=fasi, num=len(c.get("alarms", [])))
		choices[c["name"]] = details + (f"\n  {c['note']}" if c.get('note') else "")
	menu(choices, show=True, keyslist=True, numbered=STILE_MENU_NUMERICO)
	Acusticator(["f7", .013, 0, config.VOLUME])

def SelectClock(db=None):
	if not db: db = storage.LoadDB()
	if not db.get("clocks"): Acusticator(["c3", 0.72, 0, config.VOLUME], kind=2); print(_("Nessun orologio salvato.")); return None
	choices = {}
	STILE_MENU_NUMERICO = db.get("menu_numerati", False)
	for c in db["clocks"]:
		fasi = "".join([" F{n}:{t}+{i}".format(n=j+1, t=board_utils.SecondsToHMS(p["white_time"]), i=p['white_inc']) for j, p in enumerate(c["phases"])])
		choices[c["name"]] = "{ind}{fasi}".format(ind="B=N" if c["same_time"] else "B/N", fasi=fasi)
	choice = menu(choices, show=True, keyslist=True, numbered=STILE_MENU_NUMERICO)
	if choice:
		Acusticator(["f7", .013, 0, config.VOLUME])
		return next((c for c in db["clocks"] if c["name"] == choice), None)
	return None

def DeleteClock(db):
	print(_("\nEliminazione orologi salvati\n"))
	Acusticator(["b4", .02, 0, config.VOLUME,"d4",.2,0,config.VOLUME]) 
	orologio = SelectClock(db)
	if orologio:
		if key(_("Sei sicuro di voler eliminare {name}? (Invio per si', ESC per no): ").format(name=orologio['name'])).strip() == "":
			db["clocks"] = [c for c in db["clocks"] if c["name"] != orologio["name"]]
			storage.SaveDB(db); Acusticator(["c4", 0.025, 0, config.VOLUME])
			print(_("\nOrologio eliminato."))
	return

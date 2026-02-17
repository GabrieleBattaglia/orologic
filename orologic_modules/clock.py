import time
from . import config
from . import storage
from GBUtils import dgt, menu, Acusticator, key, polipo

lingua_rilevata, _ = polipo(source_language="it", config_path="settings")

try:
    db = storage.LoadDB()
    volume = db.get("volume", 1.0)
except:
    volume = 1.0

def SecondsToHMS(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return "{:02d}:{:02d}:{:02d}".format(h, m, s)

def FormatTime(seconds):
	total=int(seconds)
	h=total//3600
	m=(total%3600)//60
	s=total%60
	parts=[]
	if h:
		parts.append("{num} {label}".format(num=h, label=_('ora') if h==1 else _('ore')))
	if m:
		parts.append("{num} {label}".format(num=m, label=_('minuto') if m==1 else _('minuti')))
	if s:
		parts.append("{num} {label}".format(num=s, label=_('secondo') if s==1 else _('secondi')))
	return ", ".join(parts) if parts else _("0 secondi")

def FormatClock(seconds):
	total = int(seconds)
	hours = total // 3600
	minutes = (total % 3600) // 60
	secs = total % 60
	return "{hours:02d}:{minutes:02d}:{secs:02d}".format(hours=hours, minutes=minutes, secs=secs)

def seconds_to_mmss(seconds):
	m = int(seconds // 60)
	s = int(seconds % 60)
	return _("{minutes:02d} minuti e {seconds:02d} secondi!").format(minutes=m, seconds=s)

def parse_mmss_to_seconds(time_str):
	try:
		minutes, seconds = map(int, time_str.split(":"))
		return minutes * 60 + seconds
	except Exception as e:
		print(_("Formato orario non valido. Atteso mm:ss. Errore:"), e)
		return 0

def ParseTime(prompt):
	t=dgt(prompt,kind="s")
	try:
		h,m,s=map(int,t.split(":"))
		return h*3600+m*60+s
	except Exception as e:
		print(_("Formato orario non valido. Atteso hh:mm:ss. Errore:"),e)
		return 0

def generate_time_control_string(clock_config):
	phases = clock_config["phases"]
	tc_list = []
	for phase in phases:
		moves = phase["moves"]
		if clock_config["same_time"]:
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		else:
			base_time = int(phase["white_time"])
			inc = int(phase["white_inc"])
		if moves == 0:
			# Sudden death: se ├¿ presente l'incremento, lo includiamo
			if inc > 0:
				tc = "{base}+{inc}".format(base=base_time, inc=inc)
			else:
				tc = "{base}".format(base=base_time)
		else:
			# Time control a mosse: includiamo moves, tempo e, se presente, l'incremento
			if inc > 0:
				tc = "{moves}/{base}+{inc}".format(moves=moves, base=base_time, inc=inc)
			else:
				tc = "{moves}/{base}".format(moves=moves, base=base_time)
		tc_list.append(tc)
	return ", ".join(tc_list)

class ClockConfig:
	def __init__(self,name,same_time,phases,alarms,note):
		self.name=name
		self.same_time=same_time
		self.phases=phases
		self.alarms=alarms
		self.note=note
	def to_dict(self):
		return {"name":self.name,"same_time":self.same_time,"phases":self.phases,"alarms":self.alarms,"note":self.note}
	@staticmethod
	def from_dict(d):
		return ClockConfig(d["name"],d["same_time"],d["phases"],d.get("alarms",[]),d.get("note",""))

def CreateClock():
	print(_("\nCreazione orologi\n"))
	name=dgt(_("Nome dell'orologio: "),kind="s")
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume],sync=True)
	db=storage.LoadDB()
	if any(c["name"]==name for c in db.get("clocks", [])):
		print(_("Un orologio con questo nome esiste già."))
		Acusticator(["a3",1,0,volume],kind=2,adsr=[0,0,100,100])
		return
	same=dgt(_("Bianco e Nero partono con lo stesso tempo? (Invio per sì, 'n' per no): "),kind="s",smin=0,smax=1)
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
	same_time=True if same=="" else False
	phases=[]
	phase_count=0
	while phase_count<4:
		phase={}
		if same_time:
			total_seconds=ParseTime(_("Tempo (hh:mm:ss) per fase {num}: ").format(num=phase_count+1))
			inc=dgt(_("Incremento in secondi per fase {num}: ").format(num=phase_count+1),kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			phase["white_time"]=total_seconds
			phase["black_time"]=total_seconds
			phase["white_inc"]=inc
			phase["black_inc"]=inc
		else:
			total_seconds_w=ParseTime(_("Tempo per il bianco (hh:mm:ss) fase {num}: ").format(num=phase_count+1))
			inc_w=dgt(_("Incremento per il bianco fase {num}: ").format(num=phase_count+1),kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			total_seconds_b=ParseTime(_("Tempo per il nero (hh:mm:ss) fase {num}: ").format(num=phase_count+1))
			inc_b=dgt(_("Incremento per il nero fase {num}: ").format(num=phase_count+1),kind="i")
			Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
			phase["white_time"]=total_seconds_w
			phase["black_time"]=total_seconds_b
			phase["white_inc"]=inc_w
			phase["black_inc"]=inc_b
		moves=dgt(_("Numero di mosse per fase {num} (0 per terminare): ").format(num=phase_count+1),kind="i")
		Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
		phase["moves"]=moves
		phases.append(phase)
		if moves==0:
			break
		phase_count+=1
	alarms=[]
	num_alarms=dgt(_("Numero di allarmi da inserire (max 5, 0 per nessuno): "),kind="i",imax=5,default=0)
	Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
	for i in range(num_alarms):
		alarm_input = dgt(_("Inserisci il tempo (mm:ss) per l'allarme {num}: ").format(num=i+1), kind="s")
		Acusticator(["f7", .09, 0, volume,"d4", .07, 0, volume])
		alarm_time = parse_mmss_to_seconds(alarm_input)
		alarms.append(alarm_time)
	note=dgt(_("Inserisci una nota per l'orologio (opzionale): "),kind="s",default="")
	Acusticator(["f7", .09, 0, volume,"d5", .07, 0, volume,"p",.1,0,0,"d5", .07, 0, volume,"f7", .09, 0, volume])
	new_clock=ClockConfig(name,same_time,phases,alarms,note)
	if "clocks" not in db: db["clocks"] = []
	db["clocks"].append(new_clock.to_dict())
	storage.SaveDB(db)
	print(_("\nOrologio creato e salvato."))

def ViewClocks():
	print(_("\nVisualizzazione orologi\n"))
	db = storage.LoadDB()
	if not db.get("clocks"):
		print(_("Nessun orologio salvato."))
		return
	choices = {}
	STILE_MENU_NUMERICO = db.get("menu_numerati", False)
	for c in db["clocks"]:
		indicatore = "B=N" if c["same_time"] else "B/N"
		fasi = ""
		for j, phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str = SecondsToHMS(phase["white_time"])
				fasi += " F{num}:{time}+{inc}".format(num=j+1, time=time_str, inc=phase['white_inc'])
			else:
				time_str_w = SecondsToHMS(phase["white_time"])
				time_str_b = SecondsToHMS(phase["black_time"])
				fasi += " F{num}: Bianco:{time_w}+{inc_w}, Nero:{time_b}+{inc_b}".format(num=j+1, time_w=time_str_w, inc_w=phase['white_inc'], time_b=time_str_b, inc_b=phase['black_inc'])
		num_alarms = len(c.get("alarms", []))
		alarms_str = _(". Allarmi: ({num})").format(num=num_alarms)
		details_line = "{indicator}{phases}{alarms}".format(indicator=indicatore, phases=fasi, alarms=alarms_str)
		note_line = c.get("note", "")
		display_string = ""
		if STILE_MENU_NUMERICO:
			display_string = "'{name}' -- {details}".format(name=c["name"], details=details_line)
		else:
			display_string = details_line
		if note_line:
			display_string += "\n  " + note_line
		choices[c["name"]] = display_string
	choice = menu(choices, show=True, keyslist=True, numbered=STILE_MENU_NUMERICO)
	Acusticator(["f7", .013, 0, volume])
	if choice:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == choice), None)
		if idx is not None:
			# Dettagli visualizzati (opzionale se già nel menu)
			pass
	else:
		print(_("Nessun orologio selezionato o scelta non valida."))

def SelectClock(db):
	if not db: db = storage.LoadDB()
	if not db.get("clocks"):
		Acusticator(["c3", 0.72, 0, volume], kind=2, adsr=[0,0,100,100])
		print(_("Nessun orologio salvato."))
		return None
	print(_("Ci sono {num_clocks} orologi nella collezione.").format(num_clocks=len(db['clocks'])))
	choices = {}
	STILE_MENU_NUMERICO = db.get("menu_numerati", False)
	for c in db["clocks"]:
		indicatore = "B=N" if c["same_time"] else "B/N"
		fasi = ""
		for j, phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str = SecondsToHMS(phase["white_time"])
				fasi += " F{num}:{time}+{inc}".format(num=j+1, time=time_str, inc=phase['white_inc'])
			else:
				time_str_w = SecondsToHMS(phase["white_time"])
				time_str_b = SecondsToHMS(phase["black_time"])
				fasi += " F{num}: Bianco:{time_w}+{inc_w}, Nero:{time_b}+{inc_b}".format(num=j+1, time_w=time_str_w, inc_w=phase['white_inc'], time_b=time_str_b, inc_b=phase['black_inc'])
		num_alarms = len(c.get("alarms", []))
		alarms_str = _(". Allarmi: ({num})").format(num=num_alarms)
		details_line = "{indicator}{phases}{alarms}".format(indicator=indicatore, phases=fasi, alarms=alarms_str)
		note_line = c.get("note", "")
		display_string = ""
		if STILE_MENU_NUMERICO:
			display_string = "'{name}' -- {details}".format(name=c["name"], details=details_line)
		else:
			display_string = details_line
		if note_line:
			display_string += "\n  " + note_line
		choices[c["name"]] = display_string
	choice = menu(choices, show=True, keyslist=True, numbered=STILE_MENU_NUMERICO)
	Acusticator(["f7", .013, 0, volume])
	if choice:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == choice), None)
		if idx is not None:
			return db["clocks"][idx]
	print(_("Nessun orologio selezionato o scelta non valida."))
	return None

def DeleteClock(db):
	print(_("\nEliminazione orologi salvati\n"))
	Acusticator(["b4", .02, 0, volume,"d4",.2,0,volume]) 
	orologio = SelectClock(db)
	if	orologio is not None:
		idx = next((i for i, c in enumerate(db["clocks"]) if c["name"] == orologio["name"]), None)
		if idx is not None:
			clock_name = db["clocks"][idx]["name"]
			prompt_conferma = _("sei sicuro di voler eliminare {nomeorologio}?\nL'azione ├¿ irreversibile. Premi invio per s├¼, qualsiasi altro tasto per no: ").format(nomeorologio=clock_name)
			conferma = key(prompt_conferma).strip()
			if conferma == "":
				del db["clocks"][idx]
				Acusticator(["c4", 0.025, 0, volume])
				storage.SaveDB(db)
				print(_("\nOrologio '{clock_name}' eliminato, ne rimangono {remaining}.").format(clock_name=clock_name, remaining=len(db['clocks'])))
	return
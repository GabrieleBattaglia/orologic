# Data di concepimento: 14/02/2025 by Gabriele Battaglia e ChatGPT o3-mini-high
import sys,os,time,json,threading,datetime,chess,webbrowser,chess.pgn,re
from dateutil.relativedelta import relativedelta
from GBUtils import dgt,menu,Acusticator
#QC
BIRTH_DATE=datetime.datetime(2025,2,14,10,16)
VERSION="2.1.11"
RELEASE_DATE=datetime.datetime(2025,2,15,22,44)
PROGRAMMER="Gabriele Battaglia"
DB_FILE="orologic_db.json"
PIECE_VALUES={'R':5,'r':5,'N':3,'n':3,'B':3,'b':3,'Q':9,'q':9,'P':1,'p':1,'K':0,'k':0}
DOT_COMMANDS={
	".1":"Mostra il tempo rimanente del bianco",
	".2":"Mostra il tempo rimanente del nero",
	".3":"Confronta i tempi rimanenti e indica il vantaggio",
	".p":"Pausa/riavvia il countdown degli orologi",
	".q":"Annulla l'ultima mossa (solo in pausa)",
	".b+":"Aggiunge tempo al bianco (in pausa)",
	".b-":"Sottrae tempo al bianco (in pausa)",
	".n+":"Aggiunge tempo al nero (in pausa)",
	".n-":"Sottrae tempo al nero (in pausa)",
	".s":"Visualizza la scacchiera",
	".bianco":"Assegna vittoria al bianco (1-0)",
	".nero":"Assegna vittoria al nero (0-1)",
	".patta":"Assegna patta (1/2-1/2)",
	".*":"Assegna risultato non definito (*) e conclude la partita",
	".c":"Aggiunge un commento alla mossa corrente",
	".?":"Visualizza l'elenco dei comandi disponibili"}
MENU_CHOICES={
	"?":"Visualizza il menù",
	"c":"Crea un orologio",
	"v":"Vedi gli orologi salvati",
	"d":"Elimina un orologio salvato",
	"e":"Modifica info default per PGN",
	"m":"Visualizza il manuale",
	"g":"Inizia a giocare",
	".":"Esci dall'applicazione"}
FILE_NAMES={0:"ancona",1:"bologna",2:"como",3:"domodossola",4:"empoli",5:"firenze",6:"genova",7:"hotel"}
LETTER_FILE_MAP={chr(ord("a")+i):FILE_NAMES.get(i,chr(ord("a")+i)) for i in range(8)}
PIECE_NAMES={chess.PAWN:"pedone",chess.KNIGHT:"cavallo",chess.BISHOP:"alfiere",chess.ROOK:"torre",chess.QUEEN:"donna",chess.KING:"Re"}
def describe_move(move, board):
	# Gestione arrocco
	if board.is_castling(move):
		if chess.square_file(move.to_square) > chess.square_file(move.from_square):
			return "arrocco corto"
		else:
			return "arrocco lungo"
	# Otteniamo la notazione SAN della mossa
	try:
		san_str = board.san(move)
	except Exception as e:
		san_str = ""
	# Pattern per analizzare la mossa SAN:
	# Gruppi: 1=pezzo (opzionale), 2=disambiguazione (0-2 caratteri), 3='x' (cattura), 4=destinazione, 5=promozione (opzionale), 6=pezzo promozione, 7=check o checkmate (opzionale)
	pattern = re.compile(r'^([RNBQK])?([a-h1-8]{0,2})(x)?([a-h][1-8])(=([RNBQ]))?([+#])?$')
	m = pattern.match(san_str)
	if not m:
		# Fallback in caso di analisi fallita
		return "Mossa non analizzabile"
	piece_letter = m.group(1)
	disamb = m.group(2)
	capture = m.group(3)
	dest = m.group(4)
	promo_letter = m.group(6)
	check_mark = m.group(7)
	# Determiniamo il nome del pezzo che si muove
	if piece_letter:
		mapping = {
			"K": chess.KING,
			"Q": chess.QUEEN,
			"R": chess.ROOK,
			"B": chess.BISHOP,
			"N": chess.KNIGHT
		}
		piece_type = mapping.get(piece_letter.upper(), chess.PAWN)
		piece_name = PIECE_NAMES.get(piece_type, "").lower()
	else:
		piece_name = "pedone"
	# Iniziamo a comporre la descrizione
	descr = ""
	# Per il pedone includiamo l'articolo
	descr += piece_name
	# Se c'è disambiguazione, la aggiungiamo (traducendo lettere in nomi se possibile)
	if disamb:
		parts = []
		for ch in disamb:
			if ch.isalpha():
				parts.append(LETTER_FILE_MAP.get(ch, ch))
			else:
				parts.append(ch)
		descr += " di " + " ".join(parts)
	# Gestione cattura
	if capture:
		descr += " prende"
		# Proviamo a individuare il pezzo catturato
		captured_piece = board.piece_at(move.to_square)
		if not captured_piece and piece_letter=="" and chess.square_file(move.from_square) != chess.square_file(move.to_square):
			# Possibile en passant
			captured_sq = move.to_square + (8 if board.turn==chess.BLACK else -8)
			captured_piece = board.piece_at(captured_sq)
		if captured_piece:
			descr += PIECE_NAMES.get(captured_piece.piece_type, "").lower()
	# Descrizione destinazione
	dest_file = dest[0]
	dest_rank = dest[1]
	dest_name = LETTER_FILE_MAP.get(dest_file, dest_file)
	descr += " in " + dest_name + " " + dest_rank
	# Promozione
	if promo_letter:
		promo_mapping = {
			"Q": chess.QUEEN,
			"R": chess.ROOK,
			"B": chess.BISHOP,
			"N": chess.KNIGHT
		}
		promo_piece_type = promo_mapping.get(promo_letter.upper(), None)
		promo_piece_name = PIECE_NAMES.get(promo_piece_type, "").lower() if promo_piece_type is not None else ""
		descr += " e promuove a " + promo_piece_name
	# Check o scacco matto
	if check_mark:
		if check_mark=="+":
			descr += " scacco"
		elif check_mark=="#":
			descr += " scacco matto!"
	return descr

def CalculateMaterial(board):
	white_value=0
	black_value=0
	for square in chess.SQUARES:
		piece=board.piece_at(square)
		if piece is not None:
			piece_symbol=piece.symbol()
			if piece_symbol.isupper():
				white_value+=PIECE_VALUES[piece_symbol]
			else:
				black_value+=PIECE_VALUES[piece_symbol]
	return white_value,black_value

def normalize_move(m):
	m=m.strip()
	if m.lower().startswith("o-o-o") or m.lower().startswith("0-0-0"):
		suffix=m[len("o-o-o"):]
		return "O-O-O"+suffix
	elif m.lower().startswith("o-o") or m.lower().startswith("0-0"):
		suffix=m[len("o-o"):]
		return "O-O"+suffix
	elif m and m[0] in "rnkq" and m[0].islower():
		return m[0].upper()+m[1:]
	else:
		return m

def load_db():
	if not os.path.exists(DB_FILE):
		return {"clocks":[],"default_pgn":{}}
	with open(DB_FILE,"r") as f:
		return json.load(f)

def save_db(db):
	with open(DB_FILE,"w") as f:
		json.dump(db,f,indent="\t")

def seconds_to_hms(seconds):
	h=int(seconds//3600)
	m=int((seconds%3600)//60)
	s=int(seconds%60)
	return "{:02d}:{:02d}:{:02d}".format(h,m,s)

def format_time(seconds):
	total=int(seconds)
	h=total//3600
	m=(total%3600)//60
	s=total%60
	parts=[]
	if h:
		parts.append(f"{h} {'ora' if h==1 else 'ore'}")
	if m:
		parts.append(f"{m} {'minuto' if m==1 else 'minuti'}")
	if s:
		parts.append(f"{s} {'secondo' if s==1 else 'secondi'}")
	return ", ".join(parts) if parts else "0 secondi"

def parse_time_input(prompt):
	t=dgt(prompt,kind="s")
	try:
		h,m,s=map(int,t.split(":"))
		return h*3600+m*60+s
	except Exception as e:
		print("Formato orario non valido. Atteso hh:mm:ss. Errore:",e)
		return 0

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

def create_clock():
	print("\nCreazione orologi\n")
	name=dgt("Nome dell'orologio: ",kind="s")
	db=load_db()
	if any(c["name"]==name for c in db["clocks"]):
		print("Un orologio con questo nome esiste già.")
		return
	same=dgt("Bianco e Nero partono con lo stesso tempo? (Invio per sì, 'n' per no): ",kind="s",smin=0,smax=1)
	same_time=True if same=="" else False
	phases=[]
	phase_count=0
	while phase_count<4:
		phase={}
		if same_time:
			total_seconds=parse_time_input(f"Tempo (hh:mm:ss) per fase {phase_count+1}: ")
			inc=dgt(f"Incremento in secondi per fase {phase_count+1}: ",kind="i")
			phase["white_time"]=total_seconds
			phase["black_time"]=total_seconds
			phase["white_inc"]=inc
			phase["black_inc"]=inc
		else:
			total_seconds_w=parse_time_input(f"Tempo per il bianco (hh:mm:ss) fase {phase_count+1}: ")
			inc_w=dgt(f"Incremento per il bianco fase {phase_count+1}: ",kind="i")
			total_seconds_b=parse_time_input(f"Tempo per il nero (hh:mm:ss) fase {phase_count+1}: ")
			inc_b=dgt(f"Incremento per il nero fase {phase_count+1}: ",kind="i")
			phase["white_time"]=total_seconds_w
			phase["black_time"]=total_seconds_b
			phase["white_inc"]=inc_w
			phase["black_inc"]=inc_b
		moves=dgt(f"Numero di mosse per fase {phase_count+1} (0 per terminare): ",kind="i")
		phase["moves"]=moves
		phases.append(phase)
		if moves==0:
			break
		phase_count+=1
	alarms=[]
	num_alarms=dgt("Numero di allarmi da inserire (max 5, 0 per nessuno): ",kind="i")
	if num_alarms>5:
		num_alarms=5
	for i in range(num_alarms):
		alarm_time=dgt(f"Inserisci il tempo (in secondi) per l'allarme {i+1}: ",kind="i")
		alarms.append(alarm_time)
	note=dgt("Inserisci una nota per l'orologio (opzionale): ",kind="s",default="")
	new_clock=ClockConfig(name,same_time,phases,alarms,note)
	db["clocks"].append(new_clock.to_dict())
	save_db(db)
	print("Orologio creato e salvato.")

def view_clocks():
	print("\nVisualizzazione orologi\n")
	db=load_db()
	if not db["clocks"]:
		print("Nessun orologio salvato.")
		return
	for idx,c in enumerate(db["clocks"]):
		indicatore="B=N" if c["same_time"] else "B/N"
		fasi=""
		for i,phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str=seconds_to_hms(phase["white_time"])
				fasi+=f" F{i+1}:{time_str}+{phase['white_inc']}"
			else:
				time_str_w=seconds_to_hms(phase["white_time"])
				time_str_b=seconds_to_hms(phase["black_time"])
				fasi+=f" F{i+1}: Bianco:{time_str_w}+{phase['white_inc']}, Nero:{time_str_b}+{phase['black_inc']}"
		print(f"{idx+1}. {c['name']} - {indicatore}{fasi}")
		if c.get("note",""):
			print(f"\tNota: {c['note']}")

def select_clock():
	db=load_db()
	if not db["clocks"]:
		return None
	choices={}
	for i,c in enumerate(db["clocks"]):
		indicatore="B=N" if c["same_time"] else "B/N"
		fasi=""
		for j,phase in enumerate(c["phases"]):
			if c["same_time"]:
				time_str=seconds_to_hms(phase["white_time"])
				fasi+=f" F{j+1}:{time_str}+{phase['white_inc']}"
			else:
				time_str_w=seconds_to_hms(phase["white_time"])
				time_str_b=seconds_to_hms(phase["black_time"])
				fasi+=f" F{j+1}: Bianco:{time_str_w}+{phase['white_inc']}, Nero:{time_str_b}+{phase['black_inc']}"
		choices[str(i+1)]=f"{c['name']} - {indicatore}{fasi}"
	choice=menu(choices,show=True,keyslist=False,p="Scegli dizionario")
	try:
		index=int(choice)-1
	except:
		index=None
	if index is not None and 0<=index<len(db["clocks"]):
		return db["clocks"][index]
	return None

def delete_clock():
	print("\nEliminazione orologio\n")
	clock=select_clock()
	if clock is None:
		print("Scelta non valida o nessun orologio disponibile.")
		return
	db=load_db()
	for i,c in enumerate(db["clocks"]):
		if c["name"]==clock["name"]:
			del db["clocks"][i]
			break
	save_db(db)
	print("Orologio eliminato.")

def edit_default_pgn():
	print("\nModifica info default per PGN\n")
	db=load_db()
	default_pgn=db.get("default_pgn",{})
	default_event=default_pgn.get("Event","Orologic Game")
	event=dgt(f"Evento [{default_pgn.get('Event','Orologic Game')}]: ",kind="s",default=default_pgn.get("Event","Orologic Game"))
	if event.strip()=="":
		event=default_pgn.get("Event","Orologic Game")
	default_site=default_pgn.get("Site","Sede sconosciuta")
	site=dgt(f"Sede [{default_pgn.get('Site','Sede sconosciuta')}]: ",kind="s",default=default_pgn.get("Site","Sede sconosciuta"))
	if site.strip()=="":
		site=default_pgn.get("Site","Sede sconosciuta")
	default_round=default_pgn.get("Round","Round 1")
	round_=dgt(f"Round [{default_pgn.get('Round','Round 1')}]: ",kind="s",default=default_pgn.get("Round","Round 1"))
	if round_.strip()=="":
		round_=default_pgn.get("Round","Round 1")
	db["default_pgn"]={"Event":event,"Site":site,"Round":round_}
	save_db(db)
	print("Informazioni default per il PGN aggiornate.")

class CustomBoard(chess.Board):
	def __str__(self):
		board_str="FEN: "+str(self.fen())+"\n"
		white_material,black_material=CalculateMaterial(self)
		ranks=range(8,0,-1) if self.turn==chess.WHITE else range(1,9)
		files=range(8) if self.turn==chess.WHITE else range(7,-1,-1)
		for rank in ranks:
			board_str+=str(rank)
			for file in files:
				square=chess.square(file,rank-1)
				piece=self.piece_at(square)
				if piece:
					symbol=piece.symbol()
					if piece.color==chess.WHITE:
						board_str+=symbol.upper()
					else:
						board_str+=symbol.lower()
				else:
					board_str+=("-" if (rank+file)%2==0 else "+")
			board_str+="\n"
		board_str+=" abcdefgh" if self.turn==chess.WHITE else " hgfedcba"
		if self.fullmove_number==1 and self.turn==chess.WHITE:
			last_move_info="1.???"
		else:
			move_number=self.fullmove_number-(1 if self.turn==chess.WHITE else 0)
			if self.move_stack:
				temp_board=chess.Board()
				for move in self.move_stack[:-1]:
					temp_board.push(move)
				last_move_san=temp_board.san(self.move_stack[-1])
			else:
				last_move_san="???"
			if self.turn==chess.BLACK:
				last_move_info=f"{move_number}. {last_move_san}"
			else:
				last_move_info=f"{move_number}... {last_move_san}"
		board_str+=f" {last_move_info} Materiale: {white_material}/{black_material}"
		return board_str

class GameState:
	def __init__(self,clock_config):
		self.board=CustomBoard()
		self.clock_config=clock_config
		self.white_remaining=clock_config["phases"][0]["white_time"]
		self.black_remaining=clock_config["phases"][0]["black_time"]
		self.white_phase=0
		self.black_phase=0
		self.white_moves=0
		self.black_moves=0
		# Il turno iniziale resta "white" (bianco a muovere)
		self.active_color="white"
		self.paused=False
		self.game_over=False
		self.move_history=[]
		self.pgn_game=chess.pgn.Game()
		self.pgn_game.headers["Event"]="Orologic Game"
		self.pgn_node=self.pgn_game
	def switch_turn(self):
		if self.active_color=="white":
			self.white_moves+=1
			if self.white_phase<len(self.clock_config["phases"])-1:
				if self.white_moves>=self.clock_config["phases"][self.white_phase]["moves"] and self.clock_config["phases"][self.white_phase]["moves"]!=0:
					self.white_phase+=1
					self.white_remaining=self.clock_config["phases"][self.white_phase]["white_time"]
		else:
			self.black_moves+=1
			if self.black_phase<len(self.clock_config["phases"])-1:
				if self.black_moves>=self.clock_config["phases"][self.black_phase]["moves"] and self.clock_config["phases"][self.black_phase]["moves"]!=0:
					self.black_phase+=1
					self.black_remaining=self.clock_config["phases"][self.black_phase]["black_time"]
		self.active_color="black" if self.active_color=="white" else "white"

def clock_thread(game_state):
	last_time=time.time()
	while not game_state.game_over:
		current_time=time.time()
		elapsed=current_time-last_time
		last_time=current_time
		if not game_state.paused:
			if game_state.active_color=="white":
				game_state.white_remaining-=elapsed
				for alarm in game_state.clock_config.get("alarms",[]):
					if abs(game_state.white_remaining-alarm)<elapsed:
						print(f"Allarme: tempo del bianco raggiunto {alarm}s")
						Acusticator(["c4",0.2,0,1])
			else:
				game_state.black_remaining-=elapsed
				for alarm in game_state.clock_config.get("alarms",[]):
					if abs(game_state.black_remaining-alarm)<elapsed:
						print(f"Allarme: tempo del nero raggiunto {alarm}s")
						Acusticator(["c4",0.2,0,1])
		if game_state.white_remaining<=0 or game_state.black_remaining<=0:
			game_state.game_over=True
		time.sleep(0.1)

def start_game(clock_config):
	print("\nAvvio partita\n")
	# Richiesta dati PGN prima dell'inizio della partita
	white_player=dgt("Nome del bianco: ",kind="s")
	if white_player.strip()=="":
		white_player="Bianco"
	black_player=dgt("Nome del nero: ",kind="s")
	if black_player.strip()=="":
		black_player="Nero"
	white_elo=dgt("Elo del bianco: ",kind="s")
	if white_elo.strip()=="":
		white_elo="?"
	black_elo=dgt("Elo del nero: ",kind="s")
	if black_elo.strip()=="":
		black_elo="?"
	db=load_db()
	default_pgn=db.get("default_pgn",{})
	event=dgt(f"Evento [{default_pgn.get('Event','Orologic Game')}]: ",kind="s",default=default_pgn.get("Event","Orologic Game"))
	if event.strip()=="":
		event="Orologic Game"
	site=dgt(f"Sede [{default_pgn.get('Site','Sede sconosciuta')}]: ",kind="s",default=default_pgn.get("Site","Sede sconosciuta"))
	round_=dgt(f"Round [{default_pgn.get('Round','Round 1')}]: ",kind="s",default=default_pgn.get("Round","Round 1"))
	db["default_pgn"]={"Event":event,"Site":site,"Round":round_}
	save_db(db)
	input("Premi invio per iniziare la partita quando sei pronto...")
	# Creazione dello stato di gioco; il turno iniziale resta "white" (bianco a muovere)
	game_state=GameState(clock_config)
	# Salva i nomi dei giocatori nello stato di gioco
	game_state.white_player=white_player
	game_state.black_player=black_player
	# Imposta le intestazioni PGN
	game_state.pgn_game.headers["White"]=white_player
	game_state.pgn_game.headers["Black"]=black_player
	game_state.pgn_game.headers["WhiteElo"]=white_elo
	game_state.pgn_game.headers["BlackElo"]=black_elo
	game_state.pgn_game.headers["Event"]=event
	game_state.pgn_game.headers["Site"]=site
	game_state.pgn_game.headers["Round"]=round_
	game_state.pgn_game.headers["Annotator"]=f"Orologic {VERSION} - {PROGRAMMER}"
	game_state.pgn_game.headers["Date"]=datetime.datetime.now().strftime("%Y.%m.%d")
	threading.Thread(target=clock_thread,args=(game_state,),daemon=True).start()
	paused_time_start=None
	while not game_state.game_over:
		if not game_state.move_history:
			prompt="0. "
		elif len(game_state.move_history)%2==1:
			full_move=(len(game_state.move_history)+1)//2
			prompt=f"{full_move}. {game_state.move_history[-1]} "
		else:
			full_move=(len(game_state.move_history))//2
			prompt=f"{full_move}... {game_state.move_history[-1]} "
		if game_state.paused:
			prompt="["+prompt.strip()+"] "
		user_input=dgt(prompt,kind="s")
		if user_input.startswith("."):
			u=user_input.strip()
			cmd=u.rstrip(".").lower()
			if cmd==".?":
				menu(DOT_COMMANDS,show_only=True,p="Comandi disponibili:")
			elif cmd==".1":
				Acusticator(['a6', 0.14, -1, .5], kind=1, adsr=[0, 0, 100, 100])
				print("Tempo bianco: "+format_time(game_state.white_remaining))
			elif cmd==".2":
				Acusticator(['a6', 0.14, 1, .5], kind=1, adsr=[0, 0, 100, 100])
				print("Tempo nero: "+format_time(game_state.black_remaining))
			elif cmd==".3":
				Acusticator(['a6', 0.14, 0, .5], kind=1, adsr=[0, 0, 100, 100])
				diff=abs(game_state.white_remaining-game_state.black_remaining)
				adv="bianco" if game_state.white_remaining>game_state.black_remaining else "nero"
				print(f"{adv} in vantaggio di "+format_time(diff))
			elif cmd==".p":
				game_state.paused=not game_state.paused
				if game_state.paused:
					paused_time_start=time.time()
					Acusticator(["c5", 0.1, 1, 0.5, "g4", 0.1, 0.3, 0.5, "e4", 0.1, -0.3, 0.5, "c4", 0.1, -1, 0.5], kind=1, adsr=[2, 8, 80, 10])
				else:
					pause_duration=time.time()-paused_time_start if paused_time_start else 0
					Acusticator(["c4", 0.1, -1, 0.5, "e4", 0.1, -0.3, 0.5, "g4", 0.1, 0.3, 0.5, "c5", 0.1, 1, 0.5], kind=1, adsr=[2, 8, 80, 10])
					print("Pausa durata: "+format_time(pause_duration))
			elif cmd==".q":
				if game_state.paused and game_state.move_history:
					game_state.board.pop()
					game_state.pgn_node=game_state.pgn_node.parent
					last_move=game_state.move_history.pop()
					print("Ultima mossa annullata: "+last_move)
			elif cmd.startswith(".b+") or cmd.startswith(".b-") or cmd.startswith(".n+") or cmd.startswith(".n-"):
				if game_state.paused:
					try:
						adjust=float(cmd[3:])
						if cmd.startswith(".b+"):
							game_state.white_remaining+=adjust
						elif cmd.startswith(".b-"):
							game_state.white_remaining-=adjust
						elif cmd.startswith(".n+"):
							game_state.black_remaining+=adjust
						elif cmd.startswith(".n-"):
							game_state.black_remaining-=adjust
						print("Nuovo tempo bianco: "+format_time(game_state.white_remaining)+", nero: "+format_time(game_state.black_remaining))
					except:
						print("Comando non valido.")
			elif cmd==".s":
				print(game_state.board)
			elif cmd in [".bianco",".nero",".patta",".*"]:
				if cmd==".bianco":
					result="1-0"
				elif cmd==".nero":
					result="0-1"
				elif cmd==".patta":
					result="1/2-1/2"
				else:
					result="*"
				print("Risultato assegnato: "+result)
				game_state.pgn_game.headers["Result"]=result
				game_state.game_over=True
			elif cmd.startswith(".c"):
				comment=cmd[2:].strip()
				if game_state.move_history:
					game_state.pgn_node.comment=comment
					print("Commento registrato per la mossa: "+game_state.move_history[-1])
				else:
					print("Nessuna mossa da commentare.")
			else:
				print("Comando non riconosciuto.")
		else:
			user_input=normalize_move(user_input)
			try:
				move=game_state.board.parse_san(user_input)
				board_copy=game_state.board.copy()
				description=describe_move(move,board_copy)
				Acusticator([1000.0, 0.01, 0, 0.5], kind=1, adsr=[0, 0, 100, 0])
				# Stampa la mossa preceduta dal nome del giocatore in base al turno
				if game_state.active_color=="white":
					print(game_state.white_player+": "+description)
				else:
					print(game_state.black_player+": "+description)
				san_move=game_state.board.san(move)
				game_state.board.push(move)
				game_state.move_history.append(san_move)
				game_state.pgn_node=game_state.pgn_node.add_variation(move)
				if game_state.active_color=="white":
					game_state.white_remaining+=game_state.clock_config["phases"][game_state.white_phase]["white_inc"]
				else:
					game_state.black_remaining+=game_state.clock_config["phases"][game_state.black_phase]["black_inc"]
				game_state.switch_turn()
			except Exception as e:
				print("Mossa illegale: "+str(e))
	print("Partita terminata.")
	pgn_str=str(game_state.pgn_game)
	filename=f"{white_player}-{black_player}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pgn"
	with open(filename,"w") as f:
		f.write(pgn_str)
	print("PGN salvato come "+filename+".")
    
def open_manual():
	print("\nApertura manuale\n")
	readme="README.md"
	if os.path.exists(readme):
		webbrowser.open(readme)
	else:
		print("Il file README.md non esiste.")

def SchermataIniziale():
	now=datetime.datetime.now()
	diff1=relativedelta(now,BIRTH_DATE)
	diff2=relativedelta(now,RELEASE_DATE)
	print(f"\nOrologic ha {diff1.years} anni, {diff1.months} mesi, {diff1.days} giorni, {diff1.hours} ore e {diff1.minutes} minuti.")
	print(f"L'ultima versione è la {VERSION} ed è stata rilasciata il {RELEASE_DATE.strftime('%d/%m/%Y %H:%M')}.")
	print(f"\tcioè: {diff2.years} anni, {diff2.months} mesi, {diff2.days} giorni, {diff2.hours} ore e {diff2.minutes} minuti fa.")
	print("\t\tAutore: "+PROGRAMMER)
	print("\t\t\tDigita '?' per visualizzare il menù.")
	Acusticator(['c4', 0.125, 0, 0.5, 'd4', 0.125, 0, 0.5, 'e4', 0.125, 0, 0.5, 'g4', 0.125, 0, 0.5, 'a4', 0.125, 0, 0.5, 'e5', 0.125, 0, 0.5, 'p', 0.125, 0, 0.5, 'a5', 0.125, 0, 0.5], kind=1, adsr=[0.01, 0, 100, 99])

def main():
	SchermataIniziale()
	while True:
		scelta=menu(MENU_CHOICES,keyslist=True,ntf="Scelta non valida")
		if scelta=="?":
			print("\nMenù principale\n")
			for k,v in MENU_CHOICES.items():
				print(f"{k} - {v}")
		elif scelta=="c":
			create_clock()
		elif scelta=="v":
			view_clocks()
		elif scelta=="d":
			delete_clock()
		elif scelta=="e":
			edit_default_pgn()
		elif scelta=="m":
			open_manual()
		elif scelta=="g":
			print("\nAvvio partita\n")
			db=load_db()
			if not db["clocks"]:
				print("Nessun orologio disponibile. Creane uno prima.")
			else:
				clock_config=select_clock()
				if clock_config is not None:
					start_game(clock_config)
				else:
					print("Scelta non valida.")
		elif scelta==".":
			print("Uscita dall'applicazione.")
			exit(0)

if __name__=="__main__":
	board=CustomBoard()
	main()

# Orologic per NVDA: la scacchiera interattiva e la console di Orologic.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).
# Copyright (C) 2026 Gabriele Battaglia. Questo componente e' software
# libero, sotto la GNU General Public License versione 2 o successive: il
# testo e' in COPYING.txt.
# 25 novembre 2026: versione 1.0.0, dai prototipi collaudati da Gabriele.
# 25 novembre 2026: 1.0.1, la scacchiera si rilegge dal cursore quando il
# testo cambia, perche' le quadre del pezzo sollevato arrivino subito.

"""Il componente di NVDA per Orologic, il programma di scacchi per giocatori
ciechi e ipovedenti.

Fa due cose, e solo sulle aree che Orologic segna con la proprieta' di
finestra Orologic.area, nei processi di Orologic: in ogni altro programma, e
in ogni altro controllo di Orologic, NVDA resta com'e'.

1. La scacchiera interattiva, Orologic.area 1. Con le frecce Orologic sposta
   da se' il cursore sulla casa e annuncia la casa col suo pezzo. NVDA, come
   in ogni campo di testo, direbbe anche il carattere sotto il cursore, un
   simbolo che l'annuncio di Orologic copre a meta'. Qui, dopo una freccia,
   NVDA fa tutto come sempre, il cursore di esplorazione e la barra braille,
   ma non parla.
2. Le aree che Orologic aggiorna da se', come la console col prompt e gli
   orologi, Orologic.area 2, e anche la scacchiera. NVDA rilegge un campo di
   testo per la barra solo dopo un tasto: quando Orologic cambia il testo,
   avvisa con l'evento di Windows valueChange, e qui la barra rilegge la
   riga, senza voce e senza spostare niente: il display resta sulla pagina
   che si sta leggendo.

Perche' Orologic sappia che il componente c'e', e smetta di mandare la riga
alla barra come messaggio, sulle aree che ha segnato il componente scrive
la proprieta' Orologic.nvda, col numero del processo di NVDA. Quando NVDA si
chiude, o il componente si spegne, la toglie.

Cosa non fa, per scelta: non usa la rete, non scrive file, non lancia
programmi, non esegue testi che arrivano da fuori, non prende tasti a NVDA,
non cambia il codice di NVDA. Nelle finestre di Orologic scrive solo il segno
di presenza, e solo sulle aree che Orologic stesso ha segnato. Usa le classi
sovrapposte, la strada che NVDA prevede per dare un comportamento proprio a
un controllo, e ogni errore resta qui, nel registro di NVDA, senza fermare
NVDA.
"""

import ctypes
import os
from ctypes import wintypes

import api
import braille
import globalPluginHandler
import globalVars
import review
from logHandler import log
from NVDAObjects import NVDAObject
from NVDAObjects.behaviors import EditableTextWithAutoSelectDetection

# La proprieta' di finestra con cui Orologic segna le sue aree, e i valori.
PROPRIETA = "Orologic.area"
SCACCHIERA = 1
CONSOLE = 2
# Il segno di presenza del componente, col numero del processo di NVDA.
PRESENZA = "Orologic.nvda"
# Le aree di Orologic sono controlli RichEdit di wxPython: gli altri
# controlli non si guardano nemmeno.
CLASSI = ("RICHEDIT50W",)
# I processi di Orologic: il pacchetto compilato, e Python per chi lo usa dai
# sorgenti.
APPLICAZIONI = ("orologic", "python", "pythonw")

_user32 = ctypes.WinDLL("user32")
_GetPropW = _user32.GetPropW
_GetPropW.argtypes = (wintypes.HWND, wintypes.LPCWSTR)
_GetPropW.restype = wintypes.HANDLE
_SetPropW = _user32.SetPropW
_SetPropW.argtypes = (wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE)
_SetPropW.restype = wintypes.BOOL
_RemovePropW = _user32.RemovePropW
_RemovePropW.argtypes = (wintypes.HWND, wintypes.LPCWSTR)
_RemovePropW.restype = wintypes.HANDLE
_IsWindow = _user32.IsWindow
_IsWindow.argtypes = (wintypes.HWND,)
_IsWindow.restype = wintypes.BOOL


def _area_di(obj):
	"""Il valore di Orologic.area sulla finestra del controllo, o 0."""
	try:
		if getattr(obj, "windowClassName", None) not in CLASSI:
			return 0
		finestra = getattr(obj, "windowHandle", None)
		if not finestra:
			return 0
		area = _GetPropW(finestra, PROPRIETA) or 0
		if area not in (SCACCHIERA, CONSOLE):
			return 0
		if obj.appModule.appName not in APPLICAZIONI:
			return 0
		return area
	# Un controllo che sparisce mentre lo si guarda non deve fermare NVDA.
	except Exception:  # noqa: BLE001
		log.debugWarning("Orologic: area non letta", exc_info=True)
		return 0


class AreaDiOrologic(NVDAObject):
	"""Un'area che Orologic aggiorna da se': al valueChange la barra rilegge
	la riga, e la voce tace, perche' gli annunci li fa Orologic."""

	def event_valueChange(self):
		# Quello che NVDA fa di suo nei campi di testo, e che resta.
		if isinstance(self, EditableTextWithAutoSelectDetection):
			self.hasContentChangedSinceLastSelection = True
		try:
			# La barra rilegge la riga dov'e', e il display resta sulla pagina
			# che si sta leggendo: niente si sposta.
			braille.handler.handleUpdate(self)
		except Exception:  # noqa: BLE001
			log.debugWarning("Orologic: barra non aggiornata", exc_info=True)


class ScacchieraDiOrologic(AreaDiOrologic):
	"""La scacchiera interattiva: dopo una freccia tutto come sempre, ma
	senza la voce, perche' la casa e il pezzo li annuncia Orologic. Quando
	il testo cambia, come per le quadre del pezzo sollevato, il cursore di
	esplorazione e la barra tornano sulla traversa del cursore, come dopo un
	tasto: anche se Orologic ha riscritto tutto il testo, e la posizione di
	prima non si legge piu'."""

	def event_valueChange(self):
		try:
			fuoco = api.getFocusObject()
			if fuoco == self:
				braille.handler.handleCaretMove(fuoco)
				review.handleCaretMove(fuoco)
		except Exception:  # noqa: BLE001
			log.debugWarning("Orologic: scacchiera non riletta dal cursore", exc_info=True)
		super().event_valueChange()

	def _caretScriptPostMovedHelper(self, speakUnit, *args, **kwargs):
		# Senza unita' da leggere NVDA aggiorna il cursore di esplorazione e
		# la barra, e non parla.
		super()._caretScriptPostMovedHelper(None, *args, **kwargs)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		# Le finestre col segno di presenza, da togliere alla chiusura.
		self._segnate = set()

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		# Nelle schermate protette di Windows non si fa niente.
		if globalVars.appArgs.secure:
			return
		area = _area_di(obj)
		if area == SCACCHIERA:
			clsList.insert(0, ScacchieraDiOrologic)
		elif area == CONSOLE:
			clsList.insert(0, AreaDiOrologic)
		else:
			return
		self._segna_la_presenza(obj.windowHandle)

	def _segna_la_presenza(self, finestra):
		"""Il segno che dice a Orologic che il componente c'e'."""
		try:
			if finestra not in self._segnate:
				# Le aree chiuse escono dall'elenco.
				self._segnate = {segnata for segnata in self._segnate if _IsWindow(segnata)}
			_SetPropW(finestra, PRESENZA, os.getpid())
			self._segnate.add(finestra)
		except Exception:  # noqa: BLE001
			log.debugWarning("Orologic: segno di presenza non scritto", exc_info=True)

	def terminate(self):
		# Orologic torna a mandare la riga alla barra da se'.
		for finestra in self._segnate:
			try:
				if _IsWindow(finestra):
					_RemovePropW(finestra, PRESENZA)
			except Exception:  # noqa: BLE001
				log.debugWarning("Orologic: segno di presenza non tolto", exc_info=True)
		self._segnate.clear()
		super().terminate()

# Orologic: il documento dei RichEdit, per cambiare il testo senza toccare il cursore.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).

"""Il documento TOM, ITextDocument, dei controlli RichEdit di Orologic, e
il pezzo che cambia fra due versioni di una riga (dalla 9.2.0, 25 novembre
2026; prima il documento stava nella finestra).

Col documento un pezzo di testo cambia e il cursore resta dov'era, se e'
fuori dal pezzo: lo usa la console. Il documento pero' non scrive nei
controlli in sola lettura, come la scacchiera interattiva, che riscrive i
suoi pezzi con Replace. In tutti e due i casi NVDA, che tiene la sua
posizione di esplorazione nello stesso testo, la ritrova al suo posto.
ChangeValue invece riscrive tutto, e la posizione di NVDA non si legge piu'
finche' non si preme un tasto (Gabriele, 25 novembre 2026: le quadre del
pezzo sollevato non arrivavano alla barra).

Il documento va lasciato prima che il controllo si chiuda, nel suo
EVT_WINDOW_DESTROY: il suo rilascio, su un controllo gia' distrutto,
corromperebbe la memoria, come nelle prove del 23 novembre 2026.
"""

import ctypes

EM_GETOLEINTERFACE = 0x0400 + 60
IID_ITEXTDOCUMENT = "{8CC497C0-A1DF-11CE-8098-00AA0047BE5D}"


def documento(controllo):
    """Il documento del RichEdit, o None se non c'e', per esempio senza
    pywin32: allora si cambia il testo con Replace."""
    try:
        import pythoncom
        import pywintypes
        import win32com.client

        puntatore = ctypes.c_void_p()
        # Una copia propria di user32: i tipi degli argomenti cambiati su
        # ctypes.windll.user32 varrebbero per tutto il processo.
        manda = ctypes.WinDLL("user32").SendMessageW
        manda.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.POINTER(ctypes.c_void_p))
        manda.restype = ctypes.c_ssize_t
        manda(controllo.GetHandle(), EM_GETOLEINTERFACE, 0, ctypes.byref(puntatore))
        if not puntatore.value:
            return None
        sconosciuto = pythoncom.ObjectFromAddress(puntatore.value, pythoncom.IID_IUnknown)
        return win32com.client.Dispatch(sconosciuto.QueryInterface(pywintypes.IID(IID_ITEXTDOCUMENT), pythoncom.IID_IDispatch))
    # Senza il documento si cambia il testo con Replace, come prima.
    except Exception:  # noqa: BLE001
        return None


def con_lo_stile(controllo, intervallo):
    """Il testo scritto dal documento prende lo stile del controllo, i colori
    e i caratteri di aspetto.py, come quello di Replace: il documento da
    solo non lo applica."""
    stile = controllo.GetDefaultStyle()
    carattere = intervallo.Font
    # I colori del documento sono COLORREF: rosso, verde e blu dal basso.
    if stile.HasTextColour():
        colore = stile.GetTextColour()
        carattere.ForeColor = colore.Red() | colore.Green() << 8 | colore.Blue() << 16
    if stile.HasBackgroundColour():
        colore = stile.GetBackgroundColour()
        carattere.BackColor = colore.Red() | colore.Green() << 8 | colore.Blue() << 16
    if stile.HasFont() and stile.GetFont().IsOk():
        font = stile.GetFont()
        carattere.Size = font.GetPointSize()
        if font.GetFaceName():
            carattere.Name = font.GetFaceName()


def tratto_cambiato(vecchia, nuova):
    """Il pezzo che cambia fra due versioni di una riga, senza l'inizio e la
    fine che restano uguali: l'inizio e la fine del pezzo nella vecchia, e il
    suo testo nuovo."""
    limite = min(len(vecchia), len(nuova))
    inizio = 0
    while inizio < limite and vecchia[inizio] == nuova[inizio]:
        inizio += 1
    uguali_in_fondo = 0
    while uguali_in_fondo < limite - inizio and vecchia[-1 - uguali_in_fondo] == nuova[-1 - uguali_in_fondo]:
        uguali_in_fondo += 1
    return inizio, len(vecchia) - uguali_in_fondo, nuova[inizio : len(nuova) - uguali_in_fondo]


def sostituisci(documento_del_controllo, controllo, inizio, fine, testo):
    """Il testo del controllo da inizio a fine prende il posto: col documento
    il cursore resta dov'era, se e' fuori dal pezzo, e la funzione da' vero;
    senza, o se il documento non risponde, si usa Replace, che lo tocca, e
    da' falso."""
    if documento_del_controllo is not None:
        try:
            intervallo = documento_del_controllo.Range(inizio, fine)
            intervallo.Text = testo.replace("\n", "\r")
            con_lo_stile(controllo, intervallo)
            return True
        # Un documento che non risponde piu': si usa Replace.
        except Exception:  # noqa: BLE001, S110
            pass
    controllo.Replace(inizio, fine, testo)
    return False

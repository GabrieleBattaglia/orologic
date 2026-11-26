; Orologic, l'installatore con Inno Setup 6.
; Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).
; Nasce il 21 novembre 2026 per la 9.0.0, sul modello di Ciechino.iss, MESS.iss e MeTeOra.iss
; (issue 73, Piano della GUI.txt, T5c): l'installatore affianca lo zip, e chiede di accettare la licenza.
;
; Si compila con python setup_maker.py, dopo PyInstaller e zip_maker.py: lo script passa la versione
; di orologic_modules/version.py. L'aggiornamento automatico usa sempre lo zip. Si installa per
; utente, senza amministratore, perche' Orologic scrive i suoi dati accanto all'eseguibile e
; l'aggiornamento automatico sostituisce i file nella sua cartella. Chi ha gia' Orologic portatile
; installa sopra la sua cartella, scegliendola nella pagina della cartella: i dati restano.
; Stockfish non e' nel pacchetto: Orologic lo scarica da se', nella cartella engine.
; Nemmeno pgn-extract: Orologic lo scarica dal sito di David J. Barnes, nella cartella pgn-extract.
; Alla disinstallazione una domanda, con No gia' scelto, chiede se cancellare anche i dati, il motore
; compreso. Parla le lingue di Orologic, scelte all'avvio.

#ifndef Versione
  #error Manca la versione: si compila con python setup_maker.py
#endif

[Setup]
; L'identita' dell'installazione: non cambia mai, e non e' quella di nessun altro programma del parco.
; La stessa e' in orologic_modules/installazione.py.
AppId={{2F02E0E5-F793-4397-A56B-B2BC5D0B4CEC}
AppName=Orologic
AppVersion={#Versione}
AppVerName=Orologic {#Versione}
AppPublisher=Gabriele Battaglia (IZ4APU)
AppPublisherURL=https://github.com/GabrieleBattaglia/orologic
AppSupportURL=https://github.com/GabrieleBattaglia/orologic/issues
AppUpdatesURL=https://github.com/GabrieleBattaglia/orologic/releases
VersionInfoVersion={#Versione}
; La licenza GPL 3, da accettare prima di installare.
LicenseFile=LICENSE
; Per utente: con PrivilegesRequired=lowest {autopf} e' la cartella Programs di AppData\Local.
PrivilegesRequired=lowest
DefaultDirName={autopf}\Orologic
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=.
OutputBaseFilename=Orologic-Setup-{#Versione}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Le lingue di Orologic, scelte all'avvio dell'installatore.
ShowLanguageDialog=yes
UninstallDisplayName=Orologic
UninstallDisplayIcon={app}\orologic.exe
; Orologic aperto tiene questo mutex (installazione.py): installazione e disinstallazione chiedono di chiuderlo.
AppMutex=Orologic
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "italiano"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "espanol"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "francais"; MessagesFile: "compiler:Languages\French.isl"
Name: "portugues"; MessagesFile: "compiler:Languages\Portuguese.isl"

[CustomMessages]
; Il collegamento al terminale, Orologic con --cli, col nome scelto da Gabriele nel collaudo della T6.
italiano.Terminale=Orologic modalità a linea di comando
english.Terminale=Orologic command line mode
espanol.Terminale=Orologic modo línea de comandos
francais.Terminale=Orologic mode ligne de commande
portugues.Terminale=Orologic modo linha de comando
italiano.CancelloIDati=Cancello anche i dati di Orologic? Impostazioni, orologi, carriera contro il motore, token di Lichess, partite, resoconti, il motore e pgn-extract scaricati. Con No restano nella cartella, e reinstallando Orologic li ritrovi.
english.CancelloIDati=Shall I also delete the Orologic data? Settings, clocks, career against the engine, Lichess token, games, reports, and the downloaded engine and pgn-extract. With No they stay in the folder, and you will find them again if you reinstall Orologic.
espanol.CancelloIDati=¿Borro también los datos de Orologic? Ajustes, relojes, carrera contra el motor, token de Lichess, partidas, informes, y el motor y pgn-extract descargados. Con No se quedan en la carpeta, y al reinstalar Orologic los vuelves a encontrar.
francais.CancelloIDati=Dois-je aussi supprimer les données d'Orologic ? Réglages, pendules, carrière contre le moteur, jeton Lichess, parties, comptes rendus, et le moteur et pgn-extract téléchargés. Avec Non, elles restent dans le dossier, et vous les retrouverez en réinstallant Orologic.
portugues.CancelloIDati=Apago também os dados do Orologic? Definições, relógios, carreira contra o motor, token do Lichess, partidas, relatórios, e o motor e o pgn-extract descarregados. Com Não ficam na pasta, e ao reinstalar o Orologic voltas a encontrá-los.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; Prima di installare, via le cartelle del programma lasciate da una versione precedente. Un Orologic
; aggiornato da solo ha in _internal il manifesto dello zip: se restasse, al primo avvio
; pulisci_residui cancellerebbe tutti i file nuovi che quel manifesto non elenca. I dati stanno fuori
; da _internal, accanto all'eseguibile, e restano dove sono.
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\_internal_vecchio"

[Files]
; Il pacchetto a cartella di PyInstaller, senza i dati che una prova avesse lasciato in dist, come lo
; zip. Ogni motivo comincia con la barra rovesciata, che lo lega alla cartella dell'eseguibile, e ogni
; cartella e' scritta anche col suo contenuto, perche' createallsubdirs creerebbe quelle vuote.
Source: "dist\orologic\*"; DestDir: "{app}"; Excludes: "\settings,\settings\*,\pgn,\pgn\*,\txt,\txt\*,\images,\images\*,\engine,\engine\*,\engine.nuovo,\engine.nuovo\*,\engine.vecchio,\engine.vecchio\*,\pgn-extract,\pgn-extract\*,\pgn-extract.nuovo,\pgn-extract.nuovo\*,\pgn-extract.vecchio,\pgn-extract.vecchio\*,\log,\log\*,\logs,\logs\*,\*.log,\*.log.1,\*.tmp,\*.bak,\*.zip"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Orologic"; Filename: "{app}\orologic.exe"
Name: "{autoprograms}\{cm:Terminale}"; Filename: "{app}\orologic.exe"; Parameters: "--cli"
Name: "{autodesktop}\Orologic"; Filename: "{app}\orologic.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\orologic.exe"; Description: "{cm:LaunchProgram,Orologic}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; L'aggiornamento automatico puo' portare in _internal file che l'installatore non conosce: la
; cartella del programma si toglie intera. I dati stanno fuori da _internal, accanto all'eseguibile.
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\_internal_vecchio"

[Code]
// I dati di Orologic: le cartelle che scrive accanto all'eseguibile, il motore scaricato, con le
// sue cartelle di lavoro, e il registro dell'aggiornamento.
procedure CancellaIDati(const Cartella: String);
begin
  DelTree(Cartella + '\settings', True, True, True);
  DelTree(Cartella + '\pgn', True, True, True);
  DelTree(Cartella + '\txt', True, True, True);
  DelTree(Cartella + '\images', True, True, True);
  DelTree(Cartella + '\engine', True, True, True);
  DelTree(Cartella + '\engine.nuovo', True, True, True);
  DelTree(Cartella + '\engine.vecchio', True, True, True);
  DelTree(Cartella + '\pgn-extract', True, True, True);
  DelTree(Cartella + '\pgn-extract.nuovo', True, True, True);
  DelTree(Cartella + '\pgn-extract.vecchio', True, True, True);
  DeleteFile(Cartella + '\auto_updater_error.log');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
  begin
    if MsgBox(CustomMessage('CancelloIDati'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      CancellaIDati(ExpandConstant('{app}'));
    // La cartella si toglie solo se e' rimasta vuota.
    RemoveDir(ExpandConstant('{app}'));
  end;
end;

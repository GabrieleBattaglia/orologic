; Inno Setup Script per Orologic (Applicazione CLI)
; Creato il 13/10/2025
; esempio
[Setup]
; --- Informazioni Base dell'Applicazione ---
AppName=Orologic
; !!! MODIFICA QUI la versione della tua app ad ogni release
AppVersion=1.0.0
AppPublisher=Gabriele Battaglia
; AppPublisherURL=https://tuo-sito.com/
; AppSupportURL=https://tuo-sito.com/support/
; AppUpdatesURL=https://tuo-sito.com/updates/

; --- Impostazioni di Installazione ---
; {autopf} si espande in "C:\Program Files (x86)" o "C:\Program Files" a seconda dell'architettura
DefaultDirName={autopf}\Orologic
DefaultGroupName=Orologic
; Disabilita la richiesta di permessi se già in esecuzione come amministratore
PrivilegesRequired=admin
; Il file di output dell'installer
OutputBaseFilename=setup-orologic-v1.0.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
; --- Task Opzionali durante l'installazione ---
; Aggiunge una checkbox per consentire all'utente di aggiungere l'eseguibile al PATH
Name: "addtopath"; Description: "Aggiungi la cartella dell'applicazione al PATH di sistema"; GroupDescription: "Opzioni Aggiuntive:"; Flags: unchecked

[Files]
; --- File da Includere ---
; !!! MODIFICA QUI il percorso della cartella 'orologic' generata da PyInstaller
Source: "E:\percorso\della\tua\app\dist\orologic\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Nota: {app} è la cartella di installazione (es. C:\Program Files\Orologic)

[Icons]
; --- Icone nel Menu Start ---
; Crea una cartella nel Menu Start
Name: "{group}"; Filename: "{app}"
; Crea un'icona che apre un Command Prompt già posizionato nella cartella dell'app. Molto utile per le app CLI.
Name: "{group}\Prompt dei Comandi di Orologic"; Filename: "{cmd}"; Parameters: "/k cd /d {app}"; IconFilename: "{cmd}"
; Crea l'icona per disinstallare il programma
Name: "{group}\Disinstalla Orologic"; Filename: "{uninstallexe}"

[Run]
Filename: "{cmd}"; Parameters: "/k echo Orologic e' stato installato correttamente. Esegui 'orologic --help' per iniziare."; Description: "Mostra informazioni post-installazione"; Flags: postinstall shellexec runhidden

[Code]
// --- Codice per la gestione del PATH ---
const
    ModPathName = 'addtopath';
    ModPathType = 'system';

function NeedsRestart(): Boolean;
begin
    Result := WizardIsTaskSelected(ModPathName);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
    OldPath: string;
    NewPath: string;
begin
    if (CurStep = ssPostInstall) then
    begin
        if WizardIsTaskSelected(ModPathName) then
        begin
            // Aggiunge la cartella dell'app al PATH di sistema
            RegQueryStringValue(HKEY_LOCAL_MACHINE,
                'System\CurrentControlSet\Control\Session Manager\Environment',
                'Path', OldPath);
            NewPath := AddBackslash(ExpandConstant('{app}')) + ';' + OldPath;
            RegWriteStringValue(HKEY_LOCAL_MACHINE,
                'System\CurrentControlSet\Control\Session Manager\Environment',
                'Path', NewPath);
        end;
    end;
end;
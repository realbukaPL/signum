; Skrypt Inno Setup 6 dla Signum.
; Wersja jest przekazywana z scripts/build_installer.ps1: /DMyAppVersion=x.y.z
; Budowanie ręczne: ISCC.exe installer\signum.iss /DMyAppVersion=1.0.0

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif
#define MyAppName "Signum"
#define MyAppPublisher "Blazej"
#define MyAppExeName "Signum.exe"

[Setup]
; Stały AppId pozwala poprawnie aktualizować/odinstalowywać kolejne wersje.
AppId={{6D6C3F52-9C1B-4E6A-9A57-2B1FBD6A7E31}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoTextVersion={#MyAppVersion}
VersionInfoProductVersion={#MyAppVersion}.0
VersionInfoProductTextVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
; Instalacja per-user (bez uprawnień administratora); użytkownik może wybrać inaczej.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=output
OutputBaseFilename=Signum-Setup-{#MyAppVersion}
SetupIconFile=..\src\signum\ui\resources\signum.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AppMutex=Local\Signum-6D6C3F52-9C1B-4E6A-9A57-2B1FBD6A7E31
CloseApplications=yes
CloseApplicationsFilter=Signum.exe
RestartApplications=no

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.RiskPageTitle=Document and AI risk awareness
english.RiskPageDescription=Read the notice and confirm each point before continuing.
english.RiskCheckPurpose=I understand: Signum results require human verification.
english.RiskCheckDocuments=I understand: I must be allowed to process the selected documents.
english.RiskCheckLocal=I understand: a local AI model still processes document contents.
english.RiskCheckRemote=I understand: a remote AI service receives document contents.
english.RiskRequired=Confirm all four points to continue.
english.RequirementsTitle=Runtime and optional AI service
english.RequirementsDescription=The installer checked what Signum needs to start.
english.PythonBundled=Python runtime and application libraries: included in Signum; no separate Python installation is required.
english.OllamaFound=Ollama: detected on this computer. Signum will verify the running service and selected model before processing documents.
english.OllamaMissing=Ollama: not detected in the standard installation folders. It is optional. Install and start it before using local mode, or select a remote AI provider. Download: https://docs.ollama.com/windows
english.RequirementsNote=The installer does not download third-party AI software or models. Before every batch, Signum checks the selected service and model.
polish.RiskPageTitle=Świadomość ryzyka dla dokumentów i AI
polish.RiskPageDescription=Przeczytaj informację i potwierdź każdy punkt przed kontynuowaniem.
polish.RiskCheckPurpose=Rozumiem: wyniki Signum wymagają ręcznej weryfikacji.
polish.RiskCheckDocuments=Rozumiem: muszę mieć prawo do przetwarzania wybranych dokumentów.
polish.RiskCheckLocal=Rozumiem: lokalny model AI nadal przetwarza treść dokumentów.
polish.RiskCheckRemote=Rozumiem: zdalna usługa AI otrzymuje treść dokumentów.
polish.RiskRequired=Aby kontynuować, potwierdź wszystkie cztery punkty.
polish.RequirementsTitle=Runtime i opcjonalna usługa AI
polish.RequirementsDescription=Instalator sprawdził składniki potrzebne do uruchomienia Signum.
polish.PythonBundled=Runtime Pythona i biblioteki aplikacji: dołączone do Signum; osobna instalacja Pythona nie jest potrzebna.
polish.OllamaFound=Ollama: wykryta na tym komputerze. Signum przed analizą sprawdzi działającą usługę i wybrany model.
polish.OllamaMissing=Ollama: nie wykryto jej w standardowych katalogach. Jest opcjonalna. Zainstaluj i uruchom ją przed użyciem trybu lokalnego albo wybierz zdalnego dostawcę AI. Pobieranie: https://docs.ollama.com/windows
polish.RequirementsNote=Instalator nie pobiera zewnętrznego oprogramowania AI ani modeli. Przed każdą partią Signum sprawdza wybraną usługę i model.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Pliki tylko dla strony świadomości ryzyka. Przy kompresji solid muszą być pierwsze.
Source: "legal\RISK-NOTICE-en.txt"; Flags: dontcopy noencryption
Source: "legal\RISK-NOTICE-pl.txt"; Flags: dontcopy noencryption
Source: "..\dist\Signum\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
var
  RiskPage: TWizardPage;
  RiskMemo: TNewMemo;
  RiskCheckPurpose: TNewCheckBox;
  RiskCheckDocuments: TNewCheckBox;
  RiskCheckLocal: TNewCheckBox;
  RiskCheckRemote: TNewCheckBox;
  RequirementsPage: TOutputMsgWizardPage;

function OllamaInstalled: Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe')) or
    FileExists(ExpandConstant('{pf}\Ollama\ollama.exe')) or
    FileExists(ExpandConstant('{pf32}\Ollama\ollama.exe'));
end;

procedure UpdateRequirementsPage;
var
  OllamaMessage: String;
begin
  if OllamaInstalled then
    OllamaMessage := CustomMessage('OllamaFound')
  else
    OllamaMessage := CustomMessage('OllamaMissing');
  RequirementsPage.MsgLabel.Caption :=
    CustomMessage('PythonBundled') + #13#10 + #13#10 +
    OllamaMessage + #13#10 + #13#10 +
    CustomMessage('RequirementsNote');
end;

function RisksConfirmed: Boolean;
begin
  Result := RiskCheckPurpose.Checked and RiskCheckDocuments.Checked and
    RiskCheckLocal.Checked and RiskCheckRemote.Checked;
end;

procedure RiskCheckClick(Sender: TObject);
begin
  if WizardForm.CurPageID = RiskPage.ID then
    WizardForm.NextButton.Enabled := RisksConfirmed;
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  if WizardSilent and
     (CompareText(ExpandConstant('{param:ACKNOWLEDGERISKS|0}'), '1') <> 0) then
  begin
    SuppressibleMsgBox(
      'Instalacja cicha wymaga jawnego potwierdzenia informacji o ryzyku: ' +
      '/ACKNOWLEDGERISKS=1' + #13#10 + #13#10 +
      'Silent installation requires explicit acknowledgement of the risk ' +
      'notice: /ACKNOWLEDGERISKS=1',
      mbCriticalError, MB_OK, IDOK);
    Result := False;
  end;
end;

procedure InitializeWizard;
var
  NoticeFileName: String;
  CheckHeight: Integer;
  CheckTop: Integer;
  MemoHeight: Integer;
begin
  if ActiveLanguage = 'polish' then
    NoticeFileName := 'RISK-NOTICE-pl.txt'
  else
    NoticeFileName := 'RISK-NOTICE-en.txt';

  ExtractTemporaryFile(NoticeFileName);
  RiskPage := CreateCustomPage(wpLicense, CustomMessage('RiskPageTitle'),
    CustomMessage('RiskPageDescription'));

  CheckHeight := ScaleY(28);
  MemoHeight := RiskPage.SurfaceHeight - (4 * CheckHeight) - ScaleY(22);

  RiskMemo := TNewMemo.Create(WizardForm);
  RiskMemo.Parent := RiskPage.Surface;
  RiskMemo.SetBounds(0, 0, RiskPage.SurfaceWidth, MemoHeight);
  RiskMemo.ReadOnly := True;
  RiskMemo.ScrollBars := ssVertical;
  RiskMemo.WordWrap := True;
  RiskMemo.TabStop := False;
  RiskMemo.Lines.LoadFromFile(ExpandConstant('{tmp}\') + NoticeFileName);

  CheckTop := MemoHeight + ScaleY(8);
  RiskCheckPurpose := TNewCheckBox.Create(WizardForm);
  RiskCheckPurpose.Parent := RiskPage.Surface;
  RiskCheckPurpose.SetBounds(0, CheckTop, RiskPage.SurfaceWidth, CheckHeight);
  RiskCheckPurpose.Caption := CustomMessage('RiskCheckPurpose');
  RiskCheckPurpose.OnClick := @RiskCheckClick;

  CheckTop := CheckTop + CheckHeight;
  RiskCheckDocuments := TNewCheckBox.Create(WizardForm);
  RiskCheckDocuments.Parent := RiskPage.Surface;
  RiskCheckDocuments.SetBounds(0, CheckTop, RiskPage.SurfaceWidth, CheckHeight);
  RiskCheckDocuments.Caption := CustomMessage('RiskCheckDocuments');
  RiskCheckDocuments.OnClick := @RiskCheckClick;

  CheckTop := CheckTop + CheckHeight;
  RiskCheckLocal := TNewCheckBox.Create(WizardForm);
  RiskCheckLocal.Parent := RiskPage.Surface;
  RiskCheckLocal.SetBounds(0, CheckTop, RiskPage.SurfaceWidth, CheckHeight);
  RiskCheckLocal.Caption := CustomMessage('RiskCheckLocal');
  RiskCheckLocal.OnClick := @RiskCheckClick;

  CheckTop := CheckTop + CheckHeight;
  RiskCheckRemote := TNewCheckBox.Create(WizardForm);
  RiskCheckRemote.Parent := RiskPage.Surface;
  RiskCheckRemote.SetBounds(0, CheckTop, RiskPage.SurfaceWidth, CheckHeight);
  RiskCheckRemote.Caption := CustomMessage('RiskCheckRemote');
  RiskCheckRemote.OnClick := @RiskCheckClick;

  { InitializeSetup odrzuca tryb cichy bez jawnego parametru. }
  if WizardSilent then
  begin
    RiskCheckPurpose.Checked := True;
    RiskCheckDocuments.Checked := True;
    RiskCheckLocal.Checked := True;
    RiskCheckRemote.Checked := True;
  end;

  RequirementsPage := CreateOutputMsgPage(RiskPage.ID,
    CustomMessage('RequirementsTitle'), CustomMessage('RequirementsDescription'), '');
  UpdateRequirementsPage;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = RiskPage.ID then
    WizardForm.NextButton.Enabled := RisksConfirmed
  else if CurPageID = RequirementsPage.ID then
    UpdateRequirementsPage;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = RiskPage.ID) and not RisksConfirmed then
  begin
    MsgBox(CustomMessage('RiskRequired'), mbInformation, MB_OK);
    Result := False;
  end;
end;

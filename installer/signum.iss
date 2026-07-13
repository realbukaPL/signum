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

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Signum\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

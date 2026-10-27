#define MyAppName "太对了 SunPet"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Ganzhe2028"
#define MyAppExeName "SunPet.exe"

[Setup]
AppId={{8F2E4A1C-9B3D-4E5F-A6C7-D8E9F0A1B2C3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppComments=孙宇晨「太对了」桌面宠物 · Windows 版社区移植 · 代码 MIT
DefaultDirName={localappdata}\Programs\SunPet
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=SunPet-1.1.0-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=app.ico
UninstallDisplayIcon={app}\SunPet.exe
UninstallDisplayName={#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest

[Languages]
Name: "chinesesimp"; MessagesFile: "C:\Program Files\Inno Setup 7\Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式:"; Flags: unchecked

[Files]
Source: "dist\SunPet\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\太对了 SunPet"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\太对了 SunPet"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行桌宠"; Flags: nowait postinstall skipifsilent

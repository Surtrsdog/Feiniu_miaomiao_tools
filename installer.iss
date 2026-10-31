; ---- 肥牛妙妙工具 安装包脚本
; 用法：ISCC.exe 这个文件
;
; 说明：exe 是单文件自解压（onefile），首次运行会在**自身目录**下生成
; data\cache（约 34MB）。所以默认装到 %LOCALAPPDATA% 而不是 Program Files——
; 装到 Program Files 会因为没写权限而回落到 %LOCALAPPDATA%\ArknightsCalc，
; 虽然能用，但用户找不到缓存目录，卸载时也清不干净。

#define AppName "肥牛妙妙工具"
#define AppVer "2.6"
#define AppExe "肥牛妙妙工具.exe"
#define AppPub "Surtrsdog"
#define AppUrl "https://github.com/Surtrsdog/Feiniu_miaomiao_tools"

[Setup]
AppId={{8F3A2C71-4B9D-4E6A-9C15-7D2E8B4F1A63}
AppName={#AppName}
AppVersion={#AppVer}
AppVerName={#AppName} {#AppVer}
AppPublisher={#AppPub}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
DefaultDirName={localappdata}\FeiNiuMiaoMiao
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; 装到用户目录，不需要管理员权限
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=F:\mini api\dist
OutputBaseFilename=肥牛妙妙工具_{#AppVer}_安装包
SetupIconFile=F:\mini api\.build\app.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
; beta 版不做签名，写明避免 SmartScreen 误报困惑
VersionInfoVersion=2.6.0.0
VersionInfoProductName={#AppName}
VersionInfoProductVersion=2.6.0.0
VersionInfoCompany={#AppPub}
VersionInfoDescription={#AppName} 安装程序

[Languages]
Name: "cn"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: checkedonce

[Files]
Source: "F:\mini api\dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
; 附带一份卸载时清理用的说明
Source: "F:\mini api\README_安装说明.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\卸载 {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "立即运行 {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 首次运行生成的缓存也一并清掉，避免卸载后留 34MB 垃圾
Type: filesandordirs; Name: "{app}\data"
Type: dirifempty; Name: "{app}"

; =======================================================
;     Reels Counter Pro - Inno Setup Script (v1.0.6)
; =======================================================

#define MyAppId "3f2504e0-4f89-11d3-9a0c-0305e82c3301"

[Setup]
AppName=Reels Counter Pro
AppVersion=1.0.6
AppId={#MyAppId}
DefaultDirName={pf}\Reels Counter Pro
; บังคับให้ installer รันด้วยสิทธิ์ Admin
PrivilegesRequired=admin
DefaultGroupName=Reels Counter Pro
OutputBaseFilename=ReelsCounterPro-Setup-v1.0.6
SetupIconFile=Reels_Counter_Pro_LOGO.ico
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no
DisableProgramGroupPage=yes
CloseApplications=yes

[Files]
Source: "ReelsCounterPro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Reels_Counter_Pro_LOGO.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "Reels_Counter_Pro_LOGO_transparent.png"; DestDir: "{app}"; Flags: ignoreversion

; รวมโฟลเดอร์ _internal ทั้งหมด และลบทิ้งตอนถอนการติดตั้ง
Source: "_internal\*"; DestDir: "{app}\_internal"; Flags: recursesubdirs createallsubdirs ignoreversion

; ✅ รวม BAT สำหรับ Defender Exclusion
Source: "add_defender_exclusion.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Reels Counter Pro"; Filename: "{app}\ReelsCounterPro.exe"; IconFilename: "{app}\Reels_Counter_Pro_LOGO.ico"
Name: "{group}\Uninstall Reels Counter Pro"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Reels Counter Pro"; Filename: "{app}\ReelsCounterPro.exe"; IconFilename: "{app}\Reels_Counter_Pro_LOGO.ico"

[Run]
; เพิ่มทั้ง ExclusionPath สำหรับโฟลเดอร์หลัก (ถ้ายังไม่มี)
Filename: "powershell.exe"; \
Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ""& '{app}\add_defender_exclusion.bat' '{app}'"""; \
Flags: runhidden waituntilterminated

; แล้วตามด้วย ExclusionProcess สำหรับชื่อ updater.exe คงที่
Filename: "powershell.exe"; \
Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ""Add-MpPreference -ExclusionProcess 'ReelsCounterUpdater.exe'"""; \
Flags: runhidden waituntilterminated


; ✅ รันโปรแกรมหลังติดตั้ง
Filename: "{app}\ReelsCounterPro.exe"; Description: "Launch Reels Counter Pro"; \
  Flags: nowait postinstall; Parameters: "/postinstall"

[Code]
var
  IsUpgrade: Boolean;

// 1) ตรวจว่าเป็นอัปเกรดหรือไม่ (ใช้กับ ShouldSkipPage)
function InitializeSetup(): Boolean;
begin
  IsUpgrade := RegKeyExists(
    HKLM,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppId}'
  );
  Result := True;
end;

// 2) ถ้าเป็นอัปเกรด ให้ข้ามหน้าเลือกโฟลเดอร์
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = wpSelectDir) and IsUpgrade;
end;

// 3) หลังผู้ใช้กด Next ที่หน้าเลือกโฟลเดอร์ ให้เพิ่ม Defender Exclusion
function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
  Cmd: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    // a) เพิ่ม ExclusionPath ให้ทั้งโฟลเดอร์ {app}
    Cmd := '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden ' +
           '-Command "Add-MpPreference -ExclusionPath ''' +
           ExpandConstant('{app}') +
           '''"';
    Exec('powershell.exe', Cmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // b) เพิ่ม ExclusionProcess ให้ตัว updater ชื่อคงที่
    Cmd := '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden ' +
           '-Command "Add-MpPreference -ExclusionProcess ''ReelsCounterUpdater.exe''"';
    Exec('powershell.exe', Cmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // c) ถ้าไม่สำเร็จ แจ้งเตือนผู้ใช้ (อย่าสร้าง #13#10 ขึ้นบรรทัดแรก!)
    if ResultCode <> 0 then
      MsgBox(
        'ไม่สามารถตั้งค่า Defender Exclusion (Path+Process)'#13#10 +
        'Code=' + IntToStr(ResultCode),
        mbError,
        MB_OK
      );
  end;
end;

// 4) ก่อน Wizard สร้างหน้าแรก ให้ถอนของเก่าและ kill process ค้าง
procedure InitializeWizard();
var
  ResultCode: Integer;
begin
  // ถ้ามี uninstaller เดิม ให้ถอนก่อน
  if FileExists(ExpandConstant('{uninstallexe}')) then
    Exec(
      ExpandConstant('{uninstallexe}'),
      '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART',
      '',
      SW_HIDE, ewWaitUntilTerminated, ResultCode
    );

  // Kill process เก่าๆ
  Exec('taskkill', '/F /IM ReelsCounterPro.exe',   '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/F /IM chromedriver.exe',      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/F /IM msedgewebview2.exe',    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;







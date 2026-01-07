; =======================================================
;     Reels Counter Pro - Inno Setup Script (v1.4.7) Fix
; =======================================================

#define MyAppId "3f2504e0-4f89-11d3-9a0c-0305e82c3301"

[Setup]
WizardImageFile=setup_banner_reels_style.bmp
InfoBeforeFile=info_before.txt
AppName=Reels Counter Pro
VersionInfoVersion=1.4.7
VersionInfoDescription=Reels Counter Pro Installer
VersionInfoProductName=Reels Counter Pro
AppVersion=1.4.7
AppId={#MyAppId}
DefaultDirName=C:\Reels Counter Pro
; บังคับให้ installer รันด้วยสิทธิ์ Admin
PrivilegesRequired=admin
DefaultGroupName=Reels Counter Pro
OutputBaseFilename=ReelsCounterPro-Setup-v1.4.7
SetupIconFile=Reels_Counter_Pro_LOGO.ico
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no
DisableProgramGroupPage=yes
CloseApplications=yes
DirExistsWarning=no


[Messages]
WelcomeLabel1=Welcome to the installation of Reels Counter Pro 🎬
WelcomeLabel2=This will install Reels Counter Pro on your computer.
FinishedLabel=Setup has successfully installed Reels Counter Pro. 🎉

[Files]
Source: "ReelsCounterPro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Reels_Counter_Pro_LOGO.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "Reels_Counter_Pro_LOGO_transparent.png"; DestDir: "{app}"; Flags: ignoreversion

; รวมโฟลเดอร์ _internal ทั้งหมด และลบทิ้งตอนถอนการติดตั้ง
Source: "_internal\*"; DestDir: "{app}\_internal"; Flags: recursesubdirs createallsubdirs ignoreversion

; ✅ รวม BAT สำหรับ Defender Exclusion
Source: "add_defender_exclusion.bat"; DestDir: "{app}"; Flags: ignoreversion

; 🆕 เพิ่มไฟล์แก้ปัญหาใหม่
Source: "fix_browser_issue.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "fix_defender_exclusions.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "BROWSER_ISSUE_FIX.md"; DestDir: "{app}"; Flags: ignoreversion

; 🆕 เพิ่มโฟลเดอร์ docs
Source: "docs\*"; DestDir: "{app}\docs"; Flags: recursesubdirs createallsubdirs ignoreversion

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

// ตรวจสอบไม่ให้เลือก C:\Program Files และ C:\Program Files (x86)
function CheckValidDirName(DirName: string): Boolean;
begin
  if Pos(ExpandConstant('{pf}'), DirName) = 1 then
  begin
    MsgBox('ไม่สามารถติดตั้งใน Program Files ได้ กรุณาเลือกโฟลเดอร์อื่นที่สามารถอัปเดตไฟล์ได้', mbError, MB_OK);
    Result := False;
  end
  else if Pos(ExpandConstant('{pf32}'), DirName) = 1 then
  begin
    MsgBox('ไม่สามารถติดตั้งใน Program Files (x86) ได้ กรุณาเลือกโฟลเดอร์อื่นที่สามารถอัปเดตไฟล์ได้', mbError, MB_OK);
    Result := False;
  end
  else
    Result := True;
end;
// 2) ถ้าเป็นอัปเกรด ให้ข้ามหน้าเลือกโฟลเดอร์
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = wpSelectDir) and IsUpgrade;
end;

// 3) หลังผู้ใช้กด Next ที่หน้าเลือกโฟลเดอร์ ให้เพิ่ม Defender Exclusion
// ===================================================================
// START: บล็อกสำหรับแก้ไข - ฟังก์ชัน NextButtonClick ฉบับผสาน
// ===================================================================
function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
  Cmd: String;
begin
  // --- การตรวจสอบตอนอยู่ที่หน้าเลือกโฟลเดอร์ ---
  if CurPageID = wpSelectDir then
  begin
    // --- STEP 1: ตรวจสอบความถูกต้องของโฟลเดอร์ก่อน (Logic เดิมของลูกพี่) ---
    // ถ้า CheckValidDirName คืนค่าเป็น False (เลือกโฟลเดอร์ต้องห้าม)
    if not CheckValidDirName(WizardDirValue()) then
    begin
      // ให้หยุดการทำงานทันที และไม่ไปต่อ
      Result := False; 
      exit;
    end;

    // --- STEP 2: ถ้าโฟลเดอร์ถูกต้อง ให้เพิ่ม Defender Exclusion (Logic ใหม่ของลูกพี่) ---
    // ถ้าผ่าน Step 1 มาได้ แสดงว่าโฟลเดอร์ถูกต้องแล้ว
    
    // a) เพิ่ม ExclusionPath ให้ทั้งโฟลเดอร์ {app}
    // สั่งรัน PowerShell เพื่อเพิ่ม Exclusion Path สำหรับโฟลเดอร์ที่จะติดตั้งโปรแกรม
    Cmd := '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden ' +
           '-Command "Add-MpPreference -ExclusionPath ''' +
           ExpandConstant('{app}') +
           '''"';
    Exec('powershell.exe', Cmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // b) เพิ่ม ExclusionProcess ให้ตัว updater.exe
    // สั่งรัน PowerShell อีกครั้งเพื่อเพิ่ม Exclusion Process สำหรับไฟล์ Updater
    Cmd := '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden ' +
           '-Command "Add-MpPreference -ExclusionProcess ''ReelsCounterUpdater.exe''"';
    Exec('powershell.exe', Cmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // c) ตรวจสอบว่าการรันคำสั่งสำเร็จหรือไม่
    // (ใช้ ResultCode จากคำสั่งล่าสุด)
    if ResultCode <> 0 then
    begin
      MsgBox(
        'ไม่สามารถตั้งค่า Windows Defender Exclusion ได้'#13#10 +
        'แต่อย่างไรก็ตาม การติดตั้งจะดำเนินต่อไปตามปกติ'#13#10#13#10 +
        'Error Code: ' + IntToStr(ResultCode),
        mbError,
        MB_OK
      );
    end;
  end;

  // --- STEP 3: ถ้าผ่านเงื่อนไขทั้งหมดมาได้ ก็ให้ไปหน้าต่อไปตามปกติ ---
  Result := True; 
end;
// ===================================================================
// END: สิ้นสุดบล็อกสำหรับแก้ไข
// ===================================================================

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
  // 5) ห้ามติดตั้งใน Program Files
 // Kill process เก่าๆ
  Exec('taskkill', '/F /IM ReelsCounterPro.exe',   '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/F /IM chromedriver.exe',      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/F /IM msedgewebview2.exe',    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;











; Avto Quiz o'rnatuvchisi — eski ilova va uning ma'lumotlarini to'liq tozalash.
; Eski nomlar: productName "Avto Quiz", package "avto-quiz",
; electron-packager nomi "AvtoQuiz"; boshqa desktop ilovalar ("Avto Quiz Imtihon",
; "Avto Teacher") ham ochiq qolsa fayllarni band qiladi.

!include "LogicLib.nsh"

; Jarayonni majburan yopadi va haqiqatan tugaguncha kutadi (10 soniyagacha).
; Busiz eski fayllar "boshqa dastur band qilgan" bo'lib qoladi.
!macro avtoKillApp EXE
  nsExec::Exec 'taskkill /F /T /IM "${EXE}"'
  Pop $0
  StrCpy $R9 0
  ${Do}
    nsExec::ExecToStack 'cmd /c tasklist /NH /FI "IMAGENAME eq ${EXE}" | find /I "${EXE}"'
    Pop $0 ; 0 — hali ishlayapti, 1 — topilmadi
    Pop $1
    ${If} $0 != 0
      ${ExitDo}
    ${EndIf}
    nsExec::Exec 'taskkill /F /T /IM "${EXE}"'
    Pop $0
    Sleep 500
    IntOp $R9 $R9 + 1
    ${If} $R9 >= 20
      ${ExitDo}
    ${EndIf}
  ${Loop}
!macroend

!macro avtoKillAll
  !insertmacro avtoKillApp "Avto Quiz.exe"
  !insertmacro avtoKillApp "AvtoQuiz.exe"
  !insertmacro avtoKillApp "avto-quiz.exe"
  !insertmacro avtoKillApp "Avto Quiz Imtihon.exe"
  !insertmacro avtoKillApp "Avto Teacher.exe"
!macroend

!macro avtoWipe NAME
  ; Joriy foydalanuvchi: %APPDATA%, %LOCALAPPDATA%, HKCU\Software
  SetShellVarContext current
  RMDir /r "$APPDATA\${NAME}"
  RMDir /r "$LOCALAPPDATA\${NAME}"
  RMDir /r "$LOCALAPPDATA\${NAME}-updater"
  DeleteRegKey HKCU "Software\${NAME}"
  ; Barcha foydalanuvchilar: C:\ProgramData\<nom> (huquq bo'lmasa jim o'tadi)
  SetShellVarContext all
  RMDir /r "$APPDATA\${NAME}"
  SetShellVarContext current
!macroend

!macro avtoCleanOld
  !insertmacro avtoKillAll
  Sleep 500

  ; Eski "Avto Quiz" (xuddi shu appId) — uninstaller'iga tayanmasdan o'chiramiz:
  ; u ham fayl band bo'lsa yiqilib, "eski fayllarni o'chirib bo'lmadi" deydi.
  SetShellVarContext current
  RMDir /r "$LOCALAPPDATA\Programs\avto-quiz"
  RMDir /r "$LOCALAPPDATA\Programs\Avto Quiz"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${UNINSTALL_APP_KEY}"
  DeleteRegKey HKCU "${INSTALL_REGISTRY_KEY}"
  Delete "$DESKTOP\Avto Quiz.lnk"
  Delete "$SMPROGRAMS\Avto Quiz.lnk"

  !insertmacro avtoWipe "Avto Quiz"
  !insertmacro avtoWipe "avto-quiz"
  !insertmacro avtoWipe "AvtoQuiz"
!macroend

; O'rnatish boshida (eski versiya qidirilishidan oldin)
!macro customInit
  !insertmacro avtoCleanOld
!macroend

; Ishlab turgan ilova — so'ramasdan yopiladi (o'rnatishda ham, o'chirishda ham)
!macro customCheckAppRunning
  !insertmacro avtoKillApp "${APP_EXECUTABLE_FILENAME}"
  !insertmacro avtoKillApp "AvtoQuiz.exe"
!macroend

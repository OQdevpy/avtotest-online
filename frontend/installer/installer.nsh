; Avto Quiz o'rnatuvchisi — eski ilova va uning ma'lumotlarini to'liq tozalash.
; Eski nomlar: productName "Avto Quiz", package "avto-quiz",
; electron-packager nomi "AvtoQuiz".

!macro avtoKillApp EXE
  nsExec::Exec 'taskkill /F /T /IM "${EXE}"'
  Pop $0
!macroend

!macro avtoWipe NAME
  ; Joriy foydalanuvchi: %APPDATA%, %LOCALAPPDATA%, HKCU\Software
  SetShellVarContext current
  RMDir /r "$APPDATA\${NAME}"
  RMDir /r "$LOCALAPPDATA\${NAME}"
  DeleteRegKey HKCU "Software\${NAME}"
  ; Barcha foydalanuvchilar: C:\ProgramData\<nom> (huquq bo'lmasa jim o'tadi)
  SetShellVarContext all
  RMDir /r "$APPDATA\${NAME}"
  SetShellVarContext current
!macroend

!macro avtoCleanOld
  !insertmacro avtoKillApp "Avto Quiz.exe"
  !insertmacro avtoKillApp "AvtoQuiz.exe"
  !insertmacro avtoKillApp "avto-quiz.exe"
  Sleep 500
  !insertmacro avtoWipe "Avto Quiz"
  !insertmacro avtoWipe "avto-quiz"
  !insertmacro avtoWipe "AvtoQuiz"
!macroend

; O'rnatish boshida (eski versiya o'chirilishidan oldin)
!macro customInit
  !insertmacro avtoCleanOld
!macroend

; Ishlab turgan ilova — so'ramasdan yopiladi
!macro customCheckAppRunning
  !insertmacro avtoKillApp "${APP_EXECUTABLE_FILENAME}"
  !insertmacro avtoKillApp "AvtoQuiz.exe"
!macroend

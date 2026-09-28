; Avto Quiz o'rnatuvchisi — eski ma'lumotlarni tozalash.
;
; Ataylab minimal: jarayonlarni majburan yopish (taskkill), registr va boshqa
; dasturlarning papkalarini o'chirish kabi amallar imzolanmagan installer'da
; Windows Defender tomonidan "virus / PUA" deb bloklanadi. Ishlab turgan
; ilovani electron-builder'ning standart tekshiruvi yopadi, eski versiyani esa
; uning o'z uninstaller'i o'chiradi (appId bir xil).

; O'rnatish oxirida: ilova yopilgan, eski versiya o'chirilgan — eski
; profil (localStorage, kesh, eski token) qolmaydi. Ilovaning o'zi ham
; versiya o'zgarganda storage'ni tozalaydi (main.cjs).
!macro customInstall
  SetShellVarContext current
  RMDir /r "$APPDATA\Avto Quiz"
  RMDir /r "$APPDATA\avto-quiz"
  RMDir /r "$APPDATA\AvtoQuiz"
  RMDir /r "$LOCALAPPDATA\avto-quiz-updater"
!macroend

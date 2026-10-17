; Avto Teacher o'rnatuvchisi — eski ma'lumotlarni tozalash.
;
; Ataylab minimal: jarayonlarni majburan yopish (taskkill), registr va boshqa
; dasturlarning papkalarini o'chirish kabi amallar imzolanmagan installer'da
; Windows Defender tomonidan "virus / PUA" deb bloklanadi. Ishlab turgan
; ilovani electron-builder'ning standart tekshiruvi yopadi, eski versiyani esa
; uning o'z uninstaller'i o'chiradi (appId bir xil: com.avtotest.teacher).
;
; Faqat o'qituvchi ilovasining papkalari — o'quvchi ilovasi (Avto Quiz)
; bir kompyuterda bo'lsa, unga tegilmaydi.
!macro customInstall
  SetShellVarContext current
  RMDir /r "$APPDATA\Avto Teacher"
  RMDir /r "$APPDATA\avto-teacher"
  RMDir /r "$LOCALAPPDATA\avto-teacher-updater"
!macroend

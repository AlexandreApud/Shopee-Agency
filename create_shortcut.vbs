Set oWS = WScript.CreateObject("WScript.Shell")
strDesktop = oWS.SpecialFolders("Desktop")
strCurrentDir = oWS.CurrentDirectory

Set oLink = oWS.CreateShortcut(strDesktop & "\Shopee Agency Pro.lnk")
oLink.TargetPath = strCurrentDir & "\iniciar_calculadora.vbs"
oLink.WorkingDirectory = strCurrentDir
oLink.Description = "Shopee Agency Pro - Gestao e Lead Time"
oLink.IconLocation = "%SystemRoot%\System32\shell32.dll, 43"
oLink.Save

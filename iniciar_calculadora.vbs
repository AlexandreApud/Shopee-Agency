Set WshShell = CreateObject("WScript.Shell")
strCurrentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strCurrentDir

' Run pythonw invisibly (window style 0 = hidden, wait = false)
WshShell.Run "pythonw main.py", 0, False

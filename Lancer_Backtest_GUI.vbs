Option Explicit

' Lance le script batch du projet sans laisser de console visible.

Dim fileSystemObject
Dim shellObject
Dim projectDirectory
Dim batchFilePath
Dim commandLine

Set fileSystemObject = CreateObject("Scripting.FileSystemObject")
Set shellObject = CreateObject("WScript.Shell")

projectDirectory = fileSystemObject.GetParentFolderName(WScript.ScriptFullName)
batchFilePath = projectDirectory & "\Lancer_Backtest_GUI.bat"

If Not fileSystemObject.FileExists(batchFilePath) Then
    MsgBox "Le fichier de lancement batch est introuvable : " & batchFilePath, vbCritical, "Backtest GUI"
    WScript.Quit 1
End If

commandLine = "cmd.exe /c """ & batchFilePath & """"
shellObject.Run commandLine, 0, False

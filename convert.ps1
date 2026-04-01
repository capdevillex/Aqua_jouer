$batFile = "aqua_jouer.bat"
$exeFile = "Game selector.exe"

# Cette méthode crée un conteneur exécutable simple
Add-Type -TypeDefinition @"
using System;
using System.Diagnostics;
public class BatLauncher {
    public static void Main() {
        ProcessStartInfo psi = new ProcessStartInfo("$batFile");
        psi.WindowStyle = ProcessWindowStyle.Hidden;
        psi.CreateNoWindow = true;
        Process.Start(psi);
    }
}
"@ -OutputAssembly $exeFile
rule Suspicious_Download_Cradle
{
    meta:
        description = "Detecta patrones típicos de download cradle en PowerShell"
        severity = "medium"
    strings:
        $a = "IEX" nocase
        $b = "Net.WebClient" nocase
        $c = "DownloadString" nocase
    condition:
        2 of them
}

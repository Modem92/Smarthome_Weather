$ErrorActionPreference = 'Stop'
try {
    $agentService = Get-Service -Name ssh-agent -ErrorAction SilentlyContinue
    if ($null -eq $agentService) {
        $agentBinary = Join-Path $env:WINDIR 'System32\OpenSSH\ssh-agent.exe'
        if (-not (Test-Path -LiteralPath $agentBinary)) {
            throw 'Windows OpenSSH-Client unvollstaendig. Bitte die optionale Windows-Funktion OpenSSH-Client einrichten.'
        }
        New-Service -Name ssh-agent -BinaryPathName ('"' + $agentBinary + '"') -DisplayName 'OpenSSH Authentication Agent' -StartupType Automatic | Out-Null
    }
    Set-Service -Name ssh-agent -StartupType Automatic
    Start-Service -Name ssh-agent
    exit 0
} catch {
    exit 1
}

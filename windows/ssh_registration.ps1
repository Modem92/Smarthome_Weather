# Keep Python code off the native command line: Windows PowerShell 5.1 removes
# embedded double quotes when marshalling native arguments. SSH receives this
# script through stdin; password prompts still use the local console.
function Invoke-WetterstationKeyRegistration {
    param(
        [Parameter(Mandatory=$true)][string]$Target,
        [Parameter(Mandatory=$true)][string]$PublicBase64,
        [Parameter(Mandatory=$true)][string]$RemoteScript,
        [string]$SshExecutable = 'ssh.exe',
        [string[]]$PrefixArguments = @()
    )
    if ($PublicBase64 -notmatch '^[A-Za-z0-9+/]+={0,2}$') {
        throw 'Ungueltiger oeffentlicher Schluessel.'
    }
    $remoteCommand = 'python3 - --key-base64 ' + $PublicBase64
    # PowerShell 5.1 pipes to native programs with the global $OutputEncoding and,
    # on a UTF-8 console (code page 65001), prepends a BOM. Send exact UTF-8 without
    # BOM and restore both settings so the caller's console is unchanged.
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $previousInput = [Console]::InputEncoding
    $previousOutput = $global:OutputEncoding
    try {
        [Console]::InputEncoding = $utf8
        $global:OutputEncoding = $utf8
        $RemoteScript | & $SshExecutable @PrefixArguments -o StrictHostKeyChecking=yes -o ConnectTimeout=10 $Target $remoteCommand
    } finally {
        [Console]::InputEncoding = $previousInput
        $global:OutputEncoding = $previousOutput
    }
}

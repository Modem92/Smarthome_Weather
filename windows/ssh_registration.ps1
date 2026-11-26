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
    $RemoteScript | & $SshExecutable @PrefixArguments -o StrictHostKeyChecking=yes -o ConnectTimeout=10 $Target $remoteCommand
}

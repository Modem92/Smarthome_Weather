# Explicit one-time setup. Passwords and passphrases are entered only into OpenSSH.
$ErrorActionPreference = 'Stop'
try {
    $projectFolder = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    $settingsFile = Join-Path $projectFolder 'private\pi-update.json'
    $piUser = 'pi'
    if (Test-Path -LiteralPath $settingsFile) {
        $existing = Get-Content -LiteralPath $settingsFile -Raw | ConvertFrom-Json
        if ($existing.schema -ne 1 -or $existing.user -ne $piUser -or $existing.relative_target -ne 'wetterstation/Wetterstation') { throw 'Vorhandene Updatekonfiguration ungueltig; nichts ersetzt.' }
        $piHost = $existing.host
    } else {
        $piHost = (Read-Host 'Hostname oder IPv4-Adresse des Raspberry Pi').Trim()
    }
    if ($piHost -notmatch '^[A-Za-z0-9][A-Za-z0-9.:-]*$') { throw 'Ungueltiger Pi-Rechnername.' }
    $sshFolder = Join-Path $env:USERPROFILE '.ssh'
    $keyFile = Join-Path $sshFolder 'wetterstation_pi_ed25519'
    $publicFile = $keyFile + '.pub'
    if ($existing -and $existing.public_key -ne $publicFile) { throw 'Vorhandener Schluesselpfad weicht ab; nichts ersetzt.' }
    foreach ($cloudFolder in @($env:OneDrive, $env:OneDriveConsumer, $env:OneDriveCommercial)) {
        if ($cloudFolder -and ([IO.Path]::GetFullPath($keyFile)).StartsWith(([IO.Path]::GetFullPath($cloudFolder)).TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Der SSH-Schluessel darf nicht in OneDrive liegen.' }
    }
    Write-Host 'Einmalige Einrichtung der Pi-Anmeldung. Die Wetterstation wird nicht gestartet.'
    Write-Host 'Windows fragt gegebenenfalls nach einer Administratorfreigabe fuer den Schluesseldienst.'
    $helper = Join-Path $PSScriptRoot 'enable_ssh_agent.ps1'
    $elevated = Start-Process -FilePath 'powershell.exe' -Verb RunAs -WindowStyle Hidden -Wait -PassThru -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $helper + '"'))
    if ($elevated.ExitCode -ne 0) { throw 'Windows-Schluesseldienst konnte nicht eingerichtet werden. OpenSSH-Client und Administratorfreigabe pruefen.' }
    New-Item -ItemType Directory -Path $sshFolder -Force | Out-Null
    if ((Test-Path -LiteralPath $keyFile) -ne (Test-Path -LiteralPath $publicFile)) { throw 'Unvollstaendiges vorhandenes Schluesselpaar; nichts ueberschrieben.' }
    if (-not (Test-Path -LiteralPath $keyFile)) {
        Write-Host 'Bitte jetzt eine eigene Schluesselpassphrase eingeben und sicher aufbewahren.'
        & ssh-keygen.exe -t ed25519 -f $keyFile -C 'Wetterstation-Pi-Update'
        if ($LASTEXITCODE -ne 0) { throw 'Schluesselerstellung abgebrochen.' }
    }
    # Validate existing keys as well; never silently weaken the selected strategy.
    $keyLines = Get-Content -LiteralPath $keyFile
    if ($keyLines[0] -ne '-----BEGIN OPENSSH PRIVATE KEY-----') { throw 'Unbekanntes vorhandenes Schluesselformat; nichts ersetzt.' }
    $keyBinary = [Convert]::FromBase64String(($keyLines[1..($keyLines.Count-2)] -join ''))
    $cipherLength = [Net.IPAddress]::NetworkToHostOrder([BitConverter]::ToInt32($keyBinary, 15))
    $cipher = [Text.Encoding]::ASCII.GetString($keyBinary, 19, $cipherLength)
    if ($cipher -eq 'none') { throw 'Schluessel ohne Passphrase. Bitte dieses Paar selbst sichern/entfernen und Einrichtung mit Passphrase wiederholen; es wurde nicht auf dem Pi freigegeben.' }
    $userSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $keyFile '/inheritance:r' '/grant:r' ('*' + $userSid + ':F') | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Private Schluesseldatei konnte nicht geschuetzt werden.' }
    & ssh-add.exe $keyFile
    if ($LASTEXITCODE -ne 0) { throw 'Schluessel konnte nicht im Windows-Dienst gespeichert werden.' }
    $publicKey = (Get-Content -LiteralPath $publicFile -Raw).Trim()
    if ($publicKey -notmatch '^ssh-ed25519 [A-Za-z0-9+/=]+(?: .*)?$') { throw 'Ungueltiger oeffentlicher Schluessel.' }
    $publicBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($publicKey))
    $remoteScript = Get-Content -LiteralPath (Join-Path $projectFolder 'tools\pi\register_ssh_key.py') -Raw -Encoding UTF8
    . (Join-Path $PSScriptRoot 'ssh_registration.ps1')
    Write-Host 'Jetzt gegebenenfalls einmal das Pi-Passwort eingeben. Eine geaenderte SSH-Geraeteidentitaet wird nicht automatisch akzeptiert.'
    Invoke-WetterstationKeyRegistration -Target ($piUser + '@' + $piHost) -PublicBase64 $publicBase64 -RemoteScript $remoteScript
    if ($LASTEXITCODE -ne 0) { throw 'Pi-Schluesselregistrierung fehlgeschlagen. Vorhandene SSH-Geraeteidentitaet und Verbindung pruefen.' }
    & ssh.exe -i $publicFile -o IdentitiesOnly=yes -o BatchMode=yes -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o StrictHostKeyChecking=yes -o ConnectTimeout=10 ($piUser + '@' + $piHost) 'true'
    if ($LASTEXITCODE -ne 0) { throw 'Passwortfreie Anmeldung nicht bestaetigt; Einrichtung unvollstaendig.' }
    if (-not (Test-Path -LiteralPath $settingsFile)) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $settingsFile) -Force | Out-Null
        $config = @{ schema=1; host=$piHost; user=$piUser; relative_target='wetterstation/Wetterstation'; public_key=$publicFile }
        $temporaryConfig = $settingsFile + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
        [IO.File]::WriteAllText($temporaryConfig, ($config | ConvertTo-Json), (New-Object Text.UTF8Encoding $false))
        Move-Item -LiteralPath $temporaryConfig -Destination $settingsFile
    }
    Write-Host 'Einrichtung erfolgreich. Kuenftig Pi aktualisieren.cmd doppelklicken.'
    Write-Host 'Nach dem naechsten Windows-Neustart die Anmeldung ebenfalls pruefen.'
} catch {
    Write-Host ('Einrichtung angehalten: ' + $_.Exception.Message)
    exit 1
}

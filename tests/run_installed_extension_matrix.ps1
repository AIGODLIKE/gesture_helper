[CmdletBinding()]
param(
    [string]$PackagePath = "",
    [string[]]$ShortcutPaths = @(
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "Blender 4.2.lnk"),
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "Blender 4.3.lnk"),
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "Blender 4.4.lnk"),
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "Blender 4.5.lnk"),
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "Blender 5.0.lnk"),
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "Blender 5.1.lnk"),
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "Blender 5.2.lnk")
    ),
    [ValidateRange(10, 1800)]
    [int]$TimeoutSeconds = 120,
    [switch]$KeepArtifacts
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepositoryRoot = (Resolve-Path -LiteralPath (Split-Path $PSScriptRoot -Parent)).Path
$RepositoryTempParent = Join-Path $RepositoryRoot ".tmp"
$SystemTempParent = [IO.Path]::GetTempPath()
$RunName = "installed-extension-matrix-{0}-{1}" -f (
    Get-Date -Format "yyyyMMdd-HHmmssfff"
), ([guid]::NewGuid().ToString("N"))
$TempParent = $null
$RunRoot = $null
$RepositoryId = "gh_test"
$InstalledSmoke = Join-Path $PSScriptRoot "blender_installed_extension_smoke.py"
$IncompatibleSmoke = Join-Path $PSScriptRoot "blender_incompatible_extension_smoke.py"
$EnvironmentNames = @(
    "BLENDER_USER_CONFIG",
    "BLENDER_USER_SCRIPTS",
    "BLENDER_USER_DATAFILES",
    "BLENDER_USER_EXTENSIONS",
    "GH_TEST_REPOSITORY",
    "GH_TEST_PACKAGE_ID",
    "GH_EXPECTED_EXTENSION_VERSION",
    "GH_EXPECTED_PRESET_COUNT"
)
$OriginalEnvironment = @{}
foreach ($Name in $EnvironmentNames) {
    $OriginalEnvironment[$Name] = [Environment]::GetEnvironmentVariable(
        $Name,
        [EnvironmentVariableTarget]::Process
    )
}

function Get-TomlStringValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Toml,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $Pattern = '(?m)^\s*{0}\s*=\s*"([^"]+)"\s*(?:#.*)?$' -f [regex]::Escape($Name)
    $Match = [regex]::Match($Toml, $Pattern)
    if (-not $Match.Success) {
        throw "Missing TOML string '$Name' in packaged blender_manifest.toml"
    }
    return $Match.Groups[1].Value
}

function Get-PackageMetadata {
    param([Parameter(Mandatory = $true)][string]$ArchivePath)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Archive = [IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        $ManifestEntry = $Archive.GetEntry("blender_manifest.toml")
        if ($null -eq $ManifestEntry) {
            throw "Package has no root blender_manifest.toml: $ArchivePath"
        }
        $Reader = New-Object IO.StreamReader(
            $ManifestEntry.Open(),
            [Text.Encoding]::UTF8,
            $true
        )
        try {
            $Manifest = $Reader.ReadToEnd()
        }
        finally {
            $Reader.Dispose()
        }
    }
    finally {
        $Archive.Dispose()
    }

    return [pscustomobject]@{
        Id = Get-TomlStringValue -Toml $Manifest -Name "id"
        Version = Get-TomlStringValue -Toml $Manifest -Name "version"
        BlenderVersionMin = Get-TomlStringValue `
            -Toml $Manifest `
            -Name "blender_version_min"
    }
}

function ConvertTo-ProcessArgument {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    return '"' + $Value.Replace('"', '\"') + '"'
}

function Invoke-ProcessWithTimeout {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$LogDirectory,
        [Parameter(Mandatory = $true)][string]$Stage
    )

    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
    $StdoutPath = Join-Path $LogDirectory "$Stage.stdout.log"
    $StderrPath = Join-Path $LogDirectory "$Stage.stderr.log"
    $ArgumentList = @($Arguments | ForEach-Object {
        ConvertTo-ProcessArgument -Value $_
    })
    $ProcessInfo = New-Object Diagnostics.ProcessStartInfo
    $ProcessInfo.FileName = $FilePath
    $ProcessInfo.Arguments = $ArgumentList -join " "
    $ProcessInfo.UseShellExecute = $false
    $ProcessInfo.CreateNoWindow = $true
    $ProcessInfo.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
    $ProcessInfo.RedirectStandardOutput = $true
    $ProcessInfo.RedirectStandardError = $true
    $Process = New-Object Diagnostics.Process
    $Process.StartInfo = $ProcessInfo
    $StartedAt = Get-Date
    if (-not $Process.Start()) {
        throw "Could not start process: $FilePath"
    }
    $StdoutTask = $Process.StandardOutput.ReadToEndAsync()
    $StderrTask = $Process.StandardError.ReadToEndAsync()
    $TimedOut = $false
    if (-not $Process.WaitForExit($TimeoutSeconds * 1000)) {
        $TimedOut = $true
        $Process.Kill()
        $Process.WaitForExit()
    }
    $Process.WaitForExit()
    $Stdout = $StdoutTask.Result
    $Stderr = $StderrTask.Result
    [IO.File]::WriteAllText($StdoutPath, $Stdout)
    [IO.File]::WriteAllText($StderrPath, $Stderr)
    $ExitCode = $Process.ExitCode
    $ProcessId = $Process.Id
    $Process.Dispose()
    if ($TimedOut) {
        throw (
            "Blender stage '$Stage' timed out after $TimeoutSeconds seconds " +
            "(PID $ProcessId, started $StartedAt). Logs: $LogDirectory"
        )
    }
    return [pscustomobject]@{
        ExitCode = $ExitCode
        Stdout = $Stdout
        Stderr = $Stderr
        Output = "$Stdout`n$Stderr"
        Command = "$FilePath $($ArgumentList -join ' ')"
        Pid = $ProcessId
        StartedAt = $StartedAt
    }
}

function Assert-SuccessfulBlenderStage {
    param(
        [Parameter(Mandatory = $true)]$Result,
        [Parameter(Mandatory = $true)][string]$Stage,
        [string]$RequiredMarker = ""
    )

    $FailurePattern = @(
        "Traceback",
        "Python: Error",
        "EXCEPTION_ACCESS_VIOLATION",
        "FATAL_ERROR",
        "Failed to write preferences",
        "Permission denied",
        "Converting py args to operator properties"
    ) -join "|"
    $Failed = $Result.ExitCode -ne 0 -or $Result.Output -match $FailurePattern
    if ($RequiredMarker -and $Result.Output -notmatch [regex]::Escape($RequiredMarker)) {
        $Failed = $true
    }
    if ($Failed) {
        throw "Blender stage '$Stage' failed:`n$($Result.Command)`n$($Result.Output)"
    }
}

function Assert-IsolatedDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$Directory,
        [Parameter(Mandatory = $true)][string]$IsolationRoot
    )

    New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    $ResolvedDirectory = (Resolve-Path -LiteralPath $Directory).Path
    $ResolvedRoot = (Resolve-Path -LiteralPath $IsolationRoot).Path
    if (-not $ResolvedDirectory.StartsWith(
        "$ResolvedRoot\",
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Smoke directory escaped isolation root: $ResolvedDirectory"
    }

    $Sentinel = Join-Path $ResolvedDirectory (".write-test-" + [guid]::NewGuid().ToString("N"))
    $ReplaceSource = "$Sentinel.source"
    $ReplaceTarget = "$Sentinel.target"
    $ReplaceBackup = "$Sentinel.backup"
    try {
        [IO.File]::WriteAllText($Sentinel, "ok")
        [IO.File]::Delete($Sentinel)
        [IO.File]::WriteAllText($ReplaceSource, "new")
        [IO.File]::WriteAllText($ReplaceTarget, "old")
        [IO.File]::Replace(
            $ReplaceSource,
            $ReplaceTarget,
            $ReplaceBackup,
            $true
        )
    }
    finally {
        foreach ($Path in @(
            $Sentinel,
            $ReplaceSource,
            $ReplaceTarget,
            $ReplaceBackup
        )) {
            if (Test-Path -LiteralPath $Path) {
                Remove-Item -LiteralPath $Path -Force
            }
        }
    }
}

function Get-WritableIsolationParent {
    param([Parameter(Mandatory = $true)][string[]]$Candidates)

    $Failures = @()
    foreach ($Candidate in $Candidates) {
        $Probe = $null
        try {
            if (-not (Test-Path -LiteralPath $Candidate -PathType Container)) {
                New-Item -ItemType Directory -Path $Candidate | Out-Null
            }
            $ResolvedCandidate = (Resolve-Path -LiteralPath $Candidate).Path
            $Probe = Join-Path $ResolvedCandidate (
                "matrix-probe-" + [guid]::NewGuid().ToString("N")
            )
            New-Item -ItemType Directory -Path $Probe | Out-Null
            $ResolvedProbe = (Resolve-Path -LiteralPath $Probe).Path
            $ExpectedProbePrefix = $ResolvedCandidate.TrimEnd("\") + "\matrix-probe-"
            if (-not $ResolvedProbe.StartsWith(
                $ExpectedProbePrefix,
                [StringComparison]::OrdinalIgnoreCase
            )) {
                throw "Isolation probe escaped candidate parent: $ResolvedProbe"
            }
            $ProbeFile = Join-Path $ResolvedProbe ".write-test"
            [IO.File]::WriteAllText($ProbeFile, "ok")
            [IO.File]::Delete($ProbeFile)
            return $ResolvedCandidate
        }
        catch {
            $Failures += "$Candidate :: $($_.Exception.Message)"
        }
        finally {
            if ($Probe -and (Test-Path -LiteralPath $Probe)) {
                $ResolvedProbe = (Resolve-Path -LiteralPath $Probe).Path
                $ResolvedCandidate = (Resolve-Path -LiteralPath $Candidate).Path
                $ExpectedProbePrefix = $ResolvedCandidate.TrimEnd("\") + "\matrix-probe-"
                if (-not $ResolvedProbe.StartsWith(
                    $ExpectedProbePrefix,
                    [StringComparison]::OrdinalIgnoreCase
                )) {
                    throw "Refusing to remove unsafe probe directory: $ResolvedProbe"
                }
                Remove-Item -LiteralPath $ResolvedProbe -Recurse -Force
            }
        }
    }
    throw "No writable isolation parent was found:`n$($Failures -join "`n")"
}

function Resolve-BlenderExecutable {
    param(
        [Parameter(Mandatory = $true)][string]$ShortcutPath,
        [Parameter(Mandatory = $true)]$ShortcutShell
    )

    if (-not (Test-Path -LiteralPath $ShortcutPath -PathType Leaf)) {
        throw "Blender shortcut does not exist: $ShortcutPath"
    }
    $Shortcut = $ShortcutShell.CreateShortcut($ShortcutPath)
    $Target = $Shortcut.TargetPath
    if (-not $Target) {
        throw "Blender shortcut has no target: $ShortcutPath"
    }
    if ([IO.Path]::GetFileName($Target) -ieq "blender-launcher.exe") {
        $Target = Join-Path (Split-Path $Target -Parent) "blender.exe"
    }
    if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) {
        throw "Blender executable does not exist: $Target (from $ShortcutPath)"
    }
    return (Resolve-Path -LiteralPath $Target).Path
}

function Get-BlenderVersion {
    param(
        [Parameter(Mandatory = $true)][string]$BlenderExe,
        [Parameter(Mandatory = $true)][string]$LogDirectory,
        [Parameter(Mandatory = $true)][string]$Stage
    )

    $Result = Invoke-ProcessWithTimeout `
        -FilePath $BlenderExe `
        -Arguments @("--version") `
        -LogDirectory $LogDirectory `
        -Stage $Stage
    if ($Result.ExitCode -ne 0) {
        throw "Could not read Blender version:`n$($Result.Output)"
    }
    $Match = [regex]::Match($Result.Output, 'Blender\s+(\d+\.\d+\.\d+)')
    if (-not $Match.Success) {
        throw "Could not parse Blender version from: $($Result.Output)"
    }
    return [version]$Match.Groups[1].Value
}

function Set-TestEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$ProfileRoot,
        [Parameter(Mandatory = $true)]$Metadata
    )

    $Directories = @{
        BLENDER_USER_CONFIG = Join-Path $ProfileRoot "config"
        BLENDER_USER_SCRIPTS = Join-Path $ProfileRoot "scripts"
        BLENDER_USER_DATAFILES = Join-Path $ProfileRoot "datafiles"
        BLENDER_USER_EXTENSIONS = Join-Path $ProfileRoot "extensions"
    }
    foreach ($Name in $Directories.Keys) {
        Assert-IsolatedDirectory `
            -Directory $Directories[$Name] `
            -IsolationRoot $ProfileRoot
        [Environment]::SetEnvironmentVariable(
            $Name,
            $Directories[$Name],
            [EnvironmentVariableTarget]::Process
        )
    }
    $env:GH_TEST_REPOSITORY = $RepositoryId
    $env:GH_TEST_PACKAGE_ID = $Metadata.Id
    $env:GH_EXPECTED_EXTENSION_VERSION = $Metadata.Version
    $env:GH_EXPECTED_PRESET_COUNT = "12"
}

$TempParent = Get-WritableIsolationParent -Candidates @(
    $RepositoryTempParent,
    $SystemTempParent
)
$RunRoot = Join-Path $TempParent $RunName
New-Item -ItemType Directory -Path $RunRoot | Out-Null
$ResolvedRunRoot = (Resolve-Path -LiteralPath $RunRoot).Path
$ExpectedPrefix = (
    (Resolve-Path -LiteralPath $TempParent).Path.TrimEnd("\") +
    "\installed-extension-matrix-"
)
if (-not $ResolvedRunRoot.StartsWith(
    $ExpectedPrefix,
    [StringComparison]::OrdinalIgnoreCase
)) {
    throw "Unsafe matrix root: $ResolvedRunRoot"
}

$Succeeded = $false
$ShortcutShell = $null
$Results = @()
try {
    if (-not $PackagePath) {
        $SourceManifest = [IO.File]::ReadAllText(
            (Join-Path $RepositoryRoot "blender_manifest.toml"),
            [Text.Encoding]::UTF8
        )
        $SourceId = Get-TomlStringValue -Toml $SourceManifest -Name "id"
        $SourceVersion = Get-TomlStringValue -Toml $SourceManifest -Name "version"
        $PackagePath = Join-Path $RepositoryRoot "$SourceId-$SourceVersion.zip"
    }
    $PackagePath = (Resolve-Path -LiteralPath $PackagePath).Path
    $Metadata = Get-PackageMetadata -ArchivePath $PackagePath
    $MinimumVersion = [version]$Metadata.BlenderVersionMin
    $ShortcutShell = New-Object -ComObject WScript.Shell

    foreach ($ShortcutPath in $ShortcutPaths) {
        $BlenderExe = Resolve-BlenderExecutable `
            -ShortcutPath $ShortcutPath `
            -ShortcutShell $ShortcutShell
        $VersionKey = [IO.Path]::GetFileNameWithoutExtension($ShortcutPath) -replace '[^A-Za-z0-9._-]', '-'
        $ProfileRoot = Join-Path $RunRoot $VersionKey
        New-Item -ItemType Directory -Path $ProfileRoot | Out-Null
        $LogDirectory = Join-Path $ProfileRoot "logs"
        $BlenderVersion = Get-BlenderVersion `
            -BlenderExe $BlenderExe `
            -LogDirectory $LogDirectory `
            -Stage "version"
        Set-TestEnvironment -ProfileRoot $ProfileRoot -Metadata $Metadata
        $LocalRepository = Join-Path $ProfileRoot "repository"
        Assert-IsolatedDirectory `
            -Directory $LocalRepository `
            -IsolationRoot $ProfileRoot

        $Validate = Invoke-ProcessWithTimeout `
            -FilePath $BlenderExe `
            -Arguments @(
                "--background", "--factory-startup",
                "--command", "extension", "validate", $PackagePath
            ) `
            -LogDirectory $LogDirectory `
            -Stage "validate-package"
        Assert-SuccessfulBlenderStage `
            -Result $Validate `
            -Stage "$BlenderVersion validate-package"

        $RepoAdd = Invoke-ProcessWithTimeout `
            -FilePath $BlenderExe `
            -Arguments @(
                "--background", "--factory-startup",
                "--command", "extension", "repo-add", $RepositoryId,
                "--name", "Gesture Helper Test",
                "--directory", $LocalRepository,
                "--clear-all"
            ) `
            -LogDirectory $LogDirectory `
            -Stage "repo-add"
        Assert-SuccessfulBlenderStage `
            -Result $RepoAdd `
            -Stage "$BlenderVersion repo-add"

        $Install = Invoke-ProcessWithTimeout `
            -FilePath $BlenderExe `
            -Arguments @(
                "--background", "--command", "extension", "install-file",
                "-r", $RepositoryId, "-e", $PackagePath
            ) `
            -LogDirectory $LogDirectory `
            -Stage "install-file"

        if ($BlenderVersion -lt $MinimumVersion) {
            $InfrastructureFailure = @(
                "Traceback",
                "EXCEPTION_ACCESS_VIOLATION",
                "FATAL_ERROR",
                "Failed to write preferences",
                "Permission denied",
                "Converting py args to operator properties"
            ) -join "|"
            if ($Install.Output -match $InfrastructureFailure) {
                throw "Unsupported-version install had an infrastructure failure:`n$($Install.Output)"
            }
            $RejectionEvidence = @(
                "not compatible",
                "incompatible",
                "requires Blender",
                "blender_version_min",
                "not supported",
                "Package should have been installed but not found"
            ) -join "|"
            if ($Install.ExitCode -eq 0 -and $Install.Output -notmatch $RejectionEvidence) {
                throw (
                    "Blender $BlenderVersion unexpectedly accepted package " +
                    "requiring ${MinimumVersion}:`n$($Install.Output)"
                )
            }

            $RejectedSmoke = Invoke-ProcessWithTimeout `
                -FilePath $BlenderExe `
                -Arguments @(
                    "--background", "--python-exit-code", "1",
                    "--python", $IncompatibleSmoke
                ) `
                -LogDirectory $LogDirectory `
                -Stage "incompatible-smoke"
            Assert-SuccessfulBlenderStage `
                -Result $RejectedSmoke `
                -Stage "$BlenderVersion incompatible-smoke" `
                -RequiredMarker "INCOMPATIBLE_EXTENSION_REJECTED_OK"
            $Results += [pscustomobject]@{
                Blender = $BlenderVersion.ToString()
                Expected = "Rejected (< $MinimumVersion)"
                Result = "PASS"
                Executable = $BlenderExe
            }
            Write-Output "PASS Blender $BlenderVersion rejected incompatible package"
            continue
        }

        Assert-SuccessfulBlenderStage `
            -Result $Install `
            -Stage "$BlenderVersion install-file"
        $InstalledSmokeResult = Invoke-ProcessWithTimeout `
            -FilePath $BlenderExe `
            -Arguments @(
                "--background", "--python-exit-code", "1",
                "--python", $InstalledSmoke
            ) `
            -LogDirectory $LogDirectory `
            -Stage "installed-smoke"
        Assert-SuccessfulBlenderStage `
            -Result $InstalledSmokeResult `
            -Stage "$BlenderVersion installed-smoke" `
            -RequiredMarker "INSTALLED_EXTENSION_SMOKE_OK"
        $Results += [pscustomobject]@{
            Blender = $BlenderVersion.ToString()
            Expected = "Installed (>= $MinimumVersion)"
            Result = "PASS"
            Executable = $BlenderExe
        }
        Write-Output "PASS Blender $BlenderVersion installed and exercised package"
    }

    Write-Output ""
    Write-Output "INSTALLED_EXTENSION_MATRIX_OK $($Results.Count) versions"
    $Results | Format-Table -AutoSize
    $Succeeded = $true
}
finally {
    foreach ($Name in $EnvironmentNames) {
        [Environment]::SetEnvironmentVariable(
            $Name,
            $OriginalEnvironment[$Name],
            [EnvironmentVariableTarget]::Process
        )
    }
    if ($null -ne $ShortcutShell) {
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($ShortcutShell)
    }
    if ($Succeeded -and -not $KeepArtifacts) {
        if (-not $ResolvedRunRoot.StartsWith(
            $ExpectedPrefix,
            [StringComparison]::OrdinalIgnoreCase
        )) {
            throw "Refusing to remove unsafe matrix root: $ResolvedRunRoot"
        }
        Remove-Item -LiteralPath $ResolvedRunRoot -Recurse -Force
    }
    elseif (Test-Path -LiteralPath $ResolvedRunRoot) {
        Write-Output "Matrix artifacts retained at: $ResolvedRunRoot"
    }
}

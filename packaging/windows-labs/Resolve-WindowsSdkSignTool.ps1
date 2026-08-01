param(
    [string]$WindowsKitsRoot = (
        Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$kitsRoot = [IO.Path]::GetFullPath(
    (Resolve-Path -LiteralPath $WindowsKitsRoot).Path)
$binRoot = Join-Path $kitsRoot 'bin'
if (-not (Test-Path -LiteralPath $binRoot -PathType Container)) {
    throw 'Windows SDK bin directory is absent'
}
$rootPrefix = $kitsRoot.TrimEnd(
    [IO.Path]::DirectorySeparatorChar,
    [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
$candidates = @()
foreach ($directory in @(Get-ChildItem -LiteralPath $binRoot -Directory)) {
    $sdkVersion = $null
    if (-not [Version]::TryParse($directory.Name, [ref]$sdkVersion)) {
        continue
    }
    $candidatePath = Join-Path $directory.FullName 'x64\signtool.exe'
    if (-not (Test-Path -LiteralPath $candidatePath -PathType Leaf)) {
        continue
    }
    $resolvedPath = [IO.Path]::GetFullPath(
        (Resolve-Path -LiteralPath $candidatePath).Path)
    if (-not $resolvedPath.StartsWith(
            $rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Windows SDK SignTool candidate escaped the declared kits root'
    }
    $candidates += [pscustomobject]@{
        version = $sdkVersion
        path = $resolvedPath
    }
}
if ($candidates.Count -eq 0) {
    throw 'no versioned x64 Windows SDK SignTool candidate exists'
}

$orderedCandidates = @(
    $candidates |
        Sort-Object -Property @{ Expression = 'version'; Descending = $true },
            @{ Expression = 'path'; Descending = $false }
)
foreach ($candidate in $orderedCandidates) {
    $item = Get-Item -LiteralPath $candidate.path
    $versionInfo = $item.VersionInfo
    $signature = Get-AuthenticodeSignature -LiteralPath $candidate.path
    $microsoftSigner = $null -ne $signature.SignerCertificate -and
        $signature.SignerCertificate.Subject -match
            '(?:^|, )O=Microsoft Corporation(?:,|$)'
    if ($signature.Status -eq
            [Management.Automation.SignatureStatus]::Valid -and
        $microsoftSigner -and
        $versionInfo.CompanyName -ceq 'Microsoft Corporation' -and
        $versionInfo.OriginalFilename -ieq 'SIGNTOOL.EXE' -and
        $versionInfo.InternalName -ieq 'SignTool') {
        Write-Output $candidate.path
        exit 0
    }
}

throw 'no versioned x64 Windows SDK SignTool has valid Microsoft identity'

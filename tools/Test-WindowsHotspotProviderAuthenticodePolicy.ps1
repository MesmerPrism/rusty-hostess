#requires -Version 7.0
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Import-Module (Join-Path $repoRoot `
    "packaging\windows-hotspot-provider\WindowsAuthenticodePolicy.psm1") -Force

function Assert-RejectedBoundary {
    param([Parameter(Mandatory)][hashtable] $Observation)
    $rejected = $false
    try {
        Assert-RustyHostessProviderAuthenticodeBoundary @Observation | Out-Null
    }
    catch {
        $rejected = $true
    }
    if (-not $rejected) {
        throw "Authenticode boundary admitted a forbidden observation."
    }
}

$valid = Assert-RustyHostessProviderAuthenticodeBoundary `
    -AuthenticodeStatus valid `
    -ChainTrusted $true `
    -ChainElementCount 1 `
    -ChainStatusFlags @()
if ($valid -cne "host-chain-valid-no-public-trust-claim") {
    throw "Valid-chain assessment returned the wrong no-public-trust boundary."
}
$untrusted = Assert-RustyHostessProviderAuthenticodeBoundary `
    -AuthenticodeStatus unknown_error `
    -ChainTrusted $false `
    -ChainElementCount 1 `
    -ChainStatusFlags @("UntrustedRoot")
if ($untrusted -cne "exact-pinned-self-issued-untrusted-root-only") {
    throw "Self-issued assessment returned the wrong exact-pinned boundary."
}

foreach ($observation in @(
    @{ AuthenticodeStatus = "not_signed"; ChainTrusted = $false; ChainElementCount = 0; ChainStatusFlags = @() },
    @{ AuthenticodeStatus = "hash_mismatch"; ChainTrusted = $false; ChainElementCount = 1; ChainStatusFlags = @("UntrustedRoot") },
    @{ AuthenticodeStatus = "not_trusted"; ChainTrusted = $false; ChainElementCount = 1; ChainStatusFlags = @("UntrustedRoot") },
    @{ AuthenticodeStatus = "unknown_status"; ChainTrusted = $false; ChainElementCount = 1; ChainStatusFlags = @("UntrustedRoot") },
    @{ AuthenticodeStatus = "unknown_error"; ChainTrusted = $false; ChainElementCount = 1; ChainStatusFlags = @() },
    @{ AuthenticodeStatus = "unknown_error"; ChainTrusted = $false; ChainElementCount = 1; ChainStatusFlags = @("UntrustedRoot", "NotTimeValid") },
    @{ AuthenticodeStatus = "unknown_error"; ChainTrusted = $false; ChainElementCount = 1; ChainStatusFlags = @("PartialChain") },
    @{ AuthenticodeStatus = "unknown_error"; ChainTrusted = $false; ChainElementCount = 1; ChainStatusFlags = @("NotTimeValid") },
    @{ AuthenticodeStatus = "unknown_error"; ChainTrusted = $false; ChainElementCount = 1; ChainStatusFlags = @("Revoked") },
    @{ AuthenticodeStatus = "unknown_error"; ChainTrusted = $false; ChainElementCount = 1; ChainStatusFlags = @("NotSignatureValid") },
    @{ AuthenticodeStatus = "unknown_error"; ChainTrusted = $true; ChainElementCount = 1; ChainStatusFlags = @("UntrustedRoot") },
    @{ AuthenticodeStatus = "unknown_error"; ChainTrusted = $false; ChainElementCount = 2; ChainStatusFlags = @("UntrustedRoot") },
    @{ AuthenticodeStatus = "valid"; ChainTrusted = $false; ChainElementCount = 1; ChainStatusFlags = @() },
    @{ AuthenticodeStatus = "valid"; ChainTrusted = $true; ChainElementCount = 2; ChainStatusFlags = @() },
    @{ AuthenticodeStatus = "valid"; ChainTrusted = $true; ChainElementCount = 1; ChainStatusFlags = @("UntrustedRoot") }
)) {
    Assert-RejectedBoundary -Observation $observation
}

function New-TestCertificate {
    param(
        [string] $Subject = "CN=Rusty Hostess Test",
        [string] $EkuOid = "1.3.6.1.5.5.7.3.3"
    )
    $rsa = [Security.Cryptography.RSA]::Create(2048)
    $request = [Security.Cryptography.X509Certificates.CertificateRequest]::new(
        $Subject,
        $rsa,
        [Security.Cryptography.HashAlgorithmName]::SHA256,
        [Security.Cryptography.RSASignaturePadding]::Pkcs1
    )
    $oids = [Security.Cryptography.OidCollection]::new()
    $null = $oids.Add([Security.Cryptography.Oid]::new($EkuOid))
    $request.CertificateExtensions.Add(
        [Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new(
            $oids,
            $false
        )
    )
    $request.CertificateExtensions.Add(
        [Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new(
            [Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature,
            $false
        )
    )
    $certificate = $request.CreateSelfSigned(
        [DateTimeOffset]::UtcNow.AddMinutes(-5),
        [DateTimeOffset]::UtcNow.AddDays(2)
    )
    [pscustomobject]@{ Certificate = $certificate; Rsa = $rsa }
}

function New-TestPolicy {
    param([Parameter(Mandatory)] $Certificate)
    [pscustomobject]@{
        signer = [pscustomobject]@{
            subject = $Certificate.Subject
            issuer = $Certificate.Issuer
            thumbprint_sha1 = $Certificate.Thumbprint.Replace(" ", "").ToUpperInvariant()
            certificate_sha256 = Get-RustyHostessCertificateSha256 -Certificate $Certificate
            code_signing_eku_oid = "1.3.6.1.5.5.7.3.3"
            self_issued = $true
            timestamp_required = $true
            public_trust_claim = $false
        }
    }
}

$owned = New-TestCertificate
$wrong = New-TestCertificate
$wrongEku = New-TestCertificate -EkuOid "1.3.6.1.5.5.7.3.2"
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) (
    "rusty-hostess-authenticode-policy-" + [guid]::NewGuid().ToString("N")
)
[IO.Directory]::CreateDirectory($tempRoot) | Out-Null
try {
    $policy = New-TestPolicy -Certificate $owned.Certificate
    Assert-RustyHostessProviderSigningCertificate `
        -Certificate $owned.Certificate `
        -Policy $policy

    foreach ($rejectedCertificate in @(
        $wrong.Certificate,
        [Security.Cryptography.X509Certificates.X509Certificate2]::new(
            $owned.Certificate.RawData
        )
    )) {
        $rejected = $false
        try {
            Assert-RustyHostessProviderSigningCertificate `
                -Certificate $rejectedCertificate `
                -Policy $policy
        }
        catch { $rejected = $true }
        if (-not $rejected) {
            throw "Signing identity gate admitted a wrong or keyless certificate."
        }
    }

    $wrongEkuPolicy = New-TestPolicy -Certificate $wrongEku.Certificate
    $wrongEkuRejected = $false
    try {
        Assert-RustyHostessProviderSigningCertificate `
            -Certificate $wrongEku.Certificate `
            -Policy $wrongEkuPolicy
    }
    catch { $wrongEkuRejected = $true }
    if (-not $wrongEkuRejected) {
        throw "Signing identity gate admitted a certificate without code-signing EKU."
    }

    $signedCopy = Join-Path $tempRoot "pwsh-signed-no-timestamp.exe"
    Copy-Item -LiteralPath (Get-Process -Id $PID).Path -Destination $signedCopy
    Set-AuthenticodeSignature `
        -LiteralPath $signedCopy `
        -Certificate $owned.Certificate `
        -HashAlgorithm SHA256 | Out-Null
    $missingTimestampRejected = $false
    try {
        Get-RustyHostessProviderAuthenticodeAssessment `
            -LiteralPath $signedCopy `
            -Policy $policy | Out-Null
    }
    catch { $missingTimestampRejected = $true }
    if (-not $missingTimestampRejected) {
        throw "Production assessment admitted a signature without timestamp evidence."
    }

    $policy.signer.timestamp_required = $false
    $developmentAssessment = Get-RustyHostessProviderAuthenticodeAssessment `
        -LiteralPath $signedCopy `
        -Policy $policy
    if ($developmentAssessment.authenticode_status -cne "unknown_error" -or
        $developmentAssessment.chain_trusted -ne $false -or
        $developmentAssessment.chain_element_count -ne 1 -or
        @($developmentAssessment.chain_status_flags).Count -ne 1 -or
        $developmentAssessment.chain_status_flags[0] -cne "UntrustedRoot") {
        throw "Exact self-issued assessment did not preserve its untrusted-root boundary."
    }
    $policy.signer.timestamp_required = $true

    [IO.File]::AppendAllText($signedCopy, "tamper")
    $tamperStatus = Microsoft.PowerShell.Security\Get-AuthenticodeSignature `
        -LiteralPath $signedCopy
    if ($tamperStatus.Status -eq [Management.Automation.SignatureStatus]::Valid) {
        throw "Post-sign artifact tamper remained valid."
    }
}
finally {
    foreach ($holder in @($owned, $wrong, $wrongEku)) {
        $holder.Certificate.Dispose()
        $holder.Rsa.Dispose()
    }
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}

Write-Host "Windows hotspot provider Authenticode policy tests passed."

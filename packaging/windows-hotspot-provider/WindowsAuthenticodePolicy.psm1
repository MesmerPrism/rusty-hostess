# Copyright (C) 2026 Rusty Hostess contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RustyHostessCertificateSha256 {
    param(
        [Parameter(Mandatory)]
        [Security.Cryptography.X509Certificates.X509Certificate2] $Certificate
    )

    [Convert]::ToHexString(
        [Security.Cryptography.SHA256]::HashData($Certificate.RawData)
    ).ToLowerInvariant()
}

function Read-RustyHostessProviderReleasePolicy {
    param(
        [Parameter(Mandatory)][string] $PolicyPath,
        [Parameter(Mandatory)][string] $SchemaPath
    )

    $resolvedPolicy = (Resolve-Path -LiteralPath $PolicyPath).Path
    $resolvedSchema = (Resolve-Path -LiteralPath $SchemaPath).Path
    $policyText = Get-Content -LiteralPath $resolvedPolicy -Raw
    if (-not (Test-Json -Json $policyText -SchemaFile $resolvedSchema)) {
        throw "Windows hotspot provider release policy failed its owner schema."
    }
    $policyText | ConvertFrom-Json -Depth 10
}

function Assert-RustyHostessProviderSigningCertificate {
    param(
        [Parameter(Mandatory)]
        [Security.Cryptography.X509Certificates.X509Certificate2] $Certificate,
        [Parameter(Mandatory)] $Policy
    )

    $thumbprint = $Certificate.Thumbprint.Replace(" ", "").ToUpperInvariant()
    $certificateSha256 = Get-RustyHostessCertificateSha256 -Certificate $Certificate
    $selfIssued = $Certificate.Subject -ceq $Certificate.Issuer
    $ekuExtensions = @(
        $Certificate.Extensions |
            Where-Object { $_.Oid.Value -ceq "2.5.29.37" }
    )
    $codeSigningEku = $ekuExtensions.Count -eq 1 -and
        @(
            $ekuExtensions[0].EnhancedKeyUsages |
                Where-Object { $_.Value -ceq "1.3.6.1.5.5.7.3.3" }
        ).Count -eq 1
    if (-not $Certificate.HasPrivateKey -or
        $Certificate.Subject -cne $Policy.signer.subject -or
        $Certificate.Issuer -cne $Policy.signer.issuer -or
        $thumbprint -cne $Policy.signer.thumbprint_sha1 -or
        $certificateSha256 -cne $Policy.signer.certificate_sha256 -or
        $selfIssued -ne [bool] $Policy.signer.self_issued -or
        -not $codeSigningEku) {
        throw "Signing certificate does not equal the reviewed provider identity."
    }
}

function Test-RustyHostessCodeSigningEku {
    param(
        [Parameter(Mandatory)]
        [Security.Cryptography.X509Certificates.X509Certificate2] $Certificate
    )

    $ekuExtensions = @(
        $Certificate.Extensions |
            Where-Object { $_.Oid.Value -ceq "2.5.29.37" }
    )
    $ekuExtensions.Count -eq 1 -and
        @(
            $ekuExtensions[0].EnhancedKeyUsages |
            Where-Object { $_.Value -ceq "1.3.6.1.5.5.7.3.3" }
        ).Count -eq 1
}

function Assert-RustyHostessProviderAuthenticodeBoundary {
    param(
        [Parameter(Mandatory)]
        [ValidateSet("valid", "unknown_error", "not_signed", "hash_mismatch",
            "not_trusted", "unknown_status")]
        [string] $AuthenticodeStatus,
        [Parameter(Mandatory)][bool] $ChainTrusted,
        [Parameter(Mandatory)][int] $ChainElementCount,
        [AllowEmptyCollection()][string[]] $ChainStatusFlags = @()
    )

    $flags = @($ChainStatusFlags)
    $validBoundary = $AuthenticodeStatus -ceq "valid" -and
        $ChainTrusted -and
        $ChainElementCount -eq 1 -and
        $flags.Count -eq 0
    $selfIssuedBoundary = $AuthenticodeStatus -ceq "unknown_error" -and
        -not $ChainTrusted -and
        $ChainElementCount -eq 1 -and
        $flags.Count -eq 1 -and
        $flags[0] -ceq "UntrustedRoot"
    if (-not $validBoundary -and -not $selfIssuedBoundary) {
        throw (
            "Provider Authenticode verification is outside the reviewed " +
            "valid-or-untrusted-root-only boundary."
        )
    }
    if ($validBoundary) {
        return "host-chain-valid-no-public-trust-claim"
    }
    "exact-pinned-self-issued-untrusted-root-only"
}

function Get-RustyHostessProviderAuthenticodeAssessment {
    param(
        [Parameter(Mandatory)][string] $LiteralPath,
        [Parameter(Mandatory)] $Policy
    )

    $resolved = (Resolve-Path -LiteralPath $LiteralPath).Path
    $signature = Microsoft.PowerShell.Security\Get-AuthenticodeSignature `
        -LiteralPath $resolved
    if ($signature.SignatureType -ne
            [Management.Automation.SignatureType]::Authenticode -or
        $null -eq $signature.SignerCertificate) {
        throw "Provider artifact does not carry an Authenticode signer."
    }

    $certificate = $signature.SignerCertificate
    $thumbprint = $certificate.Thumbprint.Replace(" ", "").ToUpperInvariant()
    $certificateSha256 = Get-RustyHostessCertificateSha256 -Certificate $certificate
    $selfIssued = $certificate.Subject -ceq $certificate.Issuer
    if ($certificate.Subject -cne $Policy.signer.subject -or
        $certificate.Issuer -cne $Policy.signer.issuer -or
        $thumbprint -cne $Policy.signer.thumbprint_sha1 -or
        $certificateSha256 -cne $Policy.signer.certificate_sha256 -or
        $selfIssued -ne [bool] $Policy.signer.self_issued -or
        -not (Test-RustyHostessCodeSigningEku -Certificate $certificate) -or
        [bool] $Policy.signer.public_trust_claim) {
        throw "Provider Authenticode signer does not equal the reviewed public policy."
    }
    if ([bool] $Policy.signer.timestamp_required -and
        $null -eq $signature.TimeStamperCertificate) {
        throw "Provider Authenticode signature lacks its required timestamp evidence."
    }

    $chain = [Security.Cryptography.X509Certificates.X509Chain]::new()
    try {
        $chain.ChainPolicy.RevocationMode =
            [Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
        $chainTrusted = $chain.Build($certificate)
        $chainStatusFlags = @(
            $chain.ChainStatus |
                ForEach-Object { [string] $_.Status }
        )
        $chainElementCount = $chain.ChainElements.Count
    }
    finally {
        $chain.Dispose()
    }

    $status = switch ($signature.Status) {
        ([Management.Automation.SignatureStatus]::Valid) { "valid"; break }
        ([Management.Automation.SignatureStatus]::UnknownError) {
            "unknown_error"
            break
        }
        default { ([string] $signature.Status).ToLowerInvariant() }
    }
    $trustBoundary = Assert-RustyHostessProviderAuthenticodeBoundary `
        -AuthenticodeStatus $status `
        -ChainTrusted $chainTrusted `
        -ChainElementCount $chainElementCount `
        -ChainStatusFlags $chainStatusFlags

    [pscustomobject][ordered]@{
        state = "accepted_exact_owner_signature"
        authenticode_status = $status
        subject = $certificate.Subject
        issuer = $certificate.Issuer
        thumbprint_sha1 = $thumbprint
        certificate_sha256 = $certificateSha256
        code_signing_eku_present = $true
        self_issued = $selfIssued
        timestamp_present = $null -ne $signature.TimeStamperCertificate
        chain_trusted = [bool] $chainTrusted
        chain_element_count = [int] $chainElementCount
        chain_status_flags = @($chainStatusFlags)
        public_trust_claim = $false
        trust_boundary = $trustBoundary
    }
}

Export-ModuleMember -Function @(
    "Get-RustyHostessCertificateSha256",
    "Read-RustyHostessProviderReleasePolicy",
    "Assert-RustyHostessProviderSigningCertificate",
    "Test-RustyHostessCodeSigningEku",
    "Assert-RustyHostessProviderAuthenticodeBoundary",
    "Get-RustyHostessProviderAuthenticodeAssessment"
)

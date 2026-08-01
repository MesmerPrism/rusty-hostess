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

function Assert-RustyHostessProviderAuthenticodeEvidencePair {
    param(
        [Parameter(Mandatory)] $Recorded,
        [Parameter(Mandatory)] $Observed,
        [Parameter(Mandatory)] $Policy
    )

    $requiredFields = @(
        "state",
        "authenticode_status",
        "subject",
        "issuer",
        "thumbprint_sha1",
        "certificate_sha256",
        "code_signing_eku_present",
        "self_issued",
        "timestamp_present",
        "chain_trusted",
        "chain_element_count",
        "chain_status_flags",
        "public_trust_claim",
        "trust_boundary"
    )
    foreach ($evidence in @($Recorded, $Observed)) {
        $actualFields = @($evidence.PSObject.Properties.Name)
        foreach ($requiredField in $requiredFields) {
            if ($requiredField -cnotin $actualFields) {
                throw "Authenticode evidence is missing field '$requiredField'."
            }
        }
    }

    $recordedBoundary = Assert-RustyHostessProviderAuthenticodeBoundary `
        -AuthenticodeStatus ([string] $Recorded.authenticode_status) `
        -ChainTrusted ([bool] $Recorded.chain_trusted) `
        -ChainElementCount ([int] $Recorded.chain_element_count) `
        -ChainStatusFlags @($Recorded.chain_status_flags)
    $observedBoundary = Assert-RustyHostessProviderAuthenticodeBoundary `
        -AuthenticodeStatus ([string] $Observed.authenticode_status) `
        -ChainTrusted ([bool] $Observed.chain_trusted) `
        -ChainElementCount ([int] $Observed.chain_element_count) `
        -ChainStatusFlags @($Observed.chain_status_flags)
    if ($Recorded.trust_boundary -cne $recordedBoundary -or
        $Observed.trust_boundary -cne $observedBoundary) {
        throw "Authenticode evidence does not name its independently observed boundary."
    }

    $recordedThumbprint = ([string] $Recorded.thumbprint_sha1).
        Replace(" ", "").ToLowerInvariant()
    $observedThumbprint = ([string] $Observed.thumbprint_sha1).
        Replace(" ", "").ToLowerInvariant()
    $policyThumbprint = ([string] $Policy.signer.thumbprint_sha1).
        Replace(" ", "").ToLowerInvariant()
    $recordedCertificateSha256 = ([string] $Recorded.certificate_sha256).
        ToLowerInvariant()
    $observedCertificateSha256 = ([string] $Observed.certificate_sha256).
        ToLowerInvariant()
    $policyCertificateSha256 = ([string] $Policy.signer.certificate_sha256).
        ToLowerInvariant()

    if ($Recorded.state -cne "accepted_exact_owner_signature" -or
        $Observed.state -cne $Recorded.state -or
        $Recorded.subject -cne $Policy.signer.subject -or
        $Observed.subject -cne $Recorded.subject -or
        $Recorded.issuer -cne $Policy.signer.issuer -or
        $Observed.issuer -cne $Recorded.issuer -or
        $Recorded.subject -cne $Recorded.issuer -or
        $recordedThumbprint -cne $policyThumbprint -or
        $observedThumbprint -cne $recordedThumbprint -or
        $recordedCertificateSha256 -cne $policyCertificateSha256 -or
        $observedCertificateSha256 -cne $recordedCertificateSha256 -or
        $Recorded.code_signing_eku_present -ne $true -or
        $Observed.code_signing_eku_present -ne
            $Recorded.code_signing_eku_present -or
        $Recorded.self_issued -ne $true -or
        $Observed.self_issued -ne $Recorded.self_issued -or
        $Recorded.timestamp_present -ne $true -or
        $Observed.timestamp_present -ne $Recorded.timestamp_present -or
        $Recorded.public_trust_claim -ne $false -or
        $Observed.public_trust_claim -ne
            $Recorded.public_trust_claim -or
        $Policy.signer.code_signing_eku_oid -cne "1.3.6.1.5.5.7.3.3" -or
        $Policy.signer.self_issued -ne $true -or
        $Policy.signer.timestamp_required -ne $true -or
        [bool] $Policy.signer.public_trust_claim) {
        throw (
            "Recorded and current-host Authenticode evidence do not share " +
            "the exact owner-invariant signing identity."
        )
    }

    [pscustomobject][ordered]@{
        state = "accepted_exact_owner_signature"
        recorded_trust_boundary = $recordedBoundary
        observed_trust_boundary = $observedBoundary
        same_chain_boundary = $recordedBoundary -ceq $observedBoundary
        public_trust_claim = $false
    }
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
    "Assert-RustyHostessProviderAuthenticodeEvidencePair",
    "Get-RustyHostessProviderAuthenticodeAssessment"
)

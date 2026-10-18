"""Evidence rows for the existing companion report projection, no effects."""

SCHEMA = "rusty.hostess.sdk_graphics.iteration.v1"


def valid_report(report):
    return (report.get("schema") == SCHEMA and
             report.get("live_device_acceptance") is False and
             report.get("gpu_completion") is False and
             report.get("phase") in ("idle", "prepared", "uploaded", "adoption-pending", "unknown", "observed") and
             isinstance(report.get("events"), list) and
             isinstance(report.get("evidence_scope"), str) and
             bool(report["evidence_scope"]) and
             isinstance(report.get("reporting_errors"), list) and
             report.get("status") == ("pass" if report.get("phase") == "observed" and
                                      not report["reporting_errors"] else "warn") and
             (report.get("phase") != "observed" or report.get("pending") is None))


def project_rows(report, source, row):
    if not valid_report(report):
        return [row("sdk_graphics.invalid", "developer", "sdk_graphics", "Invalid shader adapter evidence",
                    "fail", source, authority_owner="rusty.hostess",
                    notes="No runtime, GPU or pixel acceptance can be inferred.")]
    return [row("sdk_graphics.lifecycle", "developer", "sdk_graphics", "Shader development lifecycle",
                "pass" if report["phase"] == "observed" and report.get("pending") is None and
                not report["reporting_errors"] else "warn",
                source, authority_owner="rusty.hostess", evidence_tier=report["evidence_scope"],
                evidence=report["phase"], notes="Host lifecycle only; live device and GPU acceptance remain false.",
                details={"pending": report.get("pending"), "cleanup": report.get("cleanup"),
                         "actions": report["events"], "reporting_errors": report["reporting_errors"],
                         "live_device_acceptance": False,
                         "gpu_completion": False})]

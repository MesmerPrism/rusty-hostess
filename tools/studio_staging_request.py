"""Schema-only Hostess intake for Studio staging execution requests."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.studio_staging.manifold_handoff_intake import (
    build_hostess_manifold_shell_handoff_review_intake_receipt,
    hostess_manifold_shell_handoff_review_intake_receipt_checks,
    hostess_manifold_shell_handoff_review_intake_receipt_no_runtime_started,
    hostess_manifold_shell_handoff_review_intake_source_ready,
    manifold_shell_handoff_endpoint_ids,
    manifold_shell_handoff_review_receipt_no_runtime_started,
    manifold_shell_handoff_stream_ids,
    manifold_shell_handoff_transport_ids,
    selected_manifold_shell_handoff_from_selection,
    validate_hostess_manifold_shell_handoff_review_intake_receipt,
)
from tools.studio_staging.makepad_shell_contract import (
    HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_SCHEMA,
    HOSTESS_MAKEPAD_SHELL_LAUNCH_HANDOFF_RECEIPT_VALIDATION_SCHEMA,
    HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_SCHEMA,
    HOSTESS_MAKEPAD_SHELL_CONTRACT_RECEIPT_VALIDATION_SCHEMA,
    build_hostess_makepad_shell_launch_handoff_receipt,
    build_hostess_makepad_shell_contract_receipt,
    hostess_makepad_shell_launch_handoff_receipt_no_runtime_started,
    hostess_makepad_shell_launch_handoff_source_ready,
    hostess_makepad_shell_contract_intake_no_runtime_started,
    hostess_makepad_shell_contract_receipt_checks,
    hostess_makepad_shell_contract_receipt_no_runtime_started,
    hostess_makepad_shell_contract_source_ready,
    validate_hostess_makepad_shell_launch_handoff_receipt,
    validate_hostess_makepad_shell_contract_receipt,
)


from tools.studio_staging.request_shared import *  # re-exported facade symbols

from tools.studio_staging.request_intake import *  # re-exported facade symbols

from tools.studio_staging.smoke_workflow import *  # re-exported facade symbols

from tools.studio_staging.platform_smoke import *  # re-exported facade symbols

from tools.studio_staging.pmb_release import *  # re-exported facade symbols

from tools.studio_staging.staging_handoff import *  # re-exported facade symbols

from tools.studio_staging.request_cli import main


if __name__ == "__main__":
    raise SystemExit(main())

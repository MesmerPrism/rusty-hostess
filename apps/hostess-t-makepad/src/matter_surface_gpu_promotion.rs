//! Low-rate GPU force-authority promotion readiness consumed by Hostess.
//!
//! Hostess only carries profile/evidence receipts into the Quest-Makepad
//! residency tracker. Matter remains the CPU oracle and Quest-Makepad owns the
//! GPU adapter decision.

use rusty_quest_makepad_camera_shell::QuestMakepadGpuForceProviderAbReceipt;

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub(crate) struct MatterSurfaceGpuForcePromotionReadiness {
    provider_ab_receipt: QuestMakepadGpuForceProviderAbReceipt,
}

impl MatterSurfaceGpuForcePromotionReadiness {
    pub(crate) const fn from_provider_ab_receipt(
        provider_ab_receipt: QuestMakepadGpuForceProviderAbReceipt,
    ) -> Self {
        Self {
            provider_ab_receipt,
        }
    }

    pub(crate) const fn live_recorded_provider_ab_ready(self) -> bool {
        self.provider_ab_receipt.live_recorded_provider_ab_ready()
    }
}

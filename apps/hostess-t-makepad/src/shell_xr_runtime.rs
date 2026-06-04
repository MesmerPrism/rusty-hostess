use makepad_widgets::makepad_platform::event::XrUpdateEvent;

#[derive(Clone, Debug, Default)]
pub(crate) struct ShellXrRuntimeState {
    xr_root_registered: bool,
    xr_update_observed: bool,
    xr_update_count: u64,
    in_xr_mode_observed: bool,
    controller_pose_provider_observed: bool,
    left_controller_active: bool,
    right_controller_active: bool,
    last_xr_time_s: Option<f64>,
}

impl ShellXrRuntimeState {
    pub(crate) fn registered_xr_shell() -> Self {
        Self {
            xr_root_registered: true,
            ..Self::default()
        }
    }

    pub(crate) fn observe_update(&mut self, in_xr_mode: bool, update: &XrUpdateEvent) -> bool {
        let before = self.clone();
        self.xr_update_observed = true;
        self.xr_update_count = self.xr_update_count.saturating_add(1);
        self.in_xr_mode_observed |= in_xr_mode;
        self.last_xr_time_s = Some(update.state.time);

        self.left_controller_active = update.state.left_controller.active();
        self.right_controller_active = update.state.right_controller.active();
        self.controller_pose_provider_observed =
            self.left_controller_active || self.right_controller_active;

        self.differs_from(&before)
    }

    pub(crate) fn xr_root_registered(&self) -> bool {
        self.xr_root_registered
    }

    pub(crate) fn xr_update_observed(&self) -> bool {
        self.xr_update_observed
    }

    pub(crate) fn xr_update_count(&self) -> u64 {
        self.xr_update_count
    }

    pub(crate) fn in_xr_mode_observed(&self) -> bool {
        self.in_xr_mode_observed
    }

    pub(crate) fn controller_pose_provider_observed(&self) -> bool {
        self.controller_pose_provider_observed
    }

    pub(crate) fn left_controller_active(&self) -> bool {
        self.left_controller_active
    }

    pub(crate) fn right_controller_active(&self) -> bool {
        self.right_controller_active
    }

    pub(crate) fn last_xr_time_s(&self) -> Option<f64> {
        self.last_xr_time_s
    }

    pub(crate) fn status_line(&self) -> String {
        if self.xr_update_observed {
            return format!(
                "xr updates {} / controller {}",
                self.xr_update_count,
                if self.controller_pose_provider_observed {
                    "observed"
                } else {
                    "waiting"
                }
            );
        }
        if self.xr_root_registered {
            return "xr root registered / waiting for update".to_string();
        }
        "xr root not registered".to_string()
    }

    fn differs_from(&self, other: &Self) -> bool {
        self.xr_root_registered != other.xr_root_registered
            || self.xr_update_observed != other.xr_update_observed
            || self.xr_update_count != other.xr_update_count
            || self.in_xr_mode_observed != other.in_xr_mode_observed
            || self.controller_pose_provider_observed != other.controller_pose_provider_observed
            || self.left_controller_active != other.left_controller_active
            || self.right_controller_active != other.right_controller_active
            || self.last_xr_time_s != other.last_xr_time_s
    }

    #[cfg(test)]
    pub(crate) fn test_observed_xr_controller() -> Self {
        Self {
            xr_root_registered: true,
            xr_update_observed: true,
            xr_update_count: 3,
            in_xr_mode_observed: true,
            controller_pose_provider_observed: true,
            left_controller_active: false,
            right_controller_active: true,
            last_xr_time_s: Some(12.5),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use makepad_widgets::makepad_platform::event::{XrController, XrState};
    use std::rc::Rc;

    #[test]
    fn observes_xr_update_and_active_controller() {
        let mut runtime = ShellXrRuntimeState::registered_xr_shell();
        let mut state = XrState::default();
        state.time = 12.5;
        state.right_controller.buttons = XrController::ACTIVE;
        let state = Rc::new(state);
        let update = XrUpdateEvent {
            state: state.clone(),
            last: state,
        };

        assert!(runtime.observe_update(true, &update));

        assert!(runtime.xr_root_registered());
        assert!(runtime.xr_update_observed());
        assert_eq!(runtime.xr_update_count(), 1);
        assert!(runtime.in_xr_mode_observed());
        assert!(runtime.controller_pose_provider_observed());
        assert!(!runtime.left_controller_active());
        assert!(runtime.right_controller_active());
        assert_eq!(runtime.last_xr_time_s(), Some(12.5));
    }
}

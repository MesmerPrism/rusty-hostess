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

        self.left_controller_active = controller_pose_ready(
            update.state.left_controller.active(),
            &update.state.left_controller.grip_pose,
            &update.state.left_controller.aim_pose,
        );
        self.right_controller_active = controller_pose_ready(
            update.state.right_controller.active(),
            &update.state.right_controller.grip_pose,
            &update.state.right_controller.aim_pose,
        );
        self.controller_pose_provider_observed |=
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

    #[allow(dead_code)]
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
            || self.in_xr_mode_observed != other.in_xr_mode_observed
            || self.controller_pose_provider_observed != other.controller_pose_provider_observed
            || self.left_controller_active != other.left_controller_active
            || self.right_controller_active != other.right_controller_active
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

fn controller_pose_ready(
    active: bool,
    grip_pose: &makepad_widgets::makepad_platform::makepad_math::Pose,
    aim_pose: &makepad_widgets::makepad_platform::makepad_math::Pose,
) -> bool {
    active && (grip_pose.is_finite() || aim_pose.is_finite())
}

#[cfg(test)]
mod tests {
    use super::*;
    use makepad_widgets::makepad_platform::event::{XrController, XrState};
    use makepad_widgets::makepad_platform::makepad_math::{Quat, Vec3};
    use std::rc::Rc;

    fn xr_update(time: f64, right_buttons: u16) -> XrUpdateEvent {
        let mut state = XrState::default();
        state.time = time;
        state.right_controller.buttons = right_buttons;
        state.right_controller.grip_pose.position = Vec3 {
            x: 0.1,
            y: 0.2,
            z: 0.3,
        };
        state.right_controller.grip_pose.orientation = Quat {
            x: 0.0,
            y: 0.0,
            z: 0.0,
            w: 1.0,
        };
        state.right_controller.aim_pose = state.right_controller.grip_pose;
        let state = Rc::new(state);
        XrUpdateEvent {
            state: state.clone(),
            last: state,
        }
    }

    #[test]
    fn observes_xr_update_and_active_controller() {
        let mut runtime = ShellXrRuntimeState::registered_xr_shell();
        let update = xr_update(12.5, XrController::ACTIVE);

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

    #[test]
    fn repeated_xr_updates_do_not_request_receipt_rewrite_for_count_only() {
        let mut runtime = ShellXrRuntimeState::registered_xr_shell();
        let first = xr_update(12.5, 0);
        let second = xr_update(12.6, 0);

        assert!(runtime.observe_update(true, &first));
        assert!(!runtime.observe_update(true, &second));

        assert_eq!(runtime.xr_update_count(), 2);
        assert_eq!(runtime.last_xr_time_s(), Some(12.6));
        assert!(!runtime.controller_pose_provider_observed());
    }

    #[test]
    fn controller_provider_observation_is_sticky_after_inactive_frame() {
        let mut runtime = ShellXrRuntimeState::registered_xr_shell();
        let active = xr_update(12.5, XrController::ACTIVE);
        let inactive = xr_update(12.6, 0);

        assert!(runtime.observe_update(true, &active));
        assert!(runtime.controller_pose_provider_observed());
        assert!(runtime.right_controller_active());

        assert!(runtime.observe_update(true, &inactive));
        assert!(runtime.controller_pose_provider_observed());
        assert!(!runtime.right_controller_active());
    }

    #[test]
    fn active_controller_with_invalid_pose_does_not_satisfy_provider_gate() {
        let mut runtime = ShellXrRuntimeState::registered_xr_shell();
        let mut state = XrState::default();
        state.time = 12.5;
        state.right_controller.buttons = XrController::ACTIVE;
        state.right_controller.grip_pose.position.x = f32::NAN;
        state.right_controller.aim_pose.position.x = f32::NAN;
        let state = Rc::new(state);
        let update = XrUpdateEvent {
            state: state.clone(),
            last: state,
        };

        assert!(runtime.observe_update(true, &update));

        assert!(runtime.xr_update_observed());
        assert!(!runtime.controller_pose_provider_observed());
        assert!(!runtime.right_controller_active());
    }

    #[test]
    fn active_controller_with_one_finite_pose_satisfies_provider_gate() {
        let mut runtime = ShellXrRuntimeState::registered_xr_shell();
        let mut state = XrState::default();
        state.time = 12.5;
        state.right_controller.buttons = XrController::ACTIVE;
        state.right_controller.grip_pose.position.x = f32::NAN;
        state.right_controller.aim_pose.orientation = Quat {
            x: 0.0,
            y: 0.0,
            z: 0.0,
            w: 1.0,
        };
        let state = Rc::new(state);
        let update = XrUpdateEvent {
            state: state.clone(),
            last: state,
        };

        assert!(runtime.observe_update(true, &update));

        assert!(runtime.controller_pose_provider_observed());
        assert!(runtime.right_controller_active());
    }
}

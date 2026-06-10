//! Hostess-local Makepad smoke renderer for Quest Makepad world-particle batches.
//!
//! Rusty Matter, Optics, and Quest-Makepad own runtime truth and renderer-neutral
//! rows. This module is the temporary Hostess Makepad widget implementation; a
//! reusable renderer should move to a dedicated Makepad adapter crate before reuse.

use crate::makepad_widgets::*;
use makepad_xr::scene::{xr_widget_world_transform, XrNode};
use rusty_quest_makepad_camera_shell::QuestMakepadWorldParticleBatch;

pub(crate) const HOSTESS_WORLD_PARTICLE_BILLBOARD_DRAW_LIMIT_MAX: usize = 512;

#[derive(Script, Widget)]
pub struct MatterWorldParticleBillboardCloud {
    #[redraw]
    #[live]
    draw_cube: DrawCube,
    #[rust]
    batch: Option<QuestMakepadWorldParticleBatch>,
    #[rust]
    draw_limit: usize,
    #[cast]
    #[deref]
    node: XrNode,
}

impl MatterWorldParticleBillboardCloud {
    pub(crate) fn set_world_particle_batch(
        &mut self,
        cx: &mut Cx,
        batch: Option<QuestMakepadWorldParticleBatch>,
        draw_limit: usize,
    ) {
        let draw_limit = draw_limit.min(HOSTESS_WORLD_PARTICLE_BILLBOARD_DRAW_LIMIT_MAX);
        if self.batch == batch && self.draw_limit == draw_limit {
            return;
        }
        self.batch = batch;
        self.draw_limit = draw_limit;
        self.node.redraw(cx);
    }

    fn draw_particle_billboard(
        &mut self,
        cx: &mut Cx3d,
        transform: Mat4f,
        center_radius: [f32; 4],
        color: [f32; 4],
        normal_frame: [f32; 4],
        aux: [f32; 4],
    ) {
        let radius = center_radius[3].clamp(0.012, 0.044);
        let diameter = (radius * 2.0).clamp(0.032, 0.088);
        let frame01 = normal_frame[3].clamp(0.0, 0.999_985);
        let rotation = if aux[0].is_finite() {
            aux[0]
        } else {
            frame01 * std::f32::consts::TAU
        };
        let normal_len_sq = normal_frame[0] * normal_frame[0]
            + normal_frame[1] * normal_frame[1]
            + normal_frame[2] * normal_frame[2];
        let normal = if normal_len_sq.is_finite() && normal_len_sq > 1.0e-8 {
            [normal_frame[0], normal_frame[1], normal_frame[2]]
        } else {
            [0.0, 0.0, 1.0]
        };
        let alpha = color[3].clamp(0.18, 0.72);
        let emission = 1.45 + alpha * 1.35;
        self.draw_cube.transform = transform;
        self.draw_cube.cube_pos = vec3(center_radius[0], center_radius[1], center_radius[2]);
        self.draw_cube.cube_size = vec3(diameter, frame01, rotation);
        self.draw_cube.light_dir = vec3(normal[0], normal[1], normal[2]);
        self.draw_cube.color = vec4f(
            (color[0] * emission).clamp(0.20, 1.0),
            (color[1] * emission).clamp(0.32, 1.0),
            (color[2] * emission).clamp(0.46, 1.0),
            alpha,
        );
        self.draw_cube.depth_clip = 1.0;
        self.draw_cube.draw(cx);
    }
}

impl ScriptHook for MatterWorldParticleBillboardCloud {}

impl Widget for MatterWorldParticleBillboardCloud {
    fn draw_3d(&mut self, cx: &mut Cx3d, scope: &mut Scope) -> DrawStep {
        if cx.scene_state_3d().is_none() {
            return self.node.draw_3d(cx, scope);
        }
        let Some(batch) = self.batch.clone() else {
            return self.node.draw_3d(cx, scope);
        };
        if batch.instances.is_empty() {
            return self.node.draw_3d(cx, scope);
        }

        let transform = xr_widget_world_transform(cx, scope, self.widget_uid(), &self.node);
        self.draw_cube.begin_many_instances(cx);
        for instance in batch.instances.iter().take(self.draw_limit) {
            self.draw_particle_billboard(
                cx,
                transform,
                instance.center_radius,
                instance.color,
                instance.normal_frame,
                instance.aux,
            );
        }
        self.draw_cube.end_many_instances(cx);

        self.node.draw_3d(cx, scope)
    }

    fn draw_walk(&mut self, _cx: &mut Cx2d, _scope: &mut Scope, _walk: Walk) -> DrawStep {
        DrawStep::done()
    }
}

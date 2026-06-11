//! Hostess-local Makepad smoke renderer for Quest-Makepad ADF debug batches.
//!
//! The ADF field and renderer-neutral visual are owned by Matter and Optics.
//! Quest-Makepad adapts them into bounded world rows. This widget only draws
//! those rows for install/test evidence.

use crate::makepad_widgets::*;
use makepad_xr::scene::{xr_widget_world_transform, XrNode};
use rusty_quest_makepad_camera_shell::QuestMakepadWorldAdfDebugBatch;

pub(crate) const HOSTESS_WORLD_ADF_DEBUG_DRAW_LIMIT_MAX: usize = 2048;
pub(crate) const HOSTESS_WORLD_ADF_DEBUG_RENDERER_ID: &str = "hostess-makepad-adf-debug-cell-boxes";

#[derive(Script, Widget)]
pub struct MatterWorldAdfDebugCells {
    #[redraw]
    #[live]
    draw_cube: DrawCube,
    #[rust]
    batch: Option<QuestMakepadWorldAdfDebugBatch>,
    #[rust]
    draw_limit: usize,
    #[cast]
    #[deref]
    node: XrNode,
}

impl MatterWorldAdfDebugCells {
    pub(crate) fn set_world_adf_debug_batch(
        &mut self,
        cx: &mut Cx,
        batch: Option<QuestMakepadWorldAdfDebugBatch>,
        draw_limit: usize,
    ) {
        let draw_limit = draw_limit.min(HOSTESS_WORLD_ADF_DEBUG_DRAW_LIMIT_MAX);
        if self.batch == batch && self.draw_limit == draw_limit {
            return;
        }
        self.batch = batch;
        self.draw_limit = draw_limit;
        self.node.redraw(cx);
    }

    fn draw_adf_cell(
        &mut self,
        cx: &mut Cx3d,
        transform: Mat4f,
        center_extent: [f32; 4],
        distance: [f32; 4],
        meta: [f32; 4],
    ) {
        let extent = center_extent[3].clamp(0.002, 0.080);
        let distance01 = distance[3].clamp(0.0, 1.0);
        let range01 = meta[1].clamp(0.0, 1.0);
        let level01 = (meta[0] / 8.0).clamp(0.0, 1.0);
        let alpha = (0.12 + range01 * 0.22 + level01 * 0.10).clamp(0.10, 0.42);
        self.draw_cube.transform = transform;
        self.draw_cube.cube_pos = vec3(center_extent[0], center_extent[1], center_extent[2]);
        self.draw_cube.cube_size = vec3(extent, extent, extent);
        self.draw_cube.light_dir = vec3(0.35, 0.55, 1.0);
        self.draw_cube.color = vec4f(
            (0.12 + distance01 * 0.72 + range01 * 0.12).clamp(0.12, 1.0),
            (0.46 + (1.0 - distance01) * 0.34).clamp(0.20, 1.0),
            (0.95 - distance01 * 0.46 + level01 * 0.12).clamp(0.28, 1.0),
            alpha,
        );
        self.draw_cube.depth_clip = 1.0;
        self.draw_cube.draw(cx);
    }
}

impl ScriptHook for MatterWorldAdfDebugCells {}

impl Widget for MatterWorldAdfDebugCells {
    fn draw_3d(&mut self, cx: &mut Cx3d, scope: &mut Scope) -> DrawStep {
        if cx.scene_state_3d().is_none() {
            return self.node.draw_3d(cx, scope);
        }
        let Some(batch) = self.batch.clone() else {
            return self.node.draw_3d(cx, scope);
        };
        if batch.cells.is_empty() {
            return self.node.draw_3d(cx, scope);
        }

        let transform = xr_widget_world_transform(cx, scope, self.widget_uid(), &self.node);
        self.draw_cube.begin_many_instances(cx);
        for cell in batch.cells.iter().take(self.draw_limit) {
            self.draw_adf_cell(cx, transform, cell.center_extent, cell.distance, cell.meta);
        }
        self.draw_cube.end_many_instances(cx);

        self.node.draw_3d(cx, scope)
    }

    fn draw_walk(&mut self, _cx: &mut Cx2d, _scope: &mut Scope, _walk: Walk) -> DrawStep {
        DrawStep::done()
    }
}

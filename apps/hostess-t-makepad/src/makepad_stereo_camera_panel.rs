use crate::camera_pair::makepad_display_left_from_right_source;
use crate::camera_texture_path::MakepadCameraTexturePath;
use crate::makepad_diagnostics::{
    emit_marker_line, mesh_replay_segment_vec4, MakepadCameraYuvTextures,
    MakepadTargetFootprintPush,
};
use crate::makepad_effective_settings::MakepadCameraShellFeatureUniforms;
use crate::makepad_widgets::makepad_platform::{LiveId, TextureFormat, TextureUpdated};
use crate::makepad_widgets::*;
use crate::matter_particle_texture::{MatterParticleTextureFrame, MATTER_PARTICLE_TEXTURE_SLOT};
use crate::matter_surface_uniforms::MakepadMatterSurfaceUniforms;
use crate::projection_geometry::makepad_visible_panel_draw_marker_line;
use crate::projection_settings::*;
use crate::projection_target_controls::{
    makepad_projection_target_offset_x_uv, makepad_projection_target_offset_y_uv,
    makepad_projection_target_scale,
};
use crate::runtime_settings::*;
use crate::source_metadata::{
    makepad_runtime_target_screen_footprint_pair, MakepadTargetScreenFootprintPair,
};
use makepad_xr::scene::{xr_widget_world_transform, XrNode};
use rusty_quest_makepad_camera_shell::MeshReplayUniforms;
use std::sync::atomic::{AtomicBool, Ordering};

static CAMERA_PANEL_DRAW_MARKER_EMITTED: AtomicBool = AtomicBool::new(false);
#[derive(Script, ScriptHook, Debug)]
#[repr(C)]
pub struct DrawMakepadStereoCameraPanel {
    #[rust(vec3(1.0, 1.0, 1.0))]
    pub cube_size: Vec3f,
    #[rust(vec3(0.0, 0.0, 0.0))]
    pub cube_pos: Vec3f,
    #[rust(0.0_f32)]
    pub depth_clip: f32,
    #[rust(1.0_f32)]
    pub camera_ready: f32,
    #[rust(0.0_f32)]
    pub left_rotation_steps: f32,
    #[rust(0.0_f32)]
    pub right_rotation_steps: f32,
    #[rust(1.0_f32)]
    pub exposure: f32,
    #[rust(0.0_f32)]
    pub diagnostic_solid: f32,
    #[rust(0.0_f32)]
    pub alignment_guide: f32,
    #[rust(1.0_f32)]
    pub yuv_mode: f32,
    #[rust(1.0_f32)]
    pub yuv_matrix: f32,
    #[rust(0.0_f32)]
    pub yuv_biplanar: f32,
    #[rust(2.0_f32)]
    pub texture_probe_mode: f32,
    #[rust(0.0_f32)]
    pub proof_tint_strength: f32,
    #[rust(1.9811321_f32)]
    pub content_uv_scale: f32,
    #[rust(0.032_f32)]
    pub display_eye_offset_meters: f32,
    #[rust(92.0_f32)]
    pub display_fov_y_degrees: f32,
    #[rust(1.0_f32)]
    pub display_aspect: f32,
    #[rust(0.5_f32)]
    pub projection_depth_meters: f32,
    #[rust(0.0_f32)]
    pub projection_preview_offset_y_meters: f32,
    #[rust(60.0_f32)]
    pub projection_preview_fov_y_degrees: f32,
    #[rust(1.06_f32)]
    pub projection_raw_overscan: f32,
    #[rust(1.0_f32)]
    pub suppress_live_camera_sampling: f32,
    #[rust(1.0_f32)]
    pub force_full_surface_live_camera_uv: f32,
    #[rust(1.0_f32)]
    pub force_in_surface_camera_window: f32,
    #[rust(1.0_f32)]
    pub projection_border_opacity: f32,
    #[rust(0.0_f32)]
    pub projection_border_policy: f32,
    #[rust(0.0_f32)]
    pub processing_layer: f32,
    #[rust(0.0_f32)]
    pub projection_sample_mode: f32,
    #[rust(2.0_f32)]
    pub blur_radius_px: f32,
    #[rust(1.0_f32)]
    pub peripheral_stretch_core_scale: f32,
    #[rust(0.015_f32)]
    pub peripheral_stretch_edge_inset_uv: f32,
    #[rust(0.14_f32)]
    pub peripheral_stretch_max_inset_uv: f32,
    #[rust(1.6_f32)]
    pub peripheral_stretch_curve: f32,
    #[rust(0.040_f32)]
    pub peripheral_stretch_inner_blend_uv: f32,
    #[rust(1.6_f32)]
    pub peripheral_stretch_blend_curve: f32,
    #[rust(1.0_f32)]
    pub peripheral_stretch_blend_mode: f32,
    #[rust(0.0_f32)]
    pub peripheral_stretch_debug: f32,
    #[rust(0.0_f32)]
    pub projection_area_diagnostic: f32,
    #[rust(0.0_f32)]
    pub projection_area_offset_left_uv: f32,
    #[rust(0.0_f32)]
    pub projection_area_offset_right_uv: f32,
    #[rust(0.0_f32)]
    pub projection_area_offset_vertical_uv: f32,
    #[rust(1.0_f32)]
    pub projection_area_scale_x: f32,
    #[rust(1.0_f32)]
    pub projection_area_scale_y: f32,
    #[rust(vec4(0.0, 0.0, 1.0, 0.0))]
    pub projection_target_runtime: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.5, 0.5))]
    pub left_projection_area_offset_radius_uv: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.5, 0.5))]
    pub right_projection_area_offset_radius_uv: Vec4f,
    #[rust(0.5_f32)]
    pub projection_area_radius_x_uv: f32,
    #[rust(0.5_f32)]
    pub projection_area_radius_y_uv: f32,
    #[rust(0.0_f32)]
    pub projection_area_corner_radius_uv: f32,
    #[rust(0.0_f32)]
    pub projection_area_keystone_x: f32,
    #[rust(0.0_f32)]
    pub projection_area_bow_x: f32,
    #[rust(1.0_f32)]
    pub projection_area_opacity: f32,
    #[rust(0.0_f32)]
    pub projection_alpha_mode: f32,
    #[rust(1.0_f32)]
    pub projection_alpha_scale: f32,
    #[rust(0.0_f32)]
    pub projection_alpha_bias: f32,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub mesh_replay_runtime: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub mesh_replay_segment0: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub mesh_replay_segment1: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub mesh_replay_segment2: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub mesh_replay_segment3: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub camera_shell_feature_runtime: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_surface_runtime: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_collision_contact: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_collision_normal: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_sdf_sample0: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_sdf_sample1: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_sdf_sample2: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_sdf_sample3: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_particle0: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_particle1: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_particle2: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_particle3: Vec4f,
    #[rust(vec4(0.0, 0.0, 0.0, 0.0))]
    pub matter_particle_texture_runtime: Vec4f,
    #[rust(1.0_f32)]
    pub source_sample_y_flip: f32,
    #[rust(0.0_f32)]
    pub projection_content_mapping_mode: f32,
    #[rust(1.0_f32)]
    pub display_source_eye_swap: f32,
    #[rust(1.0_f32)]
    pub horizontal_alignment_strength: f32,
    #[rust(0.0_f32)]
    pub manual_horizontal_offset_left_uv: f32,
    #[rust(0.0_f32)]
    pub manual_horizontal_offset_right_uv: f32,
    #[rust(0.0_f32)]
    pub manual_vertical_offset_uv: f32,
    #[rust(1.0_f32)]
    pub left_projection_h00: f32,
    #[rust(0.0_f32)]
    pub left_projection_h01: f32,
    #[rust(0.0_f32)]
    pub left_projection_h02: f32,
    #[rust(0.0_f32)]
    pub left_projection_h10: f32,
    #[rust(1.0_f32)]
    pub left_projection_h11: f32,
    #[rust(0.0_f32)]
    pub left_projection_h12: f32,
    #[rust(0.0_f32)]
    pub left_projection_h20: f32,
    #[rust(0.0_f32)]
    pub left_projection_h21: f32,
    #[rust(1.0_f32)]
    pub left_projection_h22: f32,
    #[rust(1.0_f32)]
    pub right_projection_h00: f32,
    #[rust(0.0_f32)]
    pub right_projection_h01: f32,
    #[rust(0.0_f32)]
    pub right_projection_h02: f32,
    #[rust(0.0_f32)]
    pub right_projection_h10: f32,
    #[rust(1.0_f32)]
    pub right_projection_h11: f32,
    #[rust(0.0_f32)]
    pub right_projection_h12: f32,
    #[rust(0.0_f32)]
    pub right_projection_h20: f32,
    #[rust(0.0_f32)]
    pub right_projection_h21: f32,
    #[rust(1.0_f32)]
    pub right_projection_h22: f32,
    #[rust(1.0_f32)]
    pub left_screen_to_camera_h00: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_camera_h01: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_camera_h02: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_camera_h10: f32,
    #[rust(1.0_f32)]
    pub left_screen_to_camera_h11: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_camera_h12: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_camera_h20: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_camera_h21: f32,
    #[rust(1.0_f32)]
    pub left_screen_to_camera_h22: f32,
    #[rust(1.0_f32)]
    pub right_screen_to_camera_h00: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_camera_h01: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_camera_h02: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_camera_h10: f32,
    #[rust(1.0_f32)]
    pub right_screen_to_camera_h11: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_camera_h12: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_camera_h20: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_camera_h21: f32,
    #[rust(1.0_f32)]
    pub right_screen_to_camera_h22: f32,
    #[rust(1.0_f32)]
    pub left_screen_to_surface_h00: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_surface_h01: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_surface_h02: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_surface_h10: f32,
    #[rust(1.0_f32)]
    pub left_screen_to_surface_h11: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_surface_h12: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_surface_h20: f32,
    #[rust(0.0_f32)]
    pub left_screen_to_surface_h21: f32,
    #[rust(1.0_f32)]
    pub left_screen_to_surface_h22: f32,
    #[rust(1.0_f32)]
    pub right_screen_to_surface_h00: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_surface_h01: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_surface_h02: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_surface_h10: f32,
    #[rust(1.0_f32)]
    pub right_screen_to_surface_h11: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_surface_h12: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_surface_h20: f32,
    #[rust(0.0_f32)]
    pub right_screen_to_surface_h21: f32,
    #[rust(1.0_f32)]
    pub right_screen_to_surface_h22: f32,
    #[deref]
    pub draw_vars: DrawVars,
    #[live(0.0_f32)]
    pub makepad_instance_marker: f32,
}

impl DrawMakepadStereoCameraPanel {
    fn assign_texture_slot(&mut self, slot: usize, texture: Option<Texture>) {
        match texture {
            Some(texture) => self.draw_vars.set_texture(slot, &texture),
            None => self.draw_vars.empty_texture(slot),
        }
    }

    pub(crate) fn set_camera_textures(
        &mut self,
        cx: &mut Cx,
        left: Option<Texture>,
        right: Option<Texture>,
    ) {
        self.assign_texture_slot(0, left);
        self.assign_texture_slot(1, right);
        self.draw_vars.redraw(cx);
    }

    fn set_camera_yuv_textures(
        &mut self,
        cx: &mut Cx,
        left: Option<MakepadCameraYuvTextures>,
        right: Option<MakepadCameraYuvTextures>,
        texture_path: MakepadCameraTexturePath,
    ) {
        let left_effective = left.clone().or_else(|| right.clone());
        let right_effective = right.clone().or_else(|| left_effective.clone());
        self.assign_texture_slot(
            2,
            left_effective.as_ref().map(|textures| textures.y.clone()),
        );
        self.assign_texture_slot(
            3,
            left_effective.as_ref().map(|textures| textures.u.clone()),
        );
        self.assign_texture_slot(
            4,
            left_effective.as_ref().map(|textures| textures.v.clone()),
        );
        self.assign_texture_slot(
            5,
            right_effective.as_ref().map(|textures| textures.y.clone()),
        );
        self.assign_texture_slot(
            6,
            right_effective.as_ref().map(|textures| textures.u.clone()),
        );
        self.assign_texture_slot(
            7,
            right_effective.as_ref().map(|textures| textures.v.clone()),
        );
        self.yuv_mode = if left_effective.is_some() && right_effective.is_some() {
            texture_path.yuv_mode()
        } else {
            0.0
        };
        self.draw_vars.redraw(cx);
    }

    fn draw(&mut self, cx: &mut CxDraw) {
        if self.draw_vars.can_instance() {
            let new_area = cx.add_instance(&self.draw_vars);
            self.draw_vars.area = cx.update_area_refs(self.draw_vars.area, new_area);
        }
    }
}

#[derive(Script, Widget)]
pub struct MakepadStereoCameraPanel {
    #[redraw]
    #[live]
    draw_panel: DrawMakepadStereoCameraPanel,
    #[live(vec3(0.92, 0.52, 0.010))]
    size: Vec3f,
    #[rust(false)]
    camera_ready: bool,
    #[rust(true)]
    camera_streaming_enabled: bool,
    #[cast]
    #[deref]
    node: XrNode,
    #[rust]
    synthetic_luma_probe_texture: Option<Texture>,
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct HorizontalAlignmentTuning {
    pub(crate) strength: f32,
    pub(crate) left_offset_uv: f32,
    pub(crate) right_offset_uv: f32,
    pub(crate) vertical_offset_uv: f32,
    pub(crate) content_uv_scale: f32,
    pub(crate) projection_border_opacity: f32,
    pub(crate) projection_border_policy: f32,
    pub(crate) processing_layer: f32,
    pub(crate) projection_sample_mode: f32,
    pub(crate) blur_radius_px: f32,
    pub(crate) peripheral_stretch_core_scale: f32,
    pub(crate) peripheral_stretch_edge_inset_uv: f32,
    pub(crate) peripheral_stretch_max_inset_uv: f32,
    pub(crate) peripheral_stretch_curve: f32,
    pub(crate) peripheral_stretch_inner_blend_uv: f32,
    pub(crate) peripheral_stretch_blend_curve: f32,
    pub(crate) peripheral_stretch_blend_mode: f32,
    pub(crate) peripheral_stretch_debug: f32,
    pub(crate) projection_area_diagnostic: f32,
    pub(crate) projection_area_offset_left_uv: f32,
    pub(crate) projection_area_offset_right_uv: f32,
    pub(crate) projection_area_offset_vertical_uv: f32,
    pub(crate) projection_area_scale_x: f32,
    pub(crate) projection_area_scale_y: f32,
    pub(crate) projection_target_offset_x_uv: f32,
    pub(crate) projection_target_offset_y_uv: f32,
    pub(crate) projection_target_scale: f32,
    pub(crate) projection_area_radius_x_uv: f32,
    pub(crate) projection_area_radius_y_uv: f32,
    pub(crate) projection_area_corner_radius_uv: f32,
    pub(crate) projection_area_keystone_x: f32,
    pub(crate) projection_area_bow_x: f32,
    pub(crate) projection_area_opacity: f32,
    pub(crate) projection_alpha_mode: f32,
    pub(crate) projection_alpha_scale: f32,
    pub(crate) projection_alpha_bias: f32,
}

impl Default for HorizontalAlignmentTuning {
    fn default() -> Self {
        let peripheral_stretch = MakepadPeripheralStretchConfig::current();
        Self {
            strength: TARGET_HORIZONTAL_ALIGNMENT_STRENGTH,
            left_offset_uv: TARGET_MANUAL_HORIZONTAL_OFFSET_LEFT_UV,
            right_offset_uv: TARGET_MANUAL_HORIZONTAL_OFFSET_RIGHT_UV,
            vertical_offset_uv: TARGET_MANUAL_VERTICAL_OFFSET_UV,
            content_uv_scale: TARGET_FULL_VIEW_CONTENT_UV_SCALE,
            projection_border_opacity: TARGET_PROJECTION_BORDER_OPACITY,
            projection_border_policy: MakepadProjectionBorderPolicy::current().shader_code(),
            processing_layer: MakepadProcessingLayer::current().shader_code(),
            projection_sample_mode: MakepadProjectionSampleMode::current().shader_code(),
            blur_radius_px: makepad_blur_radius_px(),
            peripheral_stretch_core_scale: peripheral_stretch.core_scale,
            peripheral_stretch_edge_inset_uv: peripheral_stretch.edge_inset_uv,
            peripheral_stretch_max_inset_uv: peripheral_stretch.max_inset_uv,
            peripheral_stretch_curve: peripheral_stretch.curve,
            peripheral_stretch_inner_blend_uv: peripheral_stretch.inner_blend_uv,
            peripheral_stretch_blend_curve: peripheral_stretch.blend_curve,
            peripheral_stretch_blend_mode: peripheral_stretch.blend_mode.shader_code(),
            peripheral_stretch_debug: peripheral_stretch.debug.shader_code(),
            projection_area_diagnostic: TARGET_PROJECTION_AREA_DIAGNOSTIC,
            projection_area_offset_left_uv: TARGET_PROJECTION_AREA_OFFSET_LEFT_UV,
            projection_area_offset_right_uv: TARGET_PROJECTION_AREA_OFFSET_RIGHT_UV,
            projection_area_offset_vertical_uv: TARGET_PROJECTION_AREA_OFFSET_VERTICAL_UV,
            projection_area_scale_x: TARGET_PROJECTION_AREA_SCALE_X,
            projection_area_scale_y: TARGET_PROJECTION_AREA_SCALE_Y,
            projection_target_offset_x_uv: makepad_projection_target_offset_x_uv(),
            projection_target_offset_y_uv: makepad_projection_target_offset_y_uv(),
            projection_target_scale: makepad_projection_target_scale(),
            projection_area_radius_x_uv: TARGET_PROJECTION_AREA_RADIUS_X_UV,
            projection_area_radius_y_uv: TARGET_PROJECTION_AREA_RADIUS_Y_UV,
            projection_area_corner_radius_uv: TARGET_PROJECTION_AREA_CORNER_RADIUS_UV,
            projection_area_keystone_x: TARGET_PROJECTION_AREA_KEYSTONE_X,
            projection_area_bow_x: TARGET_PROJECTION_AREA_BOW_X,
            projection_area_opacity: TARGET_PROJECTION_AREA_OPACITY,
            projection_alpha_mode: MakepadProjectionAlphaMode::current().shader_code(),
            projection_alpha_scale: makepad_projection_alpha_scale(),
            projection_alpha_bias: makepad_projection_alpha_bias(),
        }
    }
}

impl MakepadStereoCameraPanel {
    pub(crate) fn apply_projection_panel_geometry(&mut self, cx: &mut Cx) {
        let geometry = makepad_projection_panel_geometry();
        self.size = geometry.size();
        self.node.set_implicit_physics_size(self.size);
        self.node.set_pos(cx, geometry.pos());
    }

    fn set_panel_uniform_f32(&mut self, cx: &mut Cx, id: LiveId, value: f32) {
        self.draw_panel.draw_vars.set_uniform(cx, id, &[value]);
        self.draw_panel
            .draw_vars
            .set_uniform_on_area(cx, id, &[value]);
    }

    fn set_panel_uniform_vec4f(&mut self, cx: &mut Cx, id: LiveId, value: Vec4f) {
        let values = [value.x, value.y, value.z, value.w];
        self.draw_panel.draw_vars.set_uniform(cx, id, &values);
        self.draw_panel
            .draw_vars
            .set_uniform_on_area(cx, id, &values);
    }

    pub(crate) fn set_camera_streaming_enabled(&mut self, cx: &mut Cx, enabled: bool) {
        if self.camera_streaming_enabled != enabled {
            self.camera_streaming_enabled = enabled;
            self.node.redraw(cx);
        }
    }

    pub(crate) fn set_mesh_replay_uniforms(
        &mut self,
        cx: &mut Cx,
        uniforms: MeshReplayUniforms,
        feature_uniforms: MakepadCameraShellFeatureUniforms,
        matter_uniforms: MakepadMatterSurfaceUniforms,
        particle_texture_frame: MatterParticleTextureFrame,
    ) {
        let runtime = Vec4f {
            x: uniforms.enabled,
            y: uniforms.phase,
            z: uniforms.frame01,
            w: uniforms.opacity,
        };
        let segment0 = mesh_replay_segment_vec4(uniforms.segments[0]);
        let segment1 = mesh_replay_segment_vec4(uniforms.segments[1]);
        let segment2 = mesh_replay_segment_vec4(uniforms.segments[2]);
        let segment3 = mesh_replay_segment_vec4(uniforms.segments[3]);
        let feature_runtime = Vec4f {
            x: feature_uniforms.collision_enabled,
            y: feature_uniforms.sdf_adf_overlay_mode,
            z: feature_uniforms.particles_enabled,
            w: 0.0,
        };
        let matter_runtime = mesh_replay_segment_vec4(matter_uniforms.runtime);
        let matter_collision_contact = mesh_replay_segment_vec4(matter_uniforms.collision_contact);
        let matter_collision_normal = mesh_replay_segment_vec4(matter_uniforms.collision_normal);
        let matter_sdf_sample0 = mesh_replay_segment_vec4(matter_uniforms.sdf_samples[0]);
        let matter_sdf_sample1 = mesh_replay_segment_vec4(matter_uniforms.sdf_samples[1]);
        let matter_sdf_sample2 = mesh_replay_segment_vec4(matter_uniforms.sdf_samples[2]);
        let matter_sdf_sample3 = mesh_replay_segment_vec4(matter_uniforms.sdf_samples[3]);
        let matter_particle0 = mesh_replay_segment_vec4(matter_uniforms.particles[0]);
        let matter_particle1 = mesh_replay_segment_vec4(matter_uniforms.particles[1]);
        let matter_particle2 = mesh_replay_segment_vec4(matter_uniforms.particles[2]);
        let matter_particle3 = mesh_replay_segment_vec4(matter_uniforms.particles[3]);
        let matter_particle_texture_runtime =
            mesh_replay_segment_vec4(particle_texture_frame.runtime);

        self.draw_panel.mesh_replay_runtime = runtime;
        self.draw_panel.mesh_replay_segment0 = segment0;
        self.draw_panel.mesh_replay_segment1 = segment1;
        self.draw_panel.mesh_replay_segment2 = segment2;
        self.draw_panel.mesh_replay_segment3 = segment3;
        self.draw_panel.camera_shell_feature_runtime = feature_runtime;
        self.draw_panel.matter_surface_runtime = matter_runtime;
        self.draw_panel.matter_collision_contact = matter_collision_contact;
        self.draw_panel.matter_collision_normal = matter_collision_normal;
        self.draw_panel.matter_sdf_sample0 = matter_sdf_sample0;
        self.draw_panel.matter_sdf_sample1 = matter_sdf_sample1;
        self.draw_panel.matter_sdf_sample2 = matter_sdf_sample2;
        self.draw_panel.matter_sdf_sample3 = matter_sdf_sample3;
        self.draw_panel.matter_particle0 = matter_particle0;
        self.draw_panel.matter_particle1 = matter_particle1;
        self.draw_panel.matter_particle2 = matter_particle2;
        self.draw_panel.matter_particle3 = matter_particle3;
        self.draw_panel.matter_particle_texture_runtime = matter_particle_texture_runtime;
        self.draw_panel
            .assign_texture_slot(MATTER_PARTICLE_TEXTURE_SLOT, particle_texture_frame.texture);

        self.set_panel_uniform_vec4f(cx, live_id!(mesh_replay_runtime), runtime);
        self.set_panel_uniform_vec4f(cx, live_id!(mesh_replay_segment0), segment0);
        self.set_panel_uniform_vec4f(cx, live_id!(mesh_replay_segment1), segment1);
        self.set_panel_uniform_vec4f(cx, live_id!(mesh_replay_segment2), segment2);
        self.set_panel_uniform_vec4f(cx, live_id!(mesh_replay_segment3), segment3);
        self.set_panel_uniform_vec4f(cx, live_id!(camera_shell_feature_runtime), feature_runtime);
        self.set_panel_uniform_vec4f(cx, live_id!(matter_surface_runtime), matter_runtime);
        self.set_panel_uniform_vec4f(
            cx,
            live_id!(matter_collision_contact),
            matter_collision_contact,
        );
        self.set_panel_uniform_vec4f(
            cx,
            live_id!(matter_collision_normal),
            matter_collision_normal,
        );
        self.set_panel_uniform_vec4f(cx, live_id!(matter_sdf_sample0), matter_sdf_sample0);
        self.set_panel_uniform_vec4f(cx, live_id!(matter_sdf_sample1), matter_sdf_sample1);
        self.set_panel_uniform_vec4f(cx, live_id!(matter_sdf_sample2), matter_sdf_sample2);
        self.set_panel_uniform_vec4f(cx, live_id!(matter_sdf_sample3), matter_sdf_sample3);
        self.set_panel_uniform_vec4f(cx, live_id!(matter_particle0), matter_particle0);
        self.set_panel_uniform_vec4f(cx, live_id!(matter_particle1), matter_particle1);
        self.set_panel_uniform_vec4f(cx, live_id!(matter_particle2), matter_particle2);
        self.set_panel_uniform_vec4f(cx, live_id!(matter_particle3), matter_particle3);
        self.set_panel_uniform_vec4f(
            cx,
            live_id!(matter_particle_texture_runtime),
            matter_particle_texture_runtime,
        );
        self.draw_panel.draw_vars.redraw(cx);
        self.node.redraw(cx);
    }

    fn synthetic_luma_probe_texture(&mut self, cx: &mut Cx) -> Texture {
        if let Some(texture) = &self.synthetic_luma_probe_texture {
            return texture.clone();
        }

        let size = SYNTHETIC_LUMA_PROBE_SIZE;
        let mut data = Vec::with_capacity(size * size);
        for y in 0..size {
            for x in 0..size {
                let band = ((x / 16) + (y / 16)) % 4;
                data.push(8 + (band as u8) * 8);
            }
        }

        let texture = Texture::new_with_format(
            cx,
            TextureFormat::VecRu8 {
                width: size,
                height: size,
                data: Some(data),
                unpack_row_length: None,
                updated: TextureUpdated::Full,
            },
        );
        self.synthetic_luma_probe_texture = Some(texture.clone());
        texture
    }

    #[allow(clippy::too_many_arguments)]
    pub(crate) fn set_camera_textures(
        &mut self,
        cx: &mut Cx,
        left: Option<Texture>,
        right: Option<Texture>,
        left_yuv: Option<MakepadCameraYuvTextures>,
        right_yuv: Option<MakepadCameraYuvTextures>,
        texture_path: MakepadCameraTexturePath,
        left_rotation_steps: f32,
        right_rotation_steps: f32,
        left_surface_to_camera_h: [[f32; 3]; 3],
        right_surface_to_camera_h: [[f32; 3]; 3],
        left_screen_to_camera_h: [[f32; 3]; 3],
        right_screen_to_camera_h: [[f32; 3]; 3],
        left_screen_to_surface_h: [[f32; 3]; 3],
        right_screen_to_surface_h: [[f32; 3]; 3],
        source_sample_y_flip: f32,
        projection_content_mapping_mode: f32,
        tuning: HorizontalAlignmentTuning,
    ) {
        self.draw_panel.set_camera_textures(cx, left, right);
        let (left_yuv, right_yuv) = if SYNTHETIC_LUMA_SLOT_PROOF {
            let probe = self.synthetic_luma_probe_texture(cx);
            if SYNTHETIC_LUMA_ALL_SLOT_PROOF {
                for slot in 0..8 {
                    self.draw_panel
                        .assign_texture_slot(slot, Some(probe.clone()));
                }
            }
            let textures = MakepadCameraYuvTextures::new(probe.clone(), probe.clone(), probe);
            (Some(textures.clone()), Some(textures))
        } else {
            (left_yuv, right_yuv)
        };
        self.draw_panel
            .set_camera_yuv_textures(cx, left_yuv, right_yuv, texture_path);
        self.draw_panel.left_rotation_steps = left_rotation_steps;
        self.draw_panel.right_rotation_steps = right_rotation_steps;
        self.draw_panel.left_projection_h00 = left_surface_to_camera_h[0][0];
        self.draw_panel.left_projection_h01 = left_surface_to_camera_h[0][1];
        self.draw_panel.left_projection_h02 = left_surface_to_camera_h[0][2];
        self.draw_panel.left_projection_h10 = left_surface_to_camera_h[1][0];
        self.draw_panel.left_projection_h11 = left_surface_to_camera_h[1][1];
        self.draw_panel.left_projection_h12 = left_surface_to_camera_h[1][2];
        self.draw_panel.left_projection_h20 = left_surface_to_camera_h[2][0];
        self.draw_panel.left_projection_h21 = left_surface_to_camera_h[2][1];
        self.draw_panel.left_projection_h22 = left_surface_to_camera_h[2][2];
        self.draw_panel.right_projection_h00 = right_surface_to_camera_h[0][0];
        self.draw_panel.right_projection_h01 = right_surface_to_camera_h[0][1];
        self.draw_panel.right_projection_h02 = right_surface_to_camera_h[0][2];
        self.draw_panel.right_projection_h10 = right_surface_to_camera_h[1][0];
        self.draw_panel.right_projection_h11 = right_surface_to_camera_h[1][1];
        self.draw_panel.right_projection_h12 = right_surface_to_camera_h[1][2];
        self.draw_panel.right_projection_h20 = right_surface_to_camera_h[2][0];
        self.draw_panel.right_projection_h21 = right_surface_to_camera_h[2][1];
        self.draw_panel.right_projection_h22 = right_surface_to_camera_h[2][2];
        self.draw_panel.left_screen_to_camera_h00 = left_screen_to_camera_h[0][0];
        self.draw_panel.left_screen_to_camera_h01 = left_screen_to_camera_h[0][1];
        self.draw_panel.left_screen_to_camera_h02 = left_screen_to_camera_h[0][2];
        self.draw_panel.left_screen_to_camera_h10 = left_screen_to_camera_h[1][0];
        self.draw_panel.left_screen_to_camera_h11 = left_screen_to_camera_h[1][1];
        self.draw_panel.left_screen_to_camera_h12 = left_screen_to_camera_h[1][2];
        self.draw_panel.left_screen_to_camera_h20 = left_screen_to_camera_h[2][0];
        self.draw_panel.left_screen_to_camera_h21 = left_screen_to_camera_h[2][1];
        self.draw_panel.left_screen_to_camera_h22 = left_screen_to_camera_h[2][2];
        self.draw_panel.right_screen_to_camera_h00 = right_screen_to_camera_h[0][0];
        self.draw_panel.right_screen_to_camera_h01 = right_screen_to_camera_h[0][1];
        self.draw_panel.right_screen_to_camera_h02 = right_screen_to_camera_h[0][2];
        self.draw_panel.right_screen_to_camera_h10 = right_screen_to_camera_h[1][0];
        self.draw_panel.right_screen_to_camera_h11 = right_screen_to_camera_h[1][1];
        self.draw_panel.right_screen_to_camera_h12 = right_screen_to_camera_h[1][2];
        self.draw_panel.right_screen_to_camera_h20 = right_screen_to_camera_h[2][0];
        self.draw_panel.right_screen_to_camera_h21 = right_screen_to_camera_h[2][1];
        self.draw_panel.right_screen_to_camera_h22 = right_screen_to_camera_h[2][2];
        self.draw_panel.left_screen_to_surface_h00 = left_screen_to_surface_h[0][0];
        self.draw_panel.left_screen_to_surface_h01 = left_screen_to_surface_h[0][1];
        self.draw_panel.left_screen_to_surface_h02 = left_screen_to_surface_h[0][2];
        self.draw_panel.left_screen_to_surface_h10 = left_screen_to_surface_h[1][0];
        self.draw_panel.left_screen_to_surface_h11 = left_screen_to_surface_h[1][1];
        self.draw_panel.left_screen_to_surface_h12 = left_screen_to_surface_h[1][2];
        self.draw_panel.left_screen_to_surface_h20 = left_screen_to_surface_h[2][0];
        self.draw_panel.left_screen_to_surface_h21 = left_screen_to_surface_h[2][1];
        self.draw_panel.left_screen_to_surface_h22 = left_screen_to_surface_h[2][2];
        self.draw_panel.right_screen_to_surface_h00 = right_screen_to_surface_h[0][0];
        self.draw_panel.right_screen_to_surface_h01 = right_screen_to_surface_h[0][1];
        self.draw_panel.right_screen_to_surface_h02 = right_screen_to_surface_h[0][2];
        self.draw_panel.right_screen_to_surface_h10 = right_screen_to_surface_h[1][0];
        self.draw_panel.right_screen_to_surface_h11 = right_screen_to_surface_h[1][1];
        self.draw_panel.right_screen_to_surface_h12 = right_screen_to_surface_h[1][2];
        self.draw_panel.right_screen_to_surface_h20 = right_screen_to_surface_h[2][0];
        self.draw_panel.right_screen_to_surface_h21 = right_screen_to_surface_h[2][1];
        self.draw_panel.right_screen_to_surface_h22 = right_screen_to_surface_h[2][2];
        self.draw_panel.source_sample_y_flip = source_sample_y_flip.clamp(0.0, 1.0);
        self.draw_panel.projection_content_mapping_mode =
            projection_content_mapping_mode.clamp(0.0, 1.0);
        self.draw_panel.content_uv_scale = TARGET_FULL_VIEW_CONTENT_UV_SCALE;
        self.draw_panel.display_source_eye_swap = if makepad_display_left_from_right_source() {
            1.0
        } else {
            0.0
        };
        self.draw_panel.display_eye_offset_meters = TARGET_DISPLAY_EYE_OFFSET_METERS;
        self.draw_panel.display_fov_y_degrees = TARGET_DISPLAY_FOV_Y_DEGREES;
        self.draw_panel.display_aspect = TARGET_DISPLAY_ASPECT;
        self.draw_panel.projection_depth_meters = makepad_projection_depth_meters();
        self.draw_panel.projection_preview_offset_y_meters =
            makepad_projection_preview_offset_y_meters();
        self.draw_panel.projection_preview_fov_y_degrees =
            makepad_projection_preview_fov_y_degrees();
        self.draw_panel.projection_raw_overscan = makepad_projection_raw_overscan();
        self.draw_panel.suppress_live_camera_sampling = if SUPPRESS_LIVE_CAMERA_SAMPLING {
            1.0
        } else {
            0.0
        };
        self.draw_panel.force_full_surface_live_camera_uv = if FORCE_FULL_SURFACE_LIVE_CAMERA_UV {
            1.0
        } else {
            0.0
        };
        self.draw_panel.force_in_surface_camera_window = if FORCE_IN_SURFACE_CAMERA_WINDOW {
            1.0
        } else {
            0.0
        };
        self.draw_panel.projection_border_opacity = TARGET_PROJECTION_BORDER_OPACITY;
        self.draw_panel.projection_border_policy =
            MakepadProjectionBorderPolicy::current().shader_code();
        self.draw_panel.processing_layer = MakepadProcessingLayer::current().shader_code();
        self.draw_panel.projection_sample_mode =
            MakepadProjectionSampleMode::current().shader_code();
        self.draw_panel.blur_radius_px = makepad_blur_radius_px();
        let peripheral_stretch = MakepadPeripheralStretchConfig::current();
        self.draw_panel.peripheral_stretch_core_scale = peripheral_stretch.core_scale;
        self.draw_panel.peripheral_stretch_edge_inset_uv = peripheral_stretch.edge_inset_uv;
        self.draw_panel.peripheral_stretch_max_inset_uv = peripheral_stretch.max_inset_uv;
        self.draw_panel.peripheral_stretch_curve = peripheral_stretch.curve;
        self.draw_panel.peripheral_stretch_inner_blend_uv = peripheral_stretch.inner_blend_uv;
        self.draw_panel.peripheral_stretch_blend_curve = peripheral_stretch.blend_curve;
        self.draw_panel.peripheral_stretch_blend_mode = peripheral_stretch.blend_mode.shader_code();
        self.draw_panel.peripheral_stretch_debug = peripheral_stretch.debug.shader_code();
        self.draw_panel.projection_area_diagnostic = TARGET_PROJECTION_AREA_DIAGNOSTIC;
        self.draw_panel.projection_area_offset_left_uv = TARGET_PROJECTION_AREA_OFFSET_LEFT_UV;
        self.draw_panel.projection_area_offset_right_uv = TARGET_PROJECTION_AREA_OFFSET_RIGHT_UV;
        self.draw_panel.projection_area_offset_vertical_uv =
            TARGET_PROJECTION_AREA_OFFSET_VERTICAL_UV;
        self.draw_panel.projection_area_scale_x = TARGET_PROJECTION_AREA_SCALE_X;
        self.draw_panel.projection_area_scale_y = TARGET_PROJECTION_AREA_SCALE_Y;
        self.draw_panel.projection_target_runtime = Vec4f {
            x: makepad_projection_target_offset_x_uv(),
            y: makepad_projection_target_offset_y_uv(),
            z: makepad_projection_target_scale(),
            w: self.draw_panel.projection_target_runtime.w,
        };
        self.draw_panel.projection_area_radius_x_uv = TARGET_PROJECTION_AREA_RADIUS_X_UV;
        self.draw_panel.projection_area_radius_y_uv = TARGET_PROJECTION_AREA_RADIUS_Y_UV;
        self.draw_panel.projection_area_corner_radius_uv = TARGET_PROJECTION_AREA_CORNER_RADIUS_UV;
        self.draw_panel.projection_area_keystone_x = TARGET_PROJECTION_AREA_KEYSTONE_X;
        self.draw_panel.projection_area_bow_x = TARGET_PROJECTION_AREA_BOW_X;
        self.draw_panel.projection_area_opacity = TARGET_PROJECTION_AREA_OPACITY;
        self.draw_panel.projection_alpha_mode = MakepadProjectionAlphaMode::current().shader_code();
        self.draw_panel.projection_alpha_scale = makepad_projection_alpha_scale();
        self.draw_panel.projection_alpha_bias = makepad_projection_alpha_bias();
        self.set_target_footprint(cx, makepad_runtime_target_screen_footprint_pair());
        self.set_horizontal_alignment_tuning(cx, tuning);
        self.draw_panel.camera_ready = 1.0;
        self.draw_panel.texture_probe_mode = 2.0;
        self.draw_panel.draw_vars.redraw(cx);
        self.set_panel_uniform_f32(cx, live_id!(camera_ready), 1.0);
        self.set_panel_uniform_f32(cx, live_id!(yuv_mode), self.draw_panel.yuv_mode);
        self.set_panel_uniform_f32(cx, live_id!(proof_tint_strength), 0.0);
        self.set_panel_uniform_f32(cx, live_id!(texture_probe_mode), 2.0);
        let suppress_live_camera_sampling = if SUPPRESS_LIVE_CAMERA_SAMPLING {
            1.0
        } else {
            0.0
        };
        self.set_panel_uniform_f32(
            cx,
            live_id!(suppress_live_camera_sampling),
            suppress_live_camera_sampling,
        );
        let force_full_surface_live_camera_uv = if FORCE_FULL_SURFACE_LIVE_CAMERA_UV {
            1.0
        } else {
            0.0
        };
        self.set_panel_uniform_f32(
            cx,
            live_id!(force_full_surface_live_camera_uv),
            force_full_surface_live_camera_uv,
        );
        let force_in_surface_camera_window = if FORCE_IN_SURFACE_CAMERA_WINDOW {
            1.0
        } else {
            0.0
        };
        self.set_panel_uniform_f32(
            cx,
            live_id!(force_in_surface_camera_window),
            force_in_surface_camera_window,
        );
        self.set_panel_uniform_f32(
            cx,
            live_id!(projection_border_opacity),
            TARGET_PROJECTION_BORDER_OPACITY,
        );
        self.set_panel_uniform_f32(
            cx,
            live_id!(projection_border_policy),
            self.draw_panel.projection_border_policy,
        );
        self.set_panel_uniform_f32(
            cx,
            live_id!(processing_layer),
            self.draw_panel.processing_layer,
        );
        self.set_panel_uniform_f32(
            cx,
            live_id!(projection_sample_mode),
            self.draw_panel.projection_sample_mode,
        );
        self.set_panel_uniform_f32(cx, live_id!(blur_radius_px), self.draw_panel.blur_radius_px);
        self.set_panel_uniform_f32(
            cx,
            live_id!(projection_area_diagnostic),
            TARGET_PROJECTION_AREA_DIAGNOSTIC,
        );
        for (id, value) in [
            (
                live_id!(content_uv_scale),
                TARGET_FULL_VIEW_CONTENT_UV_SCALE,
            ),
            (
                live_id!(projection_border_opacity),
                TARGET_PROJECTION_BORDER_OPACITY,
            ),
            (live_id!(processing_layer), self.draw_panel.processing_layer),
            (live_id!(blur_radius_px), self.draw_panel.blur_radius_px),
            (
                live_id!(peripheral_stretch_core_scale),
                self.draw_panel.peripheral_stretch_core_scale,
            ),
            (
                live_id!(peripheral_stretch_edge_inset_uv),
                self.draw_panel.peripheral_stretch_edge_inset_uv,
            ),
            (
                live_id!(peripheral_stretch_max_inset_uv),
                self.draw_panel.peripheral_stretch_max_inset_uv,
            ),
            (
                live_id!(peripheral_stretch_curve),
                self.draw_panel.peripheral_stretch_curve,
            ),
            (
                live_id!(peripheral_stretch_inner_blend_uv),
                self.draw_panel.peripheral_stretch_inner_blend_uv,
            ),
            (
                live_id!(peripheral_stretch_blend_curve),
                self.draw_panel.peripheral_stretch_blend_curve,
            ),
            (
                live_id!(peripheral_stretch_blend_mode),
                self.draw_panel.peripheral_stretch_blend_mode,
            ),
            (
                live_id!(peripheral_stretch_debug),
                self.draw_panel.peripheral_stretch_debug,
            ),
            (
                live_id!(projection_area_diagnostic),
                TARGET_PROJECTION_AREA_DIAGNOSTIC,
            ),
            (
                live_id!(projection_area_offset_left_uv),
                TARGET_PROJECTION_AREA_OFFSET_LEFT_UV,
            ),
            (
                live_id!(projection_area_offset_right_uv),
                TARGET_PROJECTION_AREA_OFFSET_RIGHT_UV,
            ),
            (
                live_id!(projection_area_offset_vertical_uv),
                TARGET_PROJECTION_AREA_OFFSET_VERTICAL_UV,
            ),
            (
                live_id!(projection_area_scale_x),
                TARGET_PROJECTION_AREA_SCALE_X,
            ),
            (
                live_id!(projection_area_scale_y),
                TARGET_PROJECTION_AREA_SCALE_Y,
            ),
            (
                live_id!(projection_area_keystone_x),
                TARGET_PROJECTION_AREA_KEYSTONE_X,
            ),
            (
                live_id!(projection_area_bow_x),
                TARGET_PROJECTION_AREA_BOW_X,
            ),
            (
                live_id!(projection_area_opacity),
                TARGET_PROJECTION_AREA_OPACITY,
            ),
            (
                live_id!(projection_alpha_mode),
                self.draw_panel.projection_alpha_mode,
            ),
            (
                live_id!(projection_alpha_scale),
                self.draw_panel.projection_alpha_scale,
            ),
            (
                live_id!(projection_alpha_bias),
                self.draw_panel.projection_alpha_bias,
            ),
            (
                live_id!(source_sample_y_flip),
                self.draw_panel.source_sample_y_flip,
            ),
            (
                live_id!(projection_content_mapping_mode),
                self.draw_panel.projection_content_mapping_mode,
            ),
            (
                live_id!(display_eye_offset_meters),
                TARGET_DISPLAY_EYE_OFFSET_METERS,
            ),
            (
                live_id!(display_fov_y_degrees),
                TARGET_DISPLAY_FOV_Y_DEGREES,
            ),
            (live_id!(display_aspect), TARGET_DISPLAY_ASPECT),
            (
                live_id!(projection_depth_meters),
                self.draw_panel.projection_depth_meters,
            ),
            (
                live_id!(projection_preview_offset_y_meters),
                self.draw_panel.projection_preview_offset_y_meters,
            ),
            (
                live_id!(projection_preview_fov_y_degrees),
                self.draw_panel.projection_preview_fov_y_degrees,
            ),
            (
                live_id!(projection_raw_overscan),
                self.draw_panel.projection_raw_overscan,
            ),
        ] {
            self.set_panel_uniform_f32(cx, id, value);
        }
        for (id, value) in [
            (
                live_id!(left_projection_h00),
                left_surface_to_camera_h[0][0],
            ),
            (
                live_id!(left_projection_h01),
                left_surface_to_camera_h[0][1],
            ),
            (
                live_id!(left_projection_h02),
                left_surface_to_camera_h[0][2],
            ),
            (
                live_id!(left_projection_h10),
                left_surface_to_camera_h[1][0],
            ),
            (
                live_id!(left_projection_h11),
                left_surface_to_camera_h[1][1],
            ),
            (
                live_id!(left_projection_h12),
                left_surface_to_camera_h[1][2],
            ),
            (
                live_id!(left_projection_h20),
                left_surface_to_camera_h[2][0],
            ),
            (
                live_id!(left_projection_h21),
                left_surface_to_camera_h[2][1],
            ),
            (
                live_id!(left_projection_h22),
                left_surface_to_camera_h[2][2],
            ),
            (
                live_id!(right_projection_h00),
                right_surface_to_camera_h[0][0],
            ),
            (
                live_id!(right_projection_h01),
                right_surface_to_camera_h[0][1],
            ),
            (
                live_id!(right_projection_h02),
                right_surface_to_camera_h[0][2],
            ),
            (
                live_id!(right_projection_h10),
                right_surface_to_camera_h[1][0],
            ),
            (
                live_id!(right_projection_h11),
                right_surface_to_camera_h[1][1],
            ),
            (
                live_id!(right_projection_h12),
                right_surface_to_camera_h[1][2],
            ),
            (
                live_id!(right_projection_h20),
                right_surface_to_camera_h[2][0],
            ),
            (
                live_id!(right_projection_h21),
                right_surface_to_camera_h[2][1],
            ),
            (
                live_id!(right_projection_h22),
                right_surface_to_camera_h[2][2],
            ),
            (
                live_id!(left_screen_to_camera_h00),
                left_screen_to_camera_h[0][0],
            ),
            (
                live_id!(left_screen_to_camera_h01),
                left_screen_to_camera_h[0][1],
            ),
            (
                live_id!(left_screen_to_camera_h02),
                left_screen_to_camera_h[0][2],
            ),
            (
                live_id!(left_screen_to_camera_h10),
                left_screen_to_camera_h[1][0],
            ),
            (
                live_id!(left_screen_to_camera_h11),
                left_screen_to_camera_h[1][1],
            ),
            (
                live_id!(left_screen_to_camera_h12),
                left_screen_to_camera_h[1][2],
            ),
            (
                live_id!(left_screen_to_camera_h20),
                left_screen_to_camera_h[2][0],
            ),
            (
                live_id!(left_screen_to_camera_h21),
                left_screen_to_camera_h[2][1],
            ),
            (
                live_id!(left_screen_to_camera_h22),
                left_screen_to_camera_h[2][2],
            ),
            (
                live_id!(right_screen_to_camera_h00),
                right_screen_to_camera_h[0][0],
            ),
            (
                live_id!(right_screen_to_camera_h01),
                right_screen_to_camera_h[0][1],
            ),
            (
                live_id!(right_screen_to_camera_h02),
                right_screen_to_camera_h[0][2],
            ),
            (
                live_id!(right_screen_to_camera_h10),
                right_screen_to_camera_h[1][0],
            ),
            (
                live_id!(right_screen_to_camera_h11),
                right_screen_to_camera_h[1][1],
            ),
            (
                live_id!(right_screen_to_camera_h12),
                right_screen_to_camera_h[1][2],
            ),
            (
                live_id!(right_screen_to_camera_h20),
                right_screen_to_camera_h[2][0],
            ),
            (
                live_id!(right_screen_to_camera_h21),
                right_screen_to_camera_h[2][1],
            ),
            (
                live_id!(right_screen_to_camera_h22),
                right_screen_to_camera_h[2][2],
            ),
        ] {
            self.set_panel_uniform_f32(cx, id, value);
        }
        for (id, value) in [
            (
                live_id!(left_screen_to_surface_h00),
                left_screen_to_surface_h[0][0],
            ),
            (
                live_id!(left_screen_to_surface_h01),
                left_screen_to_surface_h[0][1],
            ),
            (
                live_id!(left_screen_to_surface_h02),
                left_screen_to_surface_h[0][2],
            ),
            (
                live_id!(left_screen_to_surface_h10),
                left_screen_to_surface_h[1][0],
            ),
            (
                live_id!(left_screen_to_surface_h11),
                left_screen_to_surface_h[1][1],
            ),
            (
                live_id!(left_screen_to_surface_h12),
                left_screen_to_surface_h[1][2],
            ),
            (
                live_id!(left_screen_to_surface_h20),
                left_screen_to_surface_h[2][0],
            ),
            (
                live_id!(left_screen_to_surface_h21),
                left_screen_to_surface_h[2][1],
            ),
            (
                live_id!(left_screen_to_surface_h22),
                left_screen_to_surface_h[2][2],
            ),
            (
                live_id!(right_screen_to_surface_h00),
                right_screen_to_surface_h[0][0],
            ),
            (
                live_id!(right_screen_to_surface_h01),
                right_screen_to_surface_h[0][1],
            ),
            (
                live_id!(right_screen_to_surface_h02),
                right_screen_to_surface_h[0][2],
            ),
            (
                live_id!(right_screen_to_surface_h10),
                right_screen_to_surface_h[1][0],
            ),
            (
                live_id!(right_screen_to_surface_h11),
                right_screen_to_surface_h[1][1],
            ),
            (
                live_id!(right_screen_to_surface_h12),
                right_screen_to_surface_h[1][2],
            ),
            (
                live_id!(right_screen_to_surface_h20),
                right_screen_to_surface_h[2][0],
            ),
            (
                live_id!(right_screen_to_surface_h21),
                right_screen_to_surface_h[2][1],
            ),
            (
                live_id!(right_screen_to_surface_h22),
                right_screen_to_surface_h[2][2],
            ),
        ] {
            self.set_panel_uniform_f32(cx, id, value);
        }
        self.camera_ready = true;
        self.node.redraw(cx);
    }

    pub(crate) fn set_target_footprint(
        &mut self,
        cx: &mut Cx,
        target: MakepadTargetScreenFootprintPair,
    ) {
        let push = MakepadTargetFootprintPush::from_pair(target);
        self.draw_panel.projection_target_runtime.w = push.from_metadata;
        self.draw_panel.left_projection_area_offset_radius_uv = Vec4f {
            x: push.left_offset_x_uv,
            y: push.left_offset_y_uv,
            z: push.left_radius_x_uv,
            w: push.left_radius_y_uv,
        };
        self.draw_panel.right_projection_area_offset_radius_uv = Vec4f {
            x: push.right_offset_x_uv,
            y: push.right_offset_y_uv,
            z: push.right_radius_x_uv,
            w: push.right_radius_y_uv,
        };
        for (id, value) in [
            (
                live_id!(projection_target_runtime),
                self.draw_panel.projection_target_runtime,
            ),
            (
                live_id!(left_projection_area_offset_radius_uv),
                self.draw_panel.left_projection_area_offset_radius_uv,
            ),
            (
                live_id!(right_projection_area_offset_radius_uv),
                self.draw_panel.right_projection_area_offset_radius_uv,
            ),
        ] {
            self.set_panel_uniform_vec4f(cx, id, value);
        }
        self.draw_panel.draw_vars.redraw(cx);
        self.node.redraw(cx);
    }

    pub(crate) fn set_horizontal_alignment_tuning(
        &mut self,
        cx: &mut Cx,
        tuning: HorizontalAlignmentTuning,
    ) {
        self.draw_panel.horizontal_alignment_strength = tuning.strength;
        self.draw_panel.manual_horizontal_offset_left_uv = tuning.left_offset_uv;
        self.draw_panel.manual_horizontal_offset_right_uv = tuning.right_offset_uv;
        self.draw_panel.manual_vertical_offset_uv = tuning.vertical_offset_uv;
        self.draw_panel.content_uv_scale = tuning.content_uv_scale;
        self.draw_panel.projection_border_opacity = tuning.projection_border_opacity;
        self.draw_panel.projection_border_policy = tuning.projection_border_policy;
        self.draw_panel.processing_layer = tuning.processing_layer;
        self.draw_panel.projection_sample_mode = tuning.projection_sample_mode;
        self.draw_panel.blur_radius_px = tuning.blur_radius_px;
        self.draw_panel.peripheral_stretch_core_scale = tuning.peripheral_stretch_core_scale;
        self.draw_panel.peripheral_stretch_edge_inset_uv = tuning.peripheral_stretch_edge_inset_uv;
        self.draw_panel.peripheral_stretch_max_inset_uv = tuning.peripheral_stretch_max_inset_uv;
        self.draw_panel.peripheral_stretch_curve = tuning.peripheral_stretch_curve;
        self.draw_panel.peripheral_stretch_inner_blend_uv =
            tuning.peripheral_stretch_inner_blend_uv;
        self.draw_panel.peripheral_stretch_blend_curve = tuning.peripheral_stretch_blend_curve;
        self.draw_panel.peripheral_stretch_blend_mode = tuning.peripheral_stretch_blend_mode;
        self.draw_panel.peripheral_stretch_debug = tuning.peripheral_stretch_debug;
        self.draw_panel.projection_area_diagnostic = tuning.projection_area_diagnostic;
        self.draw_panel.projection_area_offset_left_uv = tuning.projection_area_offset_left_uv;
        self.draw_panel.projection_area_offset_right_uv = tuning.projection_area_offset_right_uv;
        self.draw_panel.projection_area_offset_vertical_uv =
            tuning.projection_area_offset_vertical_uv;
        self.draw_panel.projection_area_scale_x = tuning.projection_area_scale_x;
        self.draw_panel.projection_area_scale_y = tuning.projection_area_scale_y;
        self.draw_panel.projection_target_runtime = Vec4f {
            x: tuning.projection_target_offset_x_uv,
            y: tuning.projection_target_offset_y_uv,
            z: tuning.projection_target_scale,
            w: self.draw_panel.projection_target_runtime.w,
        };
        self.draw_panel.projection_area_radius_x_uv = tuning.projection_area_radius_x_uv;
        self.draw_panel.projection_area_radius_y_uv = tuning.projection_area_radius_y_uv;
        self.draw_panel.projection_area_corner_radius_uv = tuning.projection_area_corner_radius_uv;
        self.draw_panel.projection_area_keystone_x = tuning.projection_area_keystone_x;
        self.draw_panel.projection_area_bow_x = tuning.projection_area_bow_x;
        self.draw_panel.projection_area_opacity = tuning.projection_area_opacity;
        self.draw_panel.projection_alpha_mode = tuning.projection_alpha_mode;
        self.draw_panel.projection_alpha_scale = tuning.projection_alpha_scale;
        self.draw_panel.projection_alpha_bias = tuning.projection_alpha_bias;
        for (id, value) in [
            (live_id!(horizontal_alignment_strength), tuning.strength),
            (
                live_id!(manual_horizontal_offset_left_uv),
                tuning.left_offset_uv,
            ),
            (
                live_id!(manual_horizontal_offset_right_uv),
                tuning.right_offset_uv,
            ),
            (
                live_id!(manual_vertical_offset_uv),
                tuning.vertical_offset_uv,
            ),
            (live_id!(content_uv_scale), tuning.content_uv_scale),
            (
                live_id!(projection_border_opacity),
                tuning.projection_border_opacity,
            ),
            (
                live_id!(projection_border_policy),
                tuning.projection_border_policy,
            ),
            (live_id!(processing_layer), tuning.processing_layer),
            (
                live_id!(projection_sample_mode),
                tuning.projection_sample_mode,
            ),
            (live_id!(blur_radius_px), tuning.blur_radius_px),
            (
                live_id!(peripheral_stretch_core_scale),
                tuning.peripheral_stretch_core_scale,
            ),
            (
                live_id!(peripheral_stretch_edge_inset_uv),
                tuning.peripheral_stretch_edge_inset_uv,
            ),
            (
                live_id!(peripheral_stretch_max_inset_uv),
                tuning.peripheral_stretch_max_inset_uv,
            ),
            (
                live_id!(peripheral_stretch_curve),
                tuning.peripheral_stretch_curve,
            ),
            (
                live_id!(peripheral_stretch_inner_blend_uv),
                tuning.peripheral_stretch_inner_blend_uv,
            ),
            (
                live_id!(peripheral_stretch_blend_curve),
                tuning.peripheral_stretch_blend_curve,
            ),
            (
                live_id!(peripheral_stretch_blend_mode),
                tuning.peripheral_stretch_blend_mode,
            ),
            (
                live_id!(peripheral_stretch_debug),
                tuning.peripheral_stretch_debug,
            ),
            (
                live_id!(projection_area_diagnostic),
                tuning.projection_area_diagnostic,
            ),
            (
                live_id!(projection_area_offset_left_uv),
                tuning.projection_area_offset_left_uv,
            ),
            (
                live_id!(projection_area_offset_right_uv),
                tuning.projection_area_offset_right_uv,
            ),
            (
                live_id!(projection_area_offset_vertical_uv),
                tuning.projection_area_offset_vertical_uv,
            ),
            (
                live_id!(projection_area_scale_x),
                tuning.projection_area_scale_x,
            ),
            (
                live_id!(projection_area_scale_y),
                tuning.projection_area_scale_y,
            ),
            (
                live_id!(projection_area_radius_x_uv),
                tuning.projection_area_radius_x_uv,
            ),
            (
                live_id!(projection_area_radius_y_uv),
                tuning.projection_area_radius_y_uv,
            ),
            (
                live_id!(projection_area_corner_radius_uv),
                tuning.projection_area_corner_radius_uv,
            ),
            (
                live_id!(projection_area_keystone_x),
                tuning.projection_area_keystone_x,
            ),
            (
                live_id!(projection_area_bow_x),
                tuning.projection_area_bow_x,
            ),
            (
                live_id!(projection_area_opacity),
                tuning.projection_area_opacity,
            ),
            (
                live_id!(projection_alpha_mode),
                tuning.projection_alpha_mode,
            ),
            (
                live_id!(projection_alpha_scale),
                tuning.projection_alpha_scale,
            ),
            (
                live_id!(projection_alpha_bias),
                tuning.projection_alpha_bias,
            ),
        ] {
            self.set_panel_uniform_f32(cx, id, value);
        }
        let projection_target_runtime = self.draw_panel.projection_target_runtime;
        self.set_panel_uniform_vec4f(
            cx,
            live_id!(projection_target_runtime),
            projection_target_runtime,
        );
        self.draw_panel.draw_vars.redraw(cx);
    }
}

impl ScriptHook for MakepadStereoCameraPanel {
    fn on_after_apply(
        &mut self,
        _vm: &mut ScriptVm,
        _apply: &Apply,
        _scope: &mut Scope,
        _value: ScriptValue,
    ) {
        self.node.set_implicit_physics_size(self.size);
    }
}

impl Widget for MakepadStereoCameraPanel {
    fn draw_3d(&mut self, cx: &mut Cx3d, scope: &mut Scope) -> DrawStep {
        if cx.scene_state_3d().is_none() {
            return self.node.draw_3d(cx, scope);
        }
        if !self.camera_streaming_enabled {
            return self.node.draw_3d(cx, scope);
        }
        if !CAMERA_PANEL_DRAW_MARKER_EMITTED.swap(true, Ordering::AcqRel) {
            let projection_panel_draw_enabled =
                MakepadProjectionSampleMode::current().draws_projection_panel();
            emit_marker_line(&makepad_visible_panel_draw_marker_line(
                self.camera_ready,
                projection_panel_draw_enabled,
                self.draw_panel.projection_depth_meters,
                self.draw_panel.projection_preview_fov_y_degrees,
                self.draw_panel.projection_preview_offset_y_meters,
                self.draw_panel.projection_raw_overscan,
            ));
        }
        let _world = xr_widget_world_transform(cx, scope, self.widget_uid(), &self.node);
        self.draw_panel.cube_pos = vec3f(0.0, 0.0, 0.0);
        self.draw_panel.cube_size = vec3f(1.0, 1.0, 0.0);
        self.draw_panel.depth_clip = 0.0;
        if MakepadProjectionSampleMode::current().draws_projection_panel() {
            self.draw_panel.draw(cx);
        }

        self.node.draw_3d(cx, scope)
    }

    fn draw_walk(&mut self, _cx: &mut Cx2d, _scope: &mut Scope, _walk: Walk) -> DrawStep {
        DrawStep::done()
    }
}

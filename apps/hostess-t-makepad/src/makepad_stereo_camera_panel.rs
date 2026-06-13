//! Makepad live/script definitions and Rust widget state for the Hostess stereo
//! camera projection panel.

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

script_mod! {
    use mod.pod.*
    use mod.math.*
    use mod.shader.*
    use mod.draw
    use mod.geom
    use mod.prelude.widgets.*
    use mod.widgets.*

    mod.draw.DrawMakepadStereoCameraPanel = mod.std.set_type_default() do #(DrawMakepadStereoCameraPanel::script_shader(vm)){
        alpha_blend: true
        backface_culling: false
        vertex_pos: vertex_position(vec4f)
        fb0: fragment_output(0, vec4f)
        draw_call: uniform_buffer(draw.DrawCallUniforms)
        draw_pass: uniform_buffer(draw.DrawPassUniforms)
        draw_list: uniform_buffer(draw.DrawListUniforms)
        geom: vertex_buffer(geom.QuadVertex, geom.QuadGeom)

        world: varying(vec4f)

        left_camera_texture: texture_video()
        right_camera_texture: texture_video()
        left_tex_y: texture_2d(float)
        left_tex_u: texture_2d(float)
        left_tex_v: texture_2d(float)
        right_tex_y: texture_2d(float)
        right_tex_u: texture_2d(float)
        right_tex_v: texture_2d(float)
        matter_particle_texture: texture_2d(float)
        left_projection_h00: uniform(1.0)
        left_projection_h01: uniform(0.0)
        left_projection_h02: uniform(0.0)
        left_projection_h10: uniform(0.0)
        left_projection_h11: uniform(1.0)
        left_projection_h12: uniform(0.0)
        left_projection_h20: uniform(0.0)
        left_projection_h21: uniform(0.0)
        left_projection_h22: uniform(1.0)
        right_projection_h00: uniform(1.0)
        right_projection_h01: uniform(0.0)
        right_projection_h02: uniform(0.0)
        right_projection_h10: uniform(0.0)
        right_projection_h11: uniform(1.0)
        right_projection_h12: uniform(0.0)
        right_projection_h20: uniform(0.0)
        right_projection_h21: uniform(0.0)
        right_projection_h22: uniform(1.0)
        left_screen_to_camera_h00: uniform(1.0)
        left_screen_to_camera_h01: uniform(0.0)
        left_screen_to_camera_h02: uniform(0.0)
        left_screen_to_camera_h10: uniform(0.0)
        left_screen_to_camera_h11: uniform(1.0)
        left_screen_to_camera_h12: uniform(0.0)
        left_screen_to_camera_h20: uniform(0.0)
        left_screen_to_camera_h21: uniform(0.0)
        left_screen_to_camera_h22: uniform(1.0)
        right_screen_to_camera_h00: uniform(1.0)
        right_screen_to_camera_h01: uniform(0.0)
        right_screen_to_camera_h02: uniform(0.0)
        right_screen_to_camera_h10: uniform(0.0)
        right_screen_to_camera_h11: uniform(1.0)
        right_screen_to_camera_h12: uniform(0.0)
        right_screen_to_camera_h20: uniform(0.0)
        right_screen_to_camera_h21: uniform(0.0)
        right_screen_to_camera_h22: uniform(1.0)
        left_screen_to_surface_h00: uniform(1.0)
        left_screen_to_surface_h01: uniform(0.0)
        left_screen_to_surface_h02: uniform(0.0)
        left_screen_to_surface_h10: uniform(0.0)
        left_screen_to_surface_h11: uniform(1.0)
        left_screen_to_surface_h12: uniform(0.0)
        left_screen_to_surface_h20: uniform(0.0)
        left_screen_to_surface_h21: uniform(0.0)
        left_screen_to_surface_h22: uniform(1.0)
        right_screen_to_surface_h00: uniform(1.0)
        right_screen_to_surface_h01: uniform(0.0)
        right_screen_to_surface_h02: uniform(0.0)
        right_screen_to_surface_h10: uniform(0.0)
        right_screen_to_surface_h11: uniform(1.0)
        right_screen_to_surface_h12: uniform(0.0)
        right_screen_to_surface_h20: uniform(0.0)
        right_screen_to_surface_h21: uniform(0.0)
        right_screen_to_surface_h22: uniform(1.0)
        content_uv_scale: uniform(1.60)
        display_eye_offset_meters: uniform(0.032)
        display_fov_y_degrees: uniform(92.0)
        display_aspect: uniform(1.0)
        projection_depth_meters: uniform(0.5)
        projection_preview_offset_y_meters: uniform(0.0)
        projection_preview_fov_y_degrees: uniform(60.0)
        projection_raw_overscan: uniform(1.06)
        suppress_live_camera_sampling: uniform(1.0)
        force_full_surface_live_camera_uv: uniform(1.0)
        force_in_surface_camera_window: uniform(1.0)
        projection_border_opacity: uniform(1.0)
        projection_border_policy: uniform(0.0)
        processing_layer: uniform(0.0)
        projection_sample_mode: uniform(0.0)
        blur_radius_px: uniform(2.0)
        peripheral_stretch_core_scale: uniform(1.0)
        peripheral_stretch_edge_inset_uv: uniform(0.015)
        peripheral_stretch_max_inset_uv: uniform(0.14)
        peripheral_stretch_curve: uniform(1.6)
        peripheral_stretch_inner_blend_uv: uniform(0.040)
        peripheral_stretch_blend_curve: uniform(1.6)
        peripheral_stretch_blend_mode: uniform(1.0)
        peripheral_stretch_debug: uniform(0.0)
        projection_area_diagnostic: uniform(0.0)
        projection_area_offset_left_uv: uniform(0.0)
        projection_area_offset_right_uv: uniform(0.0)
        projection_area_offset_vertical_uv: uniform(0.0)
        projection_area_scale_x: uniform(1.0)
        projection_area_scale_y: uniform(1.0)
        projection_target_runtime: uniform(vec4(0.0, 0.0, 1.0, 0.0))
        left_projection_area_offset_radius_uv: uniform(vec4(0.0, 0.0, 0.5, 0.5))
        right_projection_area_offset_radius_uv: uniform(vec4(0.0, 0.0, 0.5, 0.5))
        projection_area_radius_x_uv: uniform(0.5)
        projection_area_radius_y_uv: uniform(0.5)
        projection_area_corner_radius_uv: uniform(0.0)
        projection_area_keystone_x: uniform(0.0)
        projection_area_bow_x: uniform(0.0)
        projection_area_opacity: uniform(1.0)
        projection_alpha_mode: uniform(0.0)
        projection_alpha_scale: uniform(1.0)
        projection_alpha_bias: uniform(0.0)
        mesh_replay_runtime: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        mesh_replay_segment0: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        mesh_replay_segment1: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        mesh_replay_segment2: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        mesh_replay_segment3: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        camera_shell_feature_runtime: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_surface_runtime: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_collision_contact: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_collision_normal: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_sdf_sample0: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_sdf_sample1: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_sdf_sample2: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_sdf_sample3: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_particle0: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_particle1: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_particle2: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_particle3: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        matter_particle_texture_runtime: uniform(vec4(0.0, 0.0, 0.0, 0.0))
        source_sample_y_flip: uniform(0.0)
        projection_content_mapping_mode: uniform(0.0)
        display_source_eye_swap: uniform(0.0)
        manual_vertical_offset_uv: uniform(0.0)
        camera_ready: uniform(1.0)
        yuv_mode: uniform(1.0)
        yuv_matrix: uniform(1.0)
        yuv_biplanar: uniform(0.0)
        v_uv: varying(vec2f)

        cube_size: uniform(vec3(1.0, 1.0, 1.0))
        cube_pos: uniform(vec3(0.0, 0.0, 0.0))
        depth_clip: uniform(0.0)

        get_size: fn() {
            return self.cube_size
        }

        get_pos: fn() {
            return self.cube_pos
        }

        vertex: fn() {
            let screen_uv = clamp(self.geom.pos, vec2(0.0, 0.0), vec2(1.0, 1.0));
            let instance_marker = self.makepad_instance_marker * 0.0;
            self.world = vec4(screen_uv.x, screen_uv.y, 0.0, 1.0);
            self.v_uv = screen_uv;
            self.vertex_pos = vec4(screen_uv.x * 2.0 - 1.0, screen_uv.y * 2.0 - 1.0, instance_marker, 1.0);
        }

        active_eye_is_right: fn() -> float {
            return clamp(xr_view_id(), 0.0, 1.0);
        }

        source_eye_selector: fn() -> float {
            let display_eye = self.active_eye_is_right();
            return mix(display_eye, 1.0 - display_eye, self.display_source_eye_swap);
        }

        apply_projection_homography: fn(
            coord: vec2f,
            h00: float,
            h01: float,
            h02: float,
            h10: float,
            h11: float,
            h12: float,
            h20: float,
            h21: float,
            h22: float
        ) -> vec2f {
            let x = h00 * coord.x + h01 * coord.y + h02;
            let y = h10 * coord.x + h11 * coord.y + h12;
            let w = h20 * coord.x + h21 * coord.y + h22;
            let safe_w = mix(1.0, w, step(0.00001, abs(w)));
            return vec2(x, y) / safe_w;
        }

        source_camera_uv: fn(coord: vec2f, selector: float) -> vec2f {
            let left_uv = self.apply_projection_homography(
                coord,
                self.left_projection_h00,
                self.left_projection_h01,
                self.left_projection_h02,
                self.left_projection_h10,
                self.left_projection_h11,
                self.left_projection_h12,
                self.left_projection_h20,
                self.left_projection_h21,
                self.left_projection_h22
            );
            let right_uv = self.apply_projection_homography(
                coord,
                self.right_projection_h00,
                self.right_projection_h01,
                self.right_projection_h02,
                self.right_projection_h10,
                self.right_projection_h11,
                self.right_projection_h12,
                self.right_projection_h20,
                self.right_projection_h21,
                self.right_projection_h22
            );
            return mix(left_uv, right_uv, selector);
        }

        source_screen_camera_uv: fn(coord: vec2f, selector: float) -> vec2f {
            let left_uv = self.apply_projection_homography(
                coord,
                self.left_screen_to_camera_h00,
                self.left_screen_to_camera_h01,
                self.left_screen_to_camera_h02,
                self.left_screen_to_camera_h10,
                self.left_screen_to_camera_h11,
                self.left_screen_to_camera_h12,
                self.left_screen_to_camera_h20,
                self.left_screen_to_camera_h21,
                self.left_screen_to_camera_h22
            );
            let right_uv = self.apply_projection_homography(
                coord,
                self.right_screen_to_camera_h00,
                self.right_screen_to_camera_h01,
                self.right_screen_to_camera_h02,
                self.right_screen_to_camera_h10,
                self.right_screen_to_camera_h11,
                self.right_screen_to_camera_h12,
                self.right_screen_to_camera_h20,
                self.right_screen_to_camera_h21,
                self.right_screen_to_camera_h22
            );
            return mix(left_uv, right_uv, selector);
        }

        screen_surface_uv: fn(coord: vec2f, display_eye_selector: float) -> vec2f {
            let left_uv = self.apply_projection_homography(
                coord,
                self.left_screen_to_surface_h00,
                self.left_screen_to_surface_h01,
                self.left_screen_to_surface_h02,
                self.left_screen_to_surface_h10,
                self.left_screen_to_surface_h11,
                self.left_screen_to_surface_h12,
                self.left_screen_to_surface_h20,
                self.left_screen_to_surface_h21,
                self.left_screen_to_surface_h22
            );
            let right_uv = self.apply_projection_homography(
                coord,
                self.right_screen_to_surface_h00,
                self.right_screen_to_surface_h01,
                self.right_screen_to_surface_h02,
                self.right_screen_to_surface_h10,
                self.right_screen_to_surface_h11,
                self.right_screen_to_surface_h12,
                self.right_screen_to_surface_h20,
                self.right_screen_to_surface_h21,
                self.right_screen_to_surface_h22
            );
            return mix(left_uv, right_uv, display_eye_selector);
        }

        mapped_source_uv_for_content_mode: fn(
            projection_screen_uv: vec2f,
            target_local_uv: vec2f,
            display_eye_selector: float,
            target_local_mapping: float
        ) -> vec2f {
            if target_local_mapping > 0.5 {
                return target_local_uv;
            }
            return self.source_screen_camera_uv(projection_screen_uv, display_eye_selector);
        }

        surface_uv_for_content_mode: fn(
            projection_screen_uv: vec2f,
            target_local_uv: vec2f,
            display_eye_selector: float,
            target_local_mapping: float
        ) -> vec2f {
            if target_local_mapping > 0.5 {
                return target_local_uv;
            }
            return self.screen_surface_uv(projection_screen_uv, display_eye_selector);
        }

        projection_area_screen_base_uv: fn(coord: vec2f) -> vec2f {
            let scale = max(
                vec2(self.projection_area_scale_x, self.projection_area_scale_y),
                vec2(0.01, 0.01)
            );
            return (coord - vec2(0.5, 0.5)) * scale + vec2(0.5, 0.5);
        }

        projection_area_offset_uv: fn(display_eye_selector: float) -> vec2f {
            let metadata = step(0.5, self.projection_target_runtime.w);
            let fallback_x = mix(
                self.projection_area_offset_left_uv,
                self.projection_area_offset_right_uv,
                display_eye_selector
            );
            let metadata_x = mix(
                self.left_projection_area_offset_radius_uv.x,
                self.right_projection_area_offset_radius_uv.x,
                display_eye_selector
            );
            let metadata_y = mix(
                self.left_projection_area_offset_radius_uv.y,
                self.right_projection_area_offset_radius_uv.y,
                display_eye_selector
            );
            let base_offset = vec2(
                mix(fallback_x, metadata_x, metadata),
                mix(self.projection_area_offset_vertical_uv, metadata_y, metadata)
            );
            return clamp(
                base_offset +
                self.projection_target_runtime.xy,
                vec2(-0.5, -0.5),
                vec2(0.5, 0.5)
            );
        }

        clamp_border_seed_uv: fn(seed_uv: vec2f) -> vec2f {
            let center = vec2(0.5, 0.5);
            let radius = vec2(0.31, 0.28);
            let p = (seed_uv - center) / radius;
            let len = max(length(p), 1.0);
            return center + (p / len) * radius;
        }

        uv_valid: fn(coord: vec2f) -> float {
            return
                step(0.0, coord.x) *
                step(coord.x, 1.0) *
                step(0.0, coord.y) *
                step(coord.y, 1.0);
        }

        rotate_uv: fn(coord: vec2f, rotation_steps: float) -> vec2f {
            let coord_90 = vec2(1.0 - coord.y, coord.x);
            let coord_180 = vec2(1.0 - coord.x, 1.0 - coord.y);
            let coord_270 = vec2(coord.y, 1.0 - coord.x);
            let is_90 = step(0.5, rotation_steps) * step(rotation_steps, 1.5);
            let is_180 = step(1.5, rotation_steps) * step(rotation_steps, 2.5);
            let is_270 = step(2.5, rotation_steps);
            let is_0 = 1.0 - is_90 - is_180 - is_270;
            return coord * is_0 + coord_90 * is_90 + coord_180 * is_180 + coord_270 * is_270;
        }

        yuv_to_rgb: fn(y_val: float, u_val: float, v_val: float) -> vec3f {
            let y = (y_val * 255.0 - 16.0) / 219.0;
            let u = (u_val * 255.0 - 128.0) / 224.0;
            let v = (v_val * 255.0 - 128.0) / 224.0;

            let r709 = y + 1.5748 * v;
            let g709 = y - 0.1873 * u - 0.4681 * v;
            let b709 = y + 1.8556 * u;

            let r601 = y + 1.402 * v;
            let g601 = y - 0.3441 * u - 0.7141 * v;
            let b601 = y + 1.772 * u;

            let r2020 = y + 1.4746 * v;
            let g2020 = y - 0.1646 * u - 0.5714 * v;
            let b2020 = y + 1.8814 * u;

            let is_601 = step(0.5, self.yuv_matrix) * step(self.yuv_matrix, 1.5);
            let is_2020 = step(1.5, self.yuv_matrix);
            let is_709 = 1.0 - is_601 - is_2020;

            return vec3(
                clamp(is_709 * r709 + is_601 * r601 + is_2020 * r2020, 0.0, 1.0),
                clamp(is_709 * g709 + is_601 * g601 + is_2020 * g2020, 0.0, 1.0),
                clamp(is_709 * b709 + is_601 * b601 + is_2020 * b2020, 0.0, 1.0)
            );
        }

        yuv_to_rgb_limited_601: fn(y_val: float, u_val: float, v_val: float) -> vec3f {
            let y = (y_val * 255.0 - 16.0) / 219.0;
            let u = (u_val * 255.0 - 128.0) / 224.0;
            let v = (v_val * 255.0 - 128.0) / 224.0;
            return vec3(
                clamp(y + 1.402 * v, 0.0, 1.0),
                clamp(y - 0.3441 * u - 0.7141 * v, 0.0, 1.0),
                clamp(y + 1.772 * u, 0.0, 1.0)
            );
        }

        yuv_to_rgb_limited_709: fn(y_val: float, u_val: float, v_val: float) -> vec3f {
            let y = (y_val * 255.0 - 16.0) / 219.0;
            let u = (u_val * 255.0 - 128.0) / 224.0;
            let v = (v_val * 255.0 - 128.0) / 224.0;
            return vec3(
                clamp(y + 1.5748 * v, 0.0, 1.0),
                clamp(y - 0.1873 * u - 0.4681 * v, 0.0, 1.0),
                clamp(y + 1.8556 * u, 0.0, 1.0)
            );
        }

        yuv_to_rgb_full_601: fn(y_val: float, u_val: float, v_val: float) -> vec3f {
            let y = y_val;
            let u = u_val - 0.5;
            let v = v_val - 0.5;
            return vec3(
                clamp(y + 1.402 * v, 0.0, 1.0),
                clamp(y - 0.3441 * u - 0.7141 * v, 0.0, 1.0),
                clamp(y + 1.772 * u, 0.0, 1.0)
            );
        }

        yuv_to_rgb_full_709: fn(y_val: float, u_val: float, v_val: float) -> vec3f {
            let y = y_val;
            let u = u_val - 0.5;
            let v = v_val - 0.5;
            return vec3(
                clamp(y + 1.5748 * v, 0.0, 1.0),
                clamp(y - 0.1873 * u - 0.4681 * v, 0.0, 1.0),
                clamp(y + 1.8556 * u, 0.0, 1.0)
            );
        }

        sample_left_yuv: fn(coord: vec2f) -> vec3f {
            let y_val = self.left_tex_y.sample(coord).x;
            let uv_sample = self.left_tex_u.sample(coord);
            let u_val = uv_sample.x;
            let v_val = mix(self.left_tex_v.sample(coord).x, uv_sample.y, step(0.5, self.yuv_biplanar));
            return self.yuv_to_rgb(y_val, u_val, v_val);
        }

        sample_right_yuv: fn(coord: vec2f) -> vec3f {
            let y_val = self.right_tex_y.sample(coord).x;
            let uv_sample = self.right_tex_u.sample(coord);
            let u_val = uv_sample.x;
            let v_val = mix(self.right_tex_v.sample(coord).x, uv_sample.y, step(0.5, self.yuv_biplanar));
            return self.yuv_to_rgb(y_val, u_val, v_val);
        }

        sample_camera_rgb: fn(coord: vec2f, eye_selector: float) -> vec3f {
            let sample_uv = clamp(coord, vec2(0.0, 0.0), vec2(1.0, 1.0));
            if self.yuv_mode > 0.5 {
                if eye_selector > 0.5 {
                    return self.sample_right_yuv(sample_uv);
                }
                return self.sample_left_yuv(sample_uv);
            }
            if eye_selector > 0.5 {
                return self.right_camera_texture.sample_video(sample_uv).xyz;
            }
            return self.left_camera_texture.sample_video(sample_uv).xyz;
        }

        sample_camera_blur_rgb: fn(coord: vec2f, eye_selector: float) -> vec3f {
            let blur_source_texel = vec2(1.0 / 1280.0, 1.0 / 1280.0);
            let sample_step = blur_source_texel * clamp(self.blur_radius_px, 0.0, 16.0) * 4.0;
            let sample_uv = clamp(coord, vec2(0.0, 0.0), vec2(1.0, 1.0));
            let x0 = -2.0 * sample_step.x;
            let x1 = -1.0 * sample_step.x;
            let x2 = 0.0;
            let x3 = 1.0 * sample_step.x;
            let x4 = 2.0 * sample_step.x;
            let y0 = -2.0 * sample_step.y;
            let y1 = -1.0 * sample_step.y;
            let y2 = 0.0;
            let y3 = 1.0 * sample_step.y;
            let y4 = 2.0 * sample_step.y;
            let row0 =
                self.sample_camera_rgb(sample_uv + vec2(x0, y0), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x1, y0), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x2, y0), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x3, y0), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x4, y0), eye_selector);
            let row1 =
                self.sample_camera_rgb(sample_uv + vec2(x0, y1), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x1, y1), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x2, y1), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x3, y1), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x4, y1), eye_selector);
            let row2 =
                self.sample_camera_rgb(sample_uv + vec2(x0, y2), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x1, y2), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x2, y2), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x3, y2), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x4, y2), eye_selector);
            let row3 =
                self.sample_camera_rgb(sample_uv + vec2(x0, y3), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x1, y3), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x2, y3), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x3, y3), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x4, y3), eye_selector);
            let row4 =
                self.sample_camera_rgb(sample_uv + vec2(x0, y4), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x1, y4), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x2, y4), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x3, y4), eye_selector) +
                self.sample_camera_rgb(sample_uv + vec2(x4, y4), eye_selector);
            let color = (row0 + row1 + row2 + row3 + row4) / 25.0;
            return vec3(
                clamp(color.x, 0.0, 1.0),
                clamp(color.y, 0.0, 1.0),
                clamp(color.z, 0.0, 1.0)
            );
        }

        sample_processed_camera_rgb: fn(coord: vec2f, eye_selector: float) -> vec3f {
            if self.processing_layer > 0.5 && self.processing_layer < 1.5 {
                return self.sample_camera_blur_rgb(coord, eye_selector);
            }
            return self.sample_camera_rgb(coord, eye_selector);
        }

        sample_or_solid_camera_rgb: fn(coord: vec2f, eye_selector: float) -> vec3f {
            if self.projection_sample_mode > 0.5 {
                let left_solid = vec3(0.08, 0.28, 0.72);
                let right_solid = vec3(0.70, 0.16, 0.38);
                return mix(left_solid, right_solid, eye_selector);
            }
            return self.sample_processed_camera_rgb(coord, eye_selector);
        }

        projection_alpha_transform: fn(mask: float) -> float {
            return clamp(
                mask * max(self.projection_alpha_scale, 0.0) + self.projection_alpha_bias,
                0.0,
                1.0
            );
        }

        projection_color_alpha: fn(rgb: vec3f) -> float {
            let color = clamp(rgb, vec3(0.0, 0.0, 0.0), vec3(1.0, 1.0, 1.0));
            let luma = color.x * 0.2126 + color.y * 0.7152 + color.z * 0.0722;
            let max_channel = max(max(color.x, color.y), color.z);
            let min_channel = min(min(color.x, color.y), color.z);
            let saturation = max_channel - min_channel;
            let mode = self.projection_alpha_mode;
            if mode > 0.5 && mode < 1.5 {
                return self.projection_alpha_transform(color.x);
            }
            if mode > 1.5 && mode < 2.5 {
                return self.projection_alpha_transform(color.y);
            }
            if mode > 2.5 && mode < 3.5 {
                return self.projection_alpha_transform(color.z);
            }
            if mode > 3.5 && mode < 4.5 {
                return self.projection_alpha_transform(luma);
            }
            if mode > 4.5 && mode < 5.5 {
                return self.projection_alpha_transform(1.0 - color.x);
            }
            if mode > 5.5 && mode < 6.5 {
                return self.projection_alpha_transform(1.0 - color.y);
            }
            if mode > 6.5 && mode < 7.5 {
                return self.projection_alpha_transform(1.0 - color.z);
            }
            if mode > 7.5 && mode < 8.5 {
                return self.projection_alpha_transform(1.0 - luma);
            }
            if mode > 8.5 && mode < 9.5 {
                return self.projection_alpha_transform(max(color.x - max(color.y, color.z), 0.0));
            }
            if mode > 9.5 && mode < 10.5 {
                return self.projection_alpha_transform(max(color.y - max(color.x, color.z), 0.0));
            }
            if mode > 10.5 && mode < 11.5 {
                return self.projection_alpha_transform(max(color.z - max(color.x, color.y), 0.0));
            }
            if mode > 11.5 && mode < 12.5 {
                return self.projection_alpha_transform(saturation);
            }
            if mode > 12.5 && mode < 13.5 {
                return self.projection_alpha_transform(1.0 - saturation);
            }
            return self.projection_alpha_transform(1.0);
        }

        source_sample_uv: fn(coord: vec2f) -> vec2f {
            let sample_uv = clamp(coord, vec2(0.0, 0.0), vec2(1.0, 1.0));
            let flip_y = step(0.5, self.source_sample_y_flip);
            return vec2(sample_uv.x, mix(sample_uv.y, 1.0 - sample_uv.y, flip_y));
        }

        guide_mask: fn(coord: vec2f) -> float {
            let edge_x = min(coord.x, 1.0 - coord.x);
            let edge_y = min(coord.y, 1.0 - coord.y);
            let border = 1.0 - step(0.015, min(edge_x, edge_y));
            return clamp(border, 0.0, 1.0);
        }

        projection_border_mask: fn(coord: vec2f) -> float {
            let inside = self.uv_valid(coord);
            let edge_x = min(coord.x, 1.0 - coord.x);
            let edge_y = min(coord.y, 1.0 - coord.y);
            let border = 1.0 - step(0.025, min(edge_x, edge_y));
            return clamp(border * inside, 0.0, 1.0);
        }

        projection_area_mask: fn(area_uv: vec2f, display_eye_selector: float) -> float {
            let signed_distance = self.target_footprint_signed_distance_uv(area_uv, display_eye_selector);
            return 1.0 - step(0.0001, signed_distance);
        }

        projection_area_half_size_uv: fn(display_eye_selector: float) -> vec2f {
            let metadata = step(0.5, self.projection_target_runtime.w);
            let fallback_radius = vec2(
                self.projection_area_radius_x_uv,
                self.projection_area_radius_y_uv
            );
            let metadata_radius = vec2(
                mix(
                    self.left_projection_area_offset_radius_uv.z,
                    self.right_projection_area_offset_radius_uv.z,
                    display_eye_selector
                ),
                mix(
                    self.left_projection_area_offset_radius_uv.w,
                    self.right_projection_area_offset_radius_uv.w,
                    display_eye_selector
                )
            );
            let radius = mix(fallback_radius, metadata_radius, metadata);
            let target_scale = clamp(self.projection_target_runtime.z, 0.05, 1.50);
            return clamp(radius * target_scale, vec2(0.001, 0.001), vec2(0.50, 0.50));
        }

        projection_area_content_uv: fn(area_uv: vec2f, display_eye_selector: float) -> vec2f {
            let half_size = self.projection_area_half_size_uv(display_eye_selector);
            return (area_uv - (vec2(0.5, 0.5) - half_size)) /
                max(half_size * 2.0, vec2(0.001, 0.001));
        }

        target_footprint_signed_distance_uv: fn(area_uv: vec2f, display_eye_selector: float) -> float {
            let center = vec2(0.5, 0.5);
            let half_size = self.projection_area_half_size_uv(display_eye_selector);
            let corner_radius = clamp(
                self.projection_area_corner_radius_uv,
                0.0,
                min(half_size.x, half_size.y) - 0.001
            );
            let q = abs(area_uv - center) - (half_size - vec2(corner_radius, corner_radius));
            let outside = length(max(q, vec2(0.0, 0.0)));
            let inside = min(max(q.x, q.y), 0.0);
            return outside + inside - corner_radius;
        }

        projection_area_rect_edge_uv: fn(
            canonical_uv: vec2f,
            display_eye_selector: float,
            domain_min_uv: vec2f,
            domain_max_uv: vec2f,
            force_edge_sample: float
        ) -> vec2f {
            let center = vec2(0.5, 0.5);
            let half_size = self.projection_area_half_size_uv(display_eye_selector);
            let core_scale = clamp(self.peripheral_stretch_core_scale, 0.05, 1.0);
            let core_half_size = max(half_size * core_scale, vec2(0.001, 0.001));
            let normalized = (canonical_uv - center) / core_half_size;
            let edge_distance = max(max(abs(normalized.x), abs(normalized.y)), 0.0001);
            if edge_distance <= 1.0 && force_edge_sample <= 0.5 {
                return canonical_uv;
            }
            let effective_edge_distance =
                mix(edge_distance, max(edge_distance, 1.0), clamp(force_edge_sample, 0.0, 1.0));
            let edge_normalized = normalized / edge_distance;
            let edge_direction_uv = edge_normalized * core_half_size;
            let bounded_min_uv = min(domain_min_uv, domain_max_uv);
            let bounded_max_uv = max(domain_min_uv, domain_max_uv);
            let default_reach = 1000000.0;
            let positive_x_reach =
                (bounded_max_uv.x - center.x) / max(edge_direction_uv.x, 0.0001);
            let negative_x_reach =
                (bounded_min_uv.x - center.x) / min(edge_direction_uv.x, -0.0001);
            let reach_x = mix(
                default_reach,
                mix(negative_x_reach, positive_x_reach, step(0.0, edge_direction_uv.x)),
                step(0.0001, abs(edge_direction_uv.x))
            );
            let positive_y_reach =
                (bounded_max_uv.y - center.y) / max(edge_direction_uv.y, 0.0001);
            let negative_y_reach =
                (bounded_min_uv.y - center.y) / min(edge_direction_uv.y, -0.0001);
            let reach_y = mix(
                default_reach,
                mix(negative_y_reach, positive_y_reach, step(0.0, edge_direction_uv.y)),
                step(0.0001, abs(edge_direction_uv.y))
            );
            let exterior_reach = max(min(reach_x, reach_y) - 1.0, 0.0001);
            let exterior_t = smoothstep(
                0.0,
                1.0,
                clamp((effective_edge_distance - 1.0) / exterior_reach, 0.0, 1.0)
            );
            let edge_inset = clamp(self.peripheral_stretch_edge_inset_uv, 0.0, 0.49);
            let max_inset = clamp(
                self.peripheral_stretch_max_inset_uv,
                edge_inset,
                0.49
            );
            let curve = clamp(self.peripheral_stretch_curve, 0.25, 6.0);
            let inset = mix(edge_inset, max_inset, pow(exterior_t, curve));
            let sample_half_size = max(core_half_size - vec2(inset, inset), vec2(0.001, 0.001));
            let sample_uv = center + edge_normalized * sample_half_size;
            return clamp(sample_uv, bounded_min_uv, bounded_max_uv);
        }

        projection_area_stretch_domain_uv: fn(
            canonical_uv: vec2f,
            display_eye_selector: float,
            domain_min_uv: vec2f,
            domain_max_uv: vec2f,
            stretch_weight: float
        ) -> vec2f {
            if stretch_weight <= 0.0001 {
                return canonical_uv;
            }
            return self.projection_area_rect_edge_uv(
                canonical_uv,
                display_eye_selector,
                domain_min_uv,
                domain_max_uv,
                1.0
            );
        }

        peripheral_stretch_active: fn() -> float {
            return step(1.5, self.processing_layer);
        }

        peripheral_stretch_blend_weight: fn(signed_distance_uv: float) -> float {
            let blend_mode = floor(self.peripheral_stretch_blend_mode + 0.5);
            let inner_blend = clamp(self.peripheral_stretch_inner_blend_uv, 0.0, 0.25);
            let blend_curve = clamp(self.peripheral_stretch_blend_curve, 0.25, 6.0);
            if blend_mode < 0.5 {
                return step(0.0, signed_distance_uv);
            }
            if signed_distance_uv >= 0.0 {
                return 1.0;
            }
            if inner_blend <= 0.0001 {
                return 0.0;
            }
            let t = smoothstep(-inner_blend, 0.0, signed_distance_uv);
            return pow(t, blend_curve);
        }

        diagnostic_domain_edge_mask: fn(coord: vec2f, width: float, pad: float) -> float {
            let near_domain =
                step(-pad, coord.x) *
                step(coord.x, 1.0 + pad) *
                step(-pad, coord.y) *
                step(coord.y, 1.0 + pad);
            let edge_x = min(abs(coord.x), abs(coord.x - 1.0));
            let edge_y = min(abs(coord.y), abs(coord.y - 1.0));
            return (1.0 - step(width, min(edge_x, edge_y))) * near_domain;
        }

        diagnostic_axis_mask: fn(coord: vec2f, axis: float, width: float) -> float {
            return max(
                1.0 - step(width, abs(coord.x - axis)),
                1.0 - step(width, abs(coord.y - axis))
            );
        }

        projection_area_diagnostic_color: fn(
            surface_uv: vec2f,
            camera_uv: vec2f,
            display_eye_selector: float,
            projection_valid: float
        ) -> vec3f {
            let diagnostic_uv = clamp(camera_uv, vec2(0.0, 0.0), vec2(1.0, 1.0));
            let border = self.diagnostic_domain_edge_mask(camera_uv, 0.018, 0.060);
            let surface_guide_strength =
                1.0 - step(1.5, self.projection_area_diagnostic);
            let surface_border =
                self.diagnostic_domain_edge_mask(surface_uv, 0.010, 0.035) *
                projection_valid *
                surface_guide_strength;
            let major_axes = self.diagnostic_axis_mask(diagnostic_uv, 0.5, 0.010);
            let quarter_axes = max(
                self.diagnostic_axis_mask(diagnostic_uv, 0.25, 0.006),
                self.diagnostic_axis_mask(diagnostic_uv, 0.75, 0.006)
            );
            let diagonal = clamp(
                (1.0 - step(0.010, abs(diagnostic_uv.x - diagnostic_uv.y))) +
                (1.0 - step(0.010, abs((diagnostic_uv.x + diagnostic_uv.y) - 1.0))),
                0.0,
                1.0
            );
            let left_color = vec3(0.08, 0.30, 0.98);
            let right_color = vec3(0.98, 0.06, 0.48);
            let base = mix(left_color, right_color, display_eye_selector);
            let ramp = vec3(
                0.18 + diagnostic_uv.x * 0.62,
                0.12 + diagnostic_uv.y * 0.76,
                0.90 - diagnostic_uv.x * 0.22
            );
            let with_grid = mix(base, ramp, 0.42);
            let with_major = mix(with_grid, vec3(1.0, 1.0, 1.0), clamp(major_axes * 0.82, 0.0, 1.0));
            let with_quarters = mix(with_major, vec3(0.05, 1.0, 0.72), clamp(quarter_axes * 0.52, 0.0, 1.0));
            let with_diagonal = mix(with_quarters, vec3(1.0, 0.86, 0.04), clamp(diagonal * 0.44, 0.0, 1.0));
            let inside = mix(vec3(0.0, 0.0, 0.0), with_diagonal, projection_valid);
            let with_border = mix(inside, vec3(1.0, 0.0, 1.0), clamp(border, 0.0, 1.0));
            return mix(with_border, vec3(1.0, 1.0, 1.0), clamp(surface_border * 0.70, 0.0, 1.0));
        }

        mesh_replay_segment_distance: fn(coord: vec2f, segment: vec4f) -> float {
            let start = vec2(segment.x, segment.y);
            let end = vec2(segment.z, segment.w);
            let edge = end - start;
            let edge_len2 = max(dot(edge, edge), 0.0001);
            let t = clamp(dot(coord - start, edge) / edge_len2, 0.0, 1.0);
            let nearest = start + edge * t;
            return length(coord - nearest);
        }

        mesh_replay_segment_mask: fn(coord: vec2f, segment: vec4f) -> float {
            return 1.0 - smoothstep(0.004, 0.014, self.mesh_replay_segment_distance(coord, segment));
        }

        mesh_replay_field_distance: fn(coord: vec2f) -> float {
            let d0 = self.mesh_replay_segment_distance(coord, self.mesh_replay_segment0);
            let d1 = self.mesh_replay_segment_distance(coord, self.mesh_replay_segment1);
            let d2 = self.mesh_replay_segment_distance(coord, self.mesh_replay_segment2);
            let d3 = self.mesh_replay_segment_distance(coord, self.mesh_replay_segment3);
            return min(min(d0, d1), min(d2, d3));
        }

        mesh_replay_overlay_mask: fn(coord: vec2f) -> float {
            let enabled = step(0.5, self.mesh_replay_runtime.x);
            let inside =
                step(0.0, coord.x) *
                step(coord.x, 1.0) *
                step(0.0, coord.y) *
                step(coord.y, 1.0);
            let mask0 = self.mesh_replay_segment_mask(coord, self.mesh_replay_segment0);
            let mask1 = self.mesh_replay_segment_mask(coord, self.mesh_replay_segment1);
            let mask2 = self.mesh_replay_segment_mask(coord, self.mesh_replay_segment2);
            let mask3 = self.mesh_replay_segment_mask(coord, self.mesh_replay_segment3);
            return enabled * inside * clamp(max(max(mask0, mask1), max(mask2, mask3)), 0.0, 1.0);
        }

        mesh_replay_overlay_rgb: fn(rgb: vec3f, coord: vec2f, visibility: float) -> vec3f {
            let mask = self.mesh_replay_overlay_mask(coord) * clamp(visibility, 0.0, 1.0);
            let phase = fract(self.mesh_replay_runtime.y);
            let opacity = clamp(self.mesh_replay_runtime.w, 0.0, 1.0);
            let pulse = 0.52 + 0.28 * sin(phase * 6.28318530718);
            let replay_color =
                vec3(0.04, 0.95, 0.74) * pulse +
                vec3(0.10, 0.22, 0.95) * (1.0 - pulse);
            return mix(rgb, replay_color, clamp(mask * opacity, 0.0, 1.0));
        }

        mesh_replay_overlay_alpha: fn(alpha: float, coord: vec2f, visibility: float) -> float {
            let mask = self.mesh_replay_overlay_mask(coord) * clamp(visibility, 0.0, 1.0);
            return max(alpha, clamp(mask * self.mesh_replay_runtime.w, 0.0, 1.0));
        }

        sdf_adf_overlay_rgb: fn(rgb: vec3f, coord: vec2f, visibility: float) -> vec3f {
            let mode = floor(self.camera_shell_feature_runtime.y + 0.5);
            let sdf_active =
                step(0.5, mode) *
                (1.0 - step(1.5, mode)) *
                step(0.5, self.matter_surface_runtime.x) *
                step(0.5, self.matter_surface_runtime.z) *
                clamp(visibility, 0.0, 1.0);
            let s0 = self.matter_sdf_sample_mask(coord, self.matter_sdf_sample0);
            let s1 = self.matter_sdf_sample_mask(coord, self.matter_sdf_sample1);
            let s2 = self.matter_sdf_sample_mask(coord, self.matter_sdf_sample2);
            let s3 = self.matter_sdf_sample_mask(coord, self.matter_sdf_sample3);
            let mask = sdf_active * clamp(max(max(s0, s1), max(s2, s3)), 0.0, 1.0);
            return mix(rgb, vec3(0.03, 0.74, 0.92), clamp(mask * 0.42, 0.0, 0.42));
        }

        matter_sdf_sample_mask: fn(coord: vec2f, sample: vec4f) -> float {
            let sample_live = step(0.5, sample.w);
            let distance_uv = length(coord - vec2(sample.x, sample.y));
            let radius = mix(0.018, 0.044, clamp(1.0 - sample.z, 0.0, 1.0));
            return sample_live * (1.0 - smoothstep(radius, radius + 0.018, distance_uv));
        }

        collision_overlay_rgb: fn(rgb: vec3f, coord: vec2f, visibility: float) -> vec3f {
            let enabled =
                step(0.5, self.camera_shell_feature_runtime.x) *
                step(0.5, self.matter_surface_runtime.x) *
                step(0.5, self.matter_surface_runtime.y) *
                clamp(visibility, 0.0, 1.0);
            let contact = vec2(self.matter_collision_contact.x, self.matter_collision_contact.y);
            let probe_distance = length(coord - contact);
            let probe_mask = 1.0 - smoothstep(0.035, 0.085, probe_distance);
            let collision_mask = enabled * self.matter_collision_contact.w * probe_mask;
            return mix(rgb, vec3(1.0, 0.10, 0.04), clamp(collision_mask * 0.68, 0.0, 0.68));
        }

        matter_particle_mask: fn(coord: vec2f, particle: vec4f) -> float {
            let particle_live = step(0.001, particle.w);
            let radius = max(particle.z, 0.006);
            return particle_live * particle.w * (1.0 - smoothstep(radius, radius + 0.016, length(coord - vec2(particle.x, particle.y))));
        }

        particle_mask: fn(coord: vec2f) -> float {
            let m0 = self.matter_particle_mask(coord, self.matter_particle0);
            let m1 = self.matter_particle_mask(coord, self.matter_particle1);
            let m2 = self.matter_particle_mask(coord, self.matter_particle2);
            let m3 = self.matter_particle_mask(coord, self.matter_particle3);
            return clamp(max(max(m0, m1), max(m2, m3)), 0.0, 1.0);
        }

        particles_overlay_rgb: fn(rgb: vec3f, coord: vec2f, visibility: float) -> vec3f {
            let enabled =
                step(0.5, self.camera_shell_feature_runtime.z) *
                step(0.5, self.matter_surface_runtime.x) *
                step(0.5, self.matter_surface_runtime.w) *
                clamp(visibility, 0.0, 1.0);
            let mask = enabled * self.particle_mask(coord);
            return mix(rgb, vec3(0.96, 0.92, 0.30), clamp(mask * 0.74, 0.0, 0.74));
        }

        particle_texture_overlay_rgb: fn(rgb: vec3f, coord: vec2f, visibility: float) -> vec3f {
            let enabled =
                step(0.5, self.camera_shell_feature_runtime.z) *
                step(0.5, self.matter_surface_runtime.x) *
                step(0.5, self.matter_surface_runtime.w) *
                step(0.5, self.matter_particle_texture_runtime.x) *
                clamp(visibility, 0.0, 1.0);
            let sample = self.matter_particle_texture.sample(coord);
            let particle_rgb = sample.xyz * enabled;
            return clamp(rgb + particle_rgb, vec3(0.0, 0.0, 0.0), vec3(1.0, 1.0, 1.0));
        }

        camera_shell_overlay_rgb: fn(rgb: vec3f, coord: vec2f, visibility: float) -> vec3f {
            let field_rgb = self.sdf_adf_overlay_rgb(rgb, coord, visibility);
            let particle_texture_rgb = self.particle_texture_overlay_rgb(field_rgb, coord, visibility);
            let particle_rgb = self.particles_overlay_rgb(particle_texture_rgb, coord, visibility);
            let collision_rgb = self.collision_overlay_rgb(particle_rgb, coord, visibility);
            return self.mesh_replay_overlay_rgb(collision_rgb, coord, visibility);
        }

        pixel: fn() {
            let renderer_surface_uv = clamp(self.v_uv, vec2(0.0, 0.0), vec2(1.0, 1.0));
            let full_view_uv = vec2(renderer_surface_uv.x, 1.0 - renderer_surface_uv.y);
            let proof_guide = 0.0;
            let eye_selector = self.source_eye_selector();
            let display_eye_selector = self.active_eye_is_right();
            let projection_screen_uv_base =
                self.projection_area_screen_base_uv(full_view_uv);
            let projection_area_offset =
                self.projection_area_offset_uv(display_eye_selector);
            let canonical_projection_area_domain_uv =
                projection_screen_uv_base - projection_area_offset;
            let signed_distance_uv =
                self.target_footprint_signed_distance_uv(
                    canonical_projection_area_domain_uv,
                    display_eye_selector
                );
            let projection_area_mask =
                1.0 - step(0.0001, signed_distance_uv);
            let peripheral_stretch_active = self.peripheral_stretch_active();
            let stretch_weight =
                peripheral_stretch_active *
                self.peripheral_stretch_blend_weight(signed_distance_uv);
            let stretch_exterior =
                peripheral_stretch_active * (1.0 - projection_area_mask);
            let target_transition_band =
                peripheral_stretch_active *
                projection_area_mask *
                step(0.0001, stretch_weight);
            let target_stretch_effect_region =
                clamp(max(stretch_exterior, target_transition_band), 0.0, 1.0);
            let projection_area_scale =
                max(vec2(self.projection_area_scale_x, self.projection_area_scale_y), vec2(0.01, 0.01));
            let projection_area_domain_min_uv =
                vec2(0.5, 0.5) - projection_area_scale * 0.5 - projection_area_offset;
            let projection_area_domain_max_uv =
                vec2(0.5, 0.5) + projection_area_scale * 0.5 - projection_area_offset;
            let stretch_projection_area_domain_uv = self.projection_area_stretch_domain_uv(
                canonical_projection_area_domain_uv,
                display_eye_selector,
                projection_area_domain_min_uv,
                projection_area_domain_max_uv,
                stretch_weight
            );
            let projection_area_domain_uv = mix(
                canonical_projection_area_domain_uv,
                stretch_projection_area_domain_uv,
                clamp(stretch_weight, 0.0, 1.0) * target_stretch_effect_region
            );
            let projection_screen_uv_base_adjusted =
                projection_area_domain_uv + projection_area_offset;
            let full_frame_projection_area_mapping =
                step(0.5, self.projection_content_mapping_mode);
            let projection_screen_uv =
                mix(
                    projection_screen_uv_base_adjusted,
                    projection_area_domain_uv,
                    full_frame_projection_area_mapping
                );
            let projection_area_content_uv =
                self.projection_area_content_uv(projection_area_domain_uv, display_eye_selector);
            let mapped_source_uv_unclamped = self.mapped_source_uv_for_content_mode(
                projection_screen_uv,
                projection_area_content_uv,
                display_eye_selector,
                full_frame_projection_area_mapping
            );
            let source_uv_stretchable =
                step(abs(mapped_source_uv_unclamped.x), 65536.0) *
                step(abs(mapped_source_uv_unclamped.y), 65536.0);
            let target_local_stretch_region =
                full_frame_projection_area_mapping * target_stretch_effect_region;
            let mapped_source_uv = mix(
                mapped_source_uv_unclamped,
                clamp(mapped_source_uv_unclamped, vec2(0.0001, 0.0001), vec2(0.9999, 0.9999)),
                target_local_stretch_region
            );
            let source_uv_valid_raw = self.uv_valid(mapped_source_uv);
            let source_uv_valid =
                mix(source_uv_valid_raw, source_uv_stretchable, target_local_stretch_region);
            let homography_source_invalid_stretch_region =
                (1.0 - full_frame_projection_area_mapping) *
                target_stretch_effect_region *
                (1.0 - source_uv_valid) *
                source_uv_stretchable;
            let target_local_projection_valid =
                source_uv_valid *
                clamp(max(projection_area_mask, target_stretch_effect_region), 0.0, 1.0);
            let homography_projection_valid =
                max(
                    mix(
                        source_uv_valid * projection_area_mask,
                        source_uv_valid,
                        target_stretch_effect_region
                    ),
                    homography_source_invalid_stretch_region
                );
            let projection_valid =
                clamp(
                    mix(
                        homography_projection_valid,
                        target_local_projection_valid,
                        full_frame_projection_area_mapping
                    ),
                    0.0,
                    1.0
                );
            let surface_uv = self.surface_uv_for_content_mode(
                projection_screen_uv_base_adjusted,
                projection_area_content_uv,
                display_eye_selector,
                full_frame_projection_area_mapping
            );
            let fallback_seed_uv =
                self.clamp_border_seed_uv(clamp(surface_uv, vec2(0.0, 0.0), vec2(1.0, 1.0)));
            let projected_sample_uv = self.source_sample_uv(mapped_source_uv);
            let fallback_sample_uv = self.source_sample_uv(fallback_seed_uv);
            let sample_uv = mix(fallback_sample_uv, projected_sample_uv, projection_valid);
            let full_surface_sample_uv = self.source_sample_uv(full_view_uv);
            let live_sample_uv = mix(sample_uv, full_surface_sample_uv, self.force_full_surface_live_camera_uv);
            let live_projection_valid = mix(projection_valid, 1.0, self.force_full_surface_live_camera_uv);
            if self.camera_ready <= 0.5 {
                let waiting = vec3(0.015, 0.020, 0.024);
                let guided_waiting = mix(waiting, vec3(1.0, 0.98, 0.84), proof_guide);
                let replay_waiting = self.camera_shell_overlay_rgb(guided_waiting, full_view_uv, 1.0);
                return vec4(replay_waiting.x, replay_waiting.y, replay_waiting.z, 1.0);
            }
            if self.suppress_live_camera_sampling > 0.5 {
                let armed = vec3(0.015, 0.18, 0.08);
                let guided_armed = mix(armed, vec3(1.0, 0.98, 0.84), proof_guide);
                let replay_armed = self.camera_shell_overlay_rgb(guided_armed, full_view_uv, 1.0);
                return vec4(replay_armed.x, replay_armed.y, replay_armed.z, 1.0);
            }
            if self.projection_area_diagnostic > 0.5 {
                let diagnostic_rgb = self.projection_area_diagnostic_color(
                    surface_uv,
                    mapped_source_uv,
                    display_eye_selector,
                    projection_valid
                );
                let guided_diagnostic = mix(diagnostic_rgb, vec3(1.0, 0.98, 0.84), proof_guide);
                let replay_diagnostic = self.camera_shell_overlay_rgb(
                    guided_diagnostic,
                    projection_area_content_uv,
                    projection_area_mask
                );
                return vec4(replay_diagnostic.x, replay_diagnostic.y, replay_diagnostic.z, 1.0);
            }
            if self.force_in_surface_camera_window > 0.5 {
                let camera_window_uv = clamp(mapped_source_uv, vec2(0.0, 0.0), vec2(1.0, 1.0));
                let window_sample_uv = self.source_sample_uv(camera_window_uv);
                let camera_rgb = self.sample_or_solid_camera_rgb(window_sample_uv, eye_selector);
                let passthrough_border_policy =
                    step(0.5, self.projection_border_policy);
                let projection_area_opacity = clamp(self.projection_area_opacity, 0.0, 1.0);
                let projection_border_opacity = clamp(self.projection_border_opacity, 0.0, 1.0);
                let diagnostic_fill_rgb = vec3(1.0, 0.0, 0.0);
                let matte = mix(diagnostic_fill_rgb, vec3(0.0, 0.0, 0.0), passthrough_border_policy);
                let camera_window_valid = projection_valid;
                let region_debug =
                    step(0.5, self.peripheral_stretch_debug) *
                    step(self.peripheral_stretch_debug, 1.5);
                if peripheral_stretch_active > 0.5 &&
                    self.peripheral_stretch_debug > 1.5 &&
                    target_stretch_effect_region > 0.5 &&
                    camera_window_valid > 0.5
                {
                    let sample_debug =
                        vec3(
                            window_sample_uv.x,
                            window_sample_uv.y,
                            0.25 +
                                0.35 * target_transition_band +
                                0.35 * homography_source_invalid_stretch_region
                        );
                    return vec4(sample_debug.x, sample_debug.y, sample_debug.z, 1.0);
                }
                let transition_tint = mix(camera_rgb, vec3(0.96, 1.0, 0.08), 0.42);
                let exterior_tint = mix(camera_rgb, vec3(0.0, 0.88, 1.0), 0.48);
                let source_invalid_tint = mix(camera_rgb, vec3(0.06, 1.0, 0.34), 0.40);
                let region_rgb =
                    mix(
                        mix(
                            mix(camera_rgb, exterior_tint, stretch_exterior),
                            source_invalid_tint,
                            homography_source_invalid_stretch_region
                        ),
                        transition_tint,
                        target_transition_band
                    );
                let debug_camera_rgb =
                    mix(camera_rgb, region_rgb, region_debug * camera_window_valid);
                let window_rgb = mix(matte, debug_camera_rgb, camera_window_valid);
                let guided_window = mix(window_rgb, vec3(1.0, 0.98, 0.84), proof_guide);
                let border_alpha = projection_border_opacity * (1.0 - passthrough_border_policy);
                let area_alpha = projection_area_opacity * self.projection_color_alpha(debug_camera_rgb);
                let alpha = self.mesh_replay_overlay_alpha(
                    mix(border_alpha, area_alpha, camera_window_valid),
                    projection_area_content_uv,
                    projection_area_mask
                );
                let replay_window = self.camera_shell_overlay_rgb(
                    guided_window,
                    projection_area_content_uv,
                    projection_area_mask
                );
                let premultiplied_window = replay_window * alpha;
                return vec4(
                    premultiplied_window.x,
                    premultiplied_window.y,
                    premultiplied_window.z,
                    alpha
                );
            }
            let direct_rgb =
                self.sample_or_solid_camera_rgb(live_sample_uv, eye_selector) * mix(0.12, 1.0, live_projection_valid);
            let guided_direct = mix(direct_rgb, vec3(1.0, 0.98, 0.84), proof_guide);
            let replay_direct = self.camera_shell_overlay_rgb(guided_direct, full_view_uv, 1.0);
            return vec4(replay_direct.x, replay_direct.y, replay_direct.z, 1.0);
        }

        fragment: fn() {
            self.fb0 = depth_clip(self.world, self.pixel(), self.depth_clip);
        }
    }

    mod.widgets.MakepadStereoCameraPanelBase = #(MakepadStereoCameraPanel::register_widget(vm))
    mod.widgets.MakepadStereoCameraPanel = set_type_default() do mod.widgets.MakepadStereoCameraPanelBase{
        body: mod.widgets.XrBodyKind.Fixed
        shared_object_policy: mod.widgets.XrSharedObjectPolicy.None
        size: vec3(0.92, 0.92, 0.010)
        draw_panel +: {
            exposure: 1.06
            camera_ready: 1.0
            diagnostic_solid: 0.0
            alignment_guide: 1.0
            yuv_mode: 1.0
            yuv_matrix: 1.0
            yuv_biplanar: 0.0
            texture_probe_mode: 2.0
            proof_tint_strength: 0.0
            mesh_replay_runtime: vec4(0.0, 0.0, 0.0, 0.0)
            mesh_replay_segment0: vec4(0.0, 0.0, 0.0, 0.0)
            mesh_replay_segment1: vec4(0.0, 0.0, 0.0, 0.0)
            mesh_replay_segment2: vec4(0.0, 0.0, 0.0, 0.0)
            mesh_replay_segment3: vec4(0.0, 0.0, 0.0, 0.0)
            camera_shell_feature_runtime: vec4(0.0, 0.0, 0.0, 0.0)
            matter_surface_runtime: vec4(0.0, 0.0, 0.0, 0.0)
            matter_collision_contact: vec4(0.0, 0.0, 0.0, 0.0)
            matter_collision_normal: vec4(0.0, 0.0, 0.0, 0.0)
            matter_sdf_sample0: vec4(0.0, 0.0, 0.0, 0.0)
            matter_sdf_sample1: vec4(0.0, 0.0, 0.0, 0.0)
            matter_sdf_sample2: vec4(0.0, 0.0, 0.0, 0.0)
            matter_sdf_sample3: vec4(0.0, 0.0, 0.0, 0.0)
            matter_particle0: vec4(0.0, 0.0, 0.0, 0.0)
            matter_particle1: vec4(0.0, 0.0, 0.0, 0.0)
            matter_particle2: vec4(0.0, 0.0, 0.0, 0.0)
            matter_particle3: vec4(0.0, 0.0, 0.0, 0.0)
            matter_particle_texture_runtime: vec4(0.0, 0.0, 0.0, 0.0)
            depth_clip: 0.0
        }
    }
}
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

//! Makepad live/script definitions for the Hostess stimulus stereo field.
//!
//! Keep stimulus shader and widget defaults here so the app shell does not
//! accumulate renderer-specific volume code.

use crate::makepad_widgets::*;
use crate::stimulus_stereo_field::{DrawStimulusStereoField, StimulusStereoFieldPanel};

script_mod! {
    use mod.pod.*
    use mod.math.*
    use mod.shader.*
    use mod.draw
    use mod.geom
    use mod.prelude.widgets.*
    use mod.widgets.*

    mod.draw.DrawStimulusStereoField = mod.std.set_type_default() do #(DrawStimulusStereoField::script_shader(vm)){
        ..mod.draw.DrawQuad
        alpha_blend: false
        backface_culling: false

        enabled: 0.0
        time_seconds: 0.0
        temporal_frequency_hz: 0.0
        spatial_frequency: 8.0
        rotation_radians: 0.0
        phase_offset: 0.0
        wave_modulation: 0.0
        radial_decay: 0.0
        geometry_mix: 1.0
        edge_fade: 0.0
        source_a_b: vec4(-0.24, 0.0, 0.24, 0.0)
        source_b_weight: 1.0
        color_low: vec4(0.0, 0.0, 0.0, 1.0)
        color_high: vec4(1.0, 1.0, 1.0, 1.0)
        post_contrast: 1.0
        post_brightness: 0.0
        intensity_gain: 1.0
        background_grid_mix: 0.35
        texture_flow_strength: 0.0
        fiducial_intensity: 0.0
        binocular_color_separation: 0.0
        binocular_phase_offset_radians: 0.0
        display_eye_offset_meters: 0.032
        display_aspect: 1.0
        projection_depth_meters: 1.0
        projection_preview_fov_y_degrees: 69.763084
        projection_preview_offset_y_meters: -0.168832
        projection_raw_overscan: 1.0
        projection_rows_ready: 0.0
        volume_preview_texture: texture_2d(float)
        volume_texture_ready: 0.0
        volume_texture_blend: 0.0
        volume_renderer_ready: 0.0
        volume_renderer_blend: 0.0
        volume_raymarch_steps: 3.0
        volume_grid_frequency: 4.0
        volume_density_gain: 0.72
        volume_absorption: 1.25
        volume_phase: 0.0
        volume_eccentricity: 1.0
        volume_noise_scale: 3.0
        volume_noise_strength: 0.42
        volume_noise_motion: 0.18
        volume_oscillator_mix: 0.44
        volume_shell_mix: 0.24
        left_screen_to_surface_h00: 1.0
        left_screen_to_surface_h01: 0.0
        left_screen_to_surface_h02: 0.0
        left_screen_to_surface_h10: 0.0
        left_screen_to_surface_h11: 1.0
        left_screen_to_surface_h12: 0.0
        left_screen_to_surface_h20: 0.0
        left_screen_to_surface_h21: 0.0
        left_screen_to_surface_h22: 1.0
        right_screen_to_surface_h00: 1.0
        right_screen_to_surface_h01: 0.0
        right_screen_to_surface_h02: 0.0
        right_screen_to_surface_h10: 0.0
        right_screen_to_surface_h11: 1.0
        right_screen_to_surface_h12: 0.0
        right_screen_to_surface_h20: 0.0
        right_screen_to_surface_h21: 0.0
        right_screen_to_surface_h22: 1.0
        v_uv: varying(vec2f)

        vertex: fn() {
            let screen_uv = clamp(self.geom.pos, vec2(0.0, 0.0), vec2(1.0, 1.0))
            let instance_marker = self.rect_size.x * 0.0
            self.world = vec4(screen_uv.x, screen_uv.y, 0.0, 1.0)
            self.v_uv = screen_uv
            self.vertex_pos = vec4(screen_uv.x * 2.0 - 1.0, screen_uv.y * 2.0 - 1.0, instance_marker, 1.0)
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
            let x = h00 * coord.x + h01 * coord.y + h02
            let y = h10 * coord.x + h11 * coord.y + h12
            let w = h20 * coord.x + h21 * coord.y + h22
            let safe_w = mix(1.0, w, step(0.00001, abs(w)))
            return vec2(x, y) / safe_w
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
            )
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
            )
            return mix(left_uv, right_uv, display_eye_selector)
        }

        volume_preview_sample: fn(surface_uv: vec2f, display_eye_selector: float) -> vec4 {
            let atlas_uv = clamp(
                vec2(surface_uv.x * 0.5 + display_eye_selector * 0.5, surface_uv.y),
                vec2(0.001, 0.001),
                vec2(0.999, 0.999)
            )
            return self.volume_preview_texture.sample(atlas_uv)
        }

        fiducial_mask: fn(surface_uv: vec2f) -> float {
            let center_delta = abs(surface_uv - vec2(0.5, 0.5))
            let center_vertical =
                (1.0 - step(0.010, center_delta.x)) * (1.0 - step(0.115, center_delta.y))
            let center_horizontal =
                (1.0 - step(0.010, center_delta.y)) * (1.0 - step(0.115, center_delta.x))
            let corner_radius = 0.030
            let corner_a = 1.0 - smoothstep(0.0, corner_radius, length(surface_uv - vec2(0.08, 0.08)))
            let corner_b = 1.0 - smoothstep(0.0, corner_radius, length(surface_uv - vec2(0.92, 0.08)))
            let corner_c = 1.0 - smoothstep(0.0, corner_radius, length(surface_uv - vec2(0.08, 0.92)))
            let corner_d = 1.0 - smoothstep(0.0, corner_radius, length(surface_uv - vec2(0.92, 0.92)))
            return clamp(max(max(center_vertical, center_horizontal), max(max(corner_a, corner_b), max(corner_c, corner_d))), 0.0, 1.0)
        }

        volume_hash3: fn(x: float, y: float, z: float) -> float {
            let n = x * 0.1031 + y * 0.11369 + z * 0.13787
            let p = n - floor(n)
            let q = p * (p + 33.33)
            let r = q * (q + p + 19.19)
            return r - floor(r)
        }

        volume_value_noise: fn(p: vec3f) -> float {
            let ix = floor(p.x)
            let iy = floor(p.y)
            let iz = floor(p.z)
            let fx = p.x - ix
            let fy = p.y - iy
            let fz = p.z - iz
            let ux = fx * fx * (3.0 - 2.0 * fx)
            let uy = fy * fy * (3.0 - 2.0 * fy)
            let uz = fz * fz * (3.0 - 2.0 * fz)

            let n000 = self.volume_hash3(ix, iy, iz)
            let n100 = self.volume_hash3(ix + 1.0, iy, iz)
            let n010 = self.volume_hash3(ix, iy + 1.0, iz)
            let n110 = self.volume_hash3(ix + 1.0, iy + 1.0, iz)
            let n001 = self.volume_hash3(ix, iy, iz + 1.0)
            let n101 = self.volume_hash3(ix + 1.0, iy, iz + 1.0)
            let n011 = self.volume_hash3(ix, iy + 1.0, iz + 1.0)
            let n111 = self.volume_hash3(ix + 1.0, iy + 1.0, iz + 1.0)

            let x00 = mix(n000, n100, ux)
            let x10 = mix(n010, n110, ux)
            let x01 = mix(n001, n101, ux)
            let x11 = mix(n011, n111, ux)
            let y0 = mix(x00, x10, uy)
            let y1 = mix(x01, x11, uy)
            return mix(y0, y1, uz)
        }

        volume_fbm: fn(p: vec3f) -> float {
            let n0 = self.volume_value_noise(p)
            let n1 = self.volume_value_noise(vec3(p.x * 2.03 + 17.1, p.y * 2.03 + 29.7, p.z * 2.03 + 11.3))
            return n0 * 0.68 + n1 * 0.32
        }

        volume_oscillator_field: fn(p: vec3f) -> float {
            let freq = max(self.volume_grid_frequency, 1.0)
            let phase = self.volume_phase
            let radial = length(vec2(p.x, p.y))
            let radial_wave = sin(radial * freq * 2.21 - phase * 0.83)
            let axial_wave = sin(p.z * freq * 1.11 + phase * 1.27)
            let cross_wave = sin((p.x - p.y * 0.53 + p.z * 0.37) * freq * 0.91 + phase * 0.41)
            return radial_wave * 0.46 + axial_wave * 0.34 + cross_wave * 0.20
        }

        volume_density: fn(p: vec3f) -> float {
            let freq = max(self.volume_grid_frequency, 1.0)
            let phase = self.volume_phase
            let ellipsoid = length(vec3(p.x * 0.92, p.y * 0.92, p.z * 0.70))
            let envelope = 1.0 - smoothstep(0.18, 1.42, ellipsoid)
            let axial = sin((p.x + p.y * 0.37 + p.z * 0.21) * freq + phase)
            let folded = sin((abs(p.x) + abs(p.y) * 0.71 + p.z * 0.43) * freq * 1.37 - phase * 0.73)
            let lattice = sin((p.x * p.y + p.z * 0.28) * freq * 2.11 + phase * 1.13)
            let noise_drive = max(self.volume_noise_scale, 0.25)
            let noise_motion = clamp(self.volume_noise_motion, 0.0, 2.0)
            let noise_p = vec3(
                p.x * noise_drive + phase * noise_motion,
                p.y * noise_drive + phase * noise_motion * 0.17,
                p.z * noise_drive - phase * noise_motion * 0.11
            )
            let noise = self.volume_fbm(noise_p) * 2.0 - 1.0
            let oscillator = self.volume_oscillator_field(p)
            let shell = sin(ellipsoid * freq * 1.73 - phase * 0.91)
            let base_field = axial * 0.37 + folded * 0.26 + lattice * 0.16
            let detail_field = base_field + noise * clamp(self.volume_noise_strength, 0.0, 1.25) * 0.55
            let osc_field = mix(detail_field, oscillator, clamp(self.volume_oscillator_mix, 0.0, 1.0))
            let field = mix(osc_field, osc_field * 0.74 + shell * 0.26, clamp(self.volume_shell_mix, 0.0, 1.0))
            return clamp(smoothstep(-0.18, 0.42, field) * envelope, 0.0, 1.0)
        }

        volume_raymarch_sample: fn(surface_uv: vec2f, display_eye_selector: float, sample_t: float) -> vec4 {
            let centered = surface_uv * 2.0 - vec2(1.0, 1.0)
            let eccentricity = clamp(self.volume_eccentricity, 0.35, 2.75)
            let shaped_uv = vec2(centered.x * eccentricity, centered.y / eccentricity)
            let eye_shift = (display_eye_selector - 0.5) * self.display_eye_offset_meters * 3.125
            let ray_origin = vec3(shaped_uv.x * 0.55 + eye_shift, shaped_uv.y * 0.55, -0.90)
            let ray_dir = vec3(shaped_uv.x * 0.22 + eye_shift * 0.20, shaped_uv.y * 0.18, 1.0)
            let p = ray_origin + ray_dir * mix(0.04, 1.82, sample_t)
            let density = self.volume_density(p)
            let depth_fade = pow(1.0 - clamp(sample_t * 0.42, 0.0, 0.92), max(self.volume_absorption, 0.25))
            let sample_alpha = clamp(density * depth_fade, 0.0, 1.0)
            let base_light = 0.44 + 0.56 * (0.5 + 0.5 * sin((p.z + p.x * 0.45) * max(self.volume_grid_frequency, 1.0) + self.volume_phase))
            let base_rgb = mix(self.color_low.xyz, self.color_high.xyz, clamp(density, 0.0, 1.0))
            let eye_tint = mix(vec3(0.08, 0.78, 1.00), vec3(1.00, 0.24, 0.12), display_eye_selector)
            let rgb = base_rgb.mix(eye_tint, clamp(self.binocular_color_separation, 0.0, 1.0)) * sample_alpha * base_light
            return vec4(rgb.x, rgb.y, rgb.z, sample_alpha)
        }

        volume_raymarch: fn(surface_uv: vec2f, display_eye_selector: float) -> vec4 {
            let step_count = clamp(self.volume_raymarch_steps, 1.0, 4.0)
            let s00 = self.volume_raymarch_sample(surface_uv, display_eye_selector, 0.16667)
            let s01 = self.volume_raymarch_sample(surface_uv, display_eye_selector, 0.50000)
            if step_count <= 2.5 {
                let sum = s00 + s01
                let alpha = clamp((sum.w / 2.0) * self.volume_density_gain * max(self.volume_absorption, 0.25), 0.0, 1.0)
                let rgb = sum.xyz / max(sum.w, 0.001)
                let ambient_phase = self.volume_phase + display_eye_selector * self.binocular_phase_offset_radians
                let ambient = mix(self.color_low.xyz, self.color_high.xyz, 0.5 + 0.5 * sin(ambient_phase))
                let out_rgb = ambient.mix(rgb, alpha)
                return vec4(out_rgb.x, out_rgb.y, out_rgb.z, alpha)
            }
            let s02 = self.volume_raymarch_sample(surface_uv, display_eye_selector, 0.83333)
            if step_count <= 3.5 {
                let sum = s00 + s01 + s02
                let alpha = clamp((sum.w / 3.0) * self.volume_density_gain * max(self.volume_absorption, 0.25), 0.0, 1.0)
                let rgb = sum.xyz / max(sum.w, 0.001)
                let ambient_phase = self.volume_phase + display_eye_selector * self.binocular_phase_offset_radians
                let ambient = mix(self.color_low.xyz, self.color_high.xyz, 0.5 + 0.5 * sin(ambient_phase))
                let out_rgb = ambient.mix(rgb, alpha)
                return vec4(out_rgb.x, out_rgb.y, out_rgb.z, alpha)
            }
            let s03 = self.volume_raymarch_sample(surface_uv, display_eye_selector, 0.93750)
            let sum = s00 + s01 + s02 + s03
            let alpha = clamp((sum.w / max(step_count, 1.0)) * self.volume_density_gain * max(self.volume_absorption, 0.25), 0.0, 1.0)
            let rgb = sum.xyz / max(sum.w, 0.001)
            let ambient_phase = self.volume_phase + display_eye_selector * self.binocular_phase_offset_radians
            let ambient = mix(self.color_low.xyz, self.color_high.xyz, 0.5 + 0.5 * sin(ambient_phase))
            let out_rgb = ambient.mix(rgb, alpha)
            return vec4(out_rgb.x, out_rgb.y, out_rgb.z, alpha)
        }

        pixel: fn() {
            let renderer_uv = clamp(self.v_uv, vec2(0.0, 0.0), vec2(1.0, 1.0))
            let display_eye_screen_uv = vec2(renderer_uv.x, 1.0 - renderer_uv.y)
            let display_eye_selector = clamp(xr_view_id(), 0.0, 1.0)
            let surface_uv = self.screen_surface_uv(display_eye_screen_uv, display_eye_selector)
            let bounded_surface_uv = clamp(surface_uv, vec2(0.0, 0.0), vec2(1.0, 1.0))
            let uv = surface_uv * 2.0 - vec2(1.0, 1.0)
            let c = cos(self.rotation_radians)
            let s = sin(self.rotation_radians)
            let p = vec2(uv.x * c - uv.y * s, uv.x * s + uv.y * c)
            let source_a = self.source_a_b.xy
            let source_b = self.source_a_b.zw
            let d0 = length(p - source_a)
            let d1 = length(p - source_b)
            let tau = 6.2831853
            let phase = (self.time_seconds * max(self.temporal_frequency_hz, 0.001) + self.phase_offset) * tau
            let stripes = sin((p.x + p.y * 0.18) * self.spatial_frequency * tau + phase)
            let ripple = sin((d0 + d1 * self.source_b_weight) * self.spatial_frequency * tau - phase)
            let interference = sin((d0 - d1 * self.source_b_weight) * self.spatial_frequency * tau + phase * (1.0 + self.wave_modulation))
            let geometry_field = mix(stripes, 0.5 * (ripple + interference), clamp(self.geometry_mix, 0.0, 1.0))
            let grid_phase = phase * 1.31 + sin(phase * 0.37)
            let grid_x = sin((p.x + p.y * 0.11) * self.spatial_frequency * tau * 0.72 + grid_phase)
            let grid_y = sin((p.y - p.x * 0.17) * self.spatial_frequency * tau * 0.68 - grid_phase * 0.91)
            let grid_diag = sin((p.x + p.y) * self.spatial_frequency * tau * 0.42 + phase * (1.0 + self.wave_modulation * 0.5))
            let grid_luma = smoothstep(-0.10, 0.10, grid_x * grid_y * 0.68 + grid_diag * 0.32)
            let luma = clamp(max(smoothstep(-0.16, 0.16, geometry_field), grid_luma * clamp(self.background_grid_mix, 0.0, 1.0)), 0.0, 1.0)
            let radius = length(uv)
            let radial = pow(clamp(1.0 - radius * 0.34, 0.0, 1.0), max(self.radial_decay, 0.0))
            let edge = mix(1.0, 1.0 - smoothstep(0.72, 1.38, radius), clamp(self.edge_fade * 5.0, 0.0, 1.0))
            let pulse = 0.34 + 0.66 * (0.5 + 0.5 * sin(phase))
            let strobe_gate = clamp(pulse * (1.0 + 0.85 * clamp(self.geometry_mix, 0.0, 1.0)), 0.0, 1.0)
            let color = mix(self.color_low.xyz, self.color_high.xyz, luma)
            let rgb = color * max(radial, 0.18) * max(edge, 0.18) * strobe_gate
            let volume_render = self.volume_raymarch(bounded_surface_uv, display_eye_selector)
            let texture_flow = clamp(self.texture_flow_strength, 0.0, 0.12) * vec2(
                sin(phase * 1.17 + bounded_surface_uv.y * tau * 2.0),
                cos(phase * 0.91 + bounded_surface_uv.x * tau * 2.0)
            )
            let volume_sample = self.volume_preview_sample(clamp(bounded_surface_uv + texture_flow, vec2(0.0, 0.0), vec2(1.0, 1.0)), display_eye_selector)
            let texture_runtime_mix = clamp(self.volume_texture_ready * self.volume_texture_blend * 0.55, 0.0, 0.55)
            let procedural_rgb = volume_render.xyz * max(volume_render.w, 0.18)
            let sampled_rgb = volume_sample.xyz * max(volume_sample.w, 0.18)
            let grid_boost = mix(0.72, 1.45, clamp(grid_luma * self.background_grid_mix, 0.0, 1.0))
            let volume_rgb = procedural_rgb.mix(sampled_rgb, texture_runtime_mix) * strobe_gate * grid_boost
            let volume_mix = clamp(self.volume_renderer_ready * self.volume_renderer_blend * 0.92, 0.0, 0.92)
            let fiducial = self.fiducial_mask(bounded_surface_uv) * max(self.volume_texture_ready, self.volume_renderer_ready) * clamp(self.fiducial_intensity, 0.0, 1.0)
            let fiducial_color = mix(vec3(0.08, 0.78, 1.00), vec3(1.00, 0.24, 0.12), display_eye_selector)
            let blended_rgb = rgb.mix(volume_rgb, volume_mix).mix(fiducial_color, clamp(fiducial * 0.85, 0.0, 1.0))
            let contrasted_rgb = (blended_rgb - vec3(0.5, 0.5, 0.5)) * max(self.post_contrast, 0.0) + vec3(0.5, 0.5, 0.5) + vec3(self.post_brightness, self.post_brightness, self.post_brightness)
            let processed_rgb = clamp(contrasted_rgb * max(self.intensity_gain, 0.0), vec3(0.0, 0.0, 0.0), vec3(1.0, 1.0, 1.0))
            let proof_floor = vec3(0.025, 0.0, 0.012) * step(0.5, self.enabled)
            return vec4(max(processed_rgb, proof_floor), 1.0)
        }

        fragment: fn() {
            self.fb0 = self.pixel()
        }
    }

    mod.widgets.StimulusStereoFieldPanelBase = #(StimulusStereoFieldPanel::register_widget(vm))
    mod.widgets.StimulusStereoFieldPanel = set_type_default() do mod.widgets.StimulusStereoFieldPanelBase{
        body: mod.widgets.XrBodyKind.Fixed
        shared_object_policy: mod.widgets.XrSharedObjectPolicy.None
        draw_field: mod.draw.DrawStimulusStereoField{
            enabled: 0.0
            temporal_frequency_hz: 0.0
            spatial_frequency: 8.0
            geometry_mix: 1.0
            post_contrast: 1.0
            post_brightness: 0.0
            intensity_gain: 1.0
            background_grid_mix: 0.35
            texture_flow_strength: 0.0
            fiducial_intensity: 0.0
            binocular_color_separation: 0.0
            binocular_phase_offset_radians: 0.0
            volume_texture_ready: 0.0
            volume_texture_blend: 0.0
            volume_renderer_ready: 0.0
            volume_renderer_blend: 0.0
            volume_raymarch_steps: 3.0
            volume_grid_frequency: 4.0
            volume_density_gain: 0.72
            volume_absorption: 1.25
            volume_phase: 0.0
            volume_eccentricity: 1.0
            volume_noise_scale: 3.0
            volume_noise_strength: 0.42
            volume_noise_motion: 0.18
            volume_oscillator_mix: 0.44
            volume_shell_mix: 0.24
            color_low: vec4(0.0, 0.0, 0.0, 1.0)
            color_high: vec4(1.0, 1.0, 1.0, 1.0)
        }
    }
}

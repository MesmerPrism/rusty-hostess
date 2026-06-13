//! Hostess-local Makepad smoke renderer for Quest Makepad world-particle batches.
//!
//! Rusty Matter, Optics, and Quest-Makepad own runtime truth and renderer-neutral
//! rows. This module is the temporary Hostess Makepad widget implementation; a
//! reusable renderer should move to a dedicated Makepad adapter crate before reuse.

use crate::makepad_widgets::*;
use makepad_xr::scene::{xr_widget_world_transform, XrNode};
use rusty_quest_makepad_camera_shell::{
    ParticleRenderAnimationMode, QuestMakepadWorldParticleBatch, DEFAULT_PARTICLE_RENDER_SIZE_SCALE,
};

pub(crate) const HOSTESS_WORLD_PARTICLE_BILLBOARD_DRAW_LIMIT_MAX: usize = 8192;
const HOSTESS_WORLD_PARTICLE_BILLBOARD_SIZE_SCALE_MIN: f32 = 0.05;
const HOSTESS_WORLD_PARTICLE_BILLBOARD_SIZE_SCALE_MAX: f32 = 4.0;

script_mod! {
    use mod.pod.*
    use mod.math.*
    use mod.shader.*
    use mod.draw
    use mod.geom
    use mod.prelude.widgets.*
    use mod.widgets.*

    mod.widgets.MatterWorldParticleBillboardCloudBase = #(MatterWorldParticleBillboardCloud::register_widget(vm))
    mod.widgets.MatterWorldParticleBillboardCloud = set_type_default() do mod.widgets.MatterWorldParticleBillboardCloudBase{
        body: mod.widgets.XrBodyKind.Fixed
        shared_object_policy: mod.widgets.XrSharedObjectPolicy.None
        draw_cube +: {
            alpha_blend: true
            backface_culling: false
            light_dir: vec3(0.0, 0.0, 1.0)
            billboard_uv: varying(vec2f)
            billboard_state: varying(vec4f)

            vertex: fn() {
                let model_view = self.draw_list.view_transform * self.transform
                let center_world = model_view * vec4(self.cube_pos.x, self.cube_pos.y, self.cube_pos.z, 1.0)
                self.world = center_world

                let face_live = step(0.5, self.geom.geom_normal.z)
                let center_view = self.draw_pass.camera_view * center_world
                if face_live < 0.5 || center_view.z >= -0.000001 {
                    self.billboard_uv = vec2(0.0, 0.0)
                    self.billboard_state = vec4(0.0, 0.0, 1.0, 0.0)
                    self.lit_color = vec4(0.0, 0.0, 0.0, 0.0)
                    self.vertex_pos = vec4(2.0, 2.0, 2.0, 1.0)
                    return
                }

                let frame = clamp(self.cube_size.y, 0.0, 0.999985)
                let rotation = self.cube_size.z + frame * 6.2831853
                let cs = cos(rotation)
                let sn = sin(rotation)
                let raw_corner = self.geom.geom_pos.xy * 2.0
                let corner = vec2(
                    raw_corner.x * cs - raw_corner.y * sn,
                    raw_corner.x * sn + raw_corner.y * cs
                )

                let eye_origin = (self.draw_pass.camera_inv * vec4(0.0, 0.0, 0.0, 1.0)).xyz
                let normal_world = normalize((model_view * vec4(self.light_dir.x, self.light_dir.y, self.light_dir.z, 0.0)).xyz)
                let eye_dir = normalize(eye_origin - center_world.xyz)
                let facing = clamp(dot(normal_world, eye_dir), 0.0, 1.0)
                let frame_scale = 0.92 + 0.20 * frame
                let facing_scale = mix(0.86, 1.08, facing)
                let diameter = max(self.cube_size.x, 0.002) * frame_scale * facing_scale
                let view_pos = center_view + vec4(corner.x * diameter * 0.5, corner.y * diameter * 0.5, 0.0, 0.0)
                let projected = self.draw_pass.camera_projection * view_pos
                self.billboard_uv = corner * 0.5 + vec2(0.5, 0.5)
                self.billboard_state = vec4(frame, facing, clamp((-center_view.z - 0.05) / 12.0, 0.0, 1.0), 1.0)
                self.lit_color = self.color
                self.vertex_pos = projected
            }

            pixel: fn() {
                if self.billboard_state.w < 0.5 {
                    discard()
                }
                let p = self.billboard_uv * 2.0 - vec2(1.0, 1.0)
                let radius = length(p)
                if radius > 1.02 {
                    discard()
                }
                let frame = self.billboard_state.x
                let animated_ring = 0.60 + 0.08 * sin(frame * 6.2831853 + p.x * 3.1 - p.y * 2.2)
                let ring = 1.0 - smoothstep(0.050, 0.165, abs(radius - animated_ring))
                let core = (1.0 - smoothstep(0.12, 0.42, radius)) * 0.28
                let ripple = 0.72 + 0.28 * sin((p.x + p.y) * 7.0 + frame * 12.566371)
                let edge = 1.0 - smoothstep(0.92, 1.02, radius)
                let mask = clamp(max(core, ring * ripple) * edge, 0.0, 1.0)
                if mask < 0.002 {
                    discard()
                }
                let facing_tint = 0.80 + 0.20 * self.billboard_state.y
                let depth_atten = pow(2.0, -1.5 * self.billboard_state.z)
                let alpha = clamp(mask * self.color.w * 0.92, 0.0, 0.58)
                let rgb = min(self.color.xyz * facing_tint * depth_atten, vec3(1.0, 1.0, 1.0))
                return vec4(rgb.x * alpha, rgb.y * alpha, rgb.z * alpha, alpha)
            }

            fragment: fn() {
                self.fb0 = depth_clip(self.world, self.pixel(), self.depth_clip)
            }
        }
    }
}

#[derive(Script, Widget)]
pub struct MatterWorldParticleBillboardCloud {
    #[redraw]
    #[live]
    draw_cube: DrawCube,
    #[rust]
    batch: Option<QuestMakepadWorldParticleBatch>,
    #[rust]
    draw_limit: usize,
    #[rust]
    size_scale: f32,
    #[rust]
    animation_mode: ParticleRenderAnimationMode,
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
        size_scale: f32,
        animation_mode: ParticleRenderAnimationMode,
    ) {
        let draw_limit = draw_limit.min(HOSTESS_WORLD_PARTICLE_BILLBOARD_DRAW_LIMIT_MAX);
        let size_scale = if size_scale.is_finite() {
            size_scale.clamp(
                HOSTESS_WORLD_PARTICLE_BILLBOARD_SIZE_SCALE_MIN,
                HOSTESS_WORLD_PARTICLE_BILLBOARD_SIZE_SCALE_MAX,
            )
        } else {
            DEFAULT_PARTICLE_RENDER_SIZE_SCALE
        };
        if self.batch == batch
            && self.draw_limit == draw_limit
            && self.size_scale == size_scale
            && self.animation_mode == animation_mode
        {
            return;
        }
        self.batch = batch;
        self.draw_limit = draw_limit;
        self.size_scale = size_scale;
        self.animation_mode = animation_mode;
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
        let size_scale = if self.size_scale.is_finite() {
            self.size_scale.clamp(
                HOSTESS_WORLD_PARTICLE_BILLBOARD_SIZE_SCALE_MIN,
                HOSTESS_WORLD_PARTICLE_BILLBOARD_SIZE_SCALE_MAX,
            )
        } else {
            DEFAULT_PARTICLE_RENDER_SIZE_SCALE
        };
        let radius = (center_radius[3] * size_scale).clamp(0.012 * size_scale, 0.044 * size_scale);
        let diameter = (radius * 2.0).clamp(0.032 * size_scale, 0.088 * size_scale);
        let animated_frame = normal_frame[3].clamp(0.0, 0.999_985);
        let frame01 = if self.animation_mode.uses_frame_animation() {
            animated_frame
        } else {
            0.0
        };
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

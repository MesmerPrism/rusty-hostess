use crate::matter_surface_uniforms::project_matter_position_to_panel_uv;
use makepad_widgets::makepad_platform::{TextureFormat, TextureUpdated};
use makepad_widgets::*;
use rusty_quest_makepad_camera_shell::{
    QuestMakepadMatterSurfaceFrame, QuestMakepadParticleRow, QuestMakepadParticleUpload,
};

pub(crate) const MATTER_PARTICLE_TEXTURE_SLOT: usize = 8;
const MATTER_PARTICLE_TEXTURE_SIZE: usize = 256;
const MATTER_PARTICLE_TEXTURE_MAX_ROWS: usize = 4096;
const MATTER_PARTICLE_MIN_RADIUS_PX: f32 = 1.9;
const MATTER_PARTICLE_MAX_RADIUS_PX: f32 = 5.5;
const MATTER_PARTICLE_RADIUS_SCALE: f32 = 1.55;
const MATTER_PARTICLE_ADDITIVE_GAIN: f32 = 1.85;
const MATTER_PARTICLE_DEBUG_ALPHA_FLOOR: f32 = 0.24;
const MATTER_PARTICLE_MARKER_PREFIX: &str = "RUSTY_QUEST_MAKEPAD_MATTER_PARTICLE_TEXTURE";
const MATTER_PARTICLE_MARKER_SCHEMA: &str = "rusty.quest.makepad.matter_particle_texture.v1";

#[derive(Clone, Debug, Default)]
pub(crate) struct MatterParticleTextureFrame {
    pub(crate) texture: Option<Texture>,
    pub(crate) runtime: [f32; 4],
}

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct MatterParticleTextureStats {
    pub(crate) texture_size: usize,
    pub(crate) source_rows: usize,
    pub(crate) drawn_particles: usize,
    pub(crate) upload_bytes: usize,
    pub(crate) saturated_pixels: usize,
    pub(crate) max_alpha: u8,
}

impl MatterParticleTextureStats {
    fn runtime(self) -> [f32; 4] {
        [
            if self.drawn_particles > 0 { 1.0 } else { 0.0 },
            self.drawn_particles as f32,
            self.texture_size as f32,
            self.max_alpha as f32 / 255.0,
        ]
    }

    pub(crate) fn marker_line(self, phase: &str) -> String {
        format!(
            "{} schema={} phase={} status={} renderPlane=makepad-bgra-particle-overlay-texture sourceRows={} drawnParticles={} textureSize={}x{} uploadBytes={} saturatedPixels={} maxAlpha={}",
            MATTER_PARTICLE_MARKER_PREFIX,
            MATTER_PARTICLE_MARKER_SCHEMA,
            marker_token(phase),
            if self.drawn_particles > 0 { "ready" } else { "empty" },
            self.source_rows,
            self.drawn_particles,
            self.texture_size,
            self.texture_size,
            self.upload_bytes,
            self.saturated_pixels,
            self.max_alpha,
        )
    }
}

#[derive(Clone, Debug, Default)]
pub(crate) struct MatterParticleTextureRenderer {
    texture: Option<Texture>,
    pixels: Vec<u32>,
    markers_emitted: usize,
}

impl MatterParticleTextureRenderer {
    pub(crate) fn update_from_frame(
        &mut self,
        cx: &mut Cx,
        frame: &QuestMakepadMatterSurfaceFrame,
        bounds_min: [f32; 3],
        bounds_max: [f32; 3],
        phase: &str,
    ) -> MatterParticleTextureFrame {
        let Some(upload) = frame.particle_upload.as_ref() else {
            return MatterParticleTextureFrame::default();
        };

        let stats = rasterize_particle_upload(upload, bounds_min, bounds_max, &mut self.pixels);
        if self.markers_emitted < 8 {
            crate::emit_marker_line(&stats.marker_line(phase));
            self.markers_emitted += 1;
        }

        if stats.drawn_particles == 0 {
            return MatterParticleTextureFrame {
                runtime: stats.runtime(),
                ..MatterParticleTextureFrame::default()
            };
        }

        let texture = if let Some(texture) = self.texture.as_ref() {
            texture.swap_vec_u32(cx, &mut self.pixels);
            texture.clone()
        } else {
            let data = std::mem::take(&mut self.pixels);
            let texture = Texture::new_with_format(
                cx,
                TextureFormat::VecBGRAu8_32 {
                    width: MATTER_PARTICLE_TEXTURE_SIZE,
                    height: MATTER_PARTICLE_TEXTURE_SIZE,
                    data: Some(data),
                    updated: TextureUpdated::Full,
                },
            );
            self.texture = Some(texture.clone());
            texture
        };

        MatterParticleTextureFrame {
            texture: Some(texture),
            runtime: stats.runtime(),
        }
    }

    pub(crate) fn reset_markers(&mut self) {
        self.markers_emitted = 0;
    }
}

fn rasterize_particle_upload(
    upload: &QuestMakepadParticleUpload,
    bounds_min: [f32; 3],
    bounds_max: [f32; 3],
    pixels: &mut Vec<u32>,
) -> MatterParticleTextureStats {
    let texture_size = MATTER_PARTICLE_TEXTURE_SIZE;
    let pixel_count = texture_size * texture_size;
    pixels.clear();
    pixels.resize(pixel_count, 0);

    let mut stats = MatterParticleTextureStats {
        texture_size,
        source_rows: upload.rows.len(),
        upload_bytes: pixel_count * std::mem::size_of::<u32>(),
        ..MatterParticleTextureStats::default()
    };

    let radius_scale = bounds_extent(bounds_min, bounds_max).max(0.001);
    for row in upload.rows.iter().take(MATTER_PARTICLE_TEXTURE_MAX_ROWS) {
        if draw_particle_row(
            row,
            bounds_min,
            bounds_max,
            radius_scale,
            texture_size,
            pixels,
        ) {
            stats.drawn_particles += 1;
        }
    }

    for pixel in pixels.iter().copied() {
        let alpha = ((pixel >> 24) & 0xff) as u8;
        stats.max_alpha = stats.max_alpha.max(alpha);
        if alpha == u8::MAX {
            stats.saturated_pixels += 1;
        }
    }

    stats
}

fn draw_particle_row(
    row: &QuestMakepadParticleRow,
    bounds_min: [f32; 3],
    bounds_max: [f32; 3],
    radius_scale: f32,
    texture_size: usize,
    pixels: &mut [u32],
) -> bool {
    let position = [
        row.position_radius[0],
        row.position_radius[1],
        row.position_radius[2],
    ];
    if !position.iter().all(|value| value.is_finite()) || !row.position_radius[3].is_finite() {
        return false;
    }

    let uv = project_matter_position_to_panel_uv(position, bounds_min, bounds_max);
    let center_x = uv[0] * (texture_size.saturating_sub(1) as f32);
    let center_y = uv[1] * (texture_size.saturating_sub(1) as f32);
    if !center_x.is_finite() || !center_y.is_finite() {
        return false;
    }

    let radius_px = ((row.position_radius[3].max(0.0) / radius_scale)
        * texture_size as f32
        * MATTER_PARTICLE_RADIUS_SCALE)
        .clamp(MATTER_PARTICLE_MIN_RADIUS_PX, MATTER_PARTICLE_MAX_RADIUS_PX);
    let draw_radius = (radius_px + 1.5).ceil() as i32;
    let min_x = ((center_x.floor() as i32) - draw_radius).max(0);
    let max_x = ((center_x.ceil() as i32) + draw_radius).min(texture_size as i32 - 1);
    let min_y = ((center_y.floor() as i32) - draw_radius).max(0);
    let max_y = ((center_y.ceil() as i32) + draw_radius).min(texture_size as i32 - 1);

    let red = finite_color(row.color[0]);
    let green = finite_color(row.color[1]);
    let blue = finite_color(row.color[2]);
    let alpha = finite_color(row.color[3]).max(MATTER_PARTICLE_DEBUG_ALPHA_FLOOR);
    if alpha <= 0.001 {
        return false;
    }

    let mut touched = false;
    for y in min_y..=max_y {
        for x in min_x..=max_x {
            let dx = x as f32 + 0.5 - center_x;
            let dy = y as f32 + 0.5 - center_y;
            let distance = (dx * dx + dy * dy).sqrt();
            let falloff = smooth_particle_falloff(distance, radius_px);
            if falloff <= 0.0 {
                continue;
            }
            let coverage = (alpha * falloff).clamp(0.0, 1.0);
            let pixel_index = y as usize * texture_size + x as usize;
            add_premultiplied_particle_pixel(&mut pixels[pixel_index], red, green, blue, coverage);
            touched = true;
        }
    }
    touched
}

fn smooth_particle_falloff(distance: f32, radius_px: f32) -> f32 {
    if distance <= radius_px {
        1.0
    } else {
        let feather = 1.5_f32;
        (1.0 - ((distance - radius_px) / feather)).clamp(0.0, 1.0)
    }
}

fn add_premultiplied_particle_pixel(pixel: &mut u32, red: f32, green: f32, blue: f32, alpha: f32) {
    let old_alpha = ((*pixel >> 24) & 0xff) as u16;
    let old_red = ((*pixel >> 16) & 0xff) as u16;
    let old_green = ((*pixel >> 8) & 0xff) as u16;
    let old_blue = (*pixel & 0xff) as u16;

    let gain = alpha * MATTER_PARTICLE_ADDITIVE_GAIN * 255.0;
    let next_alpha = old_alpha.max((alpha * 255.0).round().clamp(0.0, 255.0) as u16);
    let next_red = old_red.saturating_add((red * gain).round().clamp(0.0, 255.0) as u16);
    let next_green = old_green.saturating_add((green * gain).round().clamp(0.0, 255.0) as u16);
    let next_blue = old_blue.saturating_add((blue * gain).round().clamp(0.0, 255.0) as u16);

    *pixel = ((next_alpha.min(255) as u32) << 24)
        | ((next_red.min(255) as u32) << 16)
        | ((next_green.min(255) as u32) << 8)
        | next_blue.min(255) as u32;
}

fn finite_color(value: f32) -> f32 {
    if value.is_finite() {
        value.clamp(0.0, 1.0)
    } else {
        0.0
    }
}

fn bounds_extent(bounds_min: [f32; 3], bounds_max: [f32; 3]) -> f32 {
    (bounds_max[0] - bounds_min[0])
        .max(bounds_max[1] - bounds_min[1])
        .max(bounds_max[2] - bounds_min[2])
        .max(0.0)
}

fn marker_token(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '.' | '/') {
                ch
            } else {
                '_'
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn row_at(x: f32, y: f32) -> QuestMakepadParticleRow {
        QuestMakepadParticleRow {
            position_radius: [x, y, 0.0, 0.05],
            color: [1.0, 0.92, 0.30, 0.85],
            normal_frame: [0.0, 0.0, 1.0, 0.0],
            aux: [0.0, 0.0, 0.0, 0.0],
        }
    }

    #[test]
    fn rasterizes_visible_center_particle() {
        let upload = QuestMakepadParticleUpload {
            schema_id: "test".to_owned(),
            source_rows: 1,
            rows: vec![row_at(0.0, 0.0)],
        };
        let mut pixels = Vec::new();
        let stats =
            rasterize_particle_upload(&upload, [-1.0, -1.0, -1.0], [1.0, 1.0, 1.0], &mut pixels);

        assert_eq!(stats.drawn_particles, 1);
        assert_eq!(stats.texture_size, MATTER_PARTICLE_TEXTURE_SIZE);
        assert!(stats.max_alpha > 0);
        assert!(pixels.iter().any(|pixel| *pixel != 0));
    }

    #[test]
    fn rasterizer_reports_empty_upload_without_pixels() {
        let upload = QuestMakepadParticleUpload {
            schema_id: "test".to_owned(),
            source_rows: 0,
            rows: Vec::new(),
        };
        let mut pixels = Vec::new();
        let stats =
            rasterize_particle_upload(&upload, [-1.0, -1.0, -1.0], [1.0, 1.0, 1.0], &mut pixels);

        assert_eq!(stats.drawn_particles, 0);
        assert_eq!(stats.max_alpha, 0);
        assert!(pixels.iter().all(|pixel| *pixel == 0));
    }

    #[test]
    fn rasterizes_zero_alpha_particle_with_debug_visibility_floor() {
        let mut row = row_at(0.0, 0.0);
        row.color[3] = 0.0;
        let upload = QuestMakepadParticleUpload {
            schema_id: "test".to_owned(),
            source_rows: 1,
            rows: vec![row],
        };
        let mut pixels = Vec::new();
        let stats =
            rasterize_particle_upload(&upload, [-1.0, -1.0, -1.0], [1.0, 1.0, 1.0], &mut pixels);

        assert_eq!(stats.drawn_particles, 1);
        assert!(stats.max_alpha > 0);
        assert!(pixels.iter().any(|pixel| *pixel != 0));
    }

    #[test]
    fn marker_records_texture_plane_and_counts() {
        let stats = MatterParticleTextureStats {
            texture_size: 256,
            source_rows: 1000,
            drawn_particles: 1000,
            upload_bytes: 262_144,
            saturated_pixels: 2,
            max_alpha: 255,
        };
        let marker = stats.marker_line("cadence");

        assert!(marker.starts_with(MATTER_PARTICLE_MARKER_PREFIX));
        assert!(marker.contains("renderPlane=makepad-bgra-particle-overlay-texture"));
        assert!(marker.contains("drawnParticles=1000"));
        assert!(marker.contains("uploadBytes=262144"));
    }
}

use rusty_quest_makepad_camera_shell::QuestMakepadMatterSurfaceFrame;

/// Compact Makepad uniforms derived from Matter-backed adapter rows.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct MakepadMatterSurfaceUniforms {
    pub(crate) runtime: [f32; 4],
    pub(crate) collision_contact: [f32; 4],
    pub(crate) collision_normal: [f32; 4],
    pub(crate) sdf_samples: [[f32; 4]; 4],
    pub(crate) particles: [[f32; 4]; 4],
}

impl MakepadMatterSurfaceUniforms {
    pub(crate) fn from_frame(
        frame: &QuestMakepadMatterSurfaceFrame,
        bounds_min: [f32; 3],
        bounds_max: [f32; 3],
    ) -> Self {
        let mut uniforms = Self {
            runtime: [
                1.0,
                frame.collision_upload.rows.len() as f32,
                frame
                    .sdf_slice_upload
                    .as_ref()
                    .map_or(0.0, |upload| upload.rows.len() as f32),
                frame
                    .particle_upload
                    .as_ref()
                    .map_or(0.0, |upload| upload.rows.len() as f32),
            ],
            ..Self::default()
        };

        if let Some(row) = frame.collision_upload.rows.first() {
            let uv = project_matter_position_to_panel_uv(
                [
                    row.point_distance[0],
                    row.point_distance[1],
                    row.point_distance[2],
                ],
                bounds_min,
                bounds_max,
            );
            uniforms.collision_contact =
                [uv[0], uv[1], row.point_distance[3], row.normal_overlap[3]];
            uniforms.collision_normal = [
                row.normal_overlap[0],
                row.normal_overlap[1],
                row.normal_overlap[2],
                row.normal_overlap[3],
            ];
        }

        if let Some(upload) = frame.sdf_slice_upload.as_ref() {
            let sample_count = upload.rows.len();
            if sample_count > 0 {
                let stride = (sample_count / uniforms.sdf_samples.len()).max(1);
                for (slot, uniform) in uniforms.sdf_samples.iter_mut().enumerate() {
                    let index = (slot * stride).min(sample_count - 1);
                    let row = upload.rows[index];
                    let uv = project_matter_position_to_panel_uv(
                        [row.position[0], row.position[1], row.position[2]],
                        bounds_min,
                        bounds_max,
                    );
                    *uniform = [uv[0], uv[1], row.uv_distance[2], 1.0];
                }
            }
        }

        if let Some(upload) = frame.particle_upload.as_ref() {
            let radius_scale = bounds_extent(bounds_min, bounds_max).max(0.001);
            for (uniform, row) in uniforms.particles.iter_mut().zip(upload.rows.iter()) {
                let uv = project_matter_position_to_panel_uv(
                    [
                        row.position_radius[0],
                        row.position_radius[1],
                        row.position_radius[2],
                    ],
                    bounds_min,
                    bounds_max,
                );
                let radius_uv = (row.position_radius[3] / radius_scale).clamp(0.008, 0.035);
                *uniform = [uv[0], uv[1], radius_uv, row.color[3].clamp(0.0, 1.0)];
            }
        }

        uniforms
    }
}

pub(crate) fn project_matter_position_to_panel_uv(
    position: [f32; 3],
    bounds_min: [f32; 3],
    bounds_max: [f32; 3],
) -> [f32; 2] {
    let extent_x = (bounds_max[0] - bounds_min[0]).max(0.0001);
    let extent_y = (bounds_max[1] - bounds_min[1]).max(0.0001);
    let normalized_x = (position[0] - bounds_min[0]) / extent_x;
    let normalized_y = (position[1] - bounds_min[1]) / extent_y;
    [
        ((normalized_x - 0.5) * 0.72 + 0.5).clamp(0.04, 0.96),
        ((1.0 - normalized_y - 0.5) * 0.72 + 0.5).clamp(0.04, 0.96),
    ]
}

fn bounds_extent(bounds_min: [f32; 3], bounds_max: [f32; 3]) -> f32 {
    (bounds_max[0] - bounds_min[0])
        .max(bounds_max[1] - bounds_min[1])
        .max(bounds_max[2] - bounds_min[2])
        .max(0.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn projects_center_to_panel_center() {
        let uv = project_matter_position_to_panel_uv(
            [0.0, 0.0, 0.0],
            [-1.0, -1.0, -1.0],
            [1.0, 1.0, 1.0],
        );

        assert!((uv[0] - 0.5).abs() < 1.0e-6);
        assert!((uv[1] - 0.5).abs() < 1.0e-6);
    }

    #[test]
    fn disabled_uniforms_have_zero_runtime() {
        assert_eq!(MakepadMatterSurfaceUniforms::default().runtime, [0.0; 4]);
    }
}

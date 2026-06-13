//! Makepad live/script definitions for the Hostess Makepad app shell.
//!
//! Keep the app layout here so `main.rs` stays focused on runtime wiring and
//! event handling.

use crate::makepad_widgets::*;
use crate::App;

script_mod! {
    use mod.pod.*
    use mod.math.*
    use mod.shader.*
    use mod.draw
    use mod.geom
    use mod.prelude.widgets.*
    use mod.widgets.*

    startup() do #(App::script_component(vm)){
        ui: XrRoot{
            window.inner_size: vec2(760, 480)
            pass.clear_color: #x203040
            camera.fov_y: 36.0
            camera.desktop_target: vec3(0.0, -0.05, -0.72)
            camera.distance: 1.65
            env.gravity: 0.0
            env.env_cube: false
            env.depth_mesh: false

            camera_projection_scene := XrNode{
                pos: vec3(0.0, 0.0, 0.0)

                stimulus_stereo_field := mod.widgets.StimulusStereoFieldPanel{
                    body: mod.widgets.XrBodyKind.Fixed
                    pos: vec3(0.0, 0.0, -1.0)
                }

                camera_projection_panel := mod.widgets.MakepadStereoCameraPanel{
                    body: mod.widgets.XrBodyKind.Fixed
                    size: vec3(1.0, 1.0, 0.010)
                    pos: vec3(0.0, 0.0, -1.0)
                }

                matter_particle_cloud := mod.widgets.MatterWorldParticleBillboardCloud{
                    body: mod.widgets.XrBodyKind.Fixed
                    pos: vec3(0.0, 0.0, 0.0)
                }

                matter_adf_debug_cells := mod.widgets.MatterWorldAdfDebugCells{
                    body: mod.widgets.XrBodyKind.Fixed
                    pos: vec3(0.0, 0.0, 0.0)
                }
            }

            camera_video_view := XrView{
                visible: false
                pos: vec3(0.0, -0.04, -0.764)
                logical_size: vec2(960, 540)
                pixel_scale: 0.00096
                dpi_factor: 1.0

                SolidView{
                    width: Fill
                    height: Fill
                    flow: Right
                    spacing: 0
                    draw_bg.color: #x05090dff

                    left_camera_video := Video{
                        width: 480
                        height: Fill
                        autoplay: false
                        show_controls: false
                    }

                    right_camera_video := Video{
                        width: 480
                        height: Fill
                        autoplay: false
                        show_controls: false
                    }
                }
            }

            xr_permissions := XrPermissionsFlow{}
        }
    }
}

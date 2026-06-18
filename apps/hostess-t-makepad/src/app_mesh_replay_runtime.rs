use super::*;

impl App {
    pub(super) fn refresh_mesh_replay_runtime_from_selected_settings(
        &mut self,
        phase: &str,
        force: bool,
    ) -> bool {
        let identity = makepad_effective_settings::selected_makepad_effective_settings_identity();
        if !force {
            if !identity.runtime_settings_changed_from(
                self.mesh_replay_effective_settings_path.as_deref(),
                self.current_mesh_replay_effective_settings_modified_ns(),
                self.mesh_replay_effective_settings_revision_key.as_deref(),
            ) {
                return false;
            }
        }

        let runtime_revision_key = identity.runtime_settings_revision_key();
        let gpu_proof_revision_key = identity.gpu_proof_settings_revision_key();
        let selection = makepad_effective_settings::read_selected_mesh_replay_runtime();
        let runtime_ready = selection.runtime.is_some();
        let marker_line = if selection.runtime.is_none() {
            Some(selection.marker_line(phase))
        } else {
            None
        };
        let adoption_marker_line =
            selection.adoption_marker_line(phase, &identity, runtime_revision_key.as_deref());
        self.mesh_replay_effective_settings_path = selection.source_effective_settings_path.clone();
        self.mesh_replay_effective_settings_revision_key = runtime_revision_key.clone();
        self.mesh_replay_effective_settings_gpu_proof_revision_key = gpu_proof_revision_key.clone();
        self.mesh_replay_effective_settings_modified_ns =
            selection.source_modified_ns.unwrap_or_default();
        self.mesh_replay_effective_settings_has_modified_ns =
            selection.source_modified_ns.is_some();
        self.camera_shell_effective_render_scale = selection.render_scale.unwrap_or_default();
        self.camera_shell_effective_render_scale_present = selection.render_scale.is_some();
        self.camera_shell_effective_camera_streaming_enabled = selection
            .camera_streaming_enabled
            .unwrap_or(DEFAULT_MAKEPAD_CAMERA_STREAMING_ENABLED);
        Self::set_effective_remote_camera(selection.remote_camera.clone());
        self.matter_world_particle_draw_limit = selection
            .particle_render_draw_limit
            .unwrap_or(DEFAULT_PARTICLE_RENDER_DRAW_LIMIT)
            .min(MATTER_WORLD_PARTICLE_DRAW_LIMIT_MAX);
        self.matter_world_particle_draw_limit_configured =
            selection.particle_render_draw_limit.is_some();
        self.matter_world_particle_animation_mode = selection
            .particle_render_animation_mode
            .unwrap_or(DEFAULT_PARTICLE_RENDER_ANIMATION_MODE);
        self.matter_world_particle_size_scale = selection
            .particle_render_size_scale
            .unwrap_or(DEFAULT_PARTICLE_RENDER_SIZE_SCALE);
        self.matter_world_particle_size_scale_configured =
            selection.particle_render_size_scale.is_some();
        self.camera_shell_feature_uniforms = selection.feature_uniforms;
        self.matter_surface_force_authority =
            selection.particle_force_authority.unwrap_or_default();
        self.matter_surface_gpu_force_promotion_readiness =
            MatterSurfaceGpuForcePromotionReadiness::from_provider_ab_receipt(
                selection.gpu_force_provider_ab_receipt.unwrap_or_default(),
            );
        self.matter_surface_worker = selection
            .matter_surface_runtime
            .map(QuestMakepadMatterSurfaceWorker::from_runtime);
        self.matter_surface_frame_markers_emitted = 0;
        self.matter_surface_worker_markers_emitted = 0;
        self.matter_surface_live_source_worker_markers_emitted = 0;
        self.reset_matter_surface_gpu_proof_markers();
        self.emit_matter_surface_gpu_proof_epoch_marker(
            phase,
            selection.source_effective_settings_path.as_deref(),
            gpu_proof_revision_key.as_deref(),
        );
        self.matter_surface_world_particle_markers_emitted = 0;
        self.matter_surface_world_particle_draw_markers_emitted = 0;
        self.matter_surface_world_particle_draw_waiting_marker_emitted = false;
        self.matter_surface_world_adf_debug_markers_emitted = 0;
        self.matter_surface_world_adf_debug_draw_markers_emitted = 0;
        self.matter_surface_world_adf_debug_draw_waiting_marker_emitted = false;
        self.matter_surface_last_step_seconds = f64::NEG_INFINITY;
        self.matter_surface_cached_panel_overlay_frame = MatterSurfacePanelOverlayFrame::default();
        self.matter_surface_cached_world_particle_batch = None;
        self.matter_surface_cached_world_adf_debug_batch = None;
        self.matter_particle_texture.reset_markers();
        self.live_hand_surface_source.reset_markers();
        self.matter_surface_source_selection = MatterSurfaceSourceSelection::from_runtime();
        self.stimulus_stereo_field_state = if let Some(payload) =
            selection.stimulus_profile.as_ref()
        {
            match StimulusStereoFieldState::from_profile_payload(payload) {
                Ok(state) => state,
                Err(error) => {
                    emit_marker_line(&format!(
                            "RUSTY_HOSTESS_MAKEPAD_STIMULUS_DRAW schema=rusty.hostess.makepad.stimulus_draw.v1 phase={} status=rejected issue={} profileSelected=true renderPath=makepad-xr-fragment-preview",
                            marker_token(phase),
                            marker_token(&error),
                        ));
                    StimulusStereoFieldState::disabled()
                }
            }
        } else {
            if let Some(issue) = selection.stimulus_issue.as_deref() {
                emit_marker_line(&format!(
                        "RUSTY_HOSTESS_MAKEPAD_STIMULUS_DRAW schema=rusty.hostess.makepad.stimulus_draw.v1 phase={} status=rejected issue={} profileSelected=false renderPath=makepad-xr-fragment-preview",
                        marker_token(phase),
                        marker_token(issue),
                    ));
            }
            StimulusStereoFieldState::disabled()
        };
        self.stimulus_surface_projection_rows = StimulusSurfaceProjectionRows::default();
        self.stimulus_stereo_field_markers_emitted = 0;
        self.stimulus_controller_randomize_count = 0;
        self.stimulus_volume_gpu_probe_markers_emitted = 0;
        self.stimulus_volume_gpu_probe_pending = None;
        self.stimulus_volume_raymarch_preview_markers_emitted = 0;
        self.stimulus_volume_raymarch_preview_pending = None;
        self.stimulus_volume_image_preview_markers_emitted = 0;
        self.stimulus_volume_image_preview_pending = None;
        self.stimulus_volume_image_preview_texture = None;
        self.stimulus_volume_texture_adoption_markers_emitted = 0;
        emit_marker_line(&self.matter_surface_source_selection.marker_line(phase));
        emit_marker_line(&adoption_marker_line);
        self.mesh_replay_runtime = selection.runtime;
        self.recorded_hand_surface_source =
            self.mesh_replay_runtime
                .as_ref()
                .and_then(|runtime| {
                    match RecordedHandSurfaceSource::from_replay_runtime(
                        selection.source_effective_settings_path.as_deref(),
                        runtime,
                    ) {
                        Ok(source) => source,
                        Err(error) => {
                            emit_marker_line(&format!(
                            "RUSTY_HOSTESS_MAKEPAD_RECORDED_HAND_SURFACE_SOURCE schema=rusty.hostess.makepad.recorded_hand_surface_source.v1 phase={} status=error issue={}",
                            marker_token(phase),
                            marker_token(&error),
                        ));
                            None
                        }
                    }
                });

        if let Some(marker_line) = marker_line {
            emit_marker_line(&marker_line);
        }
        if runtime_ready {
            emit_marker_line(&self.camera_shell_feature_uniform_marker_line(phase));
        }
        if let Some(source) = self.recorded_hand_surface_source.as_ref() {
            emit_marker_line(&source.marker_line(phase));
        }
        if let Some(runtime) = self.mesh_replay_runtime.as_mut() {
            runtime.step(0.0);
            if runtime.should_emit_config_marker() {
                emit_marker_line(&runtime.config_marker_line(phase));
            }
        }
        true
    }

    fn camera_shell_feature_uniform_marker_line(&self, phase: &str) -> String {
        format!(
            "RUSTY_QUEST_MAKEPAD_CAMERA_SHELL_FEATURES schema=rusty.quest.makepad.camera_shell_feature_uniforms.v1 phase={} status=ready collisionEnabled={} sdfAdfOverlayMode={} particlesEnabled={} particleForceAuthority={} particleRenderDrawLimit={} particleRenderDrawLimitSource={} particleRenderAnimationMode={} particleRenderSizeScale={} particleRenderSizeScaleSource={} renderScale={} sourcePath={}",
            marker_token(phase),
            self.camera_shell_feature_uniforms.collision_enabled >= 0.5,
            marker_token(camera_shell_sdf_adf_mode_token(
                self.camera_shell_feature_uniforms.sdf_adf_overlay_mode,
            )),
            self.camera_shell_feature_uniforms.particles_enabled >= 0.5,
            marker_token(self.matter_surface_force_authority.as_str()),
            self.current_matter_world_particle_draw_limit(),
            self.matter_world_particle_draw_limit_source(),
            marker_token(self.current_matter_world_particle_animation_mode().as_str()),
            marker_f32_token(Some(self.current_matter_world_particle_size_scale())),
            self.matter_world_particle_size_scale_source(),
            marker_f32_token(self.current_camera_shell_effective_render_scale()),
            marker_token(
                self.mesh_replay_effective_settings_path
                    .as_deref()
                    .unwrap_or("none")
            ),
        )
    }

    fn current_camera_shell_effective_render_scale(&self) -> Option<f32> {
        if self.camera_shell_effective_render_scale_present {
            Some(self.camera_shell_effective_render_scale)
        } else {
            None
        }
    }

    pub(super) fn current_matter_world_particle_draw_limit(&self) -> usize {
        if self.matter_world_particle_draw_limit_configured {
            self.matter_world_particle_draw_limit
                .min(MATTER_WORLD_PARTICLE_DRAW_LIMIT_MAX)
        } else {
            DEFAULT_PARTICLE_RENDER_DRAW_LIMIT.min(MATTER_WORLD_PARTICLE_DRAW_LIMIT_MAX)
        }
    }

    pub(super) fn current_matter_world_particle_animation_mode(
        &self,
    ) -> ParticleRenderAnimationMode {
        self.matter_world_particle_animation_mode
    }

    pub(super) fn current_matter_world_particle_size_scale(&self) -> f32 {
        if self.matter_world_particle_size_scale.is_finite()
            && self.matter_world_particle_size_scale > 0.0
        {
            self.matter_world_particle_size_scale
        } else {
            DEFAULT_PARTICLE_RENDER_SIZE_SCALE
        }
    }

    pub(super) fn matter_world_particle_size_scale_source(&self) -> &'static str {
        if self.matter_world_particle_size_scale_configured {
            "effective-settings"
        } else {
            "default"
        }
    }

    pub(super) fn matter_world_particle_draw_limit_source(&self) -> &'static str {
        if self.matter_world_particle_draw_limit_configured {
            "effective-settings"
        } else {
            "default"
        }
    }

    fn current_mesh_replay_effective_settings_modified_ns(&self) -> Option<u128> {
        if self.mesh_replay_effective_settings_has_modified_ns {
            Some(self.mesh_replay_effective_settings_modified_ns)
        } else {
            None
        }
    }

    pub(super) fn handle_mesh_replay_runtime_cadence(&mut self, cx: &mut Cx, now_seconds: f64) {
        const SETTINGS_HOTLOAD_CHECK_PERIOD_FRAMES: u64 = 30;
        if self.cadence_frame_count == 1
            || self
                .cadence_frame_count
                .saturating_sub(self.mesh_replay_settings_check_frame)
                >= SETTINGS_HOTLOAD_CHECK_PERIOD_FRAMES
        {
            self.mesh_replay_settings_check_frame = self.cadence_frame_count;
            self.refresh_matter_surface_gpu_proof_epoch_from_selected_settings("hotload");
            if self.refresh_mesh_replay_runtime_from_selected_settings("hotload", false) {
                self.apply_camera_shell_render_scale(cx, "hotload");
            }
        }

        let mut marker_lines = Vec::new();
        let uniforms = if let Some(runtime) = self.mesh_replay_runtime.as_mut() {
            runtime.step(now_seconds);
            if runtime.should_emit_config_marker() {
                marker_lines.push(runtime.config_marker_line("cadence"));
            }
            if runtime.should_emit_frame_marker() {
                marker_lines.push(runtime.frame_marker_line("cadence"));
            }
            runtime.uniforms()
        } else {
            MeshReplayUniforms::disabled()
        };

        for line in marker_lines {
            emit_marker_line(&line);
        }
        let camera_streaming_enabled = self.current_camera_streaming_enabled();
        let matter_frame = self.update_matter_surface_runtime_for_evidence(
            cx,
            now_seconds,
            "cadence",
            camera_streaming_enabled,
        );
        if camera_streaming_enabled {
            self.apply_mesh_replay_uniforms_to_panel(
                cx,
                uniforms,
                self.camera_shell_feature_uniforms,
                matter_frame.uniforms,
                matter_frame.particle_texture,
            );
        }
        self.apply_matter_world_particles_to_cloud(cx, "cadence");
        self.apply_matter_world_adf_debug_to_cells(cx, "cadence");
        self.apply_stimulus_stereo_field_to_panel(cx, "cadence", now_seconds);
    }

    fn apply_mesh_replay_uniforms_to_panel(
        &mut self,
        cx: &mut Cx,
        uniforms: MeshReplayUniforms,
        feature_uniforms: MakepadCameraShellFeatureUniforms,
        matter_uniforms: MakepadMatterSurfaceUniforms,
        particle_texture_frame: MatterParticleTextureFrame,
    ) -> bool {
        let panel_ref = self.ui.widget(cx, ids!(camera_projection_panel));
        let Some(mut panel) = panel_ref.borrow_mut::<MakepadStereoCameraPanel>() else {
            return false;
        };
        panel.set_mesh_replay_uniforms(
            cx,
            uniforms,
            feature_uniforms,
            matter_uniforms,
            particle_texture_frame,
        );
        true
    }

    fn apply_camera_shell_render_scale(&self, cx: &mut Cx, phase: &str) {
        let (render_scale, source) =
            if let Some(render_scale) = self.current_camera_shell_effective_render_scale() {
                (render_scale, "effective-settings")
            } else {
                let config = Self::runtime_config();
                (
                    runtime_float(&config, KEY_XR_RENDER_SCALE) as f32,
                    "runtime-config",
                )
            };
        cx.xr_set_render_scale(render_scale);
        emit_marker_line(&format!(
            "RUSTY_QUEST_MAKEPAD_CAMERA_SHELL_RENDER_SCALE schema=rusty.quest.makepad.camera_shell_render_scale.v1 phase={} status=applied renderScale={} source={}",
            marker_token(phase),
            marker_f32_token(Some(render_scale)),
            marker_token(source),
        ));
    }
}

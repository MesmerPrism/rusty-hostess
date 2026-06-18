use super::*;

impl App {
    #[cfg(target_os = "android")]
    pub(super) fn update_stimulus_runtime_xr_projection(&mut self, update: &XrUpdateEvent) {
        if !self.stimulus_stereo_field_state.enabled {
            return;
        }
        let views = Self::xr_display_views_from_update(update);
        if let Some(plan) = android_camera_probe::broker_full_frame_projection_plan_from_xr_views(
            "stimulus-left",
            "stimulus-right",
            1024,
            1024,
            views,
        ) {
            self.stimulus_surface_projection_rows =
                StimulusSurfaceProjectionRows::from_homographies(
                    plan.left_screen_to_surface_h,
                    plan.right_screen_to_surface_h,
                );
        }
    }

    pub(super) fn handle_stimulus_controller_randomize(
        &mut self,
        cx: &mut Cx,
        update: &XrUpdateEvent,
        camera_streaming_enabled: bool,
    ) {
        if camera_streaming_enabled
            || !self.stimulus_stereo_field_state.enabled
            || !self.stimulus_stereo_field_state.volume_present
            || !update.clicked_a()
        {
            return;
        }

        self.stimulus_controller_randomize_count =
            self.stimulus_controller_randomize_count.saturating_add(1);
        let now_seconds = update.state.time.max(0.0);
        let seed = self
            .stimulus_controller_randomize_count
            .wrapping_mul(0x9e37_79b9_7f4a_7c15)
            ^ self.cadence_xr_update_count.rotate_left(17)
            ^ now_seconds.to_bits();
        self.stimulus_stereo_field_state
            .apply_controller_randomize(seed);
        self.stimulus_stereo_field_markers_emitted = 0;
        self.stimulus_volume_gpu_probe_markers_emitted = 0;
        self.stimulus_volume_gpu_probe_pending = None;
        self.stimulus_volume_raymarch_preview_markers_emitted = 0;
        self.stimulus_volume_raymarch_preview_pending = None;
        self.stimulus_volume_image_preview_markers_emitted = 0;
        self.stimulus_volume_image_preview_pending = None;
        self.stimulus_volume_image_preview_texture = None;
        self.stimulus_volume_texture_adoption_markers_emitted = 0;

        let panel_bound =
            self.apply_stimulus_stereo_field_to_panel(cx, "xr-controller-randomize", now_seconds);
        emit_marker_line(
            &self
                .stimulus_stereo_field_state
                .controller_randomize_marker_line(
                    "xr-controller-randomize",
                    self.stimulus_controller_randomize_count,
                    self.cadence_xr_update_count,
                    now_seconds.max(0.0).min(f32::MAX as f64) as f32,
                    panel_bound,
                    self.stimulus_surface_projection_rows.ready,
                ),
        );
    }

    pub(super) fn apply_stimulus_stereo_field_to_panel(
        &mut self,
        cx: &mut Cx,
        phase: &str,
        now_seconds: f64,
    ) -> bool {
        let field_ref = self.ui.widget(cx, ids!(stimulus_stereo_field));
        let Some(mut field) = field_ref.borrow_mut::<StimulusStereoFieldPanel>() else {
            if self.stimulus_stereo_field_state.enabled
                && self.stimulus_stereo_field_markers_emitted < STIMULUS_STEREO_FIELD_MARKER_LIMIT
            {
                emit_marker_line(&format!(
                    "RUSTY_HOSTESS_MAKEPAD_STIMULUS_DRAW schema=rusty.hostess.makepad.stimulus_draw.v1 phase={} status=error issue=stimulus_stereo_field_widget_missing panelBound=false profileId={} renderPath=makepad-xr-fragment-preview",
                    marker_token(phase),
                    marker_token(&self.stimulus_stereo_field_state.profile_id),
                ));
                self.stimulus_stereo_field_markers_emitted += 1;
            }
            return false;
        };
        let time_seconds = now_seconds.max(0.0).min(f32::MAX as f64) as f32;
        let changed = field.set_stimulus_state(
            cx,
            self.stimulus_stereo_field_state.clone(),
            time_seconds,
            self.stimulus_surface_projection_rows,
            self.stimulus_volume_image_preview_texture.clone(),
        );
        if self.stimulus_stereo_field_state.enabled
            && (changed
                || self.stimulus_stereo_field_markers_emitted < STIMULUS_STEREO_FIELD_MARKER_LIMIT)
        {
            emit_marker_line(&self.stimulus_stereo_field_state.marker_line(
                phase,
                time_seconds,
                true,
                self.stimulus_surface_projection_rows.ready,
            ));
            if let Some(marker_line) = self
                .stimulus_stereo_field_state
                .volume_adoption_marker_line(phase, true)
            {
                emit_marker_line(&marker_line);
            }
            self.stimulus_stereo_field_markers_emitted += 1;
        }
        drop(field);
        self.update_stimulus_volume_gpu_probe(cx, phase);
        self.update_stimulus_volume_raymarch_preview(cx, phase);
        self.update_stimulus_volume_image_preview(cx, phase, time_seconds);
        true
    }

    fn update_stimulus_volume_gpu_probe(&mut self, cx: &mut Cx, phase: &str) {
        if !self.stimulus_stereo_field_state.enabled
            || !self.stimulus_stereo_field_state.volume_present
        {
            self.stimulus_volume_gpu_probe_pending = None;
            return;
        }

        if let Some(marker_line) = self
            .stimulus_volume_gpu_probe_pending
            .as_ref()
            .and_then(|pending| stimulus_volume_gpu_probe_poll_marker_line(cx, pending, phase))
        {
            emit_marker_line(&marker_line);
            self.stimulus_volume_gpu_probe_markers_emitted += 1;
            self.stimulus_volume_gpu_probe_pending = None;
            return;
        }

        if self.stimulus_volume_gpu_probe_markers_emitted >= STIMULUS_VOLUME_GPU_PROBE_MARKER_LIMIT
            || self.stimulus_volume_gpu_probe_pending.is_some()
        {
            return;
        }

        let Some(input) = stimulus_volume_probe_input_from_state(&self.stimulus_stereo_field_state)
        else {
            return;
        };
        if let Some(pending) = stimulus_volume_gpu_probe_submit(cx, &input) {
            self.stimulus_volume_gpu_probe_pending = Some(pending);
        }
    }

    fn update_stimulus_volume_raymarch_preview(&mut self, cx: &mut Cx, phase: &str) {
        if !self.stimulus_stereo_field_state.enabled
            || !self.stimulus_stereo_field_state.volume_present
        {
            self.stimulus_volume_raymarch_preview_pending = None;
            return;
        }

        if let Some(marker_line) = self
            .stimulus_volume_raymarch_preview_pending
            .as_ref()
            .and_then(|pending| {
                stimulus_volume_raymarch_preview_poll_marker_line(cx, pending, phase)
            })
        {
            emit_marker_line(&marker_line);
            self.stimulus_volume_raymarch_preview_markers_emitted += 1;
            self.stimulus_volume_raymarch_preview_pending = None;
            return;
        }

        if self.stimulus_volume_gpu_probe_markers_emitted == 0
            || self.stimulus_volume_raymarch_preview_markers_emitted
                >= STIMULUS_VOLUME_RAYMARCH_PREVIEW_MARKER_LIMIT
            || self.stimulus_volume_raymarch_preview_pending.is_some()
        {
            return;
        }

        let Some(input) =
            stimulus_volume_raymarch_preview_input_from_state(&self.stimulus_stereo_field_state)
        else {
            return;
        };
        if let Some(pending) = stimulus_volume_raymarch_preview_submit(cx, &input) {
            self.stimulus_volume_raymarch_preview_pending = Some(pending);
        }
    }

    fn update_stimulus_volume_image_preview(
        &mut self,
        cx: &mut Cx,
        phase: &str,
        time_seconds: f32,
    ) {
        if !self.stimulus_stereo_field_state.enabled
            || !self.stimulus_stereo_field_state.volume_present
        {
            self.stimulus_volume_image_preview_pending = None;
            self.stimulus_volume_image_preview_texture = None;
            return;
        }
        if self.stimulus_stereo_field_state.volume_texture_mix <= 0.0 {
            self.stimulus_volume_image_preview_pending = None;
            self.stimulus_volume_image_preview_texture = None;
            return;
        }

        if let Some(ready) = self
            .stimulus_volume_image_preview_pending
            .as_ref()
            .and_then(|pending| stimulus_volume_image_preview_poll_ready(cx, pending, phase))
        {
            emit_marker_line(&ready.marker_line);
            self.stimulus_volume_image_preview_markers_emitted += 1;
            self.stimulus_volume_image_preview_pending = None;
            self.adopt_stimulus_volume_image_preview_texture(cx, phase, time_seconds, ready);
            return;
        }

        if self.stimulus_volume_raymarch_preview_markers_emitted == 0
            || self.stimulus_volume_image_preview_markers_emitted
                >= STIMULUS_VOLUME_IMAGE_PREVIEW_MARKER_LIMIT
            || self.stimulus_volume_image_preview_pending.is_some()
        {
            return;
        }

        let Some(input) =
            stimulus_volume_image_preview_input_from_state(&self.stimulus_stereo_field_state)
        else {
            return;
        };
        if let Some(pending) = stimulus_volume_image_preview_submit(cx, &input) {
            self.stimulus_volume_image_preview_pending = Some(pending);
        }
    }

    fn adopt_stimulus_volume_image_preview_texture(
        &mut self,
        cx: &mut Cx,
        phase: &str,
        time_seconds: f32,
        ready: StimulusVolumeImagePreviewReady,
    ) {
        let binding = if ready.readback_matched() {
            let gpu_texture = Texture::new_with_format(
                cx,
                TextureFormat::PlatformRGBAf32 {
                    width: ready.readback.image_width,
                    height: ready.readback.image_height,
                },
            );
            if let Some(adoption) = cx.xr_gpu_f32_volume_image_preview_adopt_texture(
                ready.request_id,
                gpu_texture.texture_id(),
            ) {
                self.stimulus_volume_image_preview_texture = Some(gpu_texture);
                StimulusVolumeTextureBindingEvidence::gpu_adoption(adoption)
            } else {
                let texture = Texture::new_with_format(
                    cx,
                    TextureFormat::VecRGBAf32 {
                        width: ready.readback.image_width,
                        height: ready.readback.image_height,
                        data: Some(ready.texture_rgba.clone()),
                        updated: TextureUpdated::Full,
                    },
                );
                self.stimulus_volume_image_preview_texture = Some(texture);
                StimulusVolumeTextureBindingEvidence::cpu_upload(ready.texture_upload_bytes())
            }
        } else {
            self.stimulus_volume_image_preview_texture = None;
            StimulusVolumeTextureBindingEvidence::cpu_upload(0)
        };

        let panel_bound =
            self.bind_stimulus_stereo_field_panel(cx, time_seconds, "volume-texture-adopted");
        if self.stimulus_volume_texture_adoption_markers_emitted < 1 {
            emit_marker_line(&ready.texture_adoption_marker_line(
                phase,
                panel_bound,
                STIMULUS_VOLUME_TEXTURE_SLOT,
                &binding,
            ));
            self.stimulus_volume_texture_adoption_markers_emitted += 1;
        }
    }

    fn bind_stimulus_stereo_field_panel(
        &mut self,
        cx: &mut Cx,
        time_seconds: f32,
        _phase: &str,
    ) -> bool {
        let field_ref = self.ui.widget(cx, ids!(stimulus_stereo_field));
        let Some(mut field) = field_ref.borrow_mut::<StimulusStereoFieldPanel>() else {
            return false;
        };
        field.set_stimulus_state(
            cx,
            self.stimulus_stereo_field_state.clone(),
            time_seconds,
            self.stimulus_surface_projection_rows,
            self.stimulus_volume_image_preview_texture.clone(),
        );
        true
    }
}

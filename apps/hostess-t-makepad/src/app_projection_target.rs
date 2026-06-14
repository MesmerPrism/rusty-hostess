use super::*;

impl App {
    pub(super) fn manifold_breath_feedback_config() -> ManifoldBreathFeedbackConfig {
        ManifoldBreathFeedbackConfig {
            enabled: hotload_bool(
                KEY_MANIFOLD_BREATH_FEEDBACK_ENABLED,
                DEFAULT_MANIFOLD_BREATH_FEEDBACK_ENABLED,
            ),
            broker_host: hotload_text(KEY_MANIFOLD_BROKER_HOST, DEFAULT_MANIFOLD_BROKER_HOST),
            broker_port: hotload_u16(
                KEY_MANIFOLD_BROKER_PORT,
                DEFAULT_MANIFOLD_BROKER_PORT,
                1,
                u16::MAX,
            ),
            stream_id: hotload_text_any(
                &[
                    KEY_MANIFOLD_BREATH_FEEDBACK_STREAM,
                    makepad_config::KEY_PROJECTION_TARGET_BREATH_STREAM,
                ],
                DEFAULT_MANIFOLD_BREATH_FEEDBACK_STREAM,
            ),
            receiver_id: hotload_text(
                KEY_MANIFOLD_BREATH_FEEDBACK_RECEIVER,
                DEFAULT_MANIFOLD_BREATH_FEEDBACK_RECEIVER,
            ),
            connect_timeout_ms: hotload_u32(
                KEY_MANIFOLD_BREATH_FEEDBACK_CONNECT_TIMEOUT_MS,
                DEFAULT_MANIFOLD_BREATH_FEEDBACK_CONNECT_TIMEOUT_MS,
                50,
                5_000,
            ) as u64,
        }
    }

    pub(super) fn manifold_breath_feedback_config_marker_line(
        config: &ManifoldBreathFeedbackConfig,
    ) -> String {
        let status = if config.enabled {
            "enabled"
        } else {
            "disabled"
        };
        format!(
            "RUSTY_MAKEPAD_BREATH_FEEDBACK_CONFIG schema=rusty.gui.makepad.breath_feedback_config.v1 phase=hotload status={} enabled={} enabledRaw={} stream={} streamRaw={} receiver={} receiverRaw={} brokerHost={} brokerHostRaw={} brokerPort={} brokerPortRaw={} connectTimeoutMs={} connectTimeoutRaw={} flagsOwner=hostessctl.record_values",
            status,
            config.enabled,
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BREATH_FEEDBACK_ENABLED)),
            marker_token(&config.stream_id),
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BREATH_FEEDBACK_STREAM)),
            marker_token(&config.receiver_id),
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BREATH_FEEDBACK_RECEIVER)),
            marker_token(&config.broker_host),
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BROKER_HOST)),
            config.broker_port,
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BROKER_PORT)),
            config.connect_timeout_ms,
            marker_token(&Self::runtime_marker_value(KEY_MANIFOLD_BREATH_FEEDBACK_CONNECT_TIMEOUT_MS)),
        )
    }

    pub(super) fn runtime_marker_value(key: &'static str) -> String {
        runtime_property_value(key).unwrap_or_else(|| "default".to_string())
    }

    pub(super) fn projection_target_scale() -> f32 {
        makepad_projection_target_scale()
    }

    pub(super) fn projection_target_joystick_controls_enabled() -> bool {
        makepad_projection_target_joystick_controls_enabled_from_value(&hotload_text_any(
            &[
                makepad_config::KEY_PROJECTION_TARGET_JOYSTICK_CONTROLS,
                KEY_MAKEPAD_PROJECTION_TARGET_JOYSTICK_CONTROLS,
            ],
            DEFAULT_MAKEPAD_PROJECTION_TARGET_JOYSTICK_CONTROLS,
        ))
    }

    pub(super) fn projection_target_breath_controls_enabled() -> bool {
        makepad_projection_target_breath_controls_enabled_from_value(&hotload_text(
            makepad_config::KEY_PROJECTION_TARGET_BREATH_CONTROLS,
            "off",
        ))
    }

    pub(super) fn handle_projection_target_joystick(
        &mut self,
        cx: &mut Cx,
        update: &XrUpdateEvent,
    ) {
        if !Self::projection_target_joystick_controls_enabled() {
            self.projection_target_joystick_scale_ready = false;
            self.projection_target_joystick_last_time = 0.0;
            return;
        }

        let breath_controls_scale = Self::projection_target_breath_controls_enabled();
        let state = update.state.as_ref();
        let now_seconds = state.time.max(0.0);
        if !self.projection_target_joystick_scale_ready {
            let tuning = self.current_horizontal_alignment_tuning();
            self.projection_target_joystick_offset_x_uv =
                tuning.projection_target_offset_x_uv.clamp(-0.5, 0.5);
            self.projection_target_joystick_offset_y_uv =
                tuning.projection_target_offset_y_uv.clamp(-0.5, 0.5);
            self.projection_target_joystick_scale = tuning
                .projection_target_scale
                .clamp(PROJECTION_TARGET_MIN_SCALE, PROJECTION_TARGET_MAX_SCALE);
            self.projection_target_joystick_scale_ready = true;
            self.projection_target_joystick_last_time = now_seconds;
            Self::emit_stereo_projection_marker(&format!(
                "phase=projection-target-controller status=active source=makepad-xr-actions referenceSource=quest-composite-layer-apk projectionTargetJoystickControls=offset-scale controls=leftStick:projectionTargetOffsetUv,rightStickY:projectionTargetScale,rightA:resetOffsetAndProjectionTargetScale coordinateSpace=display-eye-screen-uv yConvention=stickUpMovesTargetUp projectionAreaScaleControlRole=diagnostic-canvas-scale-runtime-property projectionAreaScaleMin={:.4} projectionAreaScaleMax={:.4} projectionTargetScaleControlRole=reference-target-footprint-runtime-adjustment projectionTargetScaleMin={:.4} projectionTargetScaleMax={:.4} projectionTargetOffsetXUv={:.4} projectionTargetOffsetYUv={:.4} projectionTargetScale={:.4} projectionAreaScaleX={:.4} projectionAreaScaleY={:.4}",
                PROJECTION_AREA_MIN_SCALE,
                PROJECTION_AREA_MAX_SCALE,
                PROJECTION_TARGET_MIN_SCALE,
                PROJECTION_TARGET_MAX_SCALE,
                self.projection_target_joystick_offset_x_uv,
                self.projection_target_joystick_offset_y_uv,
                tuning.projection_target_scale,
                tuning.projection_area_scale_x,
                tuning.projection_area_scale_y,
            ));
        }

        let dt_seconds = if self.projection_target_joystick_last_time > 0.0 {
            (now_seconds - self.projection_target_joystick_last_time).clamp(0.0, 0.1) as f32
        } else {
            0.0
        };
        self.projection_target_joystick_last_time = now_seconds;

        let mut changed = false;
        let mut reset = false;
        if update.clicked_a() {
            self.projection_target_joystick_offset_x_uv = 0.0;
            self.projection_target_joystick_offset_y_uv = 0.0;
            self.projection_target_joystick_scale = 1.0;
            changed = true;
            reset = true;
        }
        if state.left_controller.active() {
            if let Some(next_offset_x) = makepad_projection_target_offset_step(
                self.projection_target_joystick_offset_x_uv,
                state.left_controller.stick.x,
                dt_seconds,
                false,
            ) {
                if (next_offset_x - self.projection_target_joystick_offset_x_uv).abs() > 0.0001 {
                    self.projection_target_joystick_offset_x_uv = next_offset_x;
                    changed = true;
                }
            }
            if let Some(next_offset_y) = makepad_projection_target_offset_step(
                self.projection_target_joystick_offset_y_uv,
                state.left_controller.stick.y,
                dt_seconds,
                true,
            ) {
                if (next_offset_y - self.projection_target_joystick_offset_y_uv).abs() > 0.0001 {
                    self.projection_target_joystick_offset_y_uv = next_offset_y;
                    changed = true;
                }
            }
        }
        if state.right_controller.active() && !breath_controls_scale {
            if let Some(next_scale) = makepad_projection_target_scale_step(
                self.projection_target_joystick_scale,
                state.right_controller.stick.y,
                dt_seconds,
            ) {
                if (next_scale - self.projection_target_joystick_scale).abs() > 0.0001 {
                    self.projection_target_joystick_scale = next_scale;
                    changed = true;
                }
            }
        }
        let frame = self.cadence_xr_update_count;
        let should_sample_log = self.projection_target_joystick_last_log_frame == 0
            || frame.saturating_sub(self.projection_target_joystick_last_log_frame) >= 60;
        if !changed {
            if should_sample_log {
                let tuning = self.current_horizontal_alignment_tuning();
                Self::emit_stereo_projection_marker(&format!(
                    "phase=projection-target-input status=sampled source=controller referenceSource=quest-composite-layer-apk changed=false projectionAreaScaleControlRole=diagnostic-canvas-scale-runtime-property projectionAreaScaleMin={:.4} projectionAreaScaleMax={:.4} projectionTargetScaleControlRole=reference-target-footprint-runtime-adjustment projectionTargetScaleMin={:.4} projectionTargetScaleMax={:.4} leftActive={} rightActive={} leftStickX={:.4} leftStickY={:.4} rightStickY={:.4} projectionTargetOffsetXUv={:.4} projectionTargetOffsetYUv={:.4} projectionTargetScale={:.4} projectionAreaScaleX={:.4} projectionAreaScaleY={:.4}",
                    PROJECTION_AREA_MIN_SCALE,
                    PROJECTION_AREA_MAX_SCALE,
                    PROJECTION_TARGET_MIN_SCALE,
                    PROJECTION_TARGET_MAX_SCALE,
                    state.left_controller.active(),
                    state.right_controller.active(),
                    state.left_controller.stick.x,
                    state.left_controller.stick.y,
                    state.right_controller.stick.y,
                    self.projection_target_joystick_offset_x_uv,
                    self.projection_target_joystick_offset_y_uv,
                    tuning.projection_target_scale,
                    tuning.projection_area_scale_x,
                    tuning.projection_area_scale_y,
                ));
                self.projection_target_joystick_last_log_frame = frame;
            }
            return;
        }

        let mut tuning = self.current_horizontal_alignment_tuning();
        tuning.projection_target_offset_x_uv = self.projection_target_joystick_offset_x_uv;
        tuning.projection_target_offset_y_uv = self.projection_target_joystick_offset_y_uv;
        if !breath_controls_scale {
            tuning.projection_target_scale = self.projection_target_joystick_scale;
        }
        self.projection_target_offset_x_uv = tuning.projection_target_offset_x_uv;
        self.projection_target_offset_y_uv = tuning.projection_target_offset_y_uv;
        self.projection_target_scale = tuning.projection_target_scale;
        let panel_bound = self.apply_horizontal_alignment_tuning_to_panel(cx, tuning);
        if changed
            || reset
            || self.projection_target_joystick_last_log_frame == 0
            || frame.saturating_sub(self.projection_target_joystick_last_log_frame) >= 30
        {
            Self::emit_stereo_projection_marker(&format!(
                "phase=projection-target-tuning status=ok source=controller referenceSource=quest-composite-layer-apk changed={} reset={} projectionTargetJoystickControls=offset-scale projectionAreaScaleControlRole=diagnostic-canvas-scale-runtime-property projectionAreaScaleMin={:.4} projectionAreaScaleMax={:.4} projectionTargetScaleControlRole=reference-target-footprint-runtime-adjustment projectionTargetScaleMin={:.4} projectionTargetScaleMax={:.4} projectionTargetOffsetXUv={:.4} projectionTargetOffsetYUv={:.4} projectionTargetScale={:.4} projectionAreaScaleX={:.4} projectionAreaScaleY={:.4} leftStickX={:.4} leftStickY={:.4} rightStickY={:.4} panelBound={}",
                changed,
                reset,
                PROJECTION_AREA_MIN_SCALE,
                PROJECTION_AREA_MAX_SCALE,
                PROJECTION_TARGET_MIN_SCALE,
                PROJECTION_TARGET_MAX_SCALE,
                self.projection_target_joystick_offset_x_uv,
                self.projection_target_joystick_offset_y_uv,
                tuning.projection_target_scale,
                tuning.projection_area_scale_x,
                tuning.projection_area_scale_y,
                state.left_controller.stick.x,
                state.left_controller.stick.y,
                state.right_controller.stick.y,
                panel_bound,
            ));
            self.projection_target_joystick_last_log_frame = frame;
        }
    }

    pub(super) fn handle_manifold_breath_feedback_subscription(&mut self) {
        let config = Self::manifold_breath_feedback_config();
        let config_marker = Self::manifold_breath_feedback_config_marker_line(&config);
        if self
            .manifold_breath_feedback_config_marker
            .as_ref()
            .is_none_or(|previous| previous != &config_marker)
        {
            emit_marker_line(&config_marker);
            self.manifold_breath_feedback_config_marker = Some(config_marker);
        }
        if !config.enabled {
            self.manifold_breath_feedback_subscriber = None;
            return;
        }
        if self
            .manifold_breath_feedback_subscriber
            .as_ref()
            .is_none_or(|subscriber| subscriber.config() != &config)
        {
            emit_marker_line(&format!(
                "RUSTY_MAKEPAD_BREATH_FEEDBACK_SUBSCRIBER schema=rusty.gui.makepad.breath_feedback_subscriber.v1 phase=subscribe status=ready stream={} receiver={} brokerHost={} brokerPort={} subscribeCommand=subscribe receiptCommand=breath_feedback.received receiptSchema=rusty.manifold.breath.feedback_receipt.v1",
                marker_token(&config.stream_id),
                marker_token(&config.receiver_id),
                marker_token(&config.broker_host),
                config.broker_port,
            ));
            self.manifold_breath_feedback_subscriber =
                Some(ManifoldBreathFeedbackSubscriber::new(config));
        }
    }

    pub(super) fn handle_projection_target_breath_feedback(&mut self, cx: &mut Cx) {
        if !Self::projection_target_breath_controls_enabled() {
            self.projection_target_breath_scale_ready = false;
            self.projection_target_breath_last_sequence_id = 0;
            return;
        }
        let Some(sample) = self
            .manifold_breath_feedback_subscriber
            .as_ref()
            .and_then(ManifoldBreathFeedbackSubscriber::latest_sample)
        else {
            return;
        };
        let min_quality = hotload_f32(
            makepad_config::KEY_PROJECTION_TARGET_BREATH_MIN_QUALITY,
            0.0,
            0.0,
            1.0,
        );
        if sample.quality01 < min_quality as f64 {
            return;
        }
        let min_scale = hotload_f32(
            makepad_config::KEY_PROJECTION_TARGET_BREATH_MIN_SCALE,
            TARGET_PROJECTION_TARGET_SCALE,
            PROJECTION_TARGET_MIN_SCALE,
            PROJECTION_TARGET_MAX_SCALE,
        );
        let max_scale = hotload_f32(
            makepad_config::KEY_PROJECTION_TARGET_BREATH_MAX_SCALE,
            PROJECTION_TARGET_MAX_SCALE,
            PROJECTION_TARGET_MIN_SCALE,
            PROJECTION_TARGET_MAX_SCALE,
        );
        let smoothing_alpha = hotload_f32(
            makepad_config::KEY_PROJECTION_TARGET_BREATH_SMOOTHING_ALPHA,
            PROJECTION_TARGET_BREATH_DEFAULT_SMOOTHING_ALPHA,
            0.0,
            1.0,
        );
        let invert = hotload_bool(makepad_config::KEY_PROJECTION_TARGET_BREATH_INVERT, false);
        self.apply_projection_target_breath_sample(
            cx,
            sample,
            min_scale,
            max_scale,
            smoothing_alpha,
            invert,
        );
    }

    pub(super) fn apply_projection_target_breath_sample(
        &mut self,
        cx: &mut Cx,
        sample: BreathFeedbackSample,
        min_scale: f32,
        max_scale: f32,
        smoothing_alpha: f32,
        invert: bool,
    ) {
        let was_ready = self.projection_target_breath_scale_ready;
        let previous_sequence_id = self.projection_target_breath_last_sequence_id;
        let is_new_sample = makepad_projection_target_breath_sample_is_new(
            was_ready,
            previous_sequence_id,
            sample.sequence_id,
        );
        let target_scale = makepad_projection_target_breath_scale(
            sample.volume01 as f32,
            min_scale,
            max_scale,
            invert,
        );
        let smoothing_alpha = makepad_projection_target_breath_smoothing_alpha(smoothing_alpha);
        let next_scale = if self.projection_target_breath_scale_ready {
            makepad_projection_target_breath_lerp(
                self.projection_target_scale,
                target_scale,
                smoothing_alpha,
            )
        } else {
            target_scale
        }
        .clamp(PROJECTION_TARGET_MIN_SCALE, PROJECTION_TARGET_MAX_SCALE);
        let changed = !was_ready || (next_scale - self.projection_target_scale).abs() > 0.0001;
        self.projection_target_breath_scale_ready = true;
        self.projection_target_breath_last_sequence_id = sample.sequence_id;
        self.projection_target_joystick_scale = next_scale;

        let mut tuning = self.current_horizontal_alignment_tuning();
        if Self::projection_target_joystick_controls_enabled()
            && self.projection_target_joystick_scale_ready
        {
            tuning.projection_target_offset_x_uv = self.projection_target_joystick_offset_x_uv;
            tuning.projection_target_offset_y_uv = self.projection_target_joystick_offset_y_uv;
        }
        tuning.projection_target_scale = next_scale;
        self.projection_target_offset_x_uv = tuning.projection_target_offset_x_uv;
        self.projection_target_offset_y_uv = tuning.projection_target_offset_y_uv;
        self.projection_target_scale = tuning.projection_target_scale;
        let panel_bound = self.apply_horizontal_alignment_tuning_to_panel(cx, tuning);

        if is_new_sample {
            Self::emit_stereo_projection_marker(&format!(
                "phase=projection-target-tuning status=ok source=manifold-breath-volume-selected stream={} sequenceId={} previousSequenceId={} newSample=true scaleChanged={} sourceId={} inputStreamId={} volume01={:.4} quality01={:.4} minScale={:.4} maxScale={:.4} smoothingAlpha={:.4} invert={} targetScale={:.4} projectionTargetScale={:.4} panelBound={}",
                marker_token(&sample.stream_id),
                sample.sequence_id,
                previous_sequence_id,
                changed,
                marker_token(&sample.source_id),
                marker_token(&sample.input_stream_id),
                sample.volume01,
                sample.quality01,
                min_scale,
                max_scale,
                smoothing_alpha,
                invert,
                target_scale,
                tuning.projection_target_scale,
                panel_bound,
            ));
            self.projection_target_breath_last_log_frame = self.cadence_xr_update_count;
        }
    }
}

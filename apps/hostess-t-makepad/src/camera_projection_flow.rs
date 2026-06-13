use super::*;

impl App {
    pub(super) fn record_camera_texture_update(
        &mut self,
        side: StereoEye,
        position_ms: u128,
    ) -> u64 {
        match side {
            StereoEye::Left => {
                self.cadence_left_texture_update_count =
                    self.cadence_left_texture_update_count.saturating_add(1);
                self.cadence_left_last_position_ms = position_ms;
                self.cadence_left_texture_update_count
            }
            StereoEye::Right => {
                self.cadence_right_texture_update_count =
                    self.cadence_right_texture_update_count.saturating_add(1);
                self.cadence_right_last_position_ms = position_ms;
                self.cadence_right_texture_update_count
            }
        }
    }

    pub(super) fn record_camera_texture_metadata(
        &mut self,
        side: StereoEye,
        yuv: VideoYuvMetadata,
        metadata: VideoTextureUpdateMetadata,
    ) {
        match side {
            StereoEye::Left => {
                self.paired_import_left_yuv_metadata = Some(yuv);
                self.paired_import_left_update_metadata = Some(metadata);
            }
            StereoEye::Right => {
                self.paired_import_right_yuv_metadata = Some(yuv);
                self.paired_import_right_update_metadata = Some(metadata);
            }
        }
    }

    pub(super) fn record_pending_camera_frame(
        &mut self,
        side: StereoEye,
        yuv: VideoYuvMetadata,
        metadata: VideoTextureUpdateMetadata,
        position_ms: u128,
        texture_update_count: u64,
    ) {
        let texture_path = Self::makepad_camera_texture_path_from_update_metadata(
            Self::broker_h264_enabled(),
            Self::direct_camera_hardware_buffer_external_enabled(),
            yuv.enabled,
            &metadata,
        );
        let sample = CameraTextureFrameSample::new(
            side,
            yuv,
            metadata,
            position_ms,
            texture_update_count,
            texture_path,
        );
        match side {
            StereoEye::Left => self.pending_left_camera_frame = Some(sample),
            StereoEye::Right => self.pending_right_camera_frame = Some(sample),
        }
    }

    pub(super) fn record_xr_pose_snapshot(&mut self, update: &XrUpdateEvent) {
        self.last_xr_pose_snapshot = Some(XrPoseSnapshot::from_update(
            update,
            self.cadence_xr_update_count,
        ));
    }

    pub(super) fn try_adopt_pending_stereo_camera_frame(&mut self, reason: &str) -> bool {
        let (Some(left), Some(right)) = (
            self.pending_left_camera_frame.clone(),
            self.pending_right_camera_frame.clone(),
        ) else {
            return false;
        };
        let Some(pose) = self.last_xr_pose_snapshot else {
            return false;
        };

        if let Some(adopted) = self.adopted_stereo_camera_frame.as_ref() {
            let left_advanced = left.texture_update_count > adopted.left.texture_update_count;
            let right_advanced = right.texture_update_count > adopted.right.texture_update_count;
            if !left_advanced || !right_advanced {
                return false;
            }
        }

        self.next_adopted_stereo_frame_id = self.next_adopted_stereo_frame_id.saturating_add(1);
        let adopted = AdoptedStereoCameraFrame::new(
            self.next_adopted_stereo_frame_id,
            left,
            right,
            Some(pose),
        );
        self.paired_import_left_updated = true;
        self.paired_import_right_updated = true;
        self.paired_import_left_rotation_steps = adopted.left.rotation_steps;
        self.paired_import_right_rotation_steps = adopted.right.rotation_steps;
        self.camera_projection_paired_textures_bound = false;
        self.emit_stereo_frame_adoption_marker(reason, &adopted);
        self.adopted_stereo_camera_frame = Some(adopted);
        true
    }

    pub(super) fn emit_stereo_frame_adoption_marker(
        &self,
        reason: &str,
        adopted: &AdoptedStereoCameraFrame,
    ) {
        let marker_index = FRAME_ADOPTION_MARKERS_EMITTED.fetch_add(1, Ordering::AcqRel);
        if marker_index >= FRAME_ADOPTION_MARKER_LIMIT
            && marker_index % FRAME_ADOPTION_MARKER_PERIOD != 0
        {
            return;
        }
        let pose_update_count = adopted
            .pose
            .map(|pose| pose.update_count.to_string())
            .unwrap_or_else(|| "missing".to_string());
        let predicted_display_time_ns = adopted
            .pose
            .map(|pose| pose.predicted_display_time_ns.to_string())
            .unwrap_or_else(|| "missing".to_string());
        let left_pose_valid = adopted
            .pose
            .map(|pose| pose.left_valid.to_string())
            .unwrap_or_else(|| "false".to_string());
        let right_pose_valid = adopted
            .pose
            .map(|pose| pose.right_valid.to_string())
            .unwrap_or_else(|| "false".to_string());
        let pose_source = if adopted.pose.is_some() {
            "makepad-xr-update-predicted-display-pose"
        } else {
            "missing-xr-update-pose"
        };
        emit_marker_line(&format!(
            "RUSTY_MAKEPAD_FRAME_ADOPTION schema=rusty.gui.makepad.stereo_frame_adoption.v1 phase=adopt status=ok reason={} adoptionId={} leftSide={} rightSide={} leftTextureUpdateCount={} rightTextureUpdateCount={} leftPositionMs={} rightPositionMs={} leftCameraFrameSeq={} rightCameraFrameSeq={} frameSequenceDelta={} leftCameraTimestampNs={} rightCameraTimestampNs={} timestampDeltaNs={} closeTimestampMatch={} pairingStatus={} texturePath={} poseSource={} poseUpdateCount={} predictedDisplayTimeNs={} leftPoseValid={} rightPoseValid={} leftPosePosition={} rightPosePosition={} leftPoseOrientation={} rightPoseOrientation={} adoptionPolicy=latest-complete-stereo-pair panelUpdatePolicy=adopted-pair-xr-update-only",
            marker_value(reason),
            adopted.adoption_id,
            adopted.left.side.label(),
            adopted.right.side.label(),
            adopted.left.texture_update_count,
            adopted.right.texture_update_count,
            adopted.left.position_ms,
            adopted.right.position_ms,
            optional_u64_token(adopted.left.metadata.camera_frame_sequence),
            optional_u64_token(adopted.right.metadata.camera_frame_sequence),
            optional_i64_token(adopted.pairing.sequence_delta),
            optional_u64_token(adopted.left.metadata.camera_timestamp_ns),
            optional_u64_token(adopted.right.metadata.camera_timestamp_ns),
            optional_u64_token(adopted.pairing.timestamp_delta_ns),
            adopted.pairing.close_timestamp_match,
            adopted.pairing.status,
            adopted.left.texture_path.stable_id(),
            pose_source,
            pose_update_count,
            predicted_display_time_ns,
            left_pose_valid,
            right_pose_valid,
            adopted
                .pose
                .map(|pose| vec3_marker_token(pose.left_position))
                .unwrap_or_else(|| "missing".to_string()),
            adopted
                .pose
                .map(|pose| vec3_marker_token(pose.right_position))
                .unwrap_or_else(|| "missing".to_string()),
            adopted
                .pose
                .map(|pose| vec4_marker_token(pose.left_orientation))
                .unwrap_or_else(|| "missing".to_string()),
            adopted
                .pose
                .map(|pose| vec4_marker_token(pose.right_orientation))
                .unwrap_or_else(|| "missing".to_string()),
        ));
    }

    pub(super) fn makepad_camera_texture_path_from_update_metadata(
        broker_h264_enabled: bool,
        direct_hardware_buffer_requested: bool,
        yuv_enabled: bool,
        metadata: &VideoTextureUpdateMetadata,
    ) -> MakepadCameraTexturePath {
        match metadata.resource_path {
            VideoTextureResourcePath::CpuYuvPlanes
            | VideoTextureResourcePath::SoftwareYuvPlanes => {
                if broker_h264_enabled {
                    MakepadCameraTexturePath::BrokerH264CpuYuv
                } else {
                    MakepadCameraTexturePath::DirectCpuYuvPlane
                }
            }
            VideoTextureResourcePath::HardwareBufferExternal => {
                if broker_h264_enabled {
                    MakepadCameraTexturePath::BrokerH264HardwareBuffer
                } else {
                    MakepadCameraTexturePath::DirectHardwareBufferExternal
                }
            }
            VideoTextureResourcePath::HardwareBufferYuvPlanes => {
                if broker_h264_enabled {
                    MakepadCameraTexturePath::BrokerH264HardwareBuffer
                } else {
                    MakepadCameraTexturePath::DirectHardwareBufferYuvPlane
                }
            }
            VideoTextureResourcePath::SurfaceTextureExternal => {
                if broker_h264_enabled {
                    MakepadCameraTexturePath::BrokerH264SurfaceTexture
                } else {
                    MakepadCameraTexturePath::from_direct_video_update(
                        direct_hardware_buffer_requested,
                        yuv_enabled,
                    )
                }
            }
            VideoTextureResourcePath::Unspecified => {
                if broker_h264_enabled {
                    MakepadCameraTexturePath::from_video_update(true, yuv_enabled)
                } else {
                    MakepadCameraTexturePath::from_direct_video_update(
                        direct_hardware_buffer_requested,
                        yuv_enabled,
                    )
                }
            }
        }
    }

    pub(super) fn direct_camera_texture_path(&self) -> MakepadCameraTexturePath {
        let yuv_enabled = self
            .paired_import_left_yuv_metadata
            .as_ref()
            .is_some_and(|metadata| metadata.enabled)
            || self
                .paired_import_right_yuv_metadata
                .as_ref()
                .is_some_and(|metadata| metadata.enabled);
        if let Some(metadata) = self
            .paired_import_left_update_metadata
            .as_ref()
            .or(self.paired_import_right_update_metadata.as_ref())
        {
            return Self::makepad_camera_texture_path_from_update_metadata(
                false,
                Self::direct_camera_hardware_buffer_external_enabled(),
                yuv_enabled,
                metadata,
            );
        }
        MakepadCameraTexturePath::from_direct_video_update(
            Self::direct_camera_hardware_buffer_external_enabled(),
            yuv_enabled,
        )
    }

    pub(super) fn direct_camera_hardware_buffer_external_enabled() -> bool {
        hotload_bool(
            KEY_MAKEPAD_DIRECT_CAMERA_HARDWARE_BUFFER_EXTERNAL,
            DEFAULT_MAKEPAD_DIRECT_CAMERA_HARDWARE_BUFFER_EXTERNAL,
        )
    }

    pub(super) fn direct_camera_requested_texture_path() -> MakepadCameraTexturePath {
        MakepadCameraTexturePath::from_direct_hardware_buffer_external_enabled(
            Self::direct_camera_hardware_buffer_external_enabled(),
        )
    }

    pub(super) fn cadence_camera_texture_path(&self) -> MakepadCameraTexturePath {
        if Self::broker_h264_enabled() {
            if let Some(metadata) = self
                .paired_import_left_update_metadata
                .as_ref()
                .or(self.paired_import_right_update_metadata.as_ref())
            {
                return Self::makepad_camera_texture_path_from_update_metadata(
                    true,
                    false,
                    self.paired_import_left_yuv_metadata
                        .as_ref()
                        .is_some_and(|metadata| metadata.enabled)
                        || self
                            .paired_import_right_yuv_metadata
                            .as_ref()
                            .is_some_and(|metadata| metadata.enabled),
                    metadata,
                );
            }
            if self.paired_import_left_yuv_metadata.is_some()
                || self.paired_import_right_yuv_metadata.is_some()
                || self.paired_import_left_yuv_textures.is_some()
                || self.paired_import_right_yuv_textures.is_some()
            {
                MakepadCameraTexturePath::BrokerH264CpuYuv
            } else {
                Self::broker_h264_requested_texture_path()
            }
        } else {
            self.direct_camera_texture_path()
        }
    }

    pub(super) fn use_compact_cadence_marker(&self) -> bool {
        !self.current_camera_streaming_enabled()
    }

    pub(super) fn emit_cadence_sample(
        &mut self,
        cx: &mut Cx,
        now_seconds: f64,
        interval_seconds: f64,
    ) {
        let elapsed_seconds = (now_seconds - self.cadence_start_time).max(0.0);
        let frame_delta = self
            .cadence_frame_count
            .saturating_sub(self.cadence_frame_count_at_last_sample);
        let left_delta = self
            .cadence_left_texture_update_count
            .saturating_sub(self.cadence_left_texture_update_count_at_last_sample);
        let right_delta = self
            .cadence_right_texture_update_count
            .saturating_sub(self.cadence_right_texture_update_count_at_last_sample);
        let xr_update_delta = self
            .cadence_xr_update_count
            .saturating_sub(self.cadence_xr_update_count_at_last_sample);
        let draw_event_delta = self
            .cadence_draw_event_count
            .saturating_sub(self.cadence_draw_event_count_at_last_sample);
        let paired_delta = left_delta.min(right_delta);
        let app_frame_rate_hz = rate_hz(frame_delta, interval_seconds);
        let xr_update_rate_hz = rate_hz(xr_update_delta, interval_seconds);
        let draw_event_rate_hz = rate_hz(draw_event_delta, interval_seconds);
        let left_texture_rate_hz = rate_hz(left_delta, interval_seconds);
        let right_texture_rate_hz = rate_hz(right_delta, interval_seconds);
        let paired_texture_rate_hz = rate_hz(paired_delta, interval_seconds);
        let paired_buffers_ready = self.adopted_stereo_camera_frame.is_some();
        let projection_ready = self
            .paired_import_choice
            .as_ref()
            .map(|pair| pair.projection_homography_ready)
            .unwrap_or(false);
        let (projection_mapping_ready, aligned_projection) = if paired_buffers_ready {
            (projection_ready, projection_ready)
        } else {
            (false, false)
        };
        let xr_cpu = cx.xr_frame_cpu_breakdown();
        let now_ns = diagnostic_now_ns();
        let left_camera_frame_age_ms =
            camera_frame_age_ms(self.paired_import_left_update_metadata.as_ref(), now_ns);
        let right_camera_frame_age_ms =
            camera_frame_age_ms(self.paired_import_right_update_metadata.as_ref(), now_ns);
        let paired_camera_frame_age_ms =
            optional_max_f64(left_camera_frame_age_ms, right_camera_frame_age_ms);
        let left_camera_import_lag_ms =
            camera_import_lag_ms(self.paired_import_left_update_metadata.as_ref());
        let right_camera_import_lag_ms =
            camera_import_lag_ms(self.paired_import_right_update_metadata.as_ref());
        let paired_camera_stale =
            paired_camera_frame_age_ms.map(|age_ms| age_ms > CAMERA_FRAME_STALE_THRESHOLD_MS);

        let cadence_sample = MakepadCadenceSampleMarker {
            elapsed_seconds,
            interval_seconds,
            app_frame_count: self.cadence_frame_count,
            app_frame_delta: frame_delta,
            app_frame_rate_hz,
            xr_update_count: self.cadence_xr_update_count,
            xr_update_delta,
            xr_update_rate_hz,
            draw_event_count: self.cadence_draw_event_count,
            draw_event_delta,
            draw_event_rate_hz,
            left_texture_update_count: self.cadence_left_texture_update_count,
            right_texture_update_count: self.cadence_right_texture_update_count,
            paired_texture_update_count: self
                .cadence_left_texture_update_count
                .min(self.cadence_right_texture_update_count),
            left_texture_update_delta: left_delta,
            right_texture_update_delta: right_delta,
            paired_texture_update_delta: paired_delta,
            left_texture_update_rate_hz: left_texture_rate_hz,
            right_texture_update_rate_hz: right_texture_rate_hz,
            paired_texture_update_rate_hz: paired_texture_rate_hz,
            left_last_position_ms: self.cadence_left_last_position_ms,
            right_last_position_ms: self.cadence_right_last_position_ms,
            left_camera_frame_age_ms,
            right_camera_frame_age_ms,
            paired_camera_frame_age_ms,
            left_camera_import_lag_ms,
            right_camera_import_lag_ms,
            camera_stale_threshold_ms: CAMERA_FRAME_STALE_THRESHOLD_MS,
            paired_camera_stale,
            paired_left_right_camera_frames: paired_buffers_ready,
            projection_mapping_ready,
            aligned_projection,
            visible_camera_projection_ready: self.camera_projection_textures_bound,
            xr_display_refresh_rate_hz: cx.xr_display_refresh_rate_hz(),
            xr_effective_frame_rate_hz: cx.xr_effective_frame_rate_hz(),
            xr_frame_cpu_ms: cx.xr_frame_cpu_time_ms(),
            xr_should_render: xr_cpu.map(|breakdown| breakdown.should_render),
            xr_skipped_should_render_count: xr_cpu
                .map(|breakdown| breakdown.skipped_should_render_count),
            xr_pre_frame_events_ms: xr_cpu.map(|breakdown| breakdown.pre_frame_events_ms),
            xr_post_frame_media_events_ms: xr_cpu
                .map(|breakdown| breakdown.post_frame_media_events_ms),
            xr_wait_frame_ms: xr_cpu.map(|breakdown| breakdown.wait_frame_ms),
            xr_begin_frame_ms: xr_cpu.map(|breakdown| breakdown.begin_frame_ms),
            xr_locate_space_ms: xr_cpu.map(|breakdown| breakdown.locate_space_ms),
            xr_locate_views_ms: xr_cpu.map(|breakdown| breakdown.locate_views_ms),
            xr_acquire_swapchain_ms: xr_cpu.map(|breakdown| breakdown.acquire_swapchain_ms),
            xr_wait_swapchain_ms: xr_cpu.map(|breakdown| breakdown.wait_swapchain_ms),
            xr_acquire_depth_ms: xr_cpu.map(|breakdown| breakdown.acquire_depth_ms),
            xr_update_prepare_ms: xr_cpu.map(|breakdown| breakdown.update_prepare_ms),
            xr_update_dispatch_ms: xr_cpu.map(|breakdown| breakdown.update_dispatch_ms),
            xr_next_frame_ms: xr_cpu.map(|breakdown| breakdown.next_frame_ms),
            xr_draw_event_ms: xr_cpu.map(|breakdown| breakdown.draw_event_ms),
            xr_compile_shaders_ms: xr_cpu.map(|breakdown| breakdown.compile_shaders_ms),
            xr_repaint_ms: xr_cpu.map(|breakdown| breakdown.repaint_ms),
            xr_repaint_gpu_ms: xr_cpu.and_then(|breakdown| breakdown.repaint_gpu_ms),
            xr_repaint_wait_inflight_ms: xr_cpu.map(|breakdown| breakdown.repaint_wait_inflight_ms),
            xr_repaint_prepare_textures_ms: xr_cpu
                .map(|breakdown| breakdown.repaint_prepare_textures_ms),
            xr_repaint_record_draw_ms: xr_cpu.map(|breakdown| breakdown.repaint_record_draw_ms),
            xr_repaint_submit_ms: xr_cpu.map(|breakdown| breakdown.repaint_submit_ms),
            xr_repaint_texture_upload_count: xr_cpu
                .map(|breakdown| breakdown.repaint_texture_upload_count),
            xr_repaint_texture_upload_bytes: xr_cpu
                .map(|breakdown| breakdown.repaint_texture_upload_bytes),
            xr_repaint_packet_buffer_count: xr_cpu
                .map(|breakdown| breakdown.repaint_packet_buffer_count),
            xr_repaint_packet_buffer_bytes: xr_cpu
                .map(|breakdown| breakdown.repaint_packet_buffer_bytes),
            xr_repaint_geometry_upload_bytes: xr_cpu
                .map(|breakdown| breakdown.repaint_geometry_upload_bytes),
            xr_repaint_descriptor_set_count: xr_cpu
                .map(|breakdown| breakdown.repaint_descriptor_set_count),
            xr_repaint_draw_items: xr_cpu.map(|breakdown| breakdown.repaint_draw_items),
            xr_repaint_draw_calls: xr_cpu.map(|breakdown| breakdown.repaint_draw_calls),
            xr_repaint_packets: xr_cpu.map(|breakdown| breakdown.repaint_packets),
            xr_repaint_instances: xr_cpu.map(|breakdown| breakdown.repaint_instances),
            xr_repaint_indices: xr_cpu.map(|breakdown| breakdown.repaint_indices),
            xr_depth_readback_ms: xr_cpu.map(|breakdown| breakdown.depth_readback_ms),
            xr_end_frame_ms: xr_cpu.map(|breakdown| breakdown.end_frame_ms),
            xr_resize_projection_ms: xr_cpu.map(|breakdown| breakdown.resize_projection_ms),
            texture_path: self.cadence_camera_texture_path(),
        };
        let cadence_marker = if self.use_compact_cadence_marker() {
            makepad_cadence_compact_sample_marker_line(cadence_sample)
        } else {
            makepad_cadence_sample_marker_line(cadence_sample)
        };
        emit_marker_line(&cadence_marker);

        self.cadence_last_sample_time = now_seconds;
        self.cadence_frame_count_at_last_sample = self.cadence_frame_count;
        self.cadence_xr_update_count_at_last_sample = self.cadence_xr_update_count;
        self.cadence_draw_event_count_at_last_sample = self.cadence_draw_event_count;
        self.cadence_left_texture_update_count_at_last_sample =
            self.cadence_left_texture_update_count;
        self.cadence_right_texture_update_count_at_last_sample =
            self.cadence_right_texture_update_count;
    }

    pub(super) fn arm_paired_import_timer(
        &mut self,
        cx: &mut Cx,
        delay_seconds: f64,
        reason: &str,
    ) {
        if self.paired_import_finished {
            return;
        }
        self.paired_import_timer = cx.start_timeout(delay_seconds);
        PAIRED_IMPORT_SIGNAL_READY.store(false, Ordering::Release);
        thread::spawn(move || {
            thread::sleep(Duration::from_secs_f64(delay_seconds.max(0.0)));
            PAIRED_IMPORT_SIGNAL_READY.store(true, Ordering::Release);
            SignalToUI::set_ui_signal();
        });
        Self::emit_hardware_buffer_import_marker(
            &makepad_hardware_buffer_import_timer_armed_marker_fields(reason, delay_seconds),
        );
    }

    pub(super) fn handle_broker_h264_projection_metadata(
        &mut self,
        video_id: LiveId,
        metadata_json: &str,
    ) {
        emit_raw_video_event_marker("metadata", video_id);
        if !self.current_camera_streaming_enabled() || !Self::broker_h264_enabled() {
            return;
        }
        let texture_path = Self::broker_h264_requested_texture_path();
        let Some(side) = StereoEye::from_video_id(video_id) else {
            Self::emit_hardware_buffer_import_marker(
                &makepad_stream_header_metadata_ignored_marker_fields(video_id.0, texture_path),
            );
            return;
        };
        match BrokerH264ProjectionMetadata::parse(metadata_json) {
            Ok(metadata) => {
                match side {
                    StereoEye::Left => {
                        self.broker_h264_left_projection_metadata = Some(metadata.clone())
                    }
                    StereoEye::Right => {
                        self.broker_h264_right_projection_metadata = Some(metadata.clone())
                    }
                }
                if let Some(pair) = self.paired_import_choice.as_mut() {
                    match side {
                        StereoEye::Left => {
                            pair.left.camera_id = Some(metadata.camera_id.clone());
                            if metadata.delivered_width > 0 {
                                pair.left.width = metadata.delivered_width as usize;
                            }
                            if metadata.delivered_height > 0 {
                                pair.left.height = metadata.delivered_height as usize;
                            }
                        }
                        StereoEye::Right => {
                            pair.right.camera_id = Some(metadata.camera_id.clone());
                            if metadata.delivered_width > 0 {
                                pair.right.width = metadata.delivered_width as usize;
                            }
                            if metadata.delivered_height > 0 {
                                pair.right.height = metadata.delivered_height as usize;
                            }
                        }
                    }
                    pair.projection_metadata_ready = self
                        .broker_h264_left_projection_metadata
                        .as_ref()
                        .is_some_and(|metadata| metadata.projection_metadata_ready)
                        && self
                            .broker_h264_right_projection_metadata
                            .as_ref()
                            .is_some_and(|metadata| metadata.projection_metadata_ready);
                    pair.pose_source = match (
                        self.broker_h264_left_projection_metadata.as_ref(),
                        self.broker_h264_right_projection_metadata.as_ref(),
                    ) {
                        (Some(left), Some(right)) => broker_pair_pose_source(left, right),
                        _ => metadata.pose_source.clone(),
                    };
                    pair.source_binding_mode = "broker-h264-stream-header".to_string();
                    pair.coordinate_chain =
                        "broker-h264-stream-header-to-runtime-openxr-view".to_string();
                    pair.fallback_reason = if pair.projection_metadata_ready {
                        "waiting_for_runtime_xr_view_projection".to_string()
                    } else {
                        "broker_stream_metadata_not_projection_ready".to_string()
                    };
                }
                Self::emit_hardware_buffer_import_marker(&stream_header_metadata_marker_fields(
                    side.label(),
                    &metadata,
                    texture_path,
                ));
            }
            Err(error) => {
                Self::emit_hardware_buffer_import_marker(
                    &makepad_stream_header_metadata_error_marker_fields(
                        side.label(),
                        metadata_json.len(),
                        &error,
                        texture_path,
                    ),
                );
            }
        }
    }

    pub(super) fn begin_camera_streaming_startup(&mut self, cx: &mut Cx) {
        if !self.current_camera_streaming_enabled() {
            if !self.camera_streaming_disabled_logged {
                self.camera_streaming_disabled_logged = true;
                emit_marker_line(makepad_camera2_acquisition_streaming_disabled_marker_line());
            }
            return;
        }
        if self.paired_import_started || self.paired_import_finished {
            return;
        }
        if !self.paired_import_timer.is_empty() {
            return;
        }
        if Self::broker_h264_enabled() {
            let source = Self::broker_h264_source();
            self.paired_import_choice = Some(MakepadCameraPair::from_broker_h264_source(&source));
            Self::emit_hardware_buffer_import_marker(
                &makepad_hardware_buffer_import_broker_h264_startup_marker_fields(
                    &source.broker_host,
                    source.broker_port,
                    source.stream_port,
                    Self::broker_h264_stream_port(StereoEye::Right),
                    &source.source_mode,
                    &source.decode_output_mode,
                    &source.synthetic_pattern,
                    source.preferred_width,
                    source.preferred_height,
                    source.live_stream,
                    Self::broker_h264_requested_texture_path(),
                ),
            );
        } else {
            cx.request_permission(Permission::Camera);
            cx.request_permission(Permission::HeadsetCamera);
        }
        self.arm_paired_import_timer(cx, PAIRED_IMPORT_DELAY_SECONDS, "startup");
    }

    pub(super) fn handle_paired_import_event(&mut self, cx: &mut Cx, event: &Event) {
        if !self.current_camera_streaming_enabled() {
            self.paired_import_timer = Timer::empty();
            if !self.camera_streaming_disabled_logged {
                self.camera_streaming_disabled_logged = true;
                emit_marker_line(makepad_camera2_acquisition_streaming_disabled_marker_line());
            }
            return;
        }
        if self.camera_streaming_disabled_logged {
            self.camera_streaming_disabled_logged = false;
            self.begin_camera_streaming_startup(cx);
        }
        match event {
            Event::Startup => {
                self.begin_camera_streaming_startup(cx);
            }
            Event::VideoInputs(inputs) => {
                if Self::broker_h264_enabled() {
                    return;
                }
                self.paired_import_choice = Self::pick_makepad_camera_pair(inputs);
                if !self.paired_import_selection_logged {
                    self.paired_import_selection_logged = true;
                    self.emit_makepad_camera_selection_marker(inputs);
                }
                if self.paired_import_timer.is_empty()
                    && !self.paired_import_started
                    && !self.paired_import_finished
                {
                    self.arm_paired_import_timer(cx, PAIRED_IMPORT_DELAY_SECONDS, "video-inputs");
                }
            }
            Event::TextureHandleReady(ready) => {
                self.maybe_prepare_broker_h264_import(cx, ready);
            }
            Event::VideoYuvTexturesReady(ready) => {
                emit_raw_video_event_marker("yuv-textures-ready", ready.video_id);
                if let Some(side) = StereoEye::from_video_id(ready.video_id) {
                    if Self::broker_h264_enabled() {
                        if Self::broker_h264_requested_texture_path()
                            != MakepadCameraTexturePath::BrokerH264CpuYuv
                        {
                            return;
                        }
                        let textures = MakepadCameraYuvTextures::new(
                            ready.tex_y.clone(),
                            ready.tex_u.clone(),
                            ready.tex_v.clone(),
                        );
                        match side {
                            StereoEye::Left => {
                                self.paired_import_left_yuv_textures = Some(textures)
                            }
                            StereoEye::Right => {
                                self.paired_import_right_yuv_textures = Some(textures)
                            }
                        }
                        self.camera_projection_textures_bound = false;
                        self.camera_projection_paired_textures_bound = false;
                        Self::emit_hardware_buffer_import_marker(
                            &makepad_hardware_buffer_import_yuv_textures_ready_broker_marker_fields(
                                side.label(),
                            ),
                        );
                        return;
                    }
                    let textures = MakepadCameraYuvTextures::new(
                        ready.tex_y.clone(),
                        ready.tex_u.clone(),
                        ready.tex_v.clone(),
                    );
                    match side {
                        StereoEye::Left => self.paired_import_left_yuv_textures = Some(textures),
                        StereoEye::Right => self.paired_import_right_yuv_textures = Some(textures),
                    }
                    Self::emit_hardware_buffer_import_marker(
                        &makepad_hardware_buffer_import_yuv_textures_ready_single_stream_marker_fields(
                            side.label(),
                            Self::direct_camera_requested_texture_path(),
                        ),
                    );
                }
            }
            Event::VideoPlaybackMetadata(metadata) => {
                self.handle_broker_h264_projection_metadata(
                    metadata.video_id,
                    &metadata.metadata_json,
                );
                self.emit_paired_projection_progress("stream-header-metadata");
            }
            Event::VideoPlaybackPrepared(prepared) => {
                emit_raw_video_event_marker("prepared", prepared.video_id);
                if let Some(side) = StereoEye::from_video_id(prepared.video_id) {
                    match side {
                        StereoEye::Left => self.paired_import_left_prepared = true,
                        StereoEye::Right => self.paired_import_right_prepared = true,
                    }
                    Self::emit_hardware_buffer_import_marker(
                        &makepad_hardware_buffer_import_prepared_marker_fields(
                            side.label(),
                            prepared.video_width,
                            prepared.video_height,
                            if Self::broker_h264_enabled() {
                                Self::broker_h264_requested_texture_path()
                            } else {
                                Self::direct_camera_requested_texture_path()
                            },
                        ),
                    );
                    self.emit_paired_projection_progress("prepared");
                }
            }
            Event::VideoTextureUpdated(updated) => {
                emit_raw_video_event_marker("texture-updated", updated.video_id);
                if let Some(side) = StereoEye::from_video_id(updated.video_id) {
                    let texture_update_count =
                        self.record_camera_texture_update(side, updated.current_position_ms);
                    self.record_camera_texture_metadata(
                        side,
                        updated.yuv,
                        updated.metadata.clone(),
                    );
                    self.record_pending_camera_frame(
                        side,
                        updated.yuv,
                        updated.metadata.clone(),
                        updated.current_position_ms,
                        texture_update_count,
                    );
                    if !Self::broker_h264_enabled() {
                        self.emit_yuv_texture_content_probe(cx, side, updated.yuv);
                    }
                    let marker_index =
                        TEXTURE_UPDATE_MARKERS_EMITTED.fetch_add(1, Ordering::AcqRel);
                    if should_emit_texture_update_marker(marker_index) {
                        let texture_path = Self::makepad_camera_texture_path_from_update_metadata(
                            Self::broker_h264_enabled(),
                            Self::direct_camera_hardware_buffer_external_enabled(),
                            updated.yuv.enabled,
                            &updated.metadata,
                        );
                        Self::emit_hardware_buffer_import_marker(
                            &makepad_hardware_buffer_import_texture_updated_marker_fields(
                                side.label(),
                                updated.yuv.enabled,
                                updated.yuv.biplanar,
                                updated.yuv.rotation_steps,
                                texture_path,
                                &updated.metadata,
                                MakepadProjectionBorderPolicy::current().stable_id(),
                                MakepadProcessingLayer::current().stable_id(),
                            ),
                        );
                    }
                    if self.paired_import_finished {
                        return;
                    }
                    match side {
                        StereoEye::Left => {
                            self.paired_import_left_updated = true;
                            self.paired_import_left_rotation_steps = updated.yuv.rotation_steps;
                        }
                        StereoEye::Right => {
                            self.paired_import_right_updated = true;
                            self.paired_import_right_rotation_steps = updated.yuv.rotation_steps;
                        }
                    }
                    self.complete_paired_import_if_ready(cx);
                }
            }
            Event::VideoDecodingError(error) => {
                emit_raw_video_event_marker("decode-error", error.video_id);
                if let Some(side) = StereoEye::from_video_id(error.video_id) {
                    self.paired_import_finished = true;
                    Self::emit_hardware_buffer_import_marker(
                        &makepad_hardware_buffer_import_complete_error_marker_fields(
                            side.label(),
                            &error.error,
                        ),
                    );
                    Self::emit_stereo_projection_marker(
                        &makepad_projection_complete_error_marker_fields(side.label()),
                    );
                }
            }
            _ => {}
        }

        if !self.paired_import_timer.is_empty()
            && self.paired_import_timer.is_event(event).is_some()
        {
            self.paired_import_timer = Timer::empty();
            Self::emit_hardware_buffer_import_marker(
                &makepad_hardware_buffer_import_timer_fired_marker_fields(
                    "makepad-timer",
                    self.paired_import_choice.is_some(),
                    self.paired_import_started,
                    self.paired_import_finished,
                ),
            );
            self.try_start_paired_import(cx);
        }

        if !self.paired_import_timer.is_empty()
            && matches!(event, Event::Signal)
            && PAIRED_IMPORT_SIGNAL_READY.swap(false, Ordering::AcqRel)
        {
            self.paired_import_timer = Timer::empty();
            Self::emit_hardware_buffer_import_marker(
                &makepad_hardware_buffer_import_timer_fired_marker_fields(
                    "signal-fallback",
                    self.paired_import_choice.is_some(),
                    self.paired_import_started,
                    self.paired_import_finished,
                ),
            );
            self.try_start_paired_import(cx);
        }

        if !self.native_video_widget_retry_timer.is_empty()
            && self
                .native_video_widget_retry_timer
                .is_event(event)
                .is_some()
        {
            self.native_video_widget_retry_timer = Timer::empty();
            if let Some(pair) = self.native_video_widget_retry_pair.clone() {
                if self.start_native_video_widget_surface(cx, &pair) {
                    self.paired_import_finished = true;
                    self.native_video_widget_retry_pair = None;
                }
            }
        }
    }

    pub(super) fn maybe_prepare_broker_h264_import(
        &mut self,
        cx: &mut Cx,
        ready: &TextureHandleReadyEvent,
    ) {
        if !self.current_camera_streaming_enabled() || !Self::broker_h264_enabled() {
            return;
        }

        let left_texture_id = self
            .paired_import_left_texture
            .as_ref()
            .map(Texture::texture_id);
        let right_texture_id = self
            .paired_import_right_texture
            .as_ref()
            .map(Texture::texture_id);
        let side = if Some(ready.texture_id) == left_texture_id {
            StereoEye::Left
        } else if Some(ready.texture_id) == right_texture_id {
            StereoEye::Right
        } else {
            return;
        };

        let already_requested = match side {
            StereoEye::Left => self.broker_h264_left_playback_requested,
            StereoEye::Right => self.broker_h264_right_playback_requested,
        };
        if already_requested {
            return;
        }

        let source = Self::broker_h264_source_for_eye(side);
        match side {
            StereoEye::Left => self.broker_h264_left_playback_requested = true,
            StereoEye::Right => self.broker_h264_right_playback_requested = true,
        }
        Self::emit_hardware_buffer_import_marker(
            &makepad_hardware_buffer_import_texture_handle_ready_marker_fields(
                side.label(),
                ready.handle,
                &source.broker_host,
                source.broker_port,
                source.stream_port,
                &source.source_mode,
                &source.synthetic_pattern,
                source.live_stream,
            ),
        );
        cx.prepare_video_playback(
            side.video_id(),
            VideoSource::ExternalH264(source),
            CameraPreviewMode::Texture,
            ready.handle,
            ready.texture_id,
            true,
            false,
        );
    }

    pub(super) fn request_broker_h264_import(
        &mut self,
        cx: &mut Cx,
        side: StereoEye,
        texture_id: TextureId,
    ) {
        if !self.current_camera_streaming_enabled() || !Self::broker_h264_enabled() {
            return;
        }
        let already_requested = match side {
            StereoEye::Left => self.broker_h264_left_playback_requested,
            StereoEye::Right => self.broker_h264_right_playback_requested,
        };
        if already_requested {
            return;
        }

        let source = Self::broker_h264_source_for_eye(side);
        match side {
            StereoEye::Left => self.broker_h264_left_playback_requested = true,
            StereoEye::Right => self.broker_h264_right_playback_requested = true,
        }
        Self::emit_hardware_buffer_import_marker(
            &makepad_hardware_buffer_import_broker_h264_prepare_request_marker_fields(
                side.label(),
                &source.broker_host,
                source.broker_port,
                source.stream_port,
                &source.source_mode,
                &source.decode_output_mode,
                &source.synthetic_pattern,
                source.live_stream,
                Self::broker_h264_requested_texture_path(),
            ),
        );
        cx.prepare_video_playback(
            side.video_id(),
            VideoSource::ExternalH264(source),
            CameraPreviewMode::Texture,
            0,
            texture_id,
            true,
            false,
        );
    }

    pub(super) fn try_start_paired_import(&mut self, cx: &mut Cx) {
        if !self.current_camera_streaming_enabled() {
            return;
        }
        if self.paired_import_started || self.paired_import_finished {
            return;
        }

        if Self::broker_h264_enabled() && self.paired_import_choice.is_none() {
            let source = Self::broker_h264_source();
            self.paired_import_choice = Some(MakepadCameraPair::from_broker_h264_source(&source));
        }

        let Some(pair) = self.paired_import_choice.clone() else {
            self.paired_import_wait_count = self.paired_import_wait_count.saturating_add(1);
            if self.paired_import_wait_count > PAIRED_IMPORT_MAX_WAITS {
                self.paired_import_finished = true;
                Self::emit_hardware_buffer_import_marker(
                    makepad_hardware_buffer_import_start_error_marker_fields(),
                );
                Self::emit_stereo_projection_marker(
                    "phase=start status=error pairedLeftRightGpuBuffers=false projectionMappingReady=false alignedProjection=false fallbackReason=no_makepad_camera_stereo_pair",
                );
            } else {
                Self::emit_hardware_buffer_import_marker(
                    &makepad_hardware_buffer_import_start_waiting_marker_fields(
                        self.paired_import_wait_count,
                    ),
                );
                self.arm_paired_import_timer(cx, PAIRED_IMPORT_RETRY_SECONDS, "stereo-pair-retry");
            }
            return;
        };

        let left_texture = Texture::new_with_format(cx, TextureFormat::VideoExternal);
        let right_texture = Texture::new_with_format(cx, TextureFormat::VideoExternal);
        let left_texture_id = left_texture.texture_id();
        let right_texture_id = right_texture.texture_id();
        self.paired_import_left_texture = Some(left_texture);
        self.paired_import_right_texture = Some(right_texture);
        self.paired_import_started = true;

        let broker_h264_enabled = Self::broker_h264_enabled();
        let left_stream_port = if broker_h264_enabled {
            Self::broker_h264_stream_port(StereoEye::Left).to_string()
        } else {
            "none".to_string()
        };
        let right_stream_port = if broker_h264_enabled {
            Self::broker_h264_stream_port(StereoEye::Right).to_string()
        } else {
            "none".to_string()
        };
        Self::emit_hardware_buffer_import_marker(
            &makepad_hardware_buffer_import_start_marker_fields(
                &pair,
                broker_h264_enabled,
                &frame_rate_token(pair.left.frame_rate),
                &frame_rate_token(pair.right.frame_rate),
                pixel_format_label(pair.left.pixel_format),
                &left_stream_port,
                &right_stream_port,
                PAIRED_IMPORT_DELAY_SECONDS,
                if broker_h264_enabled {
                    Self::broker_h264_requested_texture_path()
                } else {
                    Self::direct_camera_requested_texture_path()
                },
            ),
        );
        Self::emit_stereo_projection_marker(&makepad_projection_start_marker_fields(
            &pair,
            &runtime_text(&Self::runtime_config(), KEY_CAMERA_PROJECTION_MODE),
            runtime_float(&Self::runtime_config(), KEY_PROJECTION_SCALE),
            runtime_float(&Self::runtime_config(), KEY_XR_RENDER_SCALE),
        ));

        if NATIVE_VIDEO_WIDGET_SURFACE_DIAGNOSTIC {
            if self.start_native_video_widget_surface(cx, &pair) {
                self.paired_import_finished = true;
            }
            return;
        }

        if broker_h264_enabled {
            if let Some(texture) = self.paired_import_left_texture.as_ref() {
                self.request_broker_h264_import(cx, StereoEye::Left, texture.texture_id());
            }
            if let Some(texture) = self.paired_import_right_texture.as_ref() {
                self.request_broker_h264_import(cx, StereoEye::Right, texture.texture_id());
            }
            return;
        }

        let direct_camera_texture_path = Self::direct_camera_requested_texture_path();
        let left_import_texture_id = if direct_camera_texture_path.makepad_vulkan_import() {
            left_texture_id
        } else {
            TextureId::default()
        };
        let right_import_texture_id = if direct_camera_texture_path.makepad_vulkan_import() {
            right_texture_id
        } else {
            TextureId::default()
        };

        cx.prepare_headset_camera_playback(
            StereoEye::Left.video_id(),
            VideoSource::Camera(pair.left.input_id, pair.left.format_id),
            CameraPreviewMode::Texture,
            0,
            left_import_texture_id,
            true,
            false,
        );
        cx.prepare_headset_camera_playback(
            StereoEye::Right.video_id(),
            VideoSource::Camera(pair.right.input_id, pair.right.format_id),
            CameraPreviewMode::Texture,
            0,
            right_import_texture_id,
            true,
            false,
        );
    }

    pub(super) fn start_native_video_widget_surface(
        &mut self,
        cx: &mut Cx,
        pair: &MakepadCameraPair,
    ) -> bool {
        if self.native_video_widget_started {
            return true;
        }

        let left_video = self.ui.video(cx, &[live_id!(left_camera_video)]);
        let right_video = self.ui.video(cx, &[live_id!(right_camera_video)]);
        let left_unprepared = left_video.is_unprepared();
        let right_unprepared = right_video.is_unprepared();
        if !left_unprepared || !right_unprepared {
            if self.native_video_widget_retry_count >= NATIVE_VIDEO_WIDGET_MAX_RESETS {
                Self::emit_stereo_projection_marker(
                    &makepad_native_video_widget_reset_error_marker_fields(
                        left_unprepared,
                        right_unprepared,
                        left_video.is_playing(),
                        right_video.is_playing(),
                        left_video.is_cleaning_up(),
                        right_video.is_cleaning_up(),
                        self.native_video_widget_retry_count,
                    ),
                );
                return true;
            }

            if !left_unprepared && !left_video.is_cleaning_up() {
                left_video.stop_and_cleanup_resources(cx);
            }
            if !right_unprepared && !right_video.is_cleaning_up() {
                right_video.stop_and_cleanup_resources(cx);
            }
            self.native_video_widget_retry_count =
                self.native_video_widget_retry_count.saturating_add(1);
            self.native_video_widget_retry_pair = Some(pair.clone());
            self.native_video_widget_retry_timer =
                cx.start_timeout(NATIVE_VIDEO_WIDGET_RETRY_SECONDS);
            Self::emit_stereo_projection_marker(
                &makepad_native_video_widget_reset_waiting_marker_fields(
                    left_unprepared,
                    right_unprepared,
                    left_video.is_playing(),
                    right_video.is_playing(),
                    left_video.is_cleaning_up(),
                    right_video.is_cleaning_up(),
                    self.native_video_widget_retry_count,
                    NATIVE_VIDEO_WIDGET_RETRY_SECONDS,
                ),
            );
            return false;
        }

        left_video.set_camera_preview_mode(cx, VideoCameraPreviewMode::Texture);
        right_video.set_camera_preview_mode(cx, VideoCameraPreviewMode::Texture);
        left_video.set_camera_permission(VideoCameraPermission::HeadsetCamera);
        right_video.set_camera_permission(VideoCameraPermission::HeadsetCamera);
        left_video.set_source_camera(cx, pair.left.input_id, pair.left.format_id);
        right_video.set_source_camera(cx, pair.right.input_id, pair.right.format_id);
        left_video.should_dispatch_texture_updates(true);
        right_video.should_dispatch_texture_updates(true);
        left_video.begin_playback(cx);
        right_video.begin_playback(cx);
        self.native_video_widget_started = true;

        Self::emit_stereo_projection_marker(&makepad_native_video_widget_surface_marker_fields(
            pair,
            self.native_video_widget_retry_count,
        ));
        true
    }

    pub(super) fn emit_makepad_camera_selection_marker(&self, inputs: &VideoInputsEvent) {
        let source_count = inputs.descs.len();
        let format_count: usize = inputs.descs.iter().map(|desc| desc.formats.len()).sum();
        match &self.paired_import_choice {
            Some(pair) => {
                Self::emit_hardware_buffer_import_marker(
                    &makepad_hardware_buffer_import_enumerated_marker_fields(
                        pair,
                        source_count,
                        format_count,
                        &frame_rate_token(pair.left.frame_rate),
                        &frame_rate_token(pair.right.frame_rate),
                        pixel_format_label(pair.left.pixel_format),
                    ),
                );
                Self::emit_stereo_projection_marker(&makepad_projection_enumerated_marker_fields(
                    pair,
                    source_count,
                    format_count,
                ));
            }
            None => Self::emit_hardware_buffer_import_marker(
                &makepad_hardware_buffer_import_enumerated_error_marker_fields(
                    source_count,
                    format_count,
                ),
            ),
        }
    }

    pub(super) fn pick_makepad_camera_pair(inputs: &VideoInputsEvent) -> Option<MakepadCameraPair> {
        if Self::broker_h264_enabled() {
            let source = Self::broker_h264_source();
            return Some(MakepadCameraPair::from_broker_h264_source(&source));
        }
        let choices = collect_makepad_camera_choices(inputs);
        let camera2_plan = Self::latest_camera2_stereo_plan();
        camera2_plan
            .as_ref()
            .and_then(|plan| MakepadCameraPair::from_camera2_plan(&choices, plan))
            .or_else(|| MakepadCameraPair::from_best_available_pair(&choices))
    }

    pub(super) fn emit_paired_projection_progress(&self, phase: &str) {
        let Some(pair) = &self.paired_import_choice else {
            return;
        };
        Self::emit_stereo_projection_marker(&makepad_paired_projection_progress_marker_fields(
            pair,
            phase,
            self.paired_import_left_prepared,
            self.paired_import_right_prepared,
            self.paired_import_left_updated,
            self.paired_import_right_updated,
        ));
    }

    pub(super) fn emit_yuv_texture_content_probe(
        &self,
        cx: &mut Cx,
        side: StereoEye,
        yuv: VideoYuvMetadata,
    ) {
        if TEXTURE_CONTENT_PROBE_MARKERS_EMITTED.fetch_add(1, Ordering::AcqRel)
            >= TEXTURE_CONTENT_PROBE_MARKER_LIMIT
        {
            return;
        }

        let textures = match side {
            StereoEye::Left => self.paired_import_left_yuv_textures.clone(),
            StereoEye::Right => self.paired_import_right_yuv_textures.clone(),
        };

        let Some(textures) = textures else {
            Self::emit_stereo_projection_marker(
                &makepad_texture_content_probe_missing_marker_fields(
                    side.label(),
                    yuv.enabled,
                    yuv.biplanar,
                    yuv.matrix,
                    yuv.rotation_steps,
                ),
            );
            return;
        };

        let y_stats = texture_plane_content_stats(cx, &textures.y);
        let u_stats = texture_plane_content_stats(cx, &textures.u);
        let v_stats = texture_plane_content_stats(cx, &textures.v);
        let cpu_content_present =
            y_stats.readable && y_stats.data_present && y_stats.sample_count > 0 && y_stats.max > 0;

        Self::emit_stereo_projection_marker(&makepad_texture_content_probe_ok_marker_fields(
            side.label(),
            yuv.enabled,
            yuv.biplanar,
            yuv.matrix,
            yuv.rotation_steps,
            cpu_content_present,
            &y_stats.marker_fields("y"),
            &u_stats.marker_fields("u"),
            &v_stats.marker_fields("v"),
        ));
    }

    pub(super) fn bind_camera_projection_panel(&mut self, cx: &mut Cx) -> bool {
        if !self.current_camera_streaming_enabled() {
            self.camera_projection_textures_bound = false;
            self.camera_projection_paired_textures_bound = false;
            return false;
        }
        let broker_h264_enabled = Self::broker_h264_enabled();
        let projection_sample_mode = MakepadProjectionSampleMode::current();
        let camera_texture_binding_enabled = projection_sample_mode.binds_camera_textures();
        let projection_panel_draw_enabled = projection_sample_mode.draws_projection_panel();
        let adopted_frame = self.adopted_stereo_camera_frame.clone();
        let adopted_frame_id = adopted_frame
            .as_ref()
            .map(|frame| frame.adoption_id)
            .unwrap_or(0);
        let paired_streams_available = adopted_frame.is_some();
        if self.camera_projection_textures_bound
            && (!paired_streams_available || self.camera_projection_paired_textures_bound)
            && self.camera_projection_bound_adopted_frame_id == adopted_frame_id
        {
            return true;
        }
        let emit_binding_markers = !self.camera_projection_textures_bound
            || self.camera_projection_bound_adopted_frame_id != adopted_frame_id;

        let (Some(left_texture), Some(right_texture), Some(pair)) = (
            self.paired_import_left_texture.clone(),
            self.paired_import_right_texture.clone(),
            self.paired_import_choice.clone(),
        ) else {
            return false;
        };
        let left_updated_yuv = if adopted_frame
            .as_ref()
            .is_some_and(|frame| frame.left.yuv.enabled)
            || (adopted_frame.is_none() && self.paired_import_left_updated)
        {
            self.paired_import_left_yuv_textures.clone()
        } else {
            None
        };
        let right_updated_yuv = if adopted_frame
            .as_ref()
            .is_some_and(|frame| frame.right.yuv.enabled)
            || (adopted_frame.is_none() && self.paired_import_right_updated)
        {
            self.paired_import_right_yuv_textures.clone()
        } else {
            None
        };
        let proof_source_side = match (left_updated_yuv.is_some(), right_updated_yuv.is_some()) {
            (true, true) => "paired",
            (true, false) => "left",
            (false, true) => "right",
            (false, false) => "ready-only",
        };
        let (left_yuv_source, right_yuv_source) =
            match (left_updated_yuv.clone(), right_updated_yuv.clone()) {
                (Some(left), Some(right)) => (Some(left), Some(right)),
                (Some(left), None) => (Some(left.clone()), Some(left)),
                (None, Some(right)) => (Some(right.clone()), Some(right)),
                (None, None) => {
                    let left_ready = self
                        .paired_import_left_yuv_textures
                        .clone()
                        .or_else(|| self.paired_import_right_yuv_textures.clone());
                    let right_ready = self
                        .paired_import_right_yuv_textures
                        .clone()
                        .or_else(|| left_ready.clone());
                    (left_ready, right_ready)
                }
            };
        let single_stream_visual_proof = adopted_frame.is_none()
            && !(self.paired_import_left_updated && self.paired_import_right_updated);
        let broker_h264_cpu_yuv_decode = broker_h264_enabled
            && (left_yuv_source.is_some()
                || right_yuv_source.is_some()
                || self.paired_import_left_yuv_textures.is_some()
                || self.paired_import_right_yuv_textures.is_some());
        let texture_path = adopted_frame
            .as_ref()
            .map(|frame| frame.left.texture_path)
            .unwrap_or_else(|| {
                if broker_h264_enabled {
                    if broker_h264_cpu_yuv_decode {
                        MakepadCameraTexturePath::BrokerH264CpuYuv
                    } else {
                        Self::broker_h264_requested_texture_path()
                    }
                } else {
                    self.direct_camera_texture_path()
                }
            });
        let explicit_top_left_broker_stimulus = broker_h264_enabled
            && self
                .broker_h264_left_projection_metadata
                .as_ref()
                .is_some_and(
                    BrokerH264ProjectionMetadata::has_explicit_top_left_stimulus_orientation,
                )
            && self
                .broker_h264_right_projection_metadata
                .as_ref()
                .is_some_and(
                    BrokerH264ProjectionMetadata::has_explicit_top_left_stimulus_orientation,
                );
        let orientation_decision = if broker_h264_enabled {
            match (
                self.broker_h264_left_projection_metadata.as_ref(),
                self.broker_h264_right_projection_metadata.as_ref(),
            ) {
                (Some(left), Some(right)) => {
                    FrameOrientationDecision::from_broker_pair(left, right)
                }
                _ => FrameOrientationDecision::fallback("broker-h264-orientation-metadata-missing"),
            }
        } else {
            FrameOrientationDecision::direct_camera2()
        };
        let source_sample_y_flip = orientation_decision.source_sample_y_flip;
        let source_sampling_mode = if broker_h264_enabled {
            Self::broker_h264_source_sampling_mode()
        } else {
            makepad_runtime_camera_source_sampling_mode()
        };
        let full_frame_diagnostic = source_sampling_mode.uses_target_local_raster();
        let projection_content_mapping_mode = if source_sampling_mode.uses_target_local_raster() {
            1.0
        } else {
            0.0
        };
        let source_sample_transform = if source_sample_y_flip >= 0.5 {
            "stimulus-raster-y-flip"
        } else if orientation_decision.raster_orientation == FRAME_RASTER_TOP_LEFT_Y_DOWN {
            "identity-top-left-stimulus-raster"
        } else {
            "identity-y-to-match-raster-metadata"
        };
        let (left_yuv, right_yuv) = if !camera_texture_binding_enabled {
            (None, None)
        } else if texture_path.yuv_sampling_enabled() {
            if broker_h264_enabled {
                let left_yuv = left_yuv_source
                    .clone()
                    .or_else(|| right_yuv_source.clone())
                    .or_else(|| self.paired_import_left_yuv_textures.clone())
                    .or_else(|| self.paired_import_right_yuv_textures.clone());
                let right_yuv = right_yuv_source
                    .clone()
                    .or_else(|| left_yuv_source.clone())
                    .or_else(|| self.paired_import_right_yuv_textures.clone())
                    .or_else(|| left_yuv.clone());
                (left_yuv, right_yuv)
            } else {
                let (Some(left_yuv), Some(right_yuv)) = (left_yuv_source, right_yuv_source) else {
                    if !self.camera_projection_bind_error_logged {
                        Self::emit_stereo_projection_marker(
                            "phase=visible-panel-bound status=waiting visibleCameraProjectionReady=false fallbackReason=makepad_camera_yuv_plane_textures_missing",
                        );
                        self.camera_projection_bind_error_logged = true;
                    }
                    return false;
                };
                (Some(left_yuv), Some(right_yuv))
            }
        } else {
            (None, None)
        };

        let panel_ref = self.ui.widget(cx, ids!(camera_projection_panel));
        let Some(mut panel) = panel_ref.borrow_mut::<MakepadStereoCameraPanel>() else {
            if !self.camera_projection_bind_error_logged {
                Self::emit_stereo_projection_marker(
                    "phase=visible-panel-bound status=error visibleCameraProjectionReady=false fallbackReason=makepad_camera_projection_panel_missing",
                );
                self.camera_projection_bind_error_logged = true;
            }
            return false;
        };

        panel.apply_projection_panel_geometry(cx);
        let left_panel_texture = if camera_texture_binding_enabled {
            Some(left_texture)
        } else {
            None
        };
        let right_panel_texture = if camera_texture_binding_enabled {
            Some(right_texture)
        } else {
            None
        };
        panel.set_camera_textures(
            cx,
            left_panel_texture,
            right_panel_texture,
            left_yuv,
            right_yuv,
            texture_path,
            adopted_frame
                .as_ref()
                .map(|frame| frame.left.rotation_steps)
                .unwrap_or(self.paired_import_left_rotation_steps),
            adopted_frame
                .as_ref()
                .map(|frame| frame.right.rotation_steps)
                .unwrap_or(self.paired_import_right_rotation_steps),
            pair.left_surface_to_camera_h,
            pair.right_surface_to_camera_h,
            pair.left_screen_to_camera_h,
            pair.right_screen_to_camera_h,
            pair.left_screen_to_surface_h,
            pair.right_screen_to_surface_h,
            source_sample_y_flip,
            projection_content_mapping_mode,
            Self::horizontal_alignment_tuning(),
        );
        panel.set_target_footprint(cx, pair.target_footprint);
        panel.set_horizontal_alignment_tuning(cx, self.current_horizontal_alignment_tuning());
        self.camera_projection_textures_bound = true;
        self.camera_projection_paired_textures_bound = !single_stream_visual_proof;
        self.camera_projection_bound_adopted_frame_id = adopted_frame_id;
        if !emit_binding_markers {
            return true;
        }
        let content_geometry_fields = if broker_h264_enabled {
            makepad_content_geometry_marker_fields(MakepadContentGeometrySource::BrokerH264 {
                left: self.broker_h264_left_projection_metadata.as_ref(),
                right: self.broker_h264_right_projection_metadata.as_ref(),
            })
        } else {
            makepad_content_geometry_marker_fields(MakepadContentGeometrySource::DirectCamera2 {
                width: pair.left.width,
                height: pair.left.height,
                projection_geometry_profile: &pair.projection_geometry_profile,
            })
        };
        let source_color_contract = makepad_current_source_color_contract_fields();
        let source_sampling_fields = MakepadSourceSamplingHandoff::new(
            broker_h264_enabled,
            explicit_top_left_broker_stimulus,
            &orientation_decision,
            source_sampling_mode,
            projection_content_mapping_mode,
            full_frame_diagnostic,
            &pair.source_eye_mapping,
            source_sample_transform,
            &content_geometry_fields,
            &source_color_contract,
            texture_path,
        )
        .marker_fields();
        Self::emit_stereo_projection_marker(&source_sampling_fields);
        Self::emit_stereo_projection_marker(&makepad_draw_vars_bound_marker_fields(
            &pair,
            texture_path,
            broker_h264_enabled && !broker_h264_cpu_yuv_decode,
            single_stream_visual_proof,
            proof_source_side,
            camera_texture_binding_enabled,
            projection_panel_draw_enabled,
        ));
        if !self.synthetic_scene_hidden_for_camera {
            self.synthetic_scene_hidden_for_camera = true;
            Self::emit_stereo_projection_marker(
                "phase=synthetic-scene-hidden status=ok visibleCameraProjectionReady=true fallbackSceneVisible=false fallbackReason=makepad_synthetic_scene_removed_for_visual_gate",
            );
        }
        Self::emit_stereo_projection_marker(&makepad_visible_panel_bound_marker_fields(
            &pair,
            texture_path,
            self.paired_import_left_rotation_steps,
            self.paired_import_right_rotation_steps,
            single_stream_visual_proof,
            proof_source_side,
            camera_texture_binding_enabled,
            projection_panel_draw_enabled,
        ));
        true
    }

    pub(super) fn complete_paired_import_if_ready(&mut self, cx: &mut Cx) {
        if self.paired_import_finished {
            return;
        }

        let broker_h264_enabled = Self::broker_h264_enabled();
        let paired_streams_ready = self.adopted_stereo_camera_frame.is_some();
        let updated_stream_visual_proof_side = match (
            self.paired_import_left_updated,
            self.paired_import_right_updated,
        ) {
            (true, true) => "paired",
            (true, false) => "left",
            (false, true) => "right",
            (false, false) => "none",
        };
        let single_stream_ready = if broker_h264_enabled {
            false
        } else {
            let one_stream_updated =
                self.paired_import_left_updated || self.paired_import_right_updated;
            let direct_yuv_ready = self.paired_import_left_yuv_textures.is_some()
                || self.paired_import_right_yuv_textures.is_some();
            one_stream_updated
                && (!self.direct_camera_texture_path().yuv_sampling_enabled() || direct_yuv_ready)
        };
        if !paired_streams_ready && !single_stream_ready {
            self.emit_paired_projection_progress("texture-updated");
            return;
        }

        let Some(pair) = self.paired_import_choice.clone() else {
            return;
        };
        if !paired_streams_ready && !broker_h264_enabled {
            let visible_projection_ready = self.bind_camera_projection_panel(cx);
            if !self.camera_projection_single_stream_logged {
                self.camera_projection_single_stream_logged = true;
                Self::emit_stereo_projection_marker(
                    &makepad_single_stream_proof_wait_marker_fields(
                        self.paired_import_left_updated,
                        self.paired_import_right_updated,
                        self.paired_import_left_yuv_textures.is_some(),
                        self.paired_import_right_yuv_textures.is_some(),
                        self.cadence_camera_texture_path(),
                        pair.projection_homography_ready,
                        visible_projection_ready,
                        updated_stream_visual_proof_side,
                    ),
                );
            }
            return;
        }
        self.paired_import_finished = true;
        let aligned_projection = pair.projection_homography_ready && paired_streams_ready;
        let visible_projection_ready = self.bind_camera_projection_panel(cx);
        let texture_path = self.cadence_camera_texture_path();
        Self::emit_stereo_projection_marker(&makepad_projection_complete_marker_fields(
            &pair,
            paired_streams_ready,
            broker_h264_enabled,
            texture_path,
            aligned_projection,
            visible_projection_ready,
            &runtime_text(&Self::runtime_config(), KEY_CAMERA_PROJECTION_MODE),
            self.paired_import_left_rotation_steps,
            self.paired_import_right_rotation_steps,
            runtime_float(&Self::runtime_config(), KEY_PROJECTION_SCALE),
            runtime_float(&Self::runtime_config(), KEY_XR_RENDER_SCALE),
        ));
        Self::emit_stereo_comparison_parity_marker(
            "paired-projection-ready",
            &pair,
            texture_path,
            aligned_projection,
            visible_projection_ready,
        );
    }

    pub(super) fn emit_stereo_comparison_parity_marker(
        phase: &str,
        pair: &MakepadCameraPair,
        texture_path: MakepadCameraTexturePath,
        aligned_projection: bool,
        visible_projection_ready: bool,
    ) {
        let config = Self::runtime_config();
        Self::emit_projection_runtime_manifest_marker(
            phase,
            &config,
            Self::horizontal_alignment_tuning(),
        );
        emit_marker_line(&makepad_stereo_comparison_marker_line(
            pair,
            MakepadStereoComparisonMarkerInputs {
                phase,
                runtime_profile: &runtime_text(&config, KEY_RUNTIME_PROFILE),
                comparison_baseline: &runtime_text(&config, KEY_COMPARISON_BASELINE),
                camera_tier: &runtime_text(&config, KEY_CAMERA_TIER),
                acquisition_profile: &runtime_text(&config, KEY_ACQUISITION_PROFILE),
                transport_profile: &runtime_text(&config, KEY_TRANSPORT_PROFILE),
                projection_mode: &runtime_text(&config, KEY_CAMERA_PROJECTION_MODE),
                synthetic_scene: &runtime_text(&config, KEY_SYNTHETIC_SCENE),
                projection_scale: runtime_float(&config, KEY_PROJECTION_SCALE),
                xr_render_scale: runtime_float(&config, KEY_XR_RENDER_SCALE),
                texture_path,
                aligned_projection,
                visible_projection_ready,
                makepad_fork_branch: &runtime_text(&config, KEY_MAKEPAD_BRANCH),
                makepad_fork_commit: &runtime_text(&config, KEY_MAKEPAD_REVISION),
            },
        ));
    }

    #[cfg(target_os = "android")]
    pub(super) fn camera2_stereo_plan() -> Option<Camera2StereoPlan> {
        android_camera_probe::latest_stereo_projection_plan().map(Camera2StereoPlan::from)
    }

    #[cfg(not(target_os = "android"))]
    pub(super) fn camera2_stereo_plan() -> Option<Camera2StereoPlan> {
        None
    }

    pub(super) fn latest_camera2_stereo_plan() -> Option<Camera2StereoPlan> {
        let profile = Self::direct_camera_projection_geometry_profile();
        Self::camera2_stereo_plan().map(|mut plan| {
            plan.apply_projection_geometry_profile(&profile);
            plan
        })
    }

    #[cfg(target_os = "android")]
    pub(super) fn start_camera_probe_once() {
        android_camera_probe::start_camera_probe_once();
    }

    #[cfg(not(target_os = "android"))]
    pub(super) fn start_camera_probe_once() {}
}

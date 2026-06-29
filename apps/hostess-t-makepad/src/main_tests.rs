use super::*;

#[test]
fn makepad_companion_frontend_projects_shared_reports() {
    let catalog = include_str!("../../../fixtures/companion/makepad-catalog-pass.json");
    let device_link = include_str!("../../../fixtures/companion/device-link-pass.json");
    let protocol_matrix = include_str!("../../../fixtures/companion/protocol-matrix-promoted.json");
    let projection = companion_frontend::build_makepad_companion_rows_with_protocol_matrix(
        catalog,
        device_link,
        Some(protocol_matrix),
    )
    .unwrap();

    assert_eq!(projection.status, "pass");
    assert!(projection.rows.iter().any(|row| {
        row.row_family == "catalog_workspace"
            && row.row_id == "workspace.hostess_makepad.validation"
    }));
    assert!(projection
        .rows
        .iter()
        .any(|row| row.row_family == "runtime_subscriber"));
    assert!(projection.rows.iter().any(|row| {
        row.row_family == "protocol_matrix_protocol" && row.row_id == "protocol.QCL-084"
    }));
    let marker =
        companion_frontend::makepad_companion_projection_marker_line("main_tests", &projection);
    assert!(marker.contains("RUSTY_HOSTESS_MAKEPAD_COMPANION_FRONTEND"));
    assert!(marker.contains("authority=requester_inspector"));
    assert!(marker.contains("protocolMatrixRows="));
    assert!(marker.contains("protocolRows=5"));
    assert!(marker.contains("highRateJsonPayload=false"));
}

#[test]
fn makepad_companion_frontend_projects_companion_report_projection() {
    let report_projection =
        include_str!("../../../fixtures/companion/companion-report-projection-pass.json");
    let projection =
        companion_frontend::build_makepad_companion_rows_from_report_projection(report_projection)
            .unwrap();

    assert_eq!(projection.status, "pass");
    assert_eq!(projection.catalog_rows, 0);
    assert_eq!(projection.device_link_rows, 0);
    assert_eq!(projection.protocol_matrix_rows, 0);
    assert_eq!(projection.report_projection_rows, 6);
    assert!(projection.rows.iter().any(|row| {
        row.row_family == "companion_report_projection_row"
            && row.row_id == "protocol_matrix.row.QCL-081.capability.biosignal.lsl_clocked_samples"
            && row.detail.contains("tier=broker_owned")
    }));
    let marker =
        companion_frontend::makepad_companion_projection_marker_line("main_tests", &projection);
    assert!(marker.contains("RUSTY_HOSTESS_MAKEPAD_COMPANION_FRONTEND"));
    assert!(marker.contains("authority=requester_inspector"));
    assert!(marker.contains("reportProjectionRows=6"));
    assert!(marker.contains("sourceArtifactRows=2"));
    assert!(marker.contains("normalizedReportRows=3"));
    assert!(marker.contains("backendEvidence=hostess_companion_report_projection"));
    assert!(marker.contains("highRateJsonPayload=false"));
}

#[test]
fn breath_feedback_config_marker_exposes_resolved_subscriber_config() {
    let mut config = ManifoldBreathFeedbackConfig::default();
    config.enabled = true;
    config.broker_port = 18765;

    let marker = App::manifold_breath_feedback_config_marker_line(&config);

    assert!(marker.contains("RUSTY_MAKEPAD_BREATH_FEEDBACK_CONFIG"));
    assert!(marker.contains("status=enabled"));
    assert!(marker.contains("enabled=true"));
    assert!(marker.contains("enabledRaw=default"));
    assert!(marker.contains("stream=stream.breath.volume.selected"));
    assert!(marker.contains("receiver=app.makepad_camera_shell.breath_feedback"));
    assert!(marker.contains("brokerPort=18765"));
    assert!(marker.contains("flagsOwner=hostessctl.record_values"));
}

#[test]
fn broker_camera_metadata_maps_legacy_physical_profile_to_camera_projection() {
    let metadata = BrokerH264ProjectionMetadata::parse(
        r#"{
            "source": "broker_app.camera2_h264_stream",
            "cameraId": "50",
            "deliveredWidth": 1280,
            "deliveredHeight": 1280,
            "projectionGeometryProfile": "physical-camera",
            "projectionMetadataReady": true,
            "poseSource": "platform",
            "poseCoordinateConvention": "android-camera2-lens-pose-reference-from-camera",
            "intrinsics": {
                "fx": 1024.0,
                "fy": 1025.0,
                "cx": 640.0,
                "cy": 641.0,
                "skew": 0.5
            },
            "intrinsicsDomain": {
                "kind": "activeArray",
                "width": 4096,
                "height": 3072
            },
            "extrinsics": {
                "px": 0.01,
                "py": 0.02,
                "pz": 0.03,
                "qx": 0.0,
                "qy": 0.0,
                "qz": 0.0,
                "qw": 1.0
            }
        }"#,
    )
    .unwrap();

    assert!(metadata.has_camera_projection_metadata());
    assert!(metadata.requests_camera_projection_mapping());
    assert_eq!(
        metadata.projection_mapping_profile_id(),
        "camera-projection"
    );
    assert_eq!(metadata.camera_id, "50");
    assert_eq!(metadata.intrinsics.unwrap().fx, 1024.0);
    assert_eq!(metadata.intrinsics_domain.unwrap().width, 4096);
    assert_eq!(metadata.extrinsics.unwrap().rotation[3], 1.0);
}

#[test]
fn broker_full_frame_camera_metadata_keeps_projection_metadata_authoritative() {
    let metadata = BrokerH264ProjectionMetadata::parse(
        r#"{
            "source": "broker_app.camera2_h264_stream",
            "cameraId": "50",
            "deliveredWidth": 1280,
            "deliveredHeight": 1280,
            "projectionGeometryProfile": "full-frame-diagnostic",
            "sourceSamplingMode": "screen-to-camera-homography",
            "contentMappingIntent": "map-camera-frame-to-full-frame-projection-area",
            "projectionMetadataReady": true,
            "poseSource": "platform",
            "poseCoordinateConvention": "android-camera2-lens-pose-reference-from-camera",
            "intrinsics": {
                "fx": 1024.0,
                "fy": 1024.0,
                "cx": 640.0,
                "cy": 640.0
            },
            "extrinsics": {
                "px": 0.01,
                "py": 0.02,
                "pz": 0.03,
                "qx": 0.0,
                "qy": 0.0,
                "qz": 0.0,
                "qw": 1.0
            }
        }"#,
    )
    .unwrap();

    assert!(metadata.is_full_frame_diagnostic_projection());
    assert!(metadata.has_camera_projection_metadata());
    assert!(!metadata.requests_explicit_full_frame_content_mapping());
}

#[test]
fn broker_explicit_full_frame_content_intent_is_distinct_from_profile_label() {
    let metadata = BrokerH264ProjectionMetadata::parse(
        r#"{
            "source": "broker_app.synthetic_h264_stream",
            "cameraId": "synthetic-left",
            "deliveredWidth": 1280,
            "deliveredHeight": 1280,
            "projectionGeometryProfile": "full-frame-diagnostic",
            "contentMappingIntent": "map-full-frame-stimulus-to-projection-surface",
            "projectionMetadataReady": true
        }"#,
    )
    .unwrap();

    assert!(metadata.is_full_frame_diagnostic_projection());
    assert!(metadata.requests_explicit_full_frame_content_mapping());
    assert!(!metadata.has_camera_projection_metadata());
}

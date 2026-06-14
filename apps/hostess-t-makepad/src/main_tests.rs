use super::*;

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

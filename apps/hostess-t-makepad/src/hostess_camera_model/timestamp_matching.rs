//! Timestamp pairing helpers for camera frame adoption.

/// Result of nearest timestamp matching.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TimestampMatch {
    pub candidate_index: usize,
    pub delta_ns: i128,
}

impl TimestampMatch {
    pub const fn absolute_delta_ns(self) -> u128 {
        self.delta_ns.unsigned_abs()
    }
}

/// Find the nearest candidate timestamp to a target timestamp.
pub fn match_nearest_timestamp(
    target_timestamp_ns: u64,
    candidate_timestamps_ns: &[u64],
    max_delta_ns: Option<u64>,
) -> Option<TimestampMatch> {
    let best = candidate_timestamps_ns
        .iter()
        .copied()
        .enumerate()
        .map(|(candidate_index, candidate)| TimestampMatch {
            candidate_index,
            delta_ns: candidate as i128 - target_timestamp_ns as i128,
        })
        .min_by_key(|candidate| candidate.absolute_delta_ns())?;

    if max_delta_ns
        .map(|max_delta_ns| best.absolute_delta_ns() <= max_delta_ns as u128)
        .unwrap_or(true)
    {
        Some(best)
    } else {
        None
    }
}

/// Result of matching one left camera timestamp with one right camera
/// timestamp.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct StereoTimestampPair {
    pub left_index: usize,
    pub right_index: usize,
    pub delta_ns: u64,
    pub midpoint_timestamp_ns: u64,
}

/// Find the closest left/right timestamp pair within a maximum delta.
pub fn match_stereo_timestamps(
    left_timestamps_ns: &[u64],
    right_timestamps_ns: &[u64],
    max_delta_ns: u64,
) -> Option<StereoTimestampPair> {
    left_timestamps_ns
        .iter()
        .copied()
        .enumerate()
        .flat_map(|(left_index, left)| {
            right_timestamps_ns
                .iter()
                .copied()
                .enumerate()
                .map(move |(right_index, right)| {
                    let delta_ns = left.abs_diff(right);
                    StereoTimestampPair {
                        left_index,
                        right_index,
                        delta_ns,
                        midpoint_timestamp_ns: left / 2 + right / 2 + ((left % 2 + right % 2) / 2),
                    }
                })
        })
        .filter(|pair| pair.delta_ns <= max_delta_ns)
        .min_by_key(|pair| pair.delta_ns)
}

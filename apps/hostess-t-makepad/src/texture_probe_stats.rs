use makepad_widgets::makepad_platform::{TextureFormat, TextureUpdated};
use makepad_widgets::*;

#[derive(Clone, Copy)]
pub(crate) struct TexturePlaneContentStats {
    pub(crate) format: &'static str,
    pub(crate) readable: bool,
    pub(crate) data_present: bool,
    pub(crate) width: usize,
    pub(crate) height: usize,
    pub(crate) len: usize,
    pub(crate) updated: &'static str,
    pub(crate) sample_count: usize,
    pub(crate) min: u8,
    pub(crate) max: u8,
    pub(crate) mean_x1000: u32,
    pub(crate) nonzero_samples: usize,
}

impl TexturePlaneContentStats {
    fn unreadable(format: &'static str) -> Self {
        Self {
            format,
            readable: false,
            data_present: false,
            width: 0,
            height: 0,
            len: 0,
            updated: "n/a",
            sample_count: 0,
            min: 0,
            max: 0,
            mean_x1000: 0,
            nonzero_samples: 0,
        }
    }

    pub(crate) fn marker_fields(&self, prefix: &str) -> String {
        format!(
            "{}Format={} {}Readable={} {}DataPresent={} {}Width={} {}Height={} {}Len={} {}Updated={} {}SampleCount={} {}Min={} {}Max={} {}MeanX1000={} {}NonZeroSamples={}",
            prefix,
            self.format,
            prefix,
            self.readable,
            prefix,
            self.data_present,
            prefix,
            self.width,
            prefix,
            self.height,
            prefix,
            self.len,
            prefix,
            self.updated,
            prefix,
            self.sample_count,
            prefix,
            self.min,
            prefix,
            self.max,
            prefix,
            self.mean_x1000,
            prefix,
            self.nonzero_samples,
        )
    }
}

pub(crate) fn texture_plane_content_stats(
    cx: &mut Cx,
    texture: &Texture,
) -> TexturePlaneContentStats {
    match texture.get_format(cx) {
        TextureFormat::VecRu8 {
            width,
            height,
            data,
            updated,
            ..
        } => compute_u8_plane_content_stats("VecRu8", *width, *height, data.as_ref(), 1, updated),
        TextureFormat::VecRGu8 {
            width,
            height,
            data,
            updated,
            ..
        } => compute_u8_plane_content_stats("VecRGu8", *width, *height, data.as_ref(), 2, updated),
        TextureFormat::VideoYuvPlane => TexturePlaneContentStats::unreadable("VideoYuvPlane"),
        TextureFormat::VideoExternal => TexturePlaneContentStats::unreadable("VideoExternal"),
        TextureFormat::VideoRgbaHardwareBuffer => {
            TexturePlaneContentStats::unreadable("VideoRgbaHardwareBuffer")
        }
        _ => TexturePlaneContentStats::unreadable("Other"),
    }
}

fn compute_u8_plane_content_stats(
    format: &'static str,
    width: usize,
    height: usize,
    data: Option<&Vec<u8>>,
    bytes_per_sample: usize,
    updated: &TextureUpdated,
) -> TexturePlaneContentStats {
    let Some(data) = data else {
        return TexturePlaneContentStats {
            format,
            readable: true,
            data_present: false,
            width,
            height,
            len: 0,
            updated: texture_updated_label(updated),
            sample_count: 0,
            min: 0,
            max: 0,
            mean_x1000: 0,
            nonzero_samples: 0,
        };
    };

    let bytes_per_sample = bytes_per_sample.max(1);
    let sample_len = data.len() / bytes_per_sample;
    if sample_len == 0 {
        return TexturePlaneContentStats {
            format,
            readable: true,
            data_present: true,
            width,
            height,
            len: data.len(),
            updated: texture_updated_label(updated),
            sample_count: 0,
            min: 0,
            max: 0,
            mean_x1000: 0,
            nonzero_samples: 0,
        };
    }

    let step = (sample_len / 4096).max(1);
    let mut min_value = u8::MAX;
    let mut max_value = u8::MIN;
    let mut sum = 0_u64;
    let mut sample_count = 0_usize;
    let mut nonzero_samples = 0_usize;

    let mut sample_index = 0_usize;
    while sample_index < sample_len {
        let value = data[sample_index * bytes_per_sample];
        min_value = min_value.min(value);
        max_value = max_value.max(value);
        sum += value as u64;
        sample_count += 1;
        if value != 0 {
            nonzero_samples += 1;
        }
        sample_index = sample_index.saturating_add(step);
    }

    let mean_x1000 = if sample_count == 0 {
        0
    } else {
        ((sum * 1000) / sample_count as u64) as u32
    };

    TexturePlaneContentStats {
        format,
        readable: true,
        data_present: true,
        width,
        height,
        len: data.len(),
        updated: texture_updated_label(updated),
        sample_count,
        min: min_value,
        max: max_value,
        mean_x1000,
        nonzero_samples,
    }
}

fn texture_updated_label(updated: &TextureUpdated) -> &'static str {
    match updated {
        TextureUpdated::Empty => "empty",
        TextureUpdated::Partial(_) => "partial",
        TextureUpdated::Full => "full",
    }
}

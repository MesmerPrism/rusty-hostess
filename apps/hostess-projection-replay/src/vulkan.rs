use std::{
    ffi::{CStr, CString},
    fs,
    io::Cursor,
    mem,
    path::{Path, PathBuf},
    ptr,
    sync::Arc,
    time::Instant,
};

use anyhow::{anyhow, bail, Context, Result};
use ash::{util::read_spv, vk, Entry};
use image::{DynamicImage, GenericImageView, ImageBuffer, Rgba, RgbaImage};

use crate::{
    capsule::{
        resolve_path, AdapterReport, ColorInput, DepthInput, OutputReport, ReplayCapsule,
        SyntheticPattern,
    },
    sha256_file,
};

const GUIDE_TARGET_COUNT: usize = 5;
const GUIDE_OUTPUT_SCHEDULE: [usize; 6] = [0, 1, 2, 3, 1, 4];
const GUIDE_NAMES: [&str; GUIDE_TARGET_COUNT] = [
    "guide-raw-brightness",
    "guide-blur-temp",
    "guide-preblur-brightness",
    "guide-raw-strength",
    "guide-blurred-strength",
];
const GRID_VERTEX_COUNT: u32 = 32 * 32 * 6;

pub struct RenderResult {
    pub adapter: AdapterReport,
    pub outputs: Vec<OutputReport>,
}

pub struct PreviewFrame {
    pub rgba: Vec<u8>,
    pub width: u32,
    pub height: u32,
    pub gpu_round_trip_ms: f64,
}

pub struct PreviewRenderer {
    // Resource handles must be destroyed before their backing images and
    // buffers. Field drop order intentionally preserves that dependency.
    _handles: VulkanHandles,
    owner: Arc<DeviceOwner>,
    base: PathBuf,
    camera_left: GpuImage,
    camera_right: GpuImage,
    video: GpuImage,
    depth: GpuImage,
    guide_images: Vec<GpuImage>,
    output_image: GpuImage,
    readback: GpuBuffer,
    rgb_uniform: GpuBuffer,
    displacement_uniform: GpuBuffer,
    zone_uniform: GpuBuffer,
    descriptor_sets: Vec<vk::DescriptorSet>,
    guide_render_pass: vk::RenderPass,
    output_render_pass: vk::RenderPass,
    guide_framebuffers: Vec<vk::Framebuffer>,
    output_framebuffer: vk::Framebuffer,
    guide_pipeline_layout: vk::PipelineLayout,
    projection_pipeline_layout: vk::PipelineLayout,
    guide_pipelines: Vec<vk::Pipeline>,
    fullscreen_projection_pipeline: vk::Pipeline,
    displacement_projection_pipeline: Option<vk::Pipeline>,
    linear_sampler: vk::Sampler,
    nearest_sampler: vk::Sampler,
    current_frame_index: Option<usize>,
}

struct InstanceOwner {
    _entry: Entry,
    instance: ash::Instance,
}

impl Drop for InstanceOwner {
    fn drop(&mut self) {
        unsafe {
            self.instance.destroy_instance(None);
        }
    }
}

struct DeviceOwner {
    _instance: Arc<InstanceOwner>,
    device: ash::Device,
    _physical_device: vk::PhysicalDevice,
    memory_properties: vk::PhysicalDeviceMemoryProperties,
    queue: vk::Queue,
    _queue_family: u32,
    command_pool: vk::CommandPool,
}

impl Drop for DeviceOwner {
    fn drop(&mut self) {
        unsafe {
            let _ = self.device.device_wait_idle();
            self.device.destroy_command_pool(self.command_pool, None);
            self.device.destroy_device(None);
        }
    }
}

struct GpuImage {
    owner: Arc<DeviceOwner>,
    image: vk::Image,
    memory: vk::DeviceMemory,
    view: vk::ImageView,
    width: u32,
    height: u32,
    layers: u32,
    format: vk::Format,
}

impl Drop for GpuImage {
    fn drop(&mut self) {
        unsafe {
            self.owner.device.destroy_image_view(self.view, None);
            self.owner.device.destroy_image(self.image, None);
            self.owner.device.free_memory(self.memory, None);
        }
    }
}

struct GpuBuffer {
    owner: Arc<DeviceOwner>,
    buffer: vk::Buffer,
    memory: vk::DeviceMemory,
    size: vk::DeviceSize,
}

impl Drop for GpuBuffer {
    fn drop(&mut self) {
        unsafe {
            self.owner.device.destroy_buffer(self.buffer, None);
            self.owner.device.free_memory(self.memory, None);
        }
    }
}

struct VulkanHandles {
    owner: Arc<DeviceOwner>,
    samplers: Vec<vk::Sampler>,
    descriptor_pool: vk::DescriptorPool,
    descriptor_set_layouts: Vec<vk::DescriptorSetLayout>,
    pipeline_layouts: Vec<vk::PipelineLayout>,
    pipelines: Vec<vk::Pipeline>,
    render_passes: Vec<vk::RenderPass>,
    framebuffers: Vec<vk::Framebuffer>,
}

impl Drop for VulkanHandles {
    fn drop(&mut self) {
        unsafe {
            for framebuffer in self.framebuffers.drain(..) {
                self.owner.device.destroy_framebuffer(framebuffer, None);
            }
            for pipeline in self.pipelines.drain(..) {
                self.owner.device.destroy_pipeline(pipeline, None);
            }
            for layout in self.pipeline_layouts.drain(..) {
                self.owner.device.destroy_pipeline_layout(layout, None);
            }
            for render_pass in self.render_passes.drain(..) {
                self.owner.device.destroy_render_pass(render_pass, None);
            }
            if self.descriptor_pool != vk::DescriptorPool::null() {
                self.owner
                    .device
                    .destroy_descriptor_pool(self.descriptor_pool, None);
            }
            for layout in self.descriptor_set_layouts.drain(..) {
                self.owner
                    .device
                    .destroy_descriptor_set_layout(layout, None);
            }
            for sampler in self.samplers.drain(..) {
                self.owner.device.destroy_sampler(sampler, None);
            }
        }
    }
}

pub fn render_capsule(
    capsule: &ReplayCapsule,
    capsule_path: &Path,
    output_dir: &Path,
    adapter_filter: Option<&str>,
) -> Result<RenderResult> {
    let (owner, adapter) = create_device(adapter_filter)?;
    let base = capsule_path.parent().unwrap_or_else(|| Path::new("."));

    let camera_width = capsule.extent.width / 2;
    let camera_height = capsule.extent.height;
    let left_rgba = load_color_input(
        &capsule.inputs.camera_left,
        base,
        camera_width,
        camera_height,
    )?;
    let right_rgba = load_color_input(
        &capsule.inputs.camera_right,
        base,
        camera_width,
        camera_height,
    )?;
    let video_rgba = load_color_input(
        &capsule.inputs.video,
        base,
        capsule.extent.width,
        capsule.extent.height,
    )?;
    let depth_values = load_depth_input(
        &capsule.inputs.depth,
        base,
        capsule.extent.width,
        capsule.extent.height,
    )?;

    let camera_left = upload_rgba_image(&owner, &left_rgba)?;
    let camera_right = upload_rgba_image(&owner, &right_rgba)?;
    let video = upload_rgba_image(&owner, &video_rgba)?;
    let depth = upload_depth_array(
        &owner,
        capsule.extent.width,
        capsule.extent.height,
        &depth_values,
    )?;

    let guide_render_pass = create_render_pass(
        &owner.device,
        vk::Format::R8G8B8A8_UNORM,
        vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL,
    )?;
    let output_render_pass = create_render_pass(
        &owner.device,
        vk::Format::R8G8B8A8_UNORM,
        vk::ImageLayout::TRANSFER_SRC_OPTIMAL,
    )?;

    let guide_images = (0..GUIDE_TARGET_COUNT)
        .map(|_| {
            create_image(
                &owner,
                capsule.extent.width,
                capsule.extent.height,
                1,
                vk::Format::R8G8B8A8_UNORM,
                vk::ImageUsageFlags::COLOR_ATTACHMENT
                    | vk::ImageUsageFlags::SAMPLED
                    | vk::ImageUsageFlags::TRANSFER_SRC,
                vk::ImageViewType::TYPE_2D,
            )
        })
        .collect::<Result<Vec<_>>>()?;
    let guide_framebuffers = guide_images
        .iter()
        .map(|image| create_framebuffer(&owner.device, guide_render_pass, image))
        .collect::<Result<Vec<_>>>()?;

    let linear_sampler = create_sampler(&owner.device, vk::Filter::LINEAR)?;
    let nearest_sampler = create_sampler(&owner.device, vk::Filter::NEAREST)?;
    let layouts = create_descriptor_set_layouts(&owner.device)?;
    let descriptor_pool = create_descriptor_pool(&owner.device)?;
    let descriptor_sets = allocate_descriptor_sets(&owner.device, descriptor_pool, &layouts)?;

    let rgb_uniform = create_uniform_buffer(&owner, &capsule.projection.rgb_uniform)?;
    let displacement_uniform = create_uniform_buffer(&owner, capsule.projection_surface_uniform())?;
    let zone_uniform = create_uniform_buffer(&owner, &capsule.projection.zone_uniform)?;
    write_descriptor_sets(
        &owner.device,
        &descriptor_sets,
        linear_sampler,
        nearest_sampler,
        &camera_left,
        &camera_right,
        &guide_images,
        &depth,
        &video,
        &rgb_uniform,
        &displacement_uniform,
        &zone_uniform,
    );

    let guide_pipeline_layout = create_pipeline_layout(
        &owner.device,
        &layouts[0..2],
        vk::ShaderStageFlags::FRAGMENT,
        112,
    )?;
    let projection_pipeline_layout = create_pipeline_layout(
        &owner.device,
        &layouts,
        vk::ShaderStageFlags::VERTEX | vk::ShaderStageFlags::FRAGMENT,
        128,
    )?;

    let fullscreen_module = load_shader_module(
        &owner.device,
        &resolve_path(base, &capsule.shaders.fullscreen_vertex_spirv),
    )?;
    let guide_modules = capsule
        .shaders
        .guide_fragment_spirv
        .iter()
        .map(|path| load_shader_module(&owner.device, &resolve_path(base, path)))
        .collect::<Result<Vec<_>>>()?;
    let projection_fragment = load_shader_module(
        &owner.device,
        &resolve_path(base, &capsule.shaders.projection_fragment_spirv),
    )?;
    let displacement_vertex = capsule
        .shaders
        .displacement_vertex_spirv
        .as_ref()
        .map(|path| load_shader_module(&owner.device, &resolve_path(base, path)))
        .transpose()?;

    let guide_pipelines = guide_modules
        .iter()
        .enumerate()
        .map(|(index, fragment)| {
            create_graphics_pipeline(
                &owner.device,
                guide_render_pass,
                guide_pipeline_layout,
                fullscreen_module,
                *fragment,
                false,
                &format!("guide-pass-{index}"),
            )
        })
        .collect::<Result<Vec<_>>>()?;
    let projection_vertex = if capsule.tessellated_projection_requested() {
        displacement_vertex.ok_or_else(|| anyhow!("displacement vertex shader is missing"))?
    } else {
        fullscreen_module
    };
    let projection_pipeline = create_graphics_pipeline(
        &owner.device,
        output_render_pass,
        projection_pipeline_layout,
        projection_vertex,
        projection_fragment,
        true,
        "projection",
    )?;

    unsafe {
        for module in guide_modules {
            owner.device.destroy_shader_module(module, None);
        }
        if let Some(module) = displacement_vertex {
            if module != fullscreen_module {
                owner.device.destroy_shader_module(module, None);
            }
        }
        owner
            .device
            .destroy_shader_module(projection_fragment, None);
        owner.device.destroy_shader_module(fullscreen_module, None);
    }

    let mut handles = VulkanHandles {
        owner: Arc::clone(&owner),
        samplers: vec![linear_sampler, nearest_sampler],
        descriptor_pool,
        descriptor_set_layouts: layouts,
        pipeline_layouts: vec![guide_pipeline_layout, projection_pipeline_layout],
        pipelines: guide_pipelines.clone(),
        render_passes: vec![guide_render_pass, output_render_pass],
        framebuffers: guide_framebuffers.clone(),
    };
    handles.pipelines.push(projection_pipeline);

    record_guide_passes(
        &owner,
        capsule,
        guide_render_pass,
        &guide_framebuffers,
        &guide_pipelines,
        guide_pipeline_layout,
        &descriptor_sets[0..2],
    )?;

    let mut output_reports = Vec::new();
    for (index, image) in guide_images.iter().enumerate() {
        let path = output_dir.join(format!("{}.png", GUIDE_NAMES[index]));
        let rgba = read_color_image(
            &owner,
            image,
            vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL,
            vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL,
        )?;
        save_rgba(&path, image.width, image.height, &rgba)?;
        output_reports.push(output_report(GUIDE_NAMES[index], &path, &rgba)?);
    }

    for output in &capsule.outputs {
        let output_image = create_image(
            &owner,
            capsule.extent.width,
            capsule.extent.height,
            1,
            vk::Format::R8G8B8A8_UNORM,
            vk::ImageUsageFlags::COLOR_ATTACHMENT | vk::ImageUsageFlags::TRANSFER_SRC,
            vk::ImageViewType::TYPE_2D,
        )?;
        let framebuffer = create_framebuffer(&owner.device, output_render_pass, &output_image)?;
        let rgba = render_output_layer(
            &owner,
            capsule,
            &output_image,
            output_render_pass,
            framebuffer,
            projection_pipeline,
            projection_pipeline_layout,
            &descriptor_sets,
            output.override_value,
        )?;
        unsafe {
            owner.device.destroy_framebuffer(framebuffer, None);
        }
        let path = output_dir.join(format!("{}.png", sanitize_name(&output.name)));
        save_rgba(&path, capsule.extent.width, capsule.extent.height, &rgba)?;
        output_reports.push(output_report(&output.name, &path, &rgba)?);
    }

    drop(handles);
    drop(zone_uniform);
    drop(displacement_uniform);
    drop(rgb_uniform);
    drop(guide_images);
    drop(depth);
    drop(video);
    drop(camera_right);
    drop(camera_left);

    Ok(RenderResult {
        adapter,
        outputs: output_reports,
    })
}

impl PreviewRenderer {
    pub fn new(
        capsule: &ReplayCapsule,
        capsule_path: &Path,
        adapter_filter: Option<&str>,
    ) -> Result<Self> {
        let (owner, _adapter) = create_device(adapter_filter)?;
        let base = capsule_path
            .parent()
            .unwrap_or_else(|| Path::new("."))
            .to_path_buf();
        let camera_width = capsule.extent.width / 2;
        let camera_height = capsule.extent.height;
        let left_rgba = load_color_input(
            &capsule.inputs.camera_left,
            &base,
            camera_width,
            camera_height,
        )?;
        let right_rgba = load_color_input(
            &capsule.inputs.camera_right,
            &base,
            camera_width,
            camera_height,
        )?;
        let video_rgba = load_color_input(
            &capsule.inputs.video,
            &base,
            capsule.extent.width,
            capsule.extent.height,
        )?;
        let depth_values = load_depth_input(
            &capsule.inputs.depth,
            &base,
            capsule.extent.width,
            capsule.extent.height,
        )?;

        let camera_left = upload_rgba_image(&owner, &left_rgba)?;
        let camera_right = upload_rgba_image(&owner, &right_rgba)?;
        let video = upload_rgba_image(&owner, &video_rgba)?;
        let depth = upload_depth_array(
            &owner,
            capsule.extent.width,
            capsule.extent.height,
            &depth_values,
        )?;
        let guide_render_pass = create_render_pass(
            &owner.device,
            vk::Format::R8G8B8A8_UNORM,
            vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL,
        )?;
        let output_render_pass = create_render_pass(
            &owner.device,
            vk::Format::R8G8B8A8_UNORM,
            vk::ImageLayout::TRANSFER_SRC_OPTIMAL,
        )?;
        let guide_images = (0..GUIDE_TARGET_COUNT)
            .map(|_| {
                create_image(
                    &owner,
                    capsule.extent.width,
                    capsule.extent.height,
                    1,
                    vk::Format::R8G8B8A8_UNORM,
                    vk::ImageUsageFlags::COLOR_ATTACHMENT | vk::ImageUsageFlags::SAMPLED,
                    vk::ImageViewType::TYPE_2D,
                )
            })
            .collect::<Result<Vec<_>>>()?;
        let output_image = create_image(
            &owner,
            capsule.extent.width,
            capsule.extent.height,
            1,
            vk::Format::R8G8B8A8_UNORM,
            vk::ImageUsageFlags::COLOR_ATTACHMENT | vk::ImageUsageFlags::TRANSFER_SRC,
            vk::ImageViewType::TYPE_2D,
        )?;
        let guide_framebuffers = guide_images
            .iter()
            .map(|image| create_framebuffer(&owner.device, guide_render_pass, image))
            .collect::<Result<Vec<_>>>()?;
        let output_framebuffer =
            create_framebuffer(&owner.device, output_render_pass, &output_image)?;
        let readback = create_buffer(
            &owner,
            output_image.width as u64 * output_image.height as u64 * 4,
            vk::BufferUsageFlags::TRANSFER_DST,
            vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT,
        )?;

        let linear_sampler = create_sampler(&owner.device, vk::Filter::LINEAR)?;
        let nearest_sampler = create_sampler(&owner.device, vk::Filter::NEAREST)?;
        let layouts = create_descriptor_set_layouts(&owner.device)?;
        let descriptor_pool = create_descriptor_pool(&owner.device)?;
        let descriptor_sets = allocate_descriptor_sets(&owner.device, descriptor_pool, &layouts)?;
        let rgb_uniform = create_uniform_buffer(&owner, &capsule.projection.rgb_uniform)?;
        let displacement_uniform =
            create_uniform_buffer(&owner, capsule.projection_surface_uniform())?;
        let zone_uniform = create_uniform_buffer(&owner, &capsule.projection.zone_uniform)?;
        write_descriptor_sets(
            &owner.device,
            &descriptor_sets,
            linear_sampler,
            nearest_sampler,
            &camera_left,
            &camera_right,
            &guide_images,
            &depth,
            &video,
            &rgb_uniform,
            &displacement_uniform,
            &zone_uniform,
        );

        let guide_pipeline_layout = create_pipeline_layout(
            &owner.device,
            &layouts[0..2],
            vk::ShaderStageFlags::FRAGMENT,
            112,
        )?;
        let projection_pipeline_layout = create_pipeline_layout(
            &owner.device,
            &layouts,
            vk::ShaderStageFlags::VERTEX | vk::ShaderStageFlags::FRAGMENT,
            128,
        )?;
        let fullscreen_module = load_shader_module(
            &owner.device,
            &resolve_path(&base, &capsule.shaders.fullscreen_vertex_spirv),
        )?;
        let guide_modules = capsule
            .shaders
            .guide_fragment_spirv
            .iter()
            .map(|path| load_shader_module(&owner.device, &resolve_path(&base, path)))
            .collect::<Result<Vec<_>>>()?;
        let projection_fragment = load_shader_module(
            &owner.device,
            &resolve_path(&base, &capsule.shaders.projection_fragment_spirv),
        )?;
        let displacement_vertex = capsule
            .shaders
            .displacement_vertex_spirv
            .as_ref()
            .map(|path| load_shader_module(&owner.device, &resolve_path(&base, path)))
            .transpose()?;
        let guide_pipelines = guide_modules
            .iter()
            .enumerate()
            .map(|(index, fragment)| {
                create_graphics_pipeline(
                    &owner.device,
                    guide_render_pass,
                    guide_pipeline_layout,
                    fullscreen_module,
                    *fragment,
                    false,
                    &format!("preview-guide-pass-{index}"),
                )
            })
            .collect::<Result<Vec<_>>>()?;
        let fullscreen_projection_pipeline = create_graphics_pipeline(
            &owner.device,
            output_render_pass,
            projection_pipeline_layout,
            fullscreen_module,
            projection_fragment,
            true,
            "preview-projection-fullscreen",
        )?;
        let displacement_projection_pipeline = displacement_vertex
            .map(|vertex| {
                create_graphics_pipeline(
                    &owner.device,
                    output_render_pass,
                    projection_pipeline_layout,
                    vertex,
                    projection_fragment,
                    true,
                    "preview-projection-displacement",
                )
            })
            .transpose()?;

        unsafe {
            for module in guide_modules {
                owner.device.destroy_shader_module(module, None);
            }
            if let Some(module) = displacement_vertex {
                owner.device.destroy_shader_module(module, None);
            }
            owner
                .device
                .destroy_shader_module(projection_fragment, None);
            owner.device.destroy_shader_module(fullscreen_module, None);
        }

        let mut pipelines = guide_pipelines.clone();
        pipelines.push(fullscreen_projection_pipeline);
        if let Some(pipeline) = displacement_projection_pipeline {
            pipelines.push(pipeline);
        }
        let mut framebuffers = guide_framebuffers.clone();
        framebuffers.push(output_framebuffer);
        let handles = VulkanHandles {
            owner: Arc::clone(&owner),
            samplers: vec![linear_sampler, nearest_sampler],
            descriptor_pool,
            descriptor_set_layouts: layouts,
            pipeline_layouts: vec![guide_pipeline_layout, projection_pipeline_layout],
            pipelines,
            render_passes: vec![guide_render_pass, output_render_pass],
            framebuffers,
        };

        Ok(Self {
            _handles: handles,
            owner,
            base,
            camera_left,
            camera_right,
            video,
            depth,
            guide_images,
            output_image,
            readback,
            rgb_uniform,
            displacement_uniform,
            zone_uniform,
            descriptor_sets,
            guide_render_pass,
            output_render_pass,
            guide_framebuffers,
            output_framebuffer,
            guide_pipeline_layout,
            projection_pipeline_layout,
            guide_pipelines,
            fullscreen_projection_pipeline,
            displacement_projection_pipeline,
            linear_sampler,
            nearest_sampler,
            current_frame_index: None,
        })
    }

    pub fn render(&mut self, capsule: &ReplayCapsule, frame_index: usize) -> Result<PreviewFrame> {
        if capsule.extent.width != self.output_image.width
            || capsule.extent.height != self.output_image.height
        {
            bail!("preview capsule extent changed after renderer initialization");
        }
        if self.current_frame_index != Some(frame_index) {
            self.replace_inputs(capsule)?;
            self.current_frame_index = Some(frame_index);
        }
        write_buffer(
            &self.rgb_uniform,
            f32_slice_as_bytes(&capsule.projection.rgb_uniform),
        )?;
        write_buffer(
            &self.displacement_uniform,
            f32_slice_as_bytes(capsule.projection_surface_uniform()),
        )?;
        write_buffer(
            &self.zone_uniform,
            f32_slice_as_bytes(&capsule.projection.zone_uniform),
        )?;

        let projection_pipeline = if capsule.tessellated_projection_requested() {
            self.displacement_projection_pipeline
                .context("preview capsule requested tessellation without a vertex pipeline")?
        } else {
            self.fullscreen_projection_pipeline
        };
        let override_value = capsule
            .outputs
            .first()
            .context("preview capsule has no selected output")?
            .override_value;
        let started = Instant::now();
        immediate(&self.owner, |command| {
            record_guide_commands(
                &self.owner,
                capsule,
                command,
                self.guide_render_pass,
                &self.guide_framebuffers,
                &self.guide_pipelines,
                self.guide_pipeline_layout,
                &self.descriptor_sets[0..2],
            );
            record_output_commands(
                &self.owner,
                capsule,
                command,
                &self.output_image,
                self.output_render_pass,
                self.output_framebuffer,
                projection_pipeline,
                self.projection_pipeline_layout,
                &self.descriptor_sets,
                override_value,
                &self.readback,
            );
            Ok(())
        })?;
        let rgba = read_buffer(&self.readback)?;
        Ok(PreviewFrame {
            rgba,
            width: self.output_image.width,
            height: self.output_image.height,
            gpu_round_trip_ms: started.elapsed().as_secs_f64() * 1000.0,
        })
    }

    fn replace_inputs(&mut self, capsule: &ReplayCapsule) -> Result<()> {
        let camera_width = capsule.extent.width / 2;
        let camera_height = capsule.extent.height;
        let left_rgba = load_color_input(
            &capsule.inputs.camera_left,
            &self.base,
            camera_width,
            camera_height,
        )?;
        let right_rgba = load_color_input(
            &capsule.inputs.camera_right,
            &self.base,
            camera_width,
            camera_height,
        )?;
        let video_rgba = load_color_input(
            &capsule.inputs.video,
            &self.base,
            capsule.extent.width,
            capsule.extent.height,
        )?;
        let new_left = upload_rgba_image(&self.owner, &left_rgba)?;
        let new_right = upload_rgba_image(&self.owner, &right_rgba)?;
        let new_video = upload_rgba_image(&self.owner, &video_rgba)?;
        let old_left = mem::replace(&mut self.camera_left, new_left);
        let old_right = mem::replace(&mut self.camera_right, new_right);
        let old_video = mem::replace(&mut self.video, new_video);
        write_descriptor_sets(
            &self.owner.device,
            &self.descriptor_sets,
            self.linear_sampler,
            self.nearest_sampler,
            &self.camera_left,
            &self.camera_right,
            &self.guide_images,
            &self.depth,
            &self.video,
            &self.rgb_uniform,
            &self.displacement_uniform,
            &self.zone_uniform,
        );
        drop(old_video);
        drop(old_right);
        drop(old_left);
        Ok(())
    }
}

fn create_device(adapter_filter: Option<&str>) -> Result<(Arc<DeviceOwner>, AdapterReport)> {
    let entry = unsafe { Entry::load() }.context("failed to load Vulkan loader")?;
    let app_name = CString::new("hostess-projection-replay")?;
    let app_info = vk::ApplicationInfo::default()
        .application_name(&app_name)
        .application_version(1)
        .engine_name(&app_name)
        .engine_version(1)
        .api_version(vk::make_api_version(0, 1, 1, 0));
    let instance = unsafe {
        entry.create_instance(
            &vk::InstanceCreateInfo::default().application_info(&app_info),
            None,
        )
    }
    .context("failed to create Vulkan instance")?;
    let instance = Arc::new(InstanceOwner {
        _entry: entry,
        instance,
    });
    let filter = adapter_filter.map(str::to_lowercase);
    let mut candidates = unsafe { instance.instance.enumerate_physical_devices() }
        .context("failed to enumerate Vulkan devices")?
        .into_iter()
        .filter_map(|physical| {
            let properties = unsafe { instance.instance.get_physical_device_properties(physical) };
            let name = unsafe { CStr::from_ptr(properties.device_name.as_ptr()) }
                .to_string_lossy()
                .into_owned();
            if filter
                .as_ref()
                .is_some_and(|filter| !name.to_lowercase().contains(filter))
            {
                return None;
            }
            let queue_family = unsafe {
                instance
                    .instance
                    .get_physical_device_queue_family_properties(physical)
            }
            .iter()
            .enumerate()
            .find(|(_, family)| family.queue_flags.contains(vk::QueueFlags::GRAPHICS))
            .map(|(index, _)| index as u32)?;
            let score = match properties.device_type {
                vk::PhysicalDeviceType::DISCRETE_GPU => 3,
                vk::PhysicalDeviceType::INTEGRATED_GPU => 2,
                vk::PhysicalDeviceType::VIRTUAL_GPU => 1,
                _ => 0,
            };
            Some((score, physical, queue_family, properties, name))
        })
        .collect::<Vec<_>>();
    candidates.sort_by_key(|candidate| candidate.0);
    let (_, physical_device, queue_family, properties, name) = candidates
        .pop()
        .ok_or_else(|| anyhow!("no Vulkan graphics adapter matched the requested filter"))?;
    let queue_priorities = [1.0_f32];
    let queue_info = [vk::DeviceQueueCreateInfo::default()
        .queue_family_index(queue_family)
        .queue_priorities(&queue_priorities)];
    let device = unsafe {
        instance.instance.create_device(
            physical_device,
            &vk::DeviceCreateInfo::default().queue_create_infos(&queue_info),
            None,
        )
    }
    .with_context(|| format!("failed to create Vulkan device for {name}"))?;
    let queue = unsafe { device.get_device_queue(queue_family, 0) };
    let command_pool = unsafe {
        device.create_command_pool(
            &vk::CommandPoolCreateInfo::default()
                .queue_family_index(queue_family)
                .flags(vk::CommandPoolCreateFlags::RESET_COMMAND_BUFFER),
            None,
        )
    }
    .context("failed to create Vulkan command pool")?;
    let memory_properties = unsafe {
        instance
            .instance
            .get_physical_device_memory_properties(physical_device)
    };
    let adapter = AdapterReport {
        name,
        vendor_id: properties.vendor_id,
        device_id: properties.device_id,
        api_version: format_api_version(properties.api_version),
        driver_version: properties.driver_version,
        device_type: format!("{:?}", properties.device_type).to_lowercase(),
    };
    Ok((
        Arc::new(DeviceOwner {
            _instance: instance,
            device,
            _physical_device: physical_device,
            memory_properties,
            queue,
            _queue_family: queue_family,
            command_pool,
        }),
        adapter,
    ))
}

fn format_api_version(version: u32) -> String {
    format!(
        "{}.{}.{}",
        vk::api_version_major(version),
        vk::api_version_minor(version),
        vk::api_version_patch(version)
    )
}

fn load_color_input(input: &ColorInput, base: &Path, width: u32, height: u32) -> Result<RgbaImage> {
    match input {
        ColorInput::Png { path } => {
            let path = resolve_path(base, path);
            let image = image::open(&path)
                .with_context(|| format!("failed to load input PNG {}", path.display()))?
                .to_rgba8();
            if image.dimensions() != (width, height) {
                bail!(
                    "input {} is {}x{}, expected {}x{}",
                    path.display(),
                    image.width(),
                    image.height(),
                    width,
                    height
                );
            }
            Ok(image)
        }
        ColorInput::PngSequence { paths } => {
            let path = paths.first().context("video PNG sequence is empty")?;
            let path = resolve_path(base, path);
            let image = image::open(&path)
                .with_context(|| format!("failed to load input PNG {}", path.display()))?
                .to_rgba8();
            if image.dimensions() != (width, height) {
                bail!(
                    "input {} is {}x{}, expected {}x{}",
                    path.display(),
                    image.width(),
                    image.height(),
                    width,
                    height
                );
            }
            Ok(image)
        }
        ColorInput::Synthetic { pattern, variant } => {
            Ok(generate_synthetic(*pattern, *variant, width, height))
        }
        ColorInput::Transparent => Ok(RgbaImage::new(width, height)),
    }
}

fn generate_synthetic(
    pattern: SyntheticPattern,
    variant: u32,
    width: u32,
    height: u32,
) -> RgbaImage {
    ImageBuffer::from_fn(width, height, |x, y| {
        let u = x as f32 / width.saturating_sub(1).max(1) as f32;
        let v = y as f32 / height.saturating_sub(1).max(1) as f32;
        let shift = (variant % 4) as f32 * 0.125;
        let color = match pattern {
            SyntheticPattern::RgbQuadrants => {
                let quadrant = (u >= 0.5) as usize + 2 * (v >= 0.5) as usize;
                [[255, 24, 24], [24, 255, 24], [24, 24, 255], [255, 220, 24]][quadrant]
            }
            SyntheticPattern::RgbBands => {
                let band = (((u + shift).fract()) * 6.0).floor() as usize % 6;
                [
                    [255, 16, 16],
                    [255, 220, 16],
                    [16, 255, 16],
                    [16, 255, 255],
                    [16, 16, 255],
                    [255, 16, 255],
                ][band]
            }
            SyntheticPattern::RadialRings => {
                let dx = u - 0.5;
                let dy = v - 0.5;
                let ring = ((dx.hypot(dy) * 18.0 + shift * 4.0).floor() as usize) % 3;
                [[255, 32, 32], [32, 255, 32], [32, 32, 255]][ring]
            }
            SyntheticPattern::UvGradient => [
                (u * 255.0).round() as u8,
                (v * 255.0).round() as u8,
                (((1.0 - u) * (1.0 - v)) * 255.0).round() as u8,
            ],
        };
        Rgba([color[0], color[1], color[2], 255])
    })
}

fn load_depth_input(input: &DepthInput, base: &Path, width: u32, height: u32) -> Result<Vec<f32>> {
    let layer_len = (width as usize) * (height as usize);
    let one_layer = match input {
        DepthInput::Constant { meters } => {
            if !meters.is_finite() || *meters <= 0.0 {
                bail!("constant depth must be finite and positive");
            }
            vec![*meters; layer_len]
        }
        DepthInput::HorizontalRamp { near_m, far_m } => {
            if !near_m.is_finite() || !far_m.is_finite() || *near_m <= 0.0 || *far_m <= *near_m {
                bail!("depth ramp requires 0 < near_m < far_m");
            }
            (0..height)
                .flat_map(|_| {
                    (0..width).map(|x| {
                        let t = x as f32 / width.saturating_sub(1).max(1) as f32;
                        near_m + (far_m - near_m) * t
                    })
                })
                .collect()
        }
        DepthInput::Png16 {
            path,
            near_m,
            far_m,
        } => {
            let path = resolve_path(base, path);
            let image = image::open(&path)
                .with_context(|| format!("failed to load depth PNG {}", path.display()))?;
            if image.dimensions() != (width, height) {
                bail!(
                    "depth input {} is {}x{}, expected {}x{}",
                    path.display(),
                    image.width(),
                    image.height(),
                    width,
                    height
                );
            }
            let luma = image.to_luma16();
            luma.pixels()
                .map(|pixel| {
                    let t = pixel.0[0] as f32 / u16::MAX as f32;
                    near_m + (far_m - near_m) * t
                })
                .collect()
        }
    };
    let mut stereo = Vec::with_capacity(layer_len * 2);
    stereo.extend_from_slice(&one_layer);
    stereo.extend_from_slice(&one_layer);
    Ok(stereo)
}

fn upload_rgba_image(owner: &Arc<DeviceOwner>, rgba: &RgbaImage) -> Result<GpuImage> {
    let image = create_image(
        owner,
        rgba.width(),
        rgba.height(),
        1,
        vk::Format::R8G8B8A8_UNORM,
        vk::ImageUsageFlags::TRANSFER_DST | vk::ImageUsageFlags::SAMPLED,
        vk::ImageViewType::TYPE_2D,
    )?;
    let staging = create_buffer(
        owner,
        rgba.as_raw().len() as u64,
        vk::BufferUsageFlags::TRANSFER_SRC,
        vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT,
    )?;
    write_buffer(&staging, rgba.as_raw())?;
    immediate(owner, |command| unsafe {
        transition_image(
            &owner.device,
            command,
            image.image,
            vk::ImageAspectFlags::COLOR,
            1,
            vk::ImageLayout::UNDEFINED,
            vk::ImageLayout::TRANSFER_DST_OPTIMAL,
        );
        let region = [vk::BufferImageCopy::default()
            .buffer_offset(0)
            .buffer_row_length(0)
            .buffer_image_height(0)
            .image_subresource(
                vk::ImageSubresourceLayers::default()
                    .aspect_mask(vk::ImageAspectFlags::COLOR)
                    .mip_level(0)
                    .base_array_layer(0)
                    .layer_count(1),
            )
            .image_extent(vk::Extent3D {
                width: image.width,
                height: image.height,
                depth: 1,
            })];
        owner.device.cmd_copy_buffer_to_image(
            command,
            staging.buffer,
            image.image,
            vk::ImageLayout::TRANSFER_DST_OPTIMAL,
            &region,
        );
        transition_image(
            &owner.device,
            command,
            image.image,
            vk::ImageAspectFlags::COLOR,
            1,
            vk::ImageLayout::TRANSFER_DST_OPTIMAL,
            vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL,
        );
        Ok(())
    })?;
    Ok(image)
}

fn upload_depth_array(
    owner: &Arc<DeviceOwner>,
    width: u32,
    height: u32,
    depth: &[f32],
) -> Result<GpuImage> {
    if depth.len() != width as usize * height as usize * 2 {
        bail!("depth array must contain exactly two packed layers");
    }
    let image = create_image(
        owner,
        width,
        height,
        2,
        vk::Format::R32_SFLOAT,
        vk::ImageUsageFlags::TRANSFER_DST | vk::ImageUsageFlags::SAMPLED,
        vk::ImageViewType::TYPE_2D_ARRAY,
    )?;
    let bytes = f32_slice_as_bytes(depth);
    let staging = create_buffer(
        owner,
        bytes.len() as u64,
        vk::BufferUsageFlags::TRANSFER_SRC,
        vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT,
    )?;
    write_buffer(&staging, bytes)?;
    immediate(owner, |command| unsafe {
        transition_image(
            &owner.device,
            command,
            image.image,
            vk::ImageAspectFlags::COLOR,
            2,
            vk::ImageLayout::UNDEFINED,
            vk::ImageLayout::TRANSFER_DST_OPTIMAL,
        );
        let region = [vk::BufferImageCopy::default()
            .image_subresource(
                vk::ImageSubresourceLayers::default()
                    .aspect_mask(vk::ImageAspectFlags::COLOR)
                    .mip_level(0)
                    .base_array_layer(0)
                    .layer_count(2),
            )
            .image_extent(vk::Extent3D {
                width,
                height,
                depth: 1,
            })];
        owner.device.cmd_copy_buffer_to_image(
            command,
            staging.buffer,
            image.image,
            vk::ImageLayout::TRANSFER_DST_OPTIMAL,
            &region,
        );
        transition_image(
            &owner.device,
            command,
            image.image,
            vk::ImageAspectFlags::COLOR,
            2,
            vk::ImageLayout::TRANSFER_DST_OPTIMAL,
            vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL,
        );
        Ok(())
    })?;
    Ok(image)
}

fn create_image(
    owner: &Arc<DeviceOwner>,
    width: u32,
    height: u32,
    layers: u32,
    format: vk::Format,
    usage: vk::ImageUsageFlags,
    view_type: vk::ImageViewType,
) -> Result<GpuImage> {
    let image_info = vk::ImageCreateInfo::default()
        .image_type(vk::ImageType::TYPE_2D)
        .format(format)
        .extent(vk::Extent3D {
            width,
            height,
            depth: 1,
        })
        .mip_levels(1)
        .array_layers(layers)
        .samples(vk::SampleCountFlags::TYPE_1)
        .tiling(vk::ImageTiling::OPTIMAL)
        .usage(usage)
        .sharing_mode(vk::SharingMode::EXCLUSIVE)
        .initial_layout(vk::ImageLayout::UNDEFINED);
    let image = unsafe { owner.device.create_image(&image_info, None) }
        .context("failed to create Vulkan image")?;
    let requirements = unsafe { owner.device.get_image_memory_requirements(image) };
    let memory_type = find_memory_type(
        &owner.memory_properties,
        requirements.memory_type_bits,
        vk::MemoryPropertyFlags::DEVICE_LOCAL,
    )?;
    let memory = match unsafe {
        owner.device.allocate_memory(
            &vk::MemoryAllocateInfo::default()
                .allocation_size(requirements.size)
                .memory_type_index(memory_type),
            None,
        )
    } {
        Ok(memory) => memory,
        Err(error) => {
            unsafe { owner.device.destroy_image(image, None) };
            return Err(error).context("failed to allocate Vulkan image memory");
        }
    };
    if let Err(error) = unsafe { owner.device.bind_image_memory(image, memory, 0) } {
        unsafe {
            owner.device.free_memory(memory, None);
            owner.device.destroy_image(image, None);
        }
        return Err(error).context("failed to bind Vulkan image memory");
    }
    let view = match unsafe {
        owner.device.create_image_view(
            &vk::ImageViewCreateInfo::default()
                .image(image)
                .view_type(view_type)
                .format(format)
                .subresource_range(
                    vk::ImageSubresourceRange::default()
                        .aspect_mask(vk::ImageAspectFlags::COLOR)
                        .base_mip_level(0)
                        .level_count(1)
                        .base_array_layer(0)
                        .layer_count(layers),
                ),
            None,
        )
    } {
        Ok(view) => view,
        Err(error) => {
            unsafe {
                owner.device.free_memory(memory, None);
                owner.device.destroy_image(image, None);
            }
            return Err(error).context("failed to create Vulkan image view");
        }
    };
    Ok(GpuImage {
        owner: Arc::clone(owner),
        image,
        memory,
        view,
        width,
        height,
        layers,
        format,
    })
}

fn create_buffer(
    owner: &Arc<DeviceOwner>,
    size: vk::DeviceSize,
    usage: vk::BufferUsageFlags,
    properties: vk::MemoryPropertyFlags,
) -> Result<GpuBuffer> {
    let buffer = unsafe {
        owner.device.create_buffer(
            &vk::BufferCreateInfo::default()
                .size(size)
                .usage(usage)
                .sharing_mode(vk::SharingMode::EXCLUSIVE),
            None,
        )
    }
    .context("failed to create Vulkan buffer")?;
    let requirements = unsafe { owner.device.get_buffer_memory_requirements(buffer) };
    let memory_type = find_memory_type(
        &owner.memory_properties,
        requirements.memory_type_bits,
        properties,
    )?;
    let memory = match unsafe {
        owner.device.allocate_memory(
            &vk::MemoryAllocateInfo::default()
                .allocation_size(requirements.size)
                .memory_type_index(memory_type),
            None,
        )
    } {
        Ok(memory) => memory,
        Err(error) => {
            unsafe { owner.device.destroy_buffer(buffer, None) };
            return Err(error).context("failed to allocate Vulkan buffer memory");
        }
    };
    if let Err(error) = unsafe { owner.device.bind_buffer_memory(buffer, memory, 0) } {
        unsafe {
            owner.device.free_memory(memory, None);
            owner.device.destroy_buffer(buffer, None);
        }
        return Err(error).context("failed to bind Vulkan buffer memory");
    }
    Ok(GpuBuffer {
        owner: Arc::clone(owner),
        buffer,
        memory,
        size,
    })
}

fn create_uniform_buffer(owner: &Arc<DeviceOwner>, values: &[f32]) -> Result<GpuBuffer> {
    let bytes = f32_slice_as_bytes(values);
    let buffer = create_buffer(
        owner,
        bytes.len() as u64,
        vk::BufferUsageFlags::UNIFORM_BUFFER,
        vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT,
    )?;
    write_buffer(&buffer, bytes)?;
    Ok(buffer)
}

fn write_buffer(buffer: &GpuBuffer, bytes: &[u8]) -> Result<()> {
    if bytes.len() as u64 > buffer.size {
        bail!("buffer write exceeds allocation");
    }
    let mapped = unsafe {
        buffer.owner.device.map_memory(
            buffer.memory,
            0,
            bytes.len() as u64,
            vk::MemoryMapFlags::empty(),
        )
    }
    .context("failed to map Vulkan buffer")?;
    unsafe {
        ptr::copy_nonoverlapping(bytes.as_ptr(), mapped.cast::<u8>(), bytes.len());
        buffer.owner.device.unmap_memory(buffer.memory);
    }
    Ok(())
}

fn read_buffer(buffer: &GpuBuffer) -> Result<Vec<u8>> {
    let mapped = unsafe {
        buffer
            .owner
            .device
            .map_memory(buffer.memory, 0, buffer.size, vk::MemoryMapFlags::empty())
    }
    .context("failed to map Vulkan readback buffer")?;
    let bytes =
        unsafe { std::slice::from_raw_parts(mapped.cast::<u8>(), buffer.size as usize).to_vec() };
    unsafe {
        buffer.owner.device.unmap_memory(buffer.memory);
    }
    Ok(bytes)
}

fn find_memory_type(
    properties: &vk::PhysicalDeviceMemoryProperties,
    allowed_bits: u32,
    required: vk::MemoryPropertyFlags,
) -> Result<u32> {
    (0..properties.memory_type_count)
        .find(|index| {
            allowed_bits & (1 << index) != 0
                && properties.memory_types[*index as usize]
                    .property_flags
                    .contains(required)
        })
        .ok_or_else(|| anyhow!("no compatible Vulkan memory type for {required:?}"))
}

fn immediate<F>(owner: &Arc<DeviceOwner>, record: F) -> Result<()>
where
    F: FnOnce(vk::CommandBuffer) -> Result<()>,
{
    let command = unsafe {
        owner.device.allocate_command_buffers(
            &vk::CommandBufferAllocateInfo::default()
                .command_pool(owner.command_pool)
                .level(vk::CommandBufferLevel::PRIMARY)
                .command_buffer_count(1),
        )
    }
    .context("failed to allocate Vulkan command buffer")?[0];
    let result = (|| {
        unsafe {
            owner.device.begin_command_buffer(
                command,
                &vk::CommandBufferBeginInfo::default()
                    .flags(vk::CommandBufferUsageFlags::ONE_TIME_SUBMIT),
            )
        }
        .context("failed to begin Vulkan command buffer")?;
        record(command)?;
        unsafe { owner.device.end_command_buffer(command) }
            .context("failed to end Vulkan command buffer")?;
        let command_buffers = [command];
        let fence = unsafe {
            owner
                .device
                .create_fence(&vk::FenceCreateInfo::default(), None)
        }
        .context("failed to create Vulkan fence")?;
        let submit = [vk::SubmitInfo::default().command_buffers(&command_buffers)];
        let submit_result = unsafe { owner.device.queue_submit(owner.queue, &submit, fence) };
        if let Err(error) = submit_result {
            unsafe { owner.device.destroy_fence(fence, None) };
            return Err(error).context("failed to submit Vulkan command buffer");
        }
        let wait_result = unsafe { owner.device.wait_for_fences(&[fence], true, u64::MAX) };
        unsafe { owner.device.destroy_fence(fence, None) };
        wait_result.context("failed to wait for Vulkan command buffer")?;
        Ok(())
    })();
    unsafe {
        owner
            .device
            .free_command_buffers(owner.command_pool, &[command]);
    }
    result
}

unsafe fn transition_image(
    device: &ash::Device,
    command: vk::CommandBuffer,
    image: vk::Image,
    aspect: vk::ImageAspectFlags,
    layers: u32,
    old_layout: vk::ImageLayout,
    new_layout: vk::ImageLayout,
) {
    let (source_stage, source_access) = layout_source(old_layout);
    let (destination_stage, destination_access) = layout_destination(new_layout);
    let barrier = [vk::ImageMemoryBarrier::default()
        .src_access_mask(source_access)
        .dst_access_mask(destination_access)
        .old_layout(old_layout)
        .new_layout(new_layout)
        .src_queue_family_index(vk::QUEUE_FAMILY_IGNORED)
        .dst_queue_family_index(vk::QUEUE_FAMILY_IGNORED)
        .image(image)
        .subresource_range(
            vk::ImageSubresourceRange::default()
                .aspect_mask(aspect)
                .base_mip_level(0)
                .level_count(1)
                .base_array_layer(0)
                .layer_count(layers),
        )];
    device.cmd_pipeline_barrier(
        command,
        source_stage,
        destination_stage,
        vk::DependencyFlags::empty(),
        &[],
        &[],
        &barrier,
    );
}

fn layout_source(layout: vk::ImageLayout) -> (vk::PipelineStageFlags, vk::AccessFlags) {
    match layout {
        vk::ImageLayout::UNDEFINED => (
            vk::PipelineStageFlags::TOP_OF_PIPE,
            vk::AccessFlags::empty(),
        ),
        vk::ImageLayout::TRANSFER_DST_OPTIMAL => (
            vk::PipelineStageFlags::TRANSFER,
            vk::AccessFlags::TRANSFER_WRITE,
        ),
        vk::ImageLayout::TRANSFER_SRC_OPTIMAL => (
            vk::PipelineStageFlags::TRANSFER,
            vk::AccessFlags::TRANSFER_READ,
        ),
        vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL => (
            vk::PipelineStageFlags::FRAGMENT_SHADER,
            vk::AccessFlags::SHADER_READ,
        ),
        _ => (
            vk::PipelineStageFlags::ALL_COMMANDS,
            vk::AccessFlags::MEMORY_READ | vk::AccessFlags::MEMORY_WRITE,
        ),
    }
}

fn layout_destination(layout: vk::ImageLayout) -> (vk::PipelineStageFlags, vk::AccessFlags) {
    match layout {
        vk::ImageLayout::TRANSFER_DST_OPTIMAL => (
            vk::PipelineStageFlags::TRANSFER,
            vk::AccessFlags::TRANSFER_WRITE,
        ),
        vk::ImageLayout::TRANSFER_SRC_OPTIMAL => (
            vk::PipelineStageFlags::TRANSFER,
            vk::AccessFlags::TRANSFER_READ,
        ),
        vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL => (
            vk::PipelineStageFlags::FRAGMENT_SHADER,
            vk::AccessFlags::SHADER_READ,
        ),
        _ => (
            vk::PipelineStageFlags::ALL_COMMANDS,
            vk::AccessFlags::MEMORY_READ | vk::AccessFlags::MEMORY_WRITE,
        ),
    }
}

fn f32_slice_as_bytes(values: &[f32]) -> &[u8] {
    unsafe { std::slice::from_raw_parts(values.as_ptr().cast::<u8>(), mem::size_of_val(values)) }
}

fn create_render_pass(
    device: &ash::Device,
    format: vk::Format,
    final_layout: vk::ImageLayout,
) -> Result<vk::RenderPass> {
    let attachments = [vk::AttachmentDescription::default()
        .format(format)
        .samples(vk::SampleCountFlags::TYPE_1)
        .load_op(vk::AttachmentLoadOp::CLEAR)
        .store_op(vk::AttachmentStoreOp::STORE)
        .stencil_load_op(vk::AttachmentLoadOp::DONT_CARE)
        .stencil_store_op(vk::AttachmentStoreOp::DONT_CARE)
        .initial_layout(vk::ImageLayout::UNDEFINED)
        .final_layout(final_layout)];
    let color_references = [vk::AttachmentReference {
        attachment: 0,
        layout: vk::ImageLayout::COLOR_ATTACHMENT_OPTIMAL,
    }];
    let subpasses = [vk::SubpassDescription::default()
        .pipeline_bind_point(vk::PipelineBindPoint::GRAPHICS)
        .color_attachments(&color_references)];
    let dependencies = [
        vk::SubpassDependency::default()
            .src_subpass(vk::SUBPASS_EXTERNAL)
            .dst_subpass(0)
            .src_stage_mask(vk::PipelineStageFlags::TOP_OF_PIPE)
            .dst_stage_mask(vk::PipelineStageFlags::COLOR_ATTACHMENT_OUTPUT)
            .src_access_mask(vk::AccessFlags::empty())
            .dst_access_mask(vk::AccessFlags::COLOR_ATTACHMENT_WRITE),
        vk::SubpassDependency::default()
            .src_subpass(0)
            .dst_subpass(vk::SUBPASS_EXTERNAL)
            .src_stage_mask(vk::PipelineStageFlags::COLOR_ATTACHMENT_OUTPUT)
            .dst_stage_mask(
                vk::PipelineStageFlags::FRAGMENT_SHADER | vk::PipelineStageFlags::TRANSFER,
            )
            .src_access_mask(vk::AccessFlags::COLOR_ATTACHMENT_WRITE)
            .dst_access_mask(vk::AccessFlags::SHADER_READ | vk::AccessFlags::TRANSFER_READ),
    ];
    unsafe {
        device.create_render_pass(
            &vk::RenderPassCreateInfo::default()
                .attachments(&attachments)
                .subpasses(&subpasses)
                .dependencies(&dependencies),
            None,
        )
    }
    .context("failed to create Vulkan render pass")
}

fn create_framebuffer(
    device: &ash::Device,
    render_pass: vk::RenderPass,
    image: &GpuImage,
) -> Result<vk::Framebuffer> {
    let attachments = [image.view];
    unsafe {
        device.create_framebuffer(
            &vk::FramebufferCreateInfo::default()
                .render_pass(render_pass)
                .attachments(&attachments)
                .width(image.width)
                .height(image.height)
                .layers(1),
            None,
        )
    }
    .context("failed to create Vulkan framebuffer")
}

fn create_sampler(device: &ash::Device, filter: vk::Filter) -> Result<vk::Sampler> {
    unsafe {
        device.create_sampler(
            &vk::SamplerCreateInfo::default()
                .mag_filter(filter)
                .min_filter(filter)
                .mipmap_mode(vk::SamplerMipmapMode::NEAREST)
                .address_mode_u(vk::SamplerAddressMode::CLAMP_TO_EDGE)
                .address_mode_v(vk::SamplerAddressMode::CLAMP_TO_EDGE)
                .address_mode_w(vk::SamplerAddressMode::CLAMP_TO_EDGE)
                .min_lod(0.0)
                .max_lod(0.0)
                .unnormalized_coordinates(false),
            None,
        )
    }
    .context("failed to create Vulkan sampler")
}

fn create_descriptor_set_layouts(device: &ash::Device) -> Result<Vec<vk::DescriptorSetLayout>> {
    let definitions = vec![
        vec![
            combined_binding(0, vk::ShaderStageFlags::FRAGMENT),
            combined_binding(1, vk::ShaderStageFlags::FRAGMENT),
        ],
        (4..=8)
            .map(|binding| {
                combined_binding(
                    binding,
                    vk::ShaderStageFlags::VERTEX | vk::ShaderStageFlags::FRAGMENT,
                )
            })
            .collect(),
        vec![combined_binding(0, vk::ShaderStageFlags::FRAGMENT)],
        vec![
            uniform_binding(0, vk::ShaderStageFlags::FRAGMENT),
            uniform_binding(
                1,
                vk::ShaderStageFlags::VERTEX | vk::ShaderStageFlags::FRAGMENT,
            ),
        ],
        vec![combined_binding(0, vk::ShaderStageFlags::FRAGMENT)],
        vec![uniform_binding(0, vk::ShaderStageFlags::FRAGMENT)],
    ];
    let mut layouts = Vec::with_capacity(definitions.len());
    for bindings in definitions {
        match unsafe {
            device.create_descriptor_set_layout(
                &vk::DescriptorSetLayoutCreateInfo::default().bindings(&bindings),
                None,
            )
        } {
            Ok(layout) => layouts.push(layout),
            Err(error) => {
                unsafe {
                    for layout in layouts {
                        device.destroy_descriptor_set_layout(layout, None);
                    }
                }
                return Err(error).context("failed to create Vulkan descriptor set layout");
            }
        }
    }
    Ok(layouts)
}

fn combined_binding(
    binding: u32,
    stages: vk::ShaderStageFlags,
) -> vk::DescriptorSetLayoutBinding<'static> {
    vk::DescriptorSetLayoutBinding::default()
        .binding(binding)
        .descriptor_type(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
        .descriptor_count(1)
        .stage_flags(stages)
}

fn uniform_binding(
    binding: u32,
    stages: vk::ShaderStageFlags,
) -> vk::DescriptorSetLayoutBinding<'static> {
    vk::DescriptorSetLayoutBinding::default()
        .binding(binding)
        .descriptor_type(vk::DescriptorType::UNIFORM_BUFFER)
        .descriptor_count(1)
        .stage_flags(stages)
}

fn create_descriptor_pool(device: &ash::Device) -> Result<vk::DescriptorPool> {
    let pool_sizes = [
        vk::DescriptorPoolSize::default()
            .ty(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
            .descriptor_count(9),
        vk::DescriptorPoolSize::default()
            .ty(vk::DescriptorType::UNIFORM_BUFFER)
            .descriptor_count(3),
    ];
    unsafe {
        device.create_descriptor_pool(
            &vk::DescriptorPoolCreateInfo::default()
                .pool_sizes(&pool_sizes)
                .max_sets(6),
            None,
        )
    }
    .context("failed to create Vulkan descriptor pool")
}

fn allocate_descriptor_sets(
    device: &ash::Device,
    pool: vk::DescriptorPool,
    layouts: &[vk::DescriptorSetLayout],
) -> Result<Vec<vk::DescriptorSet>> {
    unsafe {
        device.allocate_descriptor_sets(
            &vk::DescriptorSetAllocateInfo::default()
                .descriptor_pool(pool)
                .set_layouts(layouts),
        )
    }
    .context("failed to allocate Vulkan descriptor sets")
}

#[allow(clippy::too_many_arguments)]
fn write_descriptor_sets(
    device: &ash::Device,
    sets: &[vk::DescriptorSet],
    linear_sampler: vk::Sampler,
    nearest_sampler: vk::Sampler,
    camera_left: &GpuImage,
    camera_right: &GpuImage,
    guides: &[GpuImage],
    depth: &GpuImage,
    video: &GpuImage,
    rgb_uniform: &GpuBuffer,
    displacement_uniform: &GpuBuffer,
    zone_uniform: &GpuBuffer,
) {
    let camera_infos = [
        image_info(linear_sampler, camera_left),
        image_info(linear_sampler, camera_right),
    ];
    let guide_infos = guides
        .iter()
        .map(|image| image_info(linear_sampler, image))
        .collect::<Vec<_>>();
    let depth_infos = [image_info(nearest_sampler, depth)];
    let video_infos = [image_info(linear_sampler, video)];
    let rgb_infos = [buffer_info(rgb_uniform)];
    let displacement_infos = [buffer_info(displacement_uniform)];
    let zone_infos = [buffer_info(zone_uniform)];
    let mut writes = vec![
        vk::WriteDescriptorSet::default()
            .dst_set(sets[0])
            .dst_binding(0)
            .descriptor_type(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
            .image_info(&camera_infos[0..1]),
        vk::WriteDescriptorSet::default()
            .dst_set(sets[0])
            .dst_binding(1)
            .descriptor_type(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
            .image_info(&camera_infos[1..2]),
        vk::WriteDescriptorSet::default()
            .dst_set(sets[2])
            .dst_binding(0)
            .descriptor_type(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
            .image_info(&depth_infos),
        vk::WriteDescriptorSet::default()
            .dst_set(sets[3])
            .dst_binding(0)
            .descriptor_type(vk::DescriptorType::UNIFORM_BUFFER)
            .buffer_info(&rgb_infos),
        vk::WriteDescriptorSet::default()
            .dst_set(sets[3])
            .dst_binding(1)
            .descriptor_type(vk::DescriptorType::UNIFORM_BUFFER)
            .buffer_info(&displacement_infos),
        vk::WriteDescriptorSet::default()
            .dst_set(sets[4])
            .dst_binding(0)
            .descriptor_type(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
            .image_info(&video_infos),
        vk::WriteDescriptorSet::default()
            .dst_set(sets[5])
            .dst_binding(0)
            .descriptor_type(vk::DescriptorType::UNIFORM_BUFFER)
            .buffer_info(&zone_infos),
    ];
    for (index, info) in guide_infos.iter().enumerate() {
        writes.push(
            vk::WriteDescriptorSet::default()
                .dst_set(sets[1])
                .dst_binding(4 + index as u32)
                .descriptor_type(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
                .image_info(std::slice::from_ref(info)),
        );
    }
    unsafe {
        device.update_descriptor_sets(&writes, &[]);
    }
}

fn image_info(sampler: vk::Sampler, image: &GpuImage) -> vk::DescriptorImageInfo {
    vk::DescriptorImageInfo::default()
        .sampler(sampler)
        .image_view(image.view)
        .image_layout(vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL)
}

fn buffer_info(buffer: &GpuBuffer) -> vk::DescriptorBufferInfo {
    vk::DescriptorBufferInfo::default()
        .buffer(buffer.buffer)
        .offset(0)
        .range(buffer.size)
}

fn create_pipeline_layout(
    device: &ash::Device,
    layouts: &[vk::DescriptorSetLayout],
    stages: vk::ShaderStageFlags,
    push_size: u32,
) -> Result<vk::PipelineLayout> {
    let ranges = [vk::PushConstantRange::default()
        .stage_flags(stages)
        .offset(0)
        .size(push_size)];
    unsafe {
        device.create_pipeline_layout(
            &vk::PipelineLayoutCreateInfo::default()
                .set_layouts(layouts)
                .push_constant_ranges(&ranges),
            None,
        )
    }
    .context("failed to create Vulkan pipeline layout")
}

fn load_shader_module(device: &ash::Device, path: &Path) -> Result<vk::ShaderModule> {
    let bytes =
        fs::read(path).with_context(|| format!("failed to read SPIR-V {}", path.display()))?;
    let code = read_spv(&mut Cursor::new(&bytes))
        .with_context(|| format!("invalid SPIR-V word stream {}", path.display()))?;
    unsafe { device.create_shader_module(&vk::ShaderModuleCreateInfo::default().code(&code), None) }
        .with_context(|| format!("failed to load exact SPIR-V {}", path.display()))
}

#[allow(clippy::too_many_arguments)]
fn create_graphics_pipeline(
    device: &ash::Device,
    render_pass: vk::RenderPass,
    pipeline_layout: vk::PipelineLayout,
    vertex: vk::ShaderModule,
    fragment: vk::ShaderModule,
    premultiplied_alpha: bool,
    label: &str,
) -> Result<vk::Pipeline> {
    let entry = CString::new("main")?;
    let stages = [
        vk::PipelineShaderStageCreateInfo::default()
            .stage(vk::ShaderStageFlags::VERTEX)
            .module(vertex)
            .name(&entry),
        vk::PipelineShaderStageCreateInfo::default()
            .stage(vk::ShaderStageFlags::FRAGMENT)
            .module(fragment)
            .name(&entry),
    ];
    let vertex_input = vk::PipelineVertexInputStateCreateInfo::default();
    let input_assembly = vk::PipelineInputAssemblyStateCreateInfo::default()
        .topology(vk::PrimitiveTopology::TRIANGLE_LIST);
    let viewport = vk::PipelineViewportStateCreateInfo::default()
        .viewport_count(1)
        .scissor_count(1);
    let rasterization = vk::PipelineRasterizationStateCreateInfo::default()
        .polygon_mode(vk::PolygonMode::FILL)
        .cull_mode(vk::CullModeFlags::NONE)
        .front_face(vk::FrontFace::COUNTER_CLOCKWISE)
        .line_width(1.0);
    let multisample = vk::PipelineMultisampleStateCreateInfo::default()
        .rasterization_samples(vk::SampleCountFlags::TYPE_1);
    let mut attachment = vk::PipelineColorBlendAttachmentState::default()
        .blend_enable(premultiplied_alpha)
        .color_write_mask(vk::ColorComponentFlags::RGBA);
    if premultiplied_alpha {
        attachment = attachment
            .src_color_blend_factor(vk::BlendFactor::ONE)
            .dst_color_blend_factor(vk::BlendFactor::ONE_MINUS_SRC_ALPHA)
            .color_blend_op(vk::BlendOp::ADD)
            .src_alpha_blend_factor(vk::BlendFactor::ONE)
            .dst_alpha_blend_factor(vk::BlendFactor::ONE_MINUS_SRC_ALPHA)
            .alpha_blend_op(vk::BlendOp::ADD);
    }
    let attachments = [attachment];
    let blend = vk::PipelineColorBlendStateCreateInfo::default().attachments(&attachments);
    let dynamic_states = [vk::DynamicState::VIEWPORT, vk::DynamicState::SCISSOR];
    let dynamic = vk::PipelineDynamicStateCreateInfo::default().dynamic_states(&dynamic_states);
    let infos = [vk::GraphicsPipelineCreateInfo::default()
        .stages(&stages)
        .vertex_input_state(&vertex_input)
        .input_assembly_state(&input_assembly)
        .viewport_state(&viewport)
        .rasterization_state(&rasterization)
        .multisample_state(&multisample)
        .color_blend_state(&blend)
        .dynamic_state(&dynamic)
        .layout(pipeline_layout)
        .render_pass(render_pass)
        .subpass(0)];
    unsafe { device.create_graphics_pipelines(vk::PipelineCache::null(), &infos, None) }
        .map_err(|(_, error)| anyhow!("failed to create {label} pipeline: {error:?}"))
        .map(|mut pipelines| pipelines.remove(0))
}

#[allow(clippy::too_many_arguments)]
fn record_guide_passes(
    owner: &Arc<DeviceOwner>,
    capsule: &ReplayCapsule,
    render_pass: vk::RenderPass,
    framebuffers: &[vk::Framebuffer],
    pipelines: &[vk::Pipeline],
    pipeline_layout: vk::PipelineLayout,
    descriptor_sets: &[vk::DescriptorSet],
) -> Result<()> {
    immediate(owner, |command| {
        record_guide_commands(
            owner,
            capsule,
            command,
            render_pass,
            framebuffers,
            pipelines,
            pipeline_layout,
            descriptor_sets,
        );
        Ok(())
    })
}

#[allow(clippy::too_many_arguments)]
fn record_guide_commands(
    owner: &Arc<DeviceOwner>,
    capsule: &ReplayCapsule,
    command: vk::CommandBuffer,
    render_pass: vk::RenderPass,
    framebuffers: &[vk::Framebuffer],
    pipelines: &[vk::Pipeline],
    pipeline_layout: vk::PipelineLayout,
    descriptor_sets: &[vk::DescriptorSet],
) {
    for (pass_index, target_index) in GUIDE_OUTPUT_SCHEDULE.into_iter().enumerate() {
        begin_render_pass(
            &owner.device,
            command,
            render_pass,
            framebuffers[target_index],
            capsule.extent.width,
            capsule.extent.height,
        );
        unsafe {
            owner.device.cmd_bind_pipeline(
                command,
                vk::PipelineBindPoint::GRAPHICS,
                pipelines[pass_index],
            );
            owner.device.cmd_bind_descriptor_sets(
                command,
                vk::PipelineBindPoint::GRAPHICS,
                pipeline_layout,
                0,
                descriptor_sets,
                &[],
            );
        }
        for eye in 0..2 {
            set_eye_view(
                &owner.device,
                command,
                capsule.extent.width,
                capsule.extent.height,
                eye,
            );
            let push = if eye == 0 {
                &capsule.guide.push_left
            } else {
                &capsule.guide.push_right
            };
            unsafe {
                owner.device.cmd_push_constants(
                    command,
                    pipeline_layout,
                    vk::ShaderStageFlags::FRAGMENT,
                    0,
                    f32_slice_as_bytes(push),
                );
                owner.device.cmd_draw(command, 3, 1, 0, 0);
            }
        }
        unsafe {
            owner.device.cmd_end_render_pass(command);
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn render_output_layer(
    owner: &Arc<DeviceOwner>,
    capsule: &ReplayCapsule,
    output: &GpuImage,
    render_pass: vk::RenderPass,
    framebuffer: vk::Framebuffer,
    pipeline: vk::Pipeline,
    pipeline_layout: vk::PipelineLayout,
    descriptor_sets: &[vk::DescriptorSet],
    override_value: f32,
) -> Result<Vec<u8>> {
    let readback = create_buffer(
        owner,
        output.width as u64 * output.height as u64 * 4,
        vk::BufferUsageFlags::TRANSFER_DST,
        vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT,
    )?;
    immediate(owner, |command| {
        record_output_commands(
            owner,
            capsule,
            command,
            output,
            render_pass,
            framebuffer,
            pipeline,
            pipeline_layout,
            descriptor_sets,
            override_value,
            &readback,
        );
        Ok(())
    })?;
    read_buffer(&readback)
}

#[allow(clippy::too_many_arguments)]
fn record_output_commands(
    owner: &Arc<DeviceOwner>,
    capsule: &ReplayCapsule,
    command: vk::CommandBuffer,
    output: &GpuImage,
    render_pass: vk::RenderPass,
    framebuffer: vk::Framebuffer,
    pipeline: vk::Pipeline,
    pipeline_layout: vk::PipelineLayout,
    descriptor_sets: &[vk::DescriptorSet],
    override_value: f32,
    readback: &GpuBuffer,
) {
    begin_render_pass(
        &owner.device,
        command,
        render_pass,
        framebuffer,
        output.width,
        output.height,
    );
    unsafe {
        owner
            .device
            .cmd_bind_pipeline(command, vk::PipelineBindPoint::GRAPHICS, pipeline);
        owner.device.cmd_bind_descriptor_sets(
            command,
            vk::PipelineBindPoint::GRAPHICS,
            pipeline_layout,
            0,
            descriptor_sets,
            &[],
        );
    }
    for eye in 0..2 {
        let scissor = if eye == 0 {
            &capsule.projection.scissor_left
        } else {
            &capsule.projection.scissor_right
        };
        set_projection_view(&owner.device, command, output.width, output.height, scissor);
        let mut push = if eye == 0 {
            capsule.projection.push_left.clone()
        } else {
            capsule.projection.push_right.clone()
        };
        push[7] = override_value;
        unsafe {
            owner.device.cmd_push_constants(
                command,
                pipeline_layout,
                vk::ShaderStageFlags::VERTEX | vk::ShaderStageFlags::FRAGMENT,
                0,
                f32_slice_as_bytes(&push),
            );
            owner.device.cmd_draw(
                command,
                if capsule.tessellated_projection_requested() {
                    GRID_VERTEX_COUNT
                } else {
                    3
                },
                1,
                0,
                0,
            );
        }
    }
    unsafe {
        owner.device.cmd_end_render_pass(command);
        let region = [vk::BufferImageCopy::default()
            .image_subresource(
                vk::ImageSubresourceLayers::default()
                    .aspect_mask(vk::ImageAspectFlags::COLOR)
                    .mip_level(0)
                    .base_array_layer(0)
                    .layer_count(1),
            )
            .image_extent(vk::Extent3D {
                width: output.width,
                height: output.height,
                depth: 1,
            })];
        owner.device.cmd_copy_image_to_buffer(
            command,
            output.image,
            vk::ImageLayout::TRANSFER_SRC_OPTIMAL,
            readback.buffer,
            &region,
        );
    }
}

fn read_color_image(
    owner: &Arc<DeviceOwner>,
    image: &GpuImage,
    current_layout: vk::ImageLayout,
    restore_layout: vk::ImageLayout,
) -> Result<Vec<u8>> {
    if image.format != vk::Format::R8G8B8A8_UNORM || image.layers != 1 {
        bail!("read_color_image supports only one-layer RGBA8 images");
    }
    let readback = create_buffer(
        owner,
        image.width as u64 * image.height as u64 * 4,
        vk::BufferUsageFlags::TRANSFER_DST,
        vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT,
    )?;
    immediate(owner, |command| unsafe {
        transition_image(
            &owner.device,
            command,
            image.image,
            vk::ImageAspectFlags::COLOR,
            1,
            current_layout,
            vk::ImageLayout::TRANSFER_SRC_OPTIMAL,
        );
        let region = [vk::BufferImageCopy::default()
            .image_subresource(
                vk::ImageSubresourceLayers::default()
                    .aspect_mask(vk::ImageAspectFlags::COLOR)
                    .mip_level(0)
                    .base_array_layer(0)
                    .layer_count(1),
            )
            .image_extent(vk::Extent3D {
                width: image.width,
                height: image.height,
                depth: 1,
            })];
        owner.device.cmd_copy_image_to_buffer(
            command,
            image.image,
            vk::ImageLayout::TRANSFER_SRC_OPTIMAL,
            readback.buffer,
            &region,
        );
        transition_image(
            &owner.device,
            command,
            image.image,
            vk::ImageAspectFlags::COLOR,
            1,
            vk::ImageLayout::TRANSFER_SRC_OPTIMAL,
            restore_layout,
        );
        Ok(())
    })?;
    read_buffer(&readback)
}

fn begin_render_pass(
    device: &ash::Device,
    command: vk::CommandBuffer,
    render_pass: vk::RenderPass,
    framebuffer: vk::Framebuffer,
    width: u32,
    height: u32,
) {
    let clear = [vk::ClearValue {
        color: vk::ClearColorValue {
            float32: [0.0, 0.0, 0.0, 0.0],
        },
    }];
    unsafe {
        device.cmd_begin_render_pass(
            command,
            &vk::RenderPassBeginInfo::default()
                .render_pass(render_pass)
                .framebuffer(framebuffer)
                .render_area(vk::Rect2D {
                    offset: vk::Offset2D { x: 0, y: 0 },
                    extent: vk::Extent2D { width, height },
                })
                .clear_values(&clear),
            vk::SubpassContents::INLINE,
        );
    }
}

fn set_eye_view(
    device: &ash::Device,
    command: vk::CommandBuffer,
    width: u32,
    height: u32,
    eye: usize,
) {
    let half = width / 2;
    let x = if eye == 0 { 0 } else { half };
    let eye_width = if eye == 0 { half } else { width - half };
    let viewports = [vk::Viewport {
        x: x as f32,
        y: 0.0,
        width: eye_width as f32,
        height: height as f32,
        min_depth: 0.0,
        max_depth: 1.0,
    }];
    let scissors = [vk::Rect2D {
        offset: vk::Offset2D { x: x as i32, y: 0 },
        extent: vk::Extent2D {
            width: eye_width,
            height,
        },
    }];
    unsafe {
        device.cmd_set_viewport(command, 0, &viewports);
        device.cmd_set_scissor(command, 0, &scissors);
    }
}

fn set_projection_view(
    device: &ash::Device,
    command: vk::CommandBuffer,
    width: u32,
    height: u32,
    rect: &[f32],
) {
    let viewports = [vk::Viewport {
        x: 0.0,
        y: 0.0,
        width: width as f32,
        height: height as f32,
        min_depth: 0.0,
        max_depth: 1.0,
    }];
    let scissors = [normalized_scissor(width, height, rect)];
    unsafe {
        device.cmd_set_viewport(command, 0, &viewports);
        device.cmd_set_scissor(command, 0, &scissors);
    }
}

fn normalized_scissor(width: u32, height: u32, rect: &[f32]) -> vk::Rect2D {
    let start_x = (rect[0] * width as f32)
        .round()
        .clamp(0.0, width.saturating_sub(1) as f32);
    let start_y = (rect[1] * height as f32)
        .round()
        .clamp(0.0, height.saturating_sub(1) as f32);
    let end_x = ((rect[0] + rect[2]) * width as f32)
        .round()
        .clamp(start_x + 1.0, width as f32);
    let end_y = ((rect[1] + rect[3]) * height as f32)
        .round()
        .clamp(start_y + 1.0, height as f32);
    vk::Rect2D {
        offset: vk::Offset2D {
            x: start_x as i32,
            y: start_y as i32,
        },
        extent: vk::Extent2D {
            width: (end_x - start_x) as u32,
            height: (end_y - start_y) as u32,
        },
    }
}

fn save_rgba(path: &Path, width: u32, height: u32, rgba: &[u8]) -> Result<()> {
    let image = RgbaImage::from_raw(width, height, rgba.to_vec())
        .ok_or_else(|| anyhow!("invalid RGBA output size for {}", path.display()))?;
    DynamicImage::ImageRgba8(image)
        .save(path)
        .with_context(|| format!("failed to save {}", path.display()))
}

fn output_report(layer: &str, path: &Path, rgba: &[u8]) -> Result<OutputReport> {
    let (alpha_min, alpha_max) = rgba
        .chunks_exact(4)
        .map(|pixel| pixel[3])
        .fold((u8::MAX, u8::MIN), |(minimum, maximum), alpha| {
            (minimum.min(alpha), maximum.max(alpha))
        });
    Ok(OutputReport {
        layer: layer.to_string(),
        path: path.display().to_string(),
        sha256: sha256_file(path)?,
        alpha_min,
        alpha_max,
    })
}

fn sanitize_name(name: &str) -> String {
    let mut sanitized = name
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || character == '-' || character == '_' {
                character.to_ascii_lowercase()
            } else {
                '-'
            }
        })
        .collect::<String>();
    while sanitized.contains("--") {
        sanitized = sanitized.replace("--", "-");
    }
    sanitized.trim_matches('-').to_string()
}

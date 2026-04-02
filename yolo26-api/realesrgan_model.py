"""
Real-ESRGAN Model Definition and Inference Utility
Embedded in project to avoid installing realesrgan/basicsr packages
which are notoriously difficult to install on Windows.

Source adapted from:
- basicsr/archs/rrdbnet_arch.py
- realesrgan/utils.py
"""

import math
import cv2
import numpy as np
import torch
from torch import nn as nn
from torch.nn import functional as F


class ResidualDenseBlock(nn.Module):
    """Residual Dense Block for RRDB"""

    def __init__(self, num_feat=64, num_grow_ch=32):
        super(ResidualDenseBlock, self).__init__()
        self.conv1 = nn.Conv2d(num_feat, num_grow_ch, 3, 1, 1)
        self.conv2 = nn.Conv2d(num_feat + num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv3 = nn.Conv2d(num_feat + 2 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv4 = nn.Conv2d(num_feat + 3 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv5 = nn.Conv2d(num_feat + 4 * num_grow_ch, num_feat, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat([x, x1], 1)))
        x3 = self.lrelu(self.conv3(torch.cat([x, x1, x2], 1)))
        x4 = self.lrelu(self.conv4(torch.cat([x, x1, x2, x3], 1)))
        x5 = self.conv5(torch.cat([x, x1, x2, x3, x4], 1))
        # Emphasis on skip connection (scale by 0.2)
        return x5 * 0.2 + x


class RRDB(nn.Module):
    """Residual in Residual Dense Block"""

    def __init__(self, num_feat, num_grow_ch=32):
        super(RRDB, self).__init__()
        self.rdb1 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb2 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb3 = ResidualDenseBlock(num_feat, num_grow_ch)

    def forward(self, x):
        out = self.rdb1(x)
        out = self.rdb2(out)
        out = self.rdb3(out)
        # Scale residual by 0.2
        return out * 0.2 + x


class RRDBNet(nn.Module):
    """
    RRDB Network for Real-ESRGAN
    Supports scales: 1, 2, 4
    """

    def __init__(self, num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4):
        super(RRDBNet, self).__init__()
        self.scale = scale
        
        # For scale 2 and 1, use pixel unshuffle
        if scale == 2:
            num_in_ch = num_in_ch * 4
        elif scale == 1:
            num_in_ch = num_in_ch * 16
            
        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        self.body = nn.ModuleList([RRDB(num_feat, num_grow_ch) for _ in range(num_block)])
        self.conv_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        
        # Upsampling layers (2x2 = 4x total)
        self.conv_up1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        
        self.conv_hr = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        # Pixel unshuffle for scale 2 and 1
        if self.scale == 2:
            feat = torch.pixel_unshuffle(x, downscale_factor=2)
        elif self.scale == 1:
            feat = torch.pixel_unshuffle(x, downscale_factor=4)
        else:
            feat = x
            
        feat = self.conv_first(feat)
        body_feat = feat
        
        for block in self.body:
            body_feat = block(body_feat)
            
        body_feat = self.conv_body(body_feat)
        feat = feat + body_feat
        
        # Upsample 2x
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode='nearest')))
        # Upsample 2x more (total 4x)
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode='nearest')))
        
        feat = self.lrelu(self.conv_hr(feat))
        out = self.conv_last(feat)
        return out


class RealESRGANer:
    """
    Real-ESRGAN Inference Utility
    Handles model loading, tiling for large images, and inference
    """

    def __init__(self, scale, model_path, model=None, tile=0, tile_pad=10, pre_pad=0, half=False, device=None):
        """
        Args:
            scale: Upsampling scale (2 or 4)
            model_path: Path to model weights (.pth file)
            model: Pre-initialized model (if None, will create RRDBNet)
            tile: Tile size for splitting large images (0 = no tiling)
            tile_pad: Padding around tiles to avoid boundary artifacts
            pre_pad: Pre-padding size
            half: Use FP16 half precision
            device: torch device (if None, auto-detect CUDA or CPU)
        """
        self.scale = scale
        self.tile_size = tile
        self.tile_pad = tile_pad
        self.pre_pad = pre_pad
        self.half = half
        
        # Auto-detect device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() and not half else 'cpu')
        else:
            self.device = device
            
        # Create model if not provided
        if model is None:
            model = RRDBNet(
                num_in_ch=3,
                num_out_ch=3,
                num_feat=64,
                num_block=23,
                num_grow_ch=32,
                scale=scale
            )
        
        # Load weights
        loadnet = torch.load(model_path, map_location=self.device)
        if 'params_ema' in loadnet:
            keyname = 'params_ema'
        elif 'params' in loadnet:
            keyname = 'params'
        else:
            keyname = 'model'  # fallback
            
        model.load_state_dict(loadnet[keyname], strict=True)
        model.eval()
        
        self.model = model.to(self.device)
        if self.half:
            self.model = self.model.half()
            
    def pre_process(self, img):
        """Prepare image for inference"""
        img = torch.from_numpy(np.transpose(img, (2, 0, 1))).float()
        if self.half:
            img = img.half()
        self.img = img.unsqueeze(0).to(self.device)
        
        # Pad image dimensions to be divisible by scale
        _, _, h, w = self.img.size()
        self.mod_pad_h = 0
        self.mod_pad_w = 0
        if h % self.scale != 0:
            self.mod_pad_h = self.scale - h % self.scale
        if w % self.scale != 0:
            self.mod_pad_w = self.scale - w % self.scale
            
        if self.mod_pad_h > 0 or self.mod_pad_w > 0:
            self.img = F.pad(self.img, (0, self.mod_pad_w, 0, self.mod_pad_h), 'reflect')

    def process(self):
        """Run model inference"""
        with torch.no_grad():
            self.output = self.model(self.img)

    def tile_process(self):
        """Process image in tiles to save memory"""
        batch, channel, height, width = self.img.shape
        output_height = height * self.scale
        output_width = width * self.scale
        output_shape = (batch, channel, output_height, output_width)
        
        self.output = self.img.new_zeros(output_shape)
        tiles_x = math.ceil(width / self.tile_size)
        tiles_y = math.ceil(height / self.tile_size)
        
        for y in range(tiles_y):
            for x in range(tiles_x):
                ofs_x = x * self.tile_size
                ofs_y = y * self.tile_size
                
                # Input tile region
                input_start_x = ofs_x
                input_end_x = min(ofs_x + self.tile_size, width)
                input_start_y = ofs_y
                input_end_y = min(ofs_y + self.tile_size, height)
                
                # Input tile with padding
                input_tile = self.img[:, :, input_start_y:input_end_y, input_start_x:input_end_x]
                padded_tile = F.pad(input_tile, (self.tile_pad, self.tile_pad, self.tile_pad, self.tile_pad), mode='reflect')
                
                # Inference
                with torch.no_grad():
                    output_tile = self.model(padded_tile)
                
                # Output tile region (remove padding)
                output_start_x = input_start_x * self.scale
                output_end_x = input_end_x * self.scale
                output_start_y = input_start_y * self.scale
                output_end_y = input_end_y * self.scale
                
                tile_pad_scaled = self.tile_pad * self.scale
                self.output[:, :, output_start_y:output_end_y, output_start_x:output_end_x] = output_tile[:, :, tile_pad_scaled:-tile_pad_scaled, tile_pad_scaled:-tile_pad_scaled]

    def post_process(self):
        """Remove padding from output"""
        if hasattr(self, 'mod_pad_h') and hasattr(self, 'mod_pad_w'):
            _, _, h, w = self.output.size()
            self.output = self.output[:, :, 0:h - self.mod_pad_h * self.scale, 0:w - self.mod_pad_w * self.scale]

    def enhance(self, img, outscale=None):
        """
        Enhance image using Real-ESRGAN
        
        Args:
            img: Input image (numpy array, BGR, uint8)
            outscale: Output scale factor (if None, use model scale)
            
        Returns:
            enhanced_img: Enhanced image (numpy array, BGR, uint8)
        """
        img = img.astype(np.float32)
        
        # Normalize to [0, 1]
        if np.max(img) > 256:
            max_range = 65535  # 16-bit image
        else:
            max_range = 255
        img = img / max_range
        
        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Pre-process
        self.pre_process(img)
        
        # Inference (tile or whole)
        if self.tile_size > 0:
            self.tile_process()
        else:
            self.process()
            
        # Post-process
        self.post_process()
        
        # Convert back to numpy
        output_img = self.output.squeeze(0).float().cpu().clamp_(0, 1).numpy()
        output_img = np.transpose(output_img[[0, 1, 2], :, :], (1, 2, 0))
        output_img = (output_img * 255.0).round().astype(np.uint8)
        
        # Convert RGB back to BGR
        output_img = cv2.cvtColor(output_img, cv2.COLOR_RGB2BGR)
        
        # Resize if outscale is specified (different from model scale)
        if outscale is not None and outscale != self.scale:
            h, w = output_img.shape[0:2]
            output_img = cv2.resize(output_img, (int(w / self.scale * outscale), int(h / self.scale * outscale)), interpolation=cv2.INTER_LANCZOS4)
            
        return output_img


# Global model instance (lazy loading)
_realesrgan_model = None

def get_realesrgan_model(model_path='weights/RealESRGAN_x4plus.pth', scale=4, tile=512):
    """
    Get or create global RealESRGAN model instance
    
    Args:
        model_path: Path to .pth weights
        scale: Model scale (2 or 4)
        tile: Tile size for large images (0 = no tile, use full image)
    """
    global _realesrgan_model
    if _realesrgan_model is None:
        print(f'[RealESRGAN] Loading model from {model_path} ...')
        _realesrgan_model = RealESRGANer(
            scale=scale,
            model_path=model_path,
            tile=tile,  # Use 512x512 tiles to avoid memory issues
            tile_pad=10,
            pre_pad=0,
            half=False  # CPU mode uses FP32
        )
        print(f'[RealESRGAN] Model loaded successfully (device: {_realesrgan_model.device})')
    return _realesrgan_model

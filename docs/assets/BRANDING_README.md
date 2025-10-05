# Brain Swarm Branding Kit

This directory contains the official branding assets for Brain Swarm, featuring our signature dark-mode aesthetic with neon blue-green gradients.

## 🎨 Color Palette

### Primary Colors (Dark Theme)
- **Background Gradient**: `#0f0f23` → `#1a1a2e` → `#16213e`
- **Accent Blue**: `#64b5f6`
- **Accent Green**: `#4CAF50`
- **Accent Teal**: `#00bcd4`
- **Text Primary**: `#e0e0e0`
- **Text Secondary**: `#b0b0b0`

### Light Theme Variants
- **Background**: `#ffffff`
- **Accent Blue**: `#1976d2`
- **Accent Green**: `#388e3c`
- **Accent Teal**: `#0097a7`

## 📁 Assets

### Favicons
- `favicon.svg` - Dark theme favicon (32x32) with neon glow effects
- `favicon-light.svg` - Light theme favicon (32x32) for bright backgrounds

### PDF Covers
- `pdf-cover.svg` - A4-sized PDF cover template (595x842px) with brain logo and branding

## 🚀 Usage Guidelines

### MkDocs Integration
```yaml
# mkdocs.yml
theme:
  name: material
  palette:
    primary: blue
    accent: teal
  logo: assets/favicon.svg
  favicon: assets/favicon.svg

extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/jfbinTECHA/brain-swarm
```

### Web Applications
```html
<!-- Dark theme favicon -->
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">

<!-- Light theme favicon (for light mode) -->
<link rel="icon" type="image/svg+xml" href="/assets/favicon-light.svg" media="(prefers-color-scheme: light)">
```

### PDF Generation
The `pdf-cover.svg` can be used as a template for:
- Documentation covers
- Report headers
- Presentation slides
- Marketing materials

Convert to PDF using tools like Inkscape or ImageMagick:
```bash
# Using ImageMagick
convert pdf-cover.svg -density 300 pdf-cover.pdf

# Using Inkscape
inkscape --export-type=pdf --export-filename=pdf-cover.pdf pdf-cover.svg
```

### PNG Generation (Fallback)
For legacy systems requiring raster images:

```python
# Using Python PIL
from PIL import Image
import cairosvg

# Convert SVG to PNG
cairosvg.svg2png(url='favicon.svg', write_to='favicon.png', output_width=32, output_height=32)
cairosvg.svg2png(url='pdf-cover.svg', write_to='pdf-cover.png', output_width=595, output_height=842)
```

Or using online tools like CloudConvert or SVG to PNG converters.

## 🛠️ Customization

### Modifying Colors
The SVG files use CSS custom properties and gradients that can be easily modified:

```css
:root {
  --brain-blue: #64b5f6;
  --brain-green: #4CAF50;
  --brain-teal: #00bcd4;
  --text-primary: #e0e0e0;
  --background-dark: #0f0f23;
}
```

### Creating New Assets
When creating new branding assets:
1. Use the established color palette
2. Maintain the brain/neural network motif
3. Include subtle glow effects for dark theme
4. Ensure scalability (SVG format preferred)
5. Test on both light and dark backgrounds

## 📋 File Formats

- **SVG**: Preferred for web and scalable graphics
- **PNG**: For legacy support or specific size requirements
- **PDF**: For print materials and documentation covers

## 🎯 Brand Voice

- **Technical**: Enterprise-grade AI orchestration
- **Innovative**: Cutting-edge swarm intelligence
- **Reliable**: Production-ready incident response
- **Scalable**: Multi-cluster federation capabilities

## 📞 Contact

For branding questions or new asset requests:
- **Team**: Brain Swarm Team
- **Email**: team@brain-swarm.dev
- **GitHub**: [jfbinTECHA/brain-swarm](https://github.com/jfbinTECHA/brain-swarm)

---

*Last updated: October 2023*
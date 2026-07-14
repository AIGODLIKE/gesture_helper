import gpu


class Texture:
    texture_list = {}

    @staticmethod
    def clear():
        Texture.texture_list.clear()

    @staticmethod
    def _rgba_floats_from_preview(preview, width: int, height: int) -> list[float] | None:
        """Return straight-alpha RGBA floats, fixing common preview alpha issues."""
        count = width * height * 4
        pixels = None

        # Prefer byte pixels — more reliable alpha from bpy.utils.previews PNGs.
        try:
            raw_int = preview.icon_pixels
            if raw_int and len(raw_int) >= count:
                pixels = [c / 255.0 for c in raw_int[:count]]
        except Exception:
            pixels = None

        if pixels is None:
            try:
                raw_f = preview.icon_pixels_float
                if raw_f and len(raw_f) >= count:
                    pixels = list(raw_f[:count])
            except Exception:
                return None

        if not pixels or len(pixels) < count:
            return None

        # If the image is fully opaque but corners are uniform dark/light, treat that
        # solid backdrop as transparent (common for chevron / "1" child icons).
        opaque = 0
        for i in range(3, count, 4):
            if pixels[i] > 0.95:
                opaque += 1
        total = width * height
        if total > 0 and opaque / total > 0.92:
            corners = (
                0,
                (width - 1) * 4,
                (height - 1) * width * 4,
                ((height - 1) * width + (width - 1)) * 4,
            )
            br = bg = bb = 0.0
            for c in corners:
                br += pixels[c]
                bg += pixels[c + 1]
                bb += pixels[c + 2]
            br /= 4.0
            bg /= 4.0
            bb /= 4.0
            # Only key out near-neutral backdrops (not saturated icon colors).
            chroma = max(br, bg, bb) - min(br, bg, bb)
            if chroma < 0.08:
                thresh = 0.12
                for i in range(0, count, 4):
                    dr = abs(pixels[i] - br)
                    dg = abs(pixels[i + 1] - bg)
                    db = abs(pixels[i + 2] - bb)
                    if dr < thresh and dg < thresh and db < thresh:
                        pixels[i + 3] = 0.0
        return pixels

    @staticmethod
    def _texture_from_icon_preview(key: str):
        from .icons import Icons

        try:
            preview = Icons.get(key)
        except KeyError:
            return None

        icon_size = preview.icon_size
        if isinstance(icon_size, int):
            width = height = icon_size
        else:
            width, height = icon_size[0], icon_size[1]
        if width <= 0 or height <= 0:
            return None

        pixels = Texture._rgba_floats_from_preview(preview, width, height)
        if not pixels:
            return None

        buffer = gpu.types.Buffer('FLOAT', len(pixels), pixels)
        # RGBA16F keeps alpha precision without the cost of RGBA32F.
        try:
            return gpu.types.GPUTexture((width, height), format='RGBA16F', data=buffer)
        except Exception:
            return gpu.types.GPUTexture((width, height), format='RGBA32F', data=buffer)

    @staticmethod
    def get_texture(key):
        if not key:
            return None

        from .icons import normalize_icon_name
        lookup = normalize_icon_name(key).lower()
        if not lookup:
            return None

        texture = Texture.texture_list.get(lookup)
        if texture is not None:
            return texture

        texture = Texture._texture_from_icon_preview(lookup)
        if texture is not None:
            Texture.texture_list[lookup] = texture
        return texture

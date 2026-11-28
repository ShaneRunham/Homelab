"""Neon 'SUGGESTIONS OPEN' banner in the DPGS Security logo style (black, hot pink tubes, pale cores)."""
import os, sys
TITLE, PILL, TAG, OUT = (sys.argv[1:5] if len(sys.argv) > 4 else ("SUGGESTIONS", "OPEN", "CREW  ·  DISCORD  ·  BLS", "suggestions_banner.png"))
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1500, 500
PINK = (255, 40, 110)
CORE = (255, 205, 225)
FONT = "/usr/share/fonts/google-noto/NotoSans-ExtraCondensedBlack.ttf"
LOGO = "server_icon.png"  # the server's own icon


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def glow(L, radii=(40, 16, 6), strength=(0.8, 1.0, 1.0)):
    out = layer()
    for r, k in zip(radii, strength):
        b = L.filter(ImageFilter.GaussianBlur(r))
        if k != 1:
            b.putalpha(b.getchannel("A").point(lambda v: int(v * k)))
        out = Image.alpha_composite(out, b)
    return out


def text(s, x, y, size, track, fill, anchor_right=False):
    L = layer()
    d = ImageDraw.Draw(L)
    f = ImageFont.truetype(FONT, size)
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + track
    return L


def width(s, size, track):
    d = ImageDraw.Draw(layer())
    f = ImageFont.truetype(FONT, size)
    return sum(d.textlength(ch, font=f) for ch in s) + track * (len(s) - 1)


img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
bloom = layer()
ImageDraw.Draw(bloom).ellipse((80, 40, 560, 470), fill=(120, 0, 50, 150))
ImageDraw.Draw(bloom).ellipse((560, 120, 1440, 400), fill=(90, 0, 40, 110))
img = Image.alpha_composite(img, bloom.filter(ImageFilter.GaussianBlur(110)))

# frame: rounded neon rectangle
frame = layer()
ImageDraw.Draw(frame).rounded_rectangle((28, 28, W - 28, H - 28), radius=36, outline=PINK + (255,), width=8)
core = layer()
ImageDraw.Draw(core).rounded_rectangle((28, 28, W - 28, H - 28), radius=36, outline=CORE + (200,), width=3)
img = Image.alpha_composite(img, glow(frame, (26, 10), (0.9, 1.0)))
img = Image.alpha_composite(Image.alpha_composite(img, frame), core.filter(ImageFilter.GaussianBlur(1)))

# the server icon on the left, as a circle with a neon ring
logo = Image.open(LOGO).convert("RGBA").resize((340, 340), Image.LANCZOS)
m = Image.new("L", (340, 340), 0)
ImageDraw.Draw(m).ellipse((0, 0, 339, 339), fill=255)
logo.putalpha(m)
ring = layer()
ImageDraw.Draw(ring).ellipse((94, 74, 446, 426), outline=PINK + (255,), width=7)
img = Image.alpha_composite(img, glow(ring, (22, 8), (0.9, 1.0)))
img.alpha_composite(logo, (100, 80))
img = Image.alpha_composite(img, ring)

# text block on the right
x0 = 520
small = text("DONTPANICGANGERS!  DPGS", x0 + 4, 92, 54, 8, PINK + (255,))
img = Image.alpha_composite(img, glow(small, (14, 6), (0.8, 1.0)))
img = Image.alpha_composite(img, small)

room = W - 90 - x0
size = 178
while width(TITLE, size, 6) > room:
    size -= 2
big = text(TITLE, x0, 140 + (178 - size) // 2, size, 6, PINK + (255,))
img = Image.alpha_composite(img, glow(big, (34, 14, 5), (0.85, 1.0, 1.0)))
img = Image.alpha_composite(img, big)
img = Image.alpha_composite(img, text(TITLE, x0, 140 + (178 - size) // 2, size, 6, CORE + (120,)))

# "OPEN" in a pill
ow = width(PILL, 72, 14)
pill = layer()
ImageDraw.Draw(pill).rounded_rectangle((x0, 352, x0 + ow + 70, 432), radius=40, fill=PINK + (255,))
img = Image.alpha_composite(img, glow(pill, (24, 8), (0.8, 0.9)))
img = Image.alpha_composite(img, pill)
img = Image.alpha_composite(img, text(PILL, x0 + 35, 346, 72, 14, (15, 0, 8, 255)))

tag = text(TAG, x0 + ow + 110, 368, 46, 6, CORE + (230,))
img = Image.alpha_composite(img, tag)

img.convert("RGB").save(OUT)
print("ok")

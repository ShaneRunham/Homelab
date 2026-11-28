"""DPGS Rider Licence (2026-11-28): an ID card for each new member (welcome), stamped REVOKED when they leave.
Drawn with Pillow and the system Noto fonts; the server icon is assets/server_icon.png.
render(avatar, name, number, joined: date, status: "unverified"|"verified", member_id, revoked=False, fallback="") -> PNG"""
import io
import math
import os
import random
import re
import unicodedata
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1400, 860
PINK = (255, 40, 110)
CORE = (255, 205, 225)
INK = (240, 232, 238)
DIM = (150, 135, 150)
AMBER = (255, 176, 60)
GREEN = (60, 220, 140)
RED = (235, 40, 50)
D = "/usr/share/fonts/google-noto/"
BLACK, BOLD, MED, MONO = D + "NotoSans-ExtraCondensedBlack.ttf", D + "NotoSans-Bold.ttf", D + "NotoSans-Medium.ttf", D + "NotoSansMono-Bold.ttf"
ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "server_icon.png")


def F(path, size):
    return ImageFont.truetype(path, size)


def layer(w=W, h=H):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def glow(L, radii=(30, 10), strength=(0.8, 1.0)):
    out = layer(*L.size)
    for r, k in zip(radii, strength):
        b = L.filter(ImageFilter.GaussianBlur(r))
        b.putalpha(b.getchannel("A").point(lambda v: int(v * k)))
        out = Image.alpha_composite(out, b)
    return out


def tracked(d, xy, s, font, fill, track=0):
    x, y = xy
    for ch in s:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + track
    return x


def tw(s, font, track=0):
    d = ImageDraw.Draw(layer(1, 1))
    return sum(d.textlength(ch, font=font) for ch in s) + track * max(0, len(s) - 1)


def clean(name, fallback=""):
    s = re.sub(r"\s*\(@[^)]*\)\s*$", "", unicodedata.normalize("NFKC", name))
    if any(unicodedata.category(ch)[0] == "L" and ord(ch) >= 0x0250 for ch in s):
        s = fallback
    s = "".join(ch for ch in s if (unicodedata.category(ch)[0] in "LNPZ" and ord(ch) < 0x0250) or ch == " ")
    return re.sub(r"\s+", " ", s).strip(" -_") or "New rider"


def render(avatar, name, number, joined, status, member_id, revoked=False, fallback=""):
    name = clean(name, fallback).upper()
    rnd = random.Random(member_id)
    accent = DIM if revoked else PINK

    # --- card body: dark plum gradient, rounded, with fine guilloche waves -----------------------------
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad = Image.new("RGBA", (W, H))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        t = y / H
        gd.line((0, y, W, y), fill=(int(28 + 20 * (1 - t)), int(10 + 4 * t), int(26 + 14 * (1 - t)), 255))
    waves = layer()
    wd = ImageDraw.Draw(waves)
    for k in range(18):
        pts = [(x, 300 + k * 28 + 26 * math.sin(x / 70 + k * 0.6)) for x in range(0, W + 10, 10)]
        wd.line(pts, fill=accent + (16,), width=2)
    grad = Image.alpha_composite(grad, waves)
    # big faint server icon watermark on the right
    icon = Image.open(ICON).convert("RGBA").resize((620, 620), Image.LANCZOS)
    if revoked:
        icon = icon.convert("LA").convert("RGBA")
    icon.putalpha(icon.getchannel("A").point(lambda v: int(v * 0.08)))
    grad.alpha_composite(icon, (W - 560, 200))
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, W - 1, H - 1), radius=48, fill=255)
    card.paste(grad, (0, 0), mask)
    if revoked:
        card = Image.alpha_composite(card, Image.new("RGBA", (W, H), (0, 0, 0, 70)))
        card.putalpha(mask)

    d = ImageDraw.Draw(card)
    # header band
    band = layer()
    ImageDraw.Draw(band).rounded_rectangle((0, 0, W - 1, 150), radius=48, fill=accent + (255,))
    ImageDraw.Draw(band).rectangle((0, 100, W - 1, 150), fill=accent + (255,))
    card = Image.alpha_composite(card, band)
    d = ImageDraw.Draw(card)
    small_icon = Image.open(ICON).convert("RGBA").resize((104, 104), Image.LANCZOS)
    m = Image.new("L", (104, 104), 0)
    ImageDraw.Draw(m).ellipse((0, 0, 103, 103), fill=255)
    if revoked:
        small_icon = small_icon.convert("LA").convert("RGBA")
    small_icon.putalpha(m)
    card.alpha_composite(small_icon, (44, 23))
    tracked(d, (170, 30), "DONTPANICGANGERS!", F(BLACK, 46), (20, 0, 10), 4)
    tracked(d, (172, 88), "OFFICIAL CREW DOCUMENT", F(BOLD, 30), (20, 0, 10, 200), 3)
    title = "RIDER LICENCE"
    tracked(d, (W - 56 - tw(title, F(BLACK, 96), 5), 14), title, F(BLACK, 96), (20, 0, 10), 5)

    # photo
    av = Image.open(io.BytesIO(avatar)).convert("RGBA").resize((420, 420), Image.LANCZOS)
    if revoked:
        av = av.convert("LA").convert("RGBA")
    pm = Image.new("L", (420, 420), 0)
    ImageDraw.Draw(pm).rounded_rectangle((0, 0, 419, 419), radius=30, fill=255)
    av.putalpha(pm)
    frame = layer()
    ImageDraw.Draw(frame).rounded_rectangle((52, 186, 52 + 428, 186 + 428), radius=34, outline=accent + (255,), width=6)
    card = Image.alpha_composite(card, glow(frame, (18, 6), (0.7, 0.9)) if not revoked else card)
    card.alpha_composite(av, (56, 190))
    card = Image.alpha_composite(card, frame)
    d = ImageDraw.Draw(card)

    # fields
    x = 530
    def field(y, label, value, font, fill=INK):
        tracked(d, (x, y), label, F(BOLD, 30), DIM, 4)
        tracked(d, (x, y + 30), value, font, fill, 2)

    nf_size = 104
    while nf_size > 56 and tw(name, F(BLACK, nf_size), 3) > W - 80 - x:
        nf_size -= 2
    nm = name
    while len(nm) > 3 and tw(nm, F(BLACK, nf_size), 3) > W - 80 - x:
        nm = nm[:-2].rstrip(" _-.") + "…"
    tracked(d, (x, 180), "NAME", F(BOLD, 30), DIM, 4)
    tracked(d, (x, 206 + (104 - nf_size) // 2), nm, F(BLACK, nf_size), INK, 3)

    field(350, "RIDER NO.", f"{number:03d}", F(MONO, 66), accent if not revoked else INK)
    tracked(d, (x + 300, 350), "JOINED", F(BOLD, 30), DIM, 4)
    tracked(d, (x + 300, 380), joined.strftime("%d %b %Y").upper(), F(MONO, 66), INK, 2)

    tracked(d, (x, 486), "STATUS", F(BOLD, 30), DIM, 4)
    st_txt, st_col = {"unverified": ("UNVERIFIED", AMBER), "verified": ("VERIFIED", GREEN)}[status]
    if revoked:
        st_txt, st_col = "REVOKED", RED
    sf = F(BLACK, 60)
    sw = tw(st_txt, sf, 5)
    pill = layer()
    ImageDraw.Draw(pill).rounded_rectangle((x, 524, x + sw + 80, 604), radius=40, outline=st_col + (255,), width=5)
    ImageDraw.Draw(pill).ellipse((x + 24, 554, x + 44, 574), fill=st_col + (255,))
    card = Image.alpha_composite(card, pill)
    d = ImageDraw.Draw(card)
    tracked(d, (x + 58, 520), st_txt, sf, st_col, 5)

    # barcode + motto along the bottom
    bx, by = 56, 656
    while bx < 470:
        w = rnd.choice((3, 3, 5, 7))
        d.rectangle((bx, by, bx + w, by + 100), fill=INK if not revoked else DIM)
        bx += w + rnd.choice((4, 5, 7, 9))
    tracked(d, (56, 770), f"DPGS-{member_id % 10**8:08d}", F(MONO, 34), DIM, 3)
    motto = "EARN YOUR SPOT"
    tracked(d, (x, 660), motto, F(BLACK, 52), accent, 8)
    tracked(d, (x, 726), "Skill · Loyalty · Discipline", F(MED, 38), DIM, 1)

    # hologram seal (iridescent server icon) bottom right
    S = 210
    seal = Image.open(ICON).convert("RGBA").resize((S, S), Image.LANCZOS).convert("L")
    seal = seal.point(lambda v: 90 + v * 0.65)
    rainbow = Image.new("RGB", (S, S))
    rd = ImageDraw.Draw(rainbow)
    for i in range(2 * S):  # diagonal iridescent bands
        h = i / (2 * S)
        rd.line((i, 0, i - S, S), width=2, fill=(int(170 + 85 * math.sin(9.4 * h)), int(170 + 85 * math.sin(9.4 * h + 2.1)),
                                                 int(190 + 65 * math.sin(9.4 * h + 4.2))))
    holo = ImageChops.multiply(rainbow, Image.merge("RGB", (seal, seal, seal))).convert("RGBA")
    shine = Image.new("L", (S, S), 0)
    ImageDraw.Draw(shine).polygon([(S * 0.15, S), (S * 0.45, S), (S, S * 0.2), (S, 0)], fill=110)
    holo = Image.composite(Image.new("RGBA", (S, S), (255, 255, 255, 255)), holo, shine.filter(ImageFilter.GaussianBlur(14)))
    sm = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sm).ellipse((0, 0, S - 1, S - 1), fill=215 if not revoked else 80)
    holo.putalpha(sm)
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((2, 2, S - 3, S - 3), outline=(255, 255, 255, 150 if not revoked else 50), width=3)
    card.alpha_composite(holo, (W - S - 56, H - S - 46))
    card.alpha_composite(ring, (W - S - 56, H - S - 46))

    if revoked:  # red rubber stamp across the card
        st = Image.new("RGBA", (900, 260), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        sd.rounded_rectangle((10, 10, 890, 250), radius=30, outline=RED + (230,), width=14)
        f = F(BLACK, 190)
        sd.text((450 - tw("REVOKED", f, 18) / 2, 8), "REVOKED", font=f, fill=RED + (230,))
        noise = Image.effect_noise((900, 260), 90).point(lambda v: 255 if v > 95 else 0)
        st.putalpha(ImageChops.multiply(st.getchannel("A"), noise))
        st = st.rotate(-14, expand=True, resample=Image.BICUBIC)
        st = st.resize((int(st.width * 1.2), int(st.height * 1.2)), Image.BICUBIC)
        card.alpha_composite(st, (W // 2 - st.width // 2 + 40, H // 2 - st.height // 2 + 40))

    # outer edge glow on a black canvas
    M = 24  # just enough room for the edge glow; outside the card stays see-through
    out = Image.new("RGBA", (W + 2 * M, H + 2 * M), (0, 0, 0, 0))
    edge = layer(W + 2 * M, H + 2 * M)
    ImageDraw.Draw(edge).rounded_rectangle((M, M, W + M - 1, H + M - 1), radius=48, outline=accent + (255,), width=4)
    out = Image.alpha_composite(out, glow(edge, (12, 5), (0.7 if not revoked else 0.25, 0.9)))
    out.alpha_composite(card, (M, M))
    out = Image.alpha_composite(out, edge)
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue()



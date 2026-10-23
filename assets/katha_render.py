import json, os, sys, random, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
M = 56
NAVY = (22, 32, 92)
NAVY2 = (38, 54, 140)
WHITE = (255, 255, 255)
GOLD = (255, 196, 40)
YELLOW = (255, 221, 74)
PINK, VIOLET, SKY, BLUE = (255, 92, 168), (140, 82, 255), (64, 170, 255), (40, 110, 255)
CREDIT = "KATHA AI · AJ Pokpak"


def font(spec, weight, size):
    return ImageFont.truetype(os.path.join(spec.get("fonts", "fonts/"), f"Prompt-{weight}.ttf"),
                              size, layout_engine=ImageFont.Layout.RAQM)


def wrap(draw, text, f, width):
    lines, cur = [], ""
    for tok in text.split(" "):
        cand = (cur + " " + tok).strip()
        if draw.textlength(cand, font=f) <= width:
            cur = cand; continue
        if cur: lines.append(cur)
        cur = ""
        for ch in tok:
            if draw.textlength(cur + ch, font=f) <= width: cur += ch
            else: lines.append(cur); cur = ch
    if cur: lines.append(cur)
    return lines


def fit(draw, text, spec, weight, size, width, min_size, max_lines=1):
    while size > min_size:
        f = font(spec, weight, size)
        if len(wrap(draw, text, f, width)) <= max_lines: return f
        size -= 4
    return font(spec, weight, min_size)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def multi_gradient(size, stops, horizontal=True):
    w, h = size
    n = w if horizontal else h
    strip = Image.new("RGBA", (n, 1))
    k = len(stops) - 1
    for i in range(n):
        t = i / max(1, n - 1) * k
        j = min(int(t), k - 1)
        strip.putpixel((i, 0), lerp(stops[j], stops[j + 1], t - j) + (255,))
    g = strip.resize((n, h if horizontal else w))
    return g if horizontal else g.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)


def gradient_text(img, xy, text, f, stops, stroke=0):
    d = ImageDraw.Draw(img)
    bb = d.textbbox(xy, text, font=f)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=f, fill=255)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    layer.paste(multi_gradient((bb[2] - bb[0] + 2, bb[3] - bb[1] + 2), stops), (bb[0], bb[1]))
    img.paste(layer, (0, 0), mask)


def shadow(img, box, radius, alpha=70, blur=18, dy=10):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((box[0], box[1] + dy, box[2], box[3] + dy), radius, fill=(20, 30, 90, alpha))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))


def sparkle(d, x, y, s, fill):
    d.polygon([(x, y - s), (x + s * .22, y - s * .22), (x + s, y), (x + s * .22, y + s * .22),
               (x, y + s), (x - s * .22, y + s * .22), (x - s, y), (x - s * .22, y - s * .22)], fill=fill)


def background(seed):
    img = multi_gradient((W, H), [(236, 228, 255), (222, 238, 255), (255, 236, 230)], horizontal=False).convert("RGBA")
    rnd = random.Random(seed)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse((620, -200, 1300, 420), fill=(170, 140, 255, 140))
    d.ellipse((-260, 140, 360, 700), fill=(255, 170, 210, 120))
    d.ellipse((520, 620, 1240, 1240), fill=(120, 190, 255, 130))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(110)))
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(rays)
    for i in range(7):
        a = math.radians(200 + i * 12)
        d.polygon([(W, 0), (W + 1600 * math.cos(a), 1600 * math.sin(a) * -1), (W + 1600 * math.cos(a + .06), -1600 * math.sin(a + .06))], fill=(255, 255, 255, 40))
    img.alpha_composite(rays.filter(ImageFilter.GaussianBlur(30)))
    bok = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(bok)
    for _ in range(26):
        x, y, r = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(14, 46)
        d.ellipse((x - r, y - r, x + r, y + r), fill=rnd.choice([(255, 255, 255, 90), (190, 170, 255, 70), (150, 210, 255, 70)]))
    img.alpha_composite(bok.filter(ImageFilter.GaussianBlur(6)))
    sp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    for x, y, s, c in [(60, 300, 26, VIOLET), (1010, 270, 20, SKY), (40, 640, 16, PINK), (1030, 690, 18, GOLD), (520, 250, 12, VIOLET)]:
        sparkle(d, x + rnd.randint(-8, 8), y + rnd.randint(-8, 8), s, c + (230,))
    img.alpha_composite(sp)
    return img


def pill(img, box, fill, radius=None, outline=None, width=0, sh=True):
    r = radius if radius is not None else (box[3] - box[1]) // 2
    if sh: shadow(img, box, r)
    ImageDraw.Draw(img).rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def render(spec, out):
    img = background(spec.get("title", ""))
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    d = ImageDraw.Draw(img)

    # --- header: logo + page name (top-left), tag (top-right)
    x0 = M
    logo = spec.get("logo")
    if logo and os.path.exists(logo):
        lg = Image.open(logo).convert("RGBA"); lg.thumbnail((170, 152))
        img.alpha_composite(lg, (M - 10, 30))
        x0 = M - 10 + lg.width + 12
    d.text((x0, 52), "KATHA AI", font=font(spec, "ExtraBold", 44), fill=NAVY)
    d.text((x0, 108), "AJ Pokpak · AI in Health", font=font(spec, "Medium", 26), fill=NAVY2)
    ft = font(spec, "SemiBold", 28)
    tag = "".join(ch for ch in spec.get("tag", "AI ใหม่") if ord(ch) < 0x2000).strip()
    tw = int(tmp.textlength(tag, font=ft))
    tb = (W - M - tw - 52, 66, W - M, 122)
    shadow(img, tb, 28)
    pg = multi_gradient((tb[2] - tb[0], tb[3] - tb[1]), [PINK, VIOLET])
    pm = Image.new("L", pg.size, 0)
    ImageDraw.Draw(pm).rounded_rectangle((0, 0, pg.width - 1, pg.height - 1), 28, fill=255)
    img.paste(pg, (tb[0], tb[1]), pm)
    ImageDraw.Draw(img).text((tb[0] + 26, tb[1] + 7), tag, font=ft, fill=WHITE)

    # --- headline block
    y = 222
    kicker = spec.get("kicker", "").strip()
    if kicker:
        fk = fit(tmp, kicker, spec, "Black", 120, W - 2 * M - 80, 64)
        bb = tmp.textbbox((0, 0), kicker, font=fk)
        kw, kh = bb[2] - bb[0], bb[3] - bb[1]
        box = (M, y, M + kw + 80, y + kh + 64)
        pill(img, box, (255, 255, 255, 255), radius=60, outline=(210, 220, 255), width=3)
        gradient_text(img, (M + 40 - bb[0], y + 32 - bb[1]), kicker, fk, [BLUE, VIOLET, PINK, (255, 150, 60)])
        y = box[3] - 14

    title = spec["title"].strip()
    fti = fit(tmp, title, spec, "Bold", 64, W - 2 * M - 70, 48, max_lines=1)
    if len(wrap(tmp, title, fti, W - 2 * M - 70)) > 1:
        fti = fit(tmp, title, spec, "Bold", 64, W - 2 * M - 70, 40, max_lines=2)
    tl = wrap(tmp, title, fti, W - 2 * M - 70)[:2]
    lh = int(fti.size * 1.32)
    tw = max(tmp.textlength(l, font=fti) for l in tl)
    box = (M + 20, y, min(W - M, int(M + 20 + tw + 70)), y + lh * len(tl) + 36)
    shadow(img, box, 40, alpha=90)
    bg = multi_gradient((box[2] - box[0], box[3] - box[1]), [NAVY, NAVY2])
    bm = Image.new("L", bg.size, 0)
    ImageDraw.Draw(bm).rounded_rectangle((0, 0, bg.width - 1, bg.height - 1), 40, fill=255)
    img.paste(bg, (box[0], box[1]), bm)
    for i, ln in enumerate(tl):
        ImageDraw.Draw(img).text((box[0] + 35, box[1] + 14 + i * lh), ln, font=fti, fill=WHITE)
    y = box[3] + 22

    hook = spec.get("hook", "").strip()
    if hook:
        fh = fit(tmp, hook, spec, "ExtraBold", 50, W - 2 * M - 150, 34, max_lines=2)
        hl = wrap(tmp, hook, fh, W - 2 * M - 150)[:2]
        hlh = int(fh.size * 1.3)
        hw = max(tmp.textlength(l, font=fh) for l in hl)
        hx1 = W - M - 20
        hx0 = int(hx1 - hw - 120)
        band = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        bh = hlh * len(hl) + 30
        bd.polygon([(hx0 + 18, y + 6), (hx1 - 60, y), (hx1 - 40, y + bh - 4), (hx0, y + bh + 4)], fill=YELLOW + (255,))
        img.alpha_composite(band)
        for i, ln in enumerate(hl):
            lw = tmp.textlength(ln, font=fh)
            ImageDraw.Draw(img).text((hx1 - 75 - lw, y + 12 + i * hlh), ln, font=fh, fill=NAVY)
        fq = font(spec, "Black", 130)
        ImageDraw.Draw(img).text((hx1 - 52, y - 46), "?", font=fq, fill=NAVY, stroke_width=6, stroke_fill=YELLOW)
        y += bh + 30

    # --- presenter (bottom-left) + bullet card (right)
    band_top = H - 236
    pres = spec.get("presenter")
    px1 = M
    if pres and os.path.exists(pres):
        p = Image.open(pres).convert("RGBA")
        ph = min(800, H - y + 4)
        p = p.resize((int(p.width * ph / p.height), ph), Image.LANCZOS)
        halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
        hx, hy = 20 + p.width // 2, H - ph + 230
        ImageDraw.Draw(halo).ellipse((hx - 300, hy - 300, hx + 300, hy + 300), fill=(255, 255, 255, 150))
        img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(60)))
        img.alpha_composite(p, (0, H - ph))
        px1 = int(p.width * 0.80)

    fb = font(spec, "Medium", 34)
    cx0, cx1 = max(px1, 470), W - M + 10
    tw_b = cx1 - cx0 - 120
    items = [wrap(tmp, b, fb, tw_b)[:2] for b in spec.get("bullets", [])[:4]]
    rows = sum(len(l) for l in items)
    ch = rows * 48 + (len(items) - 1) * 26 + 70
    card_top = max(y + 10, band_top - 92 - ch)
    box = (cx0, card_top, cx1, card_top + ch)
    shadow(img, box, 34, alpha=80, blur=22)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(box, 34, fill=(255, 255, 255, 215), outline=(255, 255, 255, 255), width=3)
    img.alpha_composite(ov)
    by = card_top + 35
    cols = [BLUE, VIOLET, PINK, (255, 150, 60)]
    fn = font(spec, "Bold", 28)
    for i, lines in enumerate(items):
        cx, cy = cx0 + 52, by + 24
        ImageDraw.Draw(img).ellipse((cx - 24, cy - 24, cx + 24, cy + 24), fill=cols[i % 4])
        n = str(i + 1)
        ImageDraw.Draw(img).text((cx - tmp.textlength(n, font=fn) / 2, cy - 22), n, font=fn, fill=WHITE)
        for j, ln in enumerate(lines):
            ImageDraw.Draw(img).text((cx0 + 96, by + j * 48), ln, font=fb, fill=NAVY)
        by += len(lines) * 48 + 26

    # --- bottom credit band with colourful waves
    waves = Image.new("RGBA", img.size, (0, 0, 0, 0))
    wd = ImageDraw.Draw(waves)
    for off, col in [(-46, GOLD), (-30, (40, 170, 90)), (-16, PINK)]:
        pts = [(x, band_top + off + 26 * math.sin(x / 170 + off / 20)) for x in range(0, W + 10, 10)]
        wd.polygon(pts + [(W, H), (0, H)], fill=col + (255,))
    pts = [(x, band_top + 24 * math.sin(x / 170)) for x in range(0, W + 10, 10)]
    img.alpha_composite(waves)
    nb = multi_gradient((W, H - band_top + 40), [NAVY, NAVY2, (60, 40, 150)])
    nm = Image.new("L", nb.size, 0)
    ImageDraw.Draw(nm).polygon([(x, y0 - band_top + 40) for x, y0 in pts] + [(W, nb.height), (0, nb.height)], fill=255)
    img.paste(nb, (0, band_top - 40), nm)
    d = ImageDraw.Draw(img)
    tx = M
    d.text((tx, band_top + 22), "เรียบเรียงโดย", font=font(spec, "Medium", 30), fill=(210, 220, 255))
    gradient_text(img, (tx, band_top + 58), spec.get("author", "ดร.ทรรศนีย์ บุญมั่น"), font(spec, "ExtraBold", 60), [GOLD, (255, 225, 120)])
    d.text((tx, band_top + 138), spec.get("author_role", "วิทยากรด้าน AI in Health"), font=font(spec, "SemiBold", 32), fill=WHITE)
    fc = font(spec, "Medium", 24)
    d.text((W - M - tmp.textlength(f"© {CREDIT}", font=fc), H - 46), f"© {CREDIT}", font=fc, fill=(200, 210, 255))
    if spec.get("date"):
        fd = font(spec, "Regular", 24)
        d.text((W - M - tmp.textlength(spec["date"], font=fd), H - 78), spec["date"], font=fd, fill=(200, 210, 255))

    img.convert("RGB").save(out, "PNG")


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    render(spec, sys.argv[2]); print("saved", sys.argv[2])

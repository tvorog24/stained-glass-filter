# -*- coding: utf-8 -*-

import random
import time
from gimpfu import *


def get_random_center(height, width):
    x = random.randint(0, width - 1)
    y = random.randint(0, height - 1)
    return x, y


def get_random_centers(n, height, width):
    random.seed(int(time.time()))
    centres = []
    for _ in range(n):
        centres.append(get_random_center(height, width))
    return centres


def process_neighbours(x, y, group_map, height, width):
    recruited_neighbours = []
    for sx in (-1, 0, 1):
        for sy in (-1, 0, 1):
            nx = sx + x
            ny = sy + y
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            if group_map[ny][nx] == -1:
                group_map[ny][nx] = group_map[y][x]
                recruited_neighbours.append((nx, ny))
    return recruited_neighbours


def init_group_map(height, width, centers):
    group_map = [[-1 for _ in range(width)] for _ in range(height)]
    group_id = 0
    for x, y in centers:
        group_map[y][x] = group_id
        group_id += 1
    return group_map


def divide_into_groups(group_map, centers, height, width):
    wave_front = {i: [centers[i]] for i in range(len(centers))}
    change_flag = True
    while change_flag:
        change_flag = False
        for key, value in wave_front.items():
            new_value = []
            for x, y in value:
                new_value += process_neighbours(x, y, group_map, height, width)
            wave_front[key] = new_value
            if len(new_value) != 0:
                change_flag = True


def create_group_map(n, height, width):
    centers = get_random_centers(n, height, width)
    group_map = init_group_map(height, width, centers)
    divide_into_groups(group_map, centers, height, width)
    return group_map


def create_bucket_set(k):
    return [{i: [] for i in range(k)} for _ in range(3)]


def init_buckets(n, k):
    buckets = []
    for _ in range(n):
        buckets.append(create_bucket_set(k))
    return buckets


def collect_colors(pixel_map, group_map, buckets, k, height, width):
    step = 256 // k
    for x in range(width):
        for y in range(height):
            gid = group_map[y][x]
            r, g, b = pixel_map[y][x]
            r_id = r // step
            g_id = g // step
            b_id = b // step
            buckets[gid][0][r_id].append(r)
            buckets[gid][1][g_id].append(g)
            buckets[gid][2][b_id].append(b)


def init_group_major_colors(n):
    return {i: [0, 0, 0] for i in range(n)}


def get_average(colors):
    if len(colors) == 0:
        return 0
    return sum(colors) // len(colors)


def calculate_major_color_rgb(buckets, group_id, rgb):
    bucket_set = buckets[group_id]
    keys = bucket_set[rgb].keys()
    bucket_id = max(keys, key=(lambda x: len(bucket_set[rgb][x])))
    color = get_average(bucket_set[rgb][bucket_id])
    return color


def calculate_major_group_colors(buckets, n):
    major_colors = init_group_major_colors(n)
    for gid in range(n):
        for rgb in range(3):
            color = calculate_major_color_rgb(buckets, gid, rgb)
            major_colors[gid][rgb] = color
    return major_colors


def recolour_pixels(pixel_map, group_map, major_colors, n, height, width):
    for x in range(width):
        for y in range(height):
            gid = group_map[y][x]
            pixel_map[y][x] = major_colors[gid]


def create_pixel_map_from_image(drawable, height, width):
    src_rgn = drawable.get_pixel_rgn(0, 0, width, height, False, False) # rgn -- ReGioN
    pixel_map = [[0, 0, 0] * width for _ in xrange(height)]
    for y in xrange(height):
        row = bytearray(src_rgn[0:width, y:y+1]) # считали целую строку
        off = 0
        shift = src_rgn.bpp
        for x in xrange(width):
            pixel_map[y][x] = [row[off], row[off + 1], row[off + 2]]
            off += shift

    return pixel_map


def apply_pixel_map_to_image(pixel_map, drawable, height, width):
    dst_rgn = drawable.get_pixel_rgn(0, 0, width, height, True, True)
    if drawable.has_alpha:
        src_rgn = drawable.get_pixel_rgn(0, 0, width, height, False, False)
        for y in xrange(height):
            image_row = bytearray(src_rgn[0:width, y:y + 1])
            out_row = bytearray(width * 4)
            pm_row = pixel_map[y]
            off = 0
            for x in xrange(width):
                r, g, b = pm_row[x]
                out_row[off] = r
                out_row[off + 1] = g
                out_row[off + 2] = b
                out_row[off + 3] = image_row[4 * x + 3]
                off += 4
            dst_rgn[0:width, y:y + 1] = str(out_row)
    else:
        for y in xrange(height):
            out_row = bytearray(width * 3)
            pm_row = pixel_map[y]
            off = 0
            for x in xrange(width):
                r, g, b = pm_row[x]
                out_row[off] = r
                out_row[off + 1] = g
                out_row[off + 2] = b
                off += 3
            dst_rgn[0:width, y:y + 1] = str(out_row)

    drawable.flush() # принудительная запись измемений
    drawable.merge_shadow(True) # сохранение изменений (слияние с теневой копией)
    drawable.update(0, 0, width, height) # обновление изображения в интерфейсе


def stained_glass_plugin(image, drawable, n, k):
    if n < 1:
        gimp.message(u"Число групп (n) должно быть >= 1")
        return
    if k not in (4, 8, 16, 32):
        gimp.message(u"Число корзин (k) должно быть или 4, или 8, или 16, или 32")
        return

    pdb.gimp_image_undo_group_start(image)
    gimp.progress_init(u"Создание витражного эффекта...")

    try:
        width = drawable.width
        height = drawable.height

        # step 1
        gimp.progress_update(0.1)
        group_map = create_group_map(n, height, width)

        # step 2
        gimp.progress_update(0.3)
        pixel_map = create_pixel_map_from_image(drawable, height, width)

        # step 3
        gimp.progress_update(0.4)
        buckets = init_buckets(n, k)

        # step 4
        gimp.progress_update(0.5)
        collect_colors(pixel_map, group_map, buckets, k, height, width)

        # step 5
        gimp.progress_update(0.6)
        major_colors = calculate_major_group_colors(buckets, n)

        # step 6
        gimp.progress_update(0.8)
        recolour_pixels(pixel_map, group_map, major_colors, n, height, width)

        # step 7
        gimp.progress_update(0.9)
        apply_pixel_map_to_image(pixel_map, drawable, height, width)

        gimp.progress_update(1.0)

    except Exception as e:
        try:
            import traceback
            gimp.message(u"Ошибка: %s" % unicode(e))
            gimp.message(u"Подробности:\n%s" % traceback.format_exc())
        except:
            pass
    finally:
        pdb.gimp_image_undo_group_end(image)
        pdb.gimp_displays_flush()

register(
    "python_fu_stained_glass",
    "Stained glass effect",
    "Creates stained glass effect by dividing pixels into groups and recolouring",
    "Taisiya Vorobyeva",
    "Taisiya Vorobyeva",
    "2025",
    "Stained glass effect",
    "RGB*",
    [
        (PF_IMAGE, "image", "Input image", None),
        (PF_DRAWABLE, "drawable", "Input drawable", None),
        (PF_INT, "n", "Number of groups", 10),
        (PF_INT, "k", "Number of buckets", 8),
    ],
    [],
    stained_glass_plugin,
    menu="<Image>/Filters/Stained Glass"
)

main()
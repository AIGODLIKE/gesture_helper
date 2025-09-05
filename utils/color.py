from math import fabs

import numpy as np


def clamp(a, b, c):
    if a < b:
        return b
    elif a > c:
        return c
    return a


def hsv_to_rgb(h, s, v):
    nr = fabs(h * 6.0 - 3.0) - 1.0
    ng = 2.0 - fabs(h * 6.0 - 2.0)
    nb = 2.0 - fabs(h * 6.0 - 4.0)

    nr = clamp(nr, 0.0, 1.0)
    nb = clamp(nb, 0.0, 1.0)
    ng = clamp(ng, 0.0, 1.0)

    r_r = ((nr - 1.0) * s + 1.0) * v
    r_g = ((ng - 1.0) * s + 1.0) * v
    r_b = ((nb - 1.0) * s + 1.0) * v

    return (
        r_r,
        r_g,
        r_b,
    )


def linear_to_srgb(c_linear):
    # 对每个颜色分量进行伽马校正
    c_srgb = np.where(c_linear <= 0.0031308, 12.92 * c_linear, 1.055 * (c_linear ** (1 / 2.4)) - 0.055)
    return c_srgb  # 假设image是一个linear RGB图像


def srgb_to_linear(c_srgb):
    # 对每个颜色分量进行逆伽马校正
    c_linear = np.where(c_srgb <= 0.04045, c_srgb / 12.92, ((c_srgb + 0.055) / 1.055) ** 2.4)
    return c_linear

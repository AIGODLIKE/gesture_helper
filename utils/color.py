import numpy as np


def linear_to_srgb(c_linear):
    # Apply gamma correction per channel
    c_srgb = np.where(c_linear <= 0.0031308, 12.92 * c_linear, 1.055 * (c_linear ** (1 / 2.4)) - 0.055)
    return c_srgb  # Assumes linear RGB input

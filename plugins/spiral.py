import numpy as np
from math import fmod, fabs, sqrt, pow, tan, pi, atan2
from copy import deepcopy

from lib.transition import Transition
from lib.buffer_utils import BufferUtils


class Spiral(Transition):
    """
    Spiral wipe
    """

    def __init__(self, app):
        Transition.__init__(self, app)
        self.revolutions = 3
        self.angle = 0.0
        self.radius = 0.0

    def __str__(self):
        return "Spiral"

    def setup(self):
        self.num_strands, self.num_pixels = BufferUtils.get_buffer_size(self._app)

        self.scene_bb = self._app.scene.get_fixture_bounding_box()
        self.scene_center = (self.scene_bb[0] + (self.scene_bb[2] - self.scene_bb[0]) / 2, self.scene_bb[1] + (self.scene_bb[3] - self.scene_bb[1]) / 2)
        dx = self.scene_bb[2] - self.scene_center[0]
        dy = self.scene_bb[3] - self.scene_center[1]
        self.scene_radius = sqrt(pow(dx,2) + pow(dy, 2))

        self.locations = self._app.scene.get_all_pixel_locations()
        self.buffer_addr = {}
        self.angles = {}
        self.radii = {}
        for pixel, location in self.locations:
            self.buffer_addr[pixel] = BufferUtils.get_buffer_address(self._app, pixel)
            dy = location[1] - self.scene_center[1]
            dx = location[0] - self.scene_center[0]
            angle = (atan2(dy, dx) + pi) / (2.0 * pi)
            self.radii[pixel] = sqrt(pow(dx,2) + pow(dy, 2))
            self.angles[pixel] = angle

    def reset(self):
        self.mask = np.tile(False, (self.num_strands, self.num_pixels, 3))
        self.angle = 0.0
        self.radius = 0.0
        self.active = deepcopy(self.locations)

    def get(self, start, end, progress):

        radius_progress = fmod(progress * self.revolutions, 1.0)
        distance_progress = self.scene_radius * progress
        distance_cutoff = (1.0 / self.revolutions) * self.scene_radius * progress

        for pixel, location in self.active:
            angle = self.angles[pixel]
            distance = self.radii[pixel]

            if distance < distance_cutoff or (distance < distance_progress and angle < radius_progress):
                strand, pa = self.buffer_addr[pixel]
                self.mask[strand][pa][:] = True
                self.active.remove((pixel, location))

        start[self.mask] = 0.0
        end[np.invert(self.mask)] = 0.0
        return start + end

    def _is_point_inside_wipe(self, point, progress):
        return np.dot((point - self.wipe_point), self.wipe_vector) >= 0
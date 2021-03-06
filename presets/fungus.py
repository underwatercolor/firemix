import colorsys
import random

from lib.raw_preset import RawPreset
from lib.colors import uint8_to_float, float_to_uint8
from lib.color_fade import ColorFade
from lib.parameters import FloatParameter, IntParameter, HSVParameter


class Fungus(RawPreset):
    """
    Spreading fungus
    Illustrates use of Scene.get_pixel_neighbors.

    Fungal pixels go through three stages:  Growing, Dying, and then Fading Out.
    """

    _growing = []
    _alive = []
    _dying = []
    _fading_out = []

    # Configurable parameters
    _spontaneous_birth_probability = 0.0001

    # Internal parameters
    _time = {}
    _pop = 0
    _fader = None
    _growth_time = 0.6
    _life_time = 1.0
    _isolated_life_time = 1.0
    _death_time = 7.0
    _birth_rate = 0.05
    _spread_rate = 0.25
    _fade_out_time = 4.0
    _mass_destruction_time = 10.0
    _mass_destruction_threshold = 150
    _pop_limit = 500
    _alive_color = (1.0, 0.0, 1.0)
    _dead_color = (0.0, 1.0, 1.0)

    def setup(self):
        self._pop = 0
        self._time = {}
        self.add_parameter(FloatParameter('growth-time', self._growth_time))
        self.add_parameter(FloatParameter('life-time', self._life_time))
        self.add_parameter(FloatParameter('isolated-life-time', self._isolated_life_time))
        self.add_parameter(FloatParameter('death-time', self._death_time))
        self.add_parameter(FloatParameter('birth-rate', self._birth_rate))
        self.add_parameter(FloatParameter('spread-rate', self._spread_rate))
        self.add_parameter(FloatParameter('fade-out-time', self._fade_out_time))
        self.add_parameter(FloatParameter('mass-destruction-time', self._mass_destruction_time))
        self.add_parameter(IntParameter('mass-destruction-threshold', self._mass_destruction_threshold))
        self.add_parameter(IntParameter('pop-limit', self._pop_limit))
        self.add_parameter(HSVParameter('alive-color', self._alive_color))
        self.add_parameter(HSVParameter('dead-color', self._dead_color))
        self.parameter_changed(None)

    def reset(self):
        self._growing = []
        self._alive = []
        self._dying = []
        self._fading_out = []
        self._pop = 0
        self._time = {}
        self.parameter_changed(None)

    def parameter_changed(self, parameter):
        self._setup_colors()
        self._growth_time = self.parameter('growth-time').get()
        self._life_time = self.parameter('life-time').get()
        self._isolated_life_time = self.parameter('isolated-life-time').get()
        self._death_time = self.parameter('death-time').get()
        self._birth_rate = self.parameter('birth-rate').get()
        self._spread_rate = self.parameter('spread-rate').get()
        self._fade_out_time = self.parameter('fade-out-time').get()
        self._mass_destruction_time = self.parameter('mass-destruction-time').get()
        self._mass_destruction_threshold = self.parameter('mass-destruction-threshold').get()
        self._pop_limit = self._pop_limit

    def _setup_colors(self):
        self._alive_color_rgb = float_to_uint8(colorsys.hsv_to_rgb(*self.parameter('alive-color').get()))
        self._dead_color_rgb = float_to_uint8(colorsys.hsv_to_rgb(*self.parameter('dead-color').get()))
        fade_colors = [(0., 0., 0.), self.parameter('alive-color').get(), self.parameter('dead-color').get(), (0., 0., 0.)]
        self._fader = ColorFade('hsv', fade_colors, tick_rate=self._mixer.get_tick_rate())

    def draw(self, dt):

        # Ensure that empty displays start up with some seeds
        p_birth = (1.0 - self._spontaneous_birth_probability) if self._pop > 5 else 0.5

        # Spontaneous birth: Rare after startup
        if (self._pop < self._pop_limit) and random.random() > p_birth:
            address = ( random.randint(0, self._max_strand - 1),
                        random.randint(0, self._max_fixture - 1),
                        random.randint(0, self._max_pixel - 1))
            if address not in (self._growing + self._alive + self._dying + self._fading_out):
                self._growing.append(address)
                self._time[address] = dt
                self._pop += 1

        # Color growth
        for address in self._growing:
            neighbors = self.scene().get_pixel_neighbors(address)
            p, color = self._get_next_color(address, self._growth_time, dt)
            if p >= 1.0:
                self._growing.remove(address)
                self._alive.append(address)
                self._time[address] = dt
            self.setp(address, color)

            # Spread
            if (self._pop < self._pop_limit) and random.random() > (1.0 - self._spread_rate):
                spread = neighbors[random.randint(0, len(neighbors) - 1)]
                if spread not in (self._growing + self._alive + self._dying + self._fading_out):
                    self._growing.append(spread)
                    self._time[spread] = dt
                    self._pop += 1

        # Lifetime
        for address in self._alive:
            neighbors = self.scene().get_pixel_neighbors(address)
            live_neighbors = [i for i in neighbors if i in self._alive]
            lt = self.parameter('life-time').get()
            if len(neighbors) < 2:
                lt = self._isolated_life_time

            if len(live_neighbors) < 2 and ((dt - self._time[address]) / lt) >= 1.0:
                self._alive.remove(address)
                self._dying.append(address)
                self._time[address] = dt
                self._pop -= 1

            self.setp(address, self._alive_color_rgb)

            # Spread
            if (self._pop < self._pop_limit) and random.random() > (1.0 - self._birth_rate):
                spread = neighbors[random.randint(0, len(neighbors) - 1)]
                if spread not in (self._growing + self._alive + self._dying + self._fading_out):
                    self._growing.append(spread)
                    self._time[spread] = dt
                    self._pop += 1

        # Color decay
        for address in self._dying:
            p, color = self._get_next_color(address, self._death_time, dt)
            if p >= 1.0:
                self._dying.remove(address)
                self._fading_out.append(address)
                self._time[address] = dt
            self.setp(address, color)

        # Fade out
        for address in self._fading_out:
            p, color = self._get_next_color(address, self._fade_out_time, dt)
            if p >= 1.0:
                self._fading_out.remove(address)
            self.setp(address, color)

        # Mass destruction
        if (self._pop == self._pop_limit) or \
                (self._pop > self._mass_destruction_threshold and ((dt % self._mass_destruction_time) == 0)):
            for i in self._alive:
                if random.random() > 0.95:
                    self._alive.remove(i)
                    self._dying.append(i)
                    self._pop -= 1
            for i in self._growing:
                if random.random() > 0.85:
                    self._growing.remove(i)
                    self._dying.append(i)
                    self._pop -= 1

    def _get_next_color(self, address, time_target, dt):
        """
        Returns the next color for a pixel, given the pixel's current state
        """
        progress = (dt - self._time[address]) / time_target

        if progress > 1.0:
            progress = 1.0
        elif dt == self._time[address]:
            progress = 0.0

        idx = progress / 3.0
        if time_target == self._death_time:
            idx += (1.0 / 3.0)
        elif time_target == self._fade_out_time:
            idx += (2.0 / 3.0)

        return (progress, self._fader.get_color(idx))

import os, pygame
import datetime
import time
import threading

from boat import Boat
from environment import Environment
from strategies.base import Base
from settings import Settings


class UpdateThread (threading.Thread):
    """Thread for updating the steering strategy"""
    FPS = 5

    def __init__(self, boat:Boat, env:Environment, strategy:Base):
        threading.Thread.__init__(self)
        self._boat = boat
        self._env = env
        self._strategy = strategy
        self._clock = pygame.time.Clock()

    def run(self):
        while 1:
            # update steering strategy
            self._strategy.update()

            # sleep remainder of frame
            self._clock.tick(Settings.UPDATE_FPS)
            fps = self._clock.get_fps()

            # update boat with current fps
            if fps > 0:
                self._boat.set_update_fps(fps)
                self._strategy.set_update_fps(fps)


class Simulator:
    """Single boat simulator"""

    SIZE = 800, 600
    BG_COLOR = 0, 0, 255
    TEXT_COLOR = 255, 255, 255
    FPS = 20

    def __init__(self, boat, env, strategies, shuffle_interval=10):
        self._boat = boat
        self._env = env
        self._strategies = strategies
        self._shuffle_interval = shuffle_interval

        # pick first strategy as default
        self._strategy_id = 0
        self._strategy = strategies[self._strategy_id]

        pygame.init()
        pygame.font.init()

        self._font = pygame.font.SysFont('Arial', 30)
        self._smallfont = pygame.font.SysFont('Arial', 20)
        self._screen = pygame.display.set_mode(self.SIZE)
        self._clock = pygame.time.Clock()

    def write_text(self, text, row):
        pos = 500, 30 + (row * 30)
        textsurface = self._font.render(text, True, self.TEXT_COLOR)
        self._screen.blit(textsurface, pos)

    def run(self):
        shuffle_time = time.time() + self._shuffle_interval

        # initial shuffle
        self._env.shuffle()
        self._boat.shuffle()

        # start thread for steering strategy
        thread = UpdateThread(self._boat, self._env, self._strategy)
        thread.daemon = True
        thread.start()

        while 1:
            # redraw everything
            self._screen.fill(self.BG_COLOR)
            self._env.update()
            self._boat.update()
            self._boat.draw(self._screen)
            self._env.draw(self._screen)

            # calculate mean of absolute course error
            if self._boat.history.shape[0] > 0:
                mae = self._boat.history.course_error.abs().mean()
            else:
                mae = 0

            self.write_text("Boat angle: %.1f°" % self._boat.boat_angle, 0)
            self.write_text("Target angle: %.1f°" % self._boat.target_angle, 1)
            self.write_text("Current deviation: %.1f°" % self._boat.get_course_error(), 2)
            self.write_text("Boat heel: %.1f°" % self._boat.boat_heel, 3)
            self.write_text("Rudder angle: %.1f°" % self._boat.rudder_angle, 4)
            self.write_text("Boat speed: %.1f knots" % self._boat.speed, 5)
            self.write_text("Angle of attack: %.1f°" % self._boat.get_angle_of_attack(), 6)
            self.write_text("Wind direction: %.1f°" % self._env.wind_direction, 8)
            self.write_text("Wind speed: %.1f knots" % self._env.wind_speed, 9)
            self.write_text("MAE: %.1f°" % mae, 11)
            self.write_text("Strategy: %s" % type(self._strategy).__name__, 13)

            textsurface = self._smallfont.render(
                "Press keys to change: 1/2 for target angle, 3/4 for wind direction, 5/6 for wind speed, s to change strategy, q to quit", True, self.TEXT_COLOR)
            self._screen.blit(textsurface, (20, 565))

            # display new frame
            pygame.display.flip()

            # shuffle once in a while
            if self._shuffle_interval and time.time() > shuffle_time:
                self._env.shuffle()
                self._boat.shuffle()
                shuffle_time += self._shuffle_interval

            # check key events
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:

                    # switch strategy
                    if event.key == pygame.K_s:
                        self._strategy_id = self._strategy_id + 1 if self._strategy_id < len(self._strategies) - 1 else 0
                        self._strategy = self._strategies[self._strategy_id]

                    # save log and quit
                    if event.key == pygame.K_q:
                        date = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d_%H%M')
                        filename = os.path.join('data', 'logs', 'history_%s.csv' % date)
                        self._boat.history.to_csv(filename)
                        print("Wrote datalog to %s" % filename)
                        exit()

            # sleep for the remainder of this frame
            self._clock.tick(Settings.DRAW_FPS)
            fps = self._clock.get_fps()

            # update boat with current fps
            if fps > 0:
                self._boat.set_draw_fps(fps)

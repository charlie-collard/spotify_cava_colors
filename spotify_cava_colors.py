#!/usr/bin/env python
from PIL import Image
from time import sleep
from io import BytesIO
from math import sqrt
import colorsys
import requests
import sys
import os
import re
import subprocess

RED = 0
GREEN = 1
BLUE = 2
HUE = 0
SATURATION = 1
VALUE = 2

FILE_PATH = os.path.realpath(__file__)[:os.path.realpath(__file__).rfind("/")]
REFRESH_TOKEN_PATH = FILE_PATH + "/auth/refresh_token"
ACCESS_TOKEN_PATH = FILE_PATH + "/auth/access_token"
APP_CREDENTIALS_PATH = FILE_PATH + "/auth/app_credentials"
HOME_DIR = os.path.expanduser("~")
CAVA_CONFIG = HOME_DIR + "/.config/cava/config"

def log(string):
    if "-d" in sys.argv:
        print(string)

def print_color(color):
    r, g, b = int(color[0]*255), int(color[1]*255), int(color[2]*255)
    log("\x1b[48;2;%d;%d;%dm        \x1b[0m #%02x%02x%02x" % (r,g,b,r,g,b))

def bucket_sort(pixels, levels):
    color_ranges = [
            max(pixels, key=lambda x: x[color])[color] -
            min(pixels, key=lambda x: x[color])[color]
            for color in [RED, GREEN, BLUE]
            ]

    split_color = color_ranges.index(max(color_ranges))
    sorted_px = sorted(pixels, key=lambda x: x[split_color])

    # Bisect the pixels
    px1 = sorted_px[:len(sorted_px)/2]
    px2 = sorted_px[len(sorted_px)/2:]
    levels -= 1
    if levels <= 0:
        return [px1, px2]
    else:
        return bucket_sort(px1, levels) + bucket_sort(px2, levels)

class RequestCtrl:
    GET = requests.get
    POST = requests.post

    PREFIX = "https://api.spotify.com/v1"
    CURRENTLY_PLAYING = {"url": PREFIX + "/me/player/currently-playing", "method": GET}
    NEW_TOKEN = {"url": "https://accounts.spotify.com/api/token", "method": POST}

    def __init__(self):
        try:
            with open(ACCESS_TOKEN_PATH) as f:
                    self.access_token = f.read()[:-1]
        except IOError:
            with open(ACCESS_TOKEN_PATH, "w") as f:
                f.write("")
            self.access_token = ""
        with open(REFRESH_TOKEN_PATH) as f:
            self.refresh_token = f.read()[:-1]
        with open(APP_CREDENTIALS_PATH) as f:
            credentials = f.read()[:-1]
            self.client_id, self.client_secret = credentials.split(":")

    def make_request(self, endpoint, extra={}):
        url = endpoint["url"]
        method = endpoint["method"]
        log("Making request to '%s'..." % url)
        headers = {
                "Authorization": "Bearer %s" % self.access_token
                }
        if method.func_name == self.POST.func_name:
            if endpoint == self.NEW_TOKEN:
                headers.pop("Authorization")
            r = method(url, data=extra, headers=headers)
        else:
            r = method(url, params=extra, headers=headers)

        # Obey rate limiting
        if r.status_code == 429:
            backoff_time = int(r.headers["Retry-After"])
            log("Hit rate limit, sleeping for %d seconds..." % backoff_time)
            time.sleep(backoff_time)
            return self.make_request(endpoint, extra)

        json = r.json()
        if "error" in json:
            if endpoint != self.NEW_TOKEN:
                token_extras = {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token"
                        }
                token_r = self.make_request(self.NEW_TOKEN, extra=token_extras)
                self.access_token = token_r["access_token"]
                with open(ACCESS_TOKEN_PATH, "w") as f:
                    f.write(self.access_token + "\n")
                return self.make_request(endpoint, extra)
            else:
                log("Error, could not get new access token:\n" + str(r.json()))
                exit()
        else:
            return json

def best_color(colors):
    fitnesses = [color[VALUE]*300 for color in colors]
    rgb_colors = [colorsys.hsv_to_rgb(c[HUE], c[SATURATION], c[VALUE]) for c in colors]
    for i in range(len(rgb_colors)):
        color = rgb_colors[i]
        color_difference = abs(color[RED] - color[GREEN]) + abs(color[RED] - color[BLUE]) + abs(color[GREEN] - color[BLUE])
        fitnesses[i] += color_difference*150
    return colors[fitnesses.index(max(fitnesses))]

if __name__ == "__main__":
    while True:
        line = sys.stdin.readline()
        if "Spotify" in line:
            while True:
                line = sys.stdin.readline()
                if "image_data" in line:
                    break
            while True:
                line = sys.stdin.readline()
                if "array of bytes" in line:
                    break
            px = []
            cur = []
            while True:
                line = sys.stdin.readline()
                if "]" in line:
                    break
                line = line.split()
                while len(line) > 0:
                    cur.append(int(line.pop(0), 16))
                    if len(cur) == 3:
                        px.append(tuple(cur))
                        cur = []

            # ctrl = RequestCtrl()
            # response = ctrl.make_request(RequestCtrl.CURRENTLY_PLAYING)
            # try:
                # images = response["item"]["album"]["images"]
                # assert len(images) != 0
                # smallest_url = min(images, key=lambda x: x["width"])["url"]
            # except (KeyError, AssertionError):
                # log("Error getting image url")
                # exit()

            # img = Image.open(BytesIO(requests.get(smallest_url).content))
            # px = img.getdata()
            # px = list(px)
            px = filter(lambda x: not (x[RED]>235 and x[GREEN]>235 and x[BLUE]>235), px)
            px = filter(lambda x: not (x[RED]<30 and x[GREEN]<30 and x[BLUE]<30), px)
            px = map(lambda x: (x[RED]/255., x[GREEN]/255., x[BLUE]/255.), px)

            # Split the pixels into 2**n buckets
            buckets = bucket_sort(px, 3)
            colors = []
            for bucket in buckets:
                color_sums = reduce(lambda x, y: (x[RED]+y[RED], x[GREEN]+y[GREEN], x[BLUE]+y[BLUE]), bucket)
                rgb_color = map(lambda x: x/len(bucket), color_sums)
                hsv_color = colorsys.rgb_to_hsv(rgb_color[RED], rgb_color[GREEN], rgb_color[BLUE])
                print_color(rgb_color)
                colors.append(hsv_color)

            # Pick the brightest color
            color1 = best_color(colors)
            colors.remove(color1)
            # Filter colors with similar hues to the first chosen
            no_similar_colors = filter(lambda x: min(1-abs(x[HUE]-color1[HUE]), abs(x[HUE]-color1[HUE])) > 0.1, colors)
            if len(no_similar_colors) != 0 and any(map(lambda x: x[VALUE]>0.4, no_similar_colors)):
                color2 = max(no_similar_colors, key=lambda x: x[VALUE])
            else:
                color2 = best_color(colors)

            # Darkest should be first
            if color1[VALUE] > color2[VALUE]:
                color1, color2 = color2, color1

            rgb_color1 = colorsys.hsv_to_rgb(color1[HUE], color1[SATURATION], color1[VALUE])
            rgb_color2 = colorsys.hsv_to_rgb(color2[HUE], color2[SATURATION], color2[VALUE])
            log("Color 1:")
            print_color(rgb_color1)
            log("Color 2:")
            print_color(rgb_color2)
            r1, g1, b1 = int(rgb_color1[RED]*255), int(rgb_color1[GREEN]*255), int(rgb_color1[BLUE]*255)
            r2, g2, b2 = int(rgb_color2[RED]*255), int(rgb_color2[GREEN]*255), int(rgb_color2[BLUE]*255)
            # Clamp colors in case of floating point rounding errors
            r1, g1, b1 = max(r1, 0), max(g1, 0), max(b1, 0)
            r2, g2, b2 = max(r2, 0), max(g2, 0), max(b2, 0)
            r1, g1, b1 = min(r1, 255), min(g1, 255), min(b1, 255)
            r2, g2, b2 = min(r2, 255), min(g2, 255), min(b2, 255)

            with open(CAVA_CONFIG) as f:
                config_contents = f.read()
            config_contents = re.sub(r"^gradient_color_1 = '#.*'$",
                    "gradient_color_1 = '#%02x%02x%02x'" % (r1, g1, b1),
                    config_contents,
                    flags=re.MULTILINE)
            config_contents = re.sub(r"^gradient_color_2 = '#.*'$",
                    "gradient_color_2 = '#%02x%02x%02x'" % (r2, g2, b2),
                    config_contents,
                    flags=re.MULTILINE)

            with open(CAVA_CONFIG, "w") as f:
                f.write(config_contents)

            # Tell cava to reload its config
            subprocess.Popen(["pkill", "-USR1", "cava"])

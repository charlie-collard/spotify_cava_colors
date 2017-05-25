from PIL import Image
from time import sleep
from io import BytesIO
import itertools
import sys
import colorsys
import requests
import os
import re
import subprocess

RED = 0
GREEN = 1
BLUE = 2
HOME_DIR = os.path.expanduser("~")
CAVA_CONFIG = HOME_DIR + "/.config/cava/config"

def print_color(color):
    r, g, b = int(color[0]*255), int(color[1]*255), int(color[2]*255)
    print("\x1b[48;2;%d;%d;%dm        \x1b[0m" % (r,g,b) + " #%02x%02x%02x" % (r,g,b))
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
    if levels == 0:
        return [px1, px2]
    else:
        return bucket_sort(px1, levels) + bucket_sort(px2, levels)

# Lower is better (distance from 1/6 difference)
def rate_fitness(color1, color2):
    return abs(1./6 - abs(color1[0] - color2[0]))

class RequestCtrl:
    GET = requests.get
    POST = requests.post

    PREFIX = "https://api.spotify.com/v1"
    CURRENTLY_PLAYING = {"url": PREFIX + "/me/player/currently-playing", "method": GET}
    NEW_TOKEN = {"url": "https://accounts.spotify.com/api/token", "method": POST}

    def __init__(self):
        with open("auth/refresh_token") as f:
            self.refresh_token = f.read()[:-1]
        with open("auth/access_token") as f:
            self.access_token = f.read()[:-1]
        with open("auth/app_credentials") as f:
            credentials = f.read()[:-1]
            self.client_id, self.client_secret = credentials.split(":")

    def make_request(self, endpoint, extra={}):
        url = endpoint["url"]
        method = endpoint["method"]
        print("Making request to '%s'..." % url)
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
                print(token_extras)
                token_r = self.make_request(self.NEW_TOKEN, token_extras)
                self.access_token = token_r["access_token"]
                with open("auth/access_token", "w") as f:
                    f.write(self.access_token + "\n")
                return self.make_request(endpoint, extra)
            else:
                print("Error, could not get new access token:\n" + str(r.json()))
                exit()
        else:
            return json


if __name__ == "__main__":
    ctrl = RequestCtrl()
    response = ctrl.make_request(RequestCtrl.CURRENTLY_PLAYING)
    try:
        images = response["item"]["album"]["images"]
        assert len(images) != 0
        largest_url = max(images, key=lambda x: x["width"])["url"]
    except (KeyError, AssertionError):
        print("Error getting image url")
        exit()

    img = Image.open(BytesIO(requests.get(largest_url).content))
    px = img.getdata()
    px = list(px)
    px = filter(lambda x: not (x[0]>250 and x[1]>250 and x[2]>250), px)
    px = filter(lambda x: not (x[0]<30 and x[1]<30 and x[2]<30), px)
    px = map(lambda x: (x[0]/255., x[1]/255., x[2]/255.), px)

    # Split the pixels into 2**n buckets
    buckets = bucket_sort(px, 4)
    colors = []
    for bucket in buckets:
        color_sums = reduce(lambda x, y: (x[0]+y[0], x[1]+y[1], x[2]+y[2]), bucket)
        color = map(lambda x: x/len(bucket), color_sums)
        hsv_color = colorsys.rgb_to_hsv(color[0], color[1], color[2])
        colors.append(hsv_color)
        print_color(color)

    best_pair = (colors[0], colors[1])
    best_fitness = rate_fitness(colors[0], colors[1])
    for i in range(len(colors)):
        color = colors[i]
        for other_color in colors[i+1:]:
            fitness = rate_fitness(color, other_color)
            if fitness < best_fitness:
                best_pair = (color, other_color)
                best_fitness = fitness

    # Darkest should be first
    if best_pair[0][2] > best_pair[1][2]:
        best_pair = (best_pair[1], best_pair[0])
    print("Best colors found with a fitness of %f" % best_fitness)
    rgb_color1 = colorsys.hsv_to_rgb(best_pair[0][0], best_pair[0][1], best_pair[0][2])
    rgb_color2 = colorsys.hsv_to_rgb(best_pair[1][0], best_pair[1][1], best_pair[1][2])
    print_color(rgb_color1)
    print_color(rgb_color2)

    with open(CAVA_CONFIG) as f:
        cava_config = f.read()
    r1, g1, b1 = int(rgb_color1[0]*255), int(rgb_color1[1]*255), int(rgb_color1[2]*255)
    r2, g2, b2 = int(rgb_color2[0]*255), int(rgb_color2[1]*255), int(rgb_color2[2]*255)
    cava_config = re.sub(r"^gradient_color_1 = '#.*$",
            "gradient_color_1 = '#%02x%02x%02x'" % (r1, g1, b1),
            cava_config,
            flags=re.MULTILINE)
    cava_config = re.sub(r"^gradient_color_2 = '#.*$",
            "gradient_color_2 = '#%02x%02x%02x'" % (r2, g2, b2),
            cava_config,
            flags=re.MULTILINE)

    with open(CAVA_CONFIG, "w") as f:
        f.write(cava_config)

    subprocess.Popen(["pkill", "-USR1", "cava"])

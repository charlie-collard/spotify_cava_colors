from PIL import Image
import itertools
import sys
import colorsys

RED = 0
GREEN = 1
BLUE = 2

def print_color(color):
    r, g, b = int(color[0]*255), int(color[1]*255), int(color[2]*255)
    print("\x1b[48;2;%d;%d;%dm        \x1b[0m" % (r,g,b) + " #%02x%02x%02x" % (r,g,b))

def four_color_split(pixels):
    return bucket_sort(pixels, 4)

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

if __name__ == "__main__":
    img = Image.open(sys.argv[1])
    px = img.getdata()
    px = list(px)
    px = filter(lambda x: not (x[0]>250 and x[1]>250 and x[2]>250), px)
    px = filter(lambda x: not (x[0]<10 and x[1]<10 and x[2]<10), px)
    px = map(lambda x: (x[0]/255., x[1]/255., x[2]/255.), px)
    buckets = four_color_split(px)
    colors = []
    for bucket in buckets:
        color_sums = reduce(lambda x, y: (x[0]+y[0], x[1]+y[1], x[2]+y[2]), bucket)
        color = map(lambda x: x/len(bucket), color_sums)
        colors.append(colorsys.rgb_to_hsv(color[0], color[1], color[2]))
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
    print("Best colors found with a distance of %f" % best_fitness)
    print_color(colorsys.hsv_to_rgb(best_pair[0][0], best_pair[0][1], best_pair[0][2]))
    print_color(colorsys.hsv_to_rgb(best_pair[1][0], best_pair[1][1], best_pair[1][2]))

#!/usr/bin/env python3

"""
This script creates a random floor layout/patterns and saves the
pattern as .png image and as .csv file.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
import os
from random import uniform
arena_size = os.environ.get("ARENADIM")
if arena_size is None:
    print("ARENADIM is not set; generating the floor with the default canvas size")
else:
    print(arena_size)

argos_name = os.environ.get("ARGOSNAME", "").strip().lower()
print(f"ARGOSNAME={argos_name or 'unset'}")

np.random.seed(seed=1)

percentage_white = 0.25
tiles_per_side_list = [22, 31, 38]
#tiles_per_side_list = [10]

def create_shuffled_matrix(tiles_per_side):

    total_tiles = tiles_per_side ** 2
    percentage_black = 1 - percentage_white
    total_white = total_tiles * percentage_white
    total_black = total_tiles * percentage_black
    
    white_tiles_array = np.zeros(int(total_white))
    black_tiles_array = np.ones(int(total_black))
    total_tiles_array = np.append(white_tiles_array, black_tiles_array)


    np.random.shuffle(total_tiles_array)

    # Check if one tile is missing
    if (len(total_tiles_array) == total_tiles - 1):
        total_tiles_array = np.append(total_tiles_array, 1.0)
        print("Missing one tile")
    X = total_tiles_array.reshape((tiles_per_side, tiles_per_side), order='F')
        
    fig = plt.figure()
    plt.xticks([])
    plt.yticks([])
    plt.gca().set_axis_off()
    plt.subplots_adjust(top = 1, bottom = 0, right = 1, left = 0, 
                        hspace = 0, wspace = 0)
    plt.gca().xaxis.set_major_locator(plt.NullLocator())
    plt.gca().yaxis.set_major_locator(plt.NullLocator())
    plt.imshow(X, cmap='Greys',  interpolation='nearest')
    plt.subplots_adjust(top = 1, bottom = 0, right = 1, left = 0, 
                        hspace = 0, wspace = 0)
    plt.margins(0,0)

    # Save as png
    img_name = str(tiles_per_side) + ".png"
    print("Saving image to " + img_name)
    plt.savefig(img_name, bbox_inches = 'tight')

    # Save as pdf
    img_name_pdf = str(tiles_per_side) + ".pdf"
    print("Saving image to " + img_name_pdf)
    plt.savefig(img_name_pdf, bbox_inches = 'tight')

    # Save as svg
    img_name_svg = str(tiles_per_side) + ".svg"
    print("Saving image to " + img_name_svg)
    plt.savefig(img_name_svg, bbox_inches = 'tight')    
    
    # Save as csv
    csv_name = str(tiles_per_side) + ".csv"
    np.savetxt(csv_name, total_tiles_array, delimiter='\n', fmt='%d')
    
    # Remove white space around the image
    os.system('convert ' + img_name +  ' -trim ' + img_name)
    print("Saving CSV layout file to " + csv_name)
    

def prepare_canvas():
    cm = 1/2.54
    fig, ax = plt.subplots(figsize=(10*cm, 10*cm))
    ax.set_facecolor('white')
    plt.xticks([])
    plt.yticks([])
    plt.gca().set_axis_off()
    plt.gca().xaxis.set_major_locator(plt.NullLocator())
    plt.gca().yaxis.set_major_locator(plt.NullLocator())
    plt.subplots_adjust(top = 1, bottom = 0, right = 1, left = 0, hspace = 0, wspace = 0)
    plt.margins(0,0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal', adjustable='box')
    # make axes fill the full figure (no margins) so coordinates map to image corners
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_position([0, 0, 1, 1])
    return fig, ax


def _env_float(name, default):
    value = os.environ.get(name, "")
    return default if value == "" else float(value)


def save_floor(fig, img_name="floor.png", trim=False, dpi=200):
    print("Saving image to " + img_name)
    # save exactly the figure canvas without tight cropping or extra padding
    fig.savefig(img_name, dpi=dpi, bbox_inches=None, pad_inches=0)
    if trim:
        os.system('convert ' + img_name + ' -trim ' + img_name)


def draw_obstacle_triangle(ax):
    arena_dim = _env_float("ARENADIM", 1.0)
    zone_size = _env_float("ZONE_SIZE", 0.5)
    zone_ratio = min(max(zone_size / arena_dim, 0.05), 0.95)

    triangle = Polygon(
        [(1.05, 1.05), (1.0 - zone_ratio, 1.0), (1.0, 1.0 - zone_ratio)],
        closed=True,
        facecolor="#f3d36b",
        edgecolor="#d1b23f",
        linewidth=2,
        alpha=0.95,
    )
    ax.add_patch(triangle)


def create_blank_floor():
    fig, _ = prepare_canvas()
    save_floor(fig, trim=False)


def create_obstacle_floor():
    fig, ax = prepare_canvas()
    draw_obstacle_triangle(ax)
    save_floor(fig, trim=False)
    
def create_market_resources(market_percent_size, number_resources, quality_range):  

    cm = 1/2.54
    fig, ax = plt.subplots(figsize=(10*cm, 10*cm))
    plt.xticks([])
    plt.yticks([])
    plt.gca().set_axis_off()
    plt.gca().xaxis.set_major_locator(plt.NullLocator())
    plt.gca().yaxis.set_major_locator(plt.NullLocator())
    plt.subplots_adjust(top = 1, bottom = 0, right = 1, left = 0, hspace = 0, wspace = 0)
    plt.margins(0,0)
    # ax.add_patch(Rectangle((0.5-market_percent_size/2, 0.5-market_percent_size/2), market_percent_size, market_percent_size, color="yellow"))
    # f = open('resources.txt', 'w+')
    # for i in range(0,number_resources):
    #     circle_quality = round(uniform(quality_range[0],quality_range[1]), 2)
    #     circle_center = (uniform(0,1), uniform(0,1))
    #     ax.add_patch(Circle(circle_center, circle_quality, color="red"))
    #     f.write(' '.join([str(round(x,2)) for x in circle_center])+ ' ' + str(round(circle_quality,2))+'\n')
    

    # Save as png
    img_name = "market" + ".png"
    print("Saving image to " + img_name)
    plt.savefig(img_name, bbox_inches = 'tight')


def main_shuffled_matrix():
    for tiles_per_side in tiles_per_side_list:
        create_shuffled_matrix(tiles_per_side)
        

def main_market():
    create_market_resources(0.2,5,[0.02,0.1])


def main_shuffled_matrix():
    for tiles_per_side in tiles_per_side_list:
        create_shuffled_matrix(tiles_per_side)


def main():
    if argos_name == "greeter" or argos_name == "foraging":
        create_blank_floor()
    elif argos_name == "obstacle":
        create_obstacle_floor()
    else:
        print("Unknown ARGOSNAME, generating blank floor")
        create_blank_floor()

if __name__ == "__main__":
    # main_shuffled_matrix()
    main()


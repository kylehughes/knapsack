# sudo pip install Pillow

import os
import re

from PIL import Image

nameRegex = re.compile("^([^_]+)_(\d+)x(\d+)\.[a-z]+$")
nameFormat = "{0}_{1}x{2}{3}"

unchangedFiles = []
changedFiles

print "#####################"
print "# Rename Wallpapers #"
print "#####################"

for filename in os.listdir("."):

    name, extension = os.path.splitext(filename)
    
    wallpaperHeight = ""
    wallpaperWidth = ""
    wallpaperExtension = extension

    nameMatch = nameRegex.match(name)
    if nameMatch:
        wallpaperName = nameMatch.group(1)
    else:
        wallpaperName = name

    try:
        image = Image.open(filename)

        wallpaperWidth = image.size[0]
        wallpaperHeight = image.size[1]

        newFilename = nameFormat.format(wallpaperName, wallpaperWidth, wallpaperHeight, wallpaperExtension)

        os.rename(filename, newFilename)
    except IOError:
        pass


import os

from PIL import Image


def main():
    index = 0
    while os.path.exists(f"./images/map-{index}.png") and not os.path.exists(f"./images_small/map-{index+1}.png"):
        image = Image.open(f"./images/map-{index}.png")
        image.resize((2000, 2000)).save(f"./images_small/map-{index}.png")
        index += 1

    os.system("ffmpeg -f image2 -r 1 -i ./images_small/map-%d.png -vcodec mpeg4 -y ./map.mp4")


if __name__ == "__main__":
    main()

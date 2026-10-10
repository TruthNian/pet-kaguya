"""Face-free fixed source crops for a more coherent intermediate wave pose."""
from PIL import Image
from canonical import ROOT

OUT=ROOT/'candidates/phase5/wave-middle-link-v1'
BOX=(250,500,550,950)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for source,name in [('candidates/phase5/wave-art-middle-v2/pose.png','edit-target.png'),
                        ('candidates/phase5/wave-amplitude-v1/pose.png','peak-reference.png'),
                        ('sources/canonical/artwork.png','rest-reference.png')]:
        with Image.open(ROOT/source) as image:
            image.convert('RGBA').crop(BOX).save(OUT/name)


def inspect_generated():
    from canonical import load_canonical
    from arm_material import project_fixed_crop
    from review_waiting import grid
    with Image.open(OUT/'generated.png') as image:
        mapped=project_fixed_crop(load_canonical(),image.convert('RGBA'),[1024,1536],BOX)
    grid(mapped,(270,560,527,840)).save(ROOT/'work/wave-middle-link-grid.png')


if __name__=='__main__':
    import sys
    inspect_generated() if '--inspect' in sys.argv else main()

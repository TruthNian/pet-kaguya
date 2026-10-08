"""Face-free lower-body backing guide; technical material, never a pet pose."""
from PIL import ImageDraw

from canonical import ROOT, load_canonical
from review_waiting import grid

OUT = ROOT/'candidates/phase5/leg-backing-v1'
BOX = (400,850,820,1260)
LEFT = [[487,924],[575,931],[572,956],[563,983],[554,1012],[560,1029],
        [580,1040],[599,1055],[596,1076],[580,1090],[589,1108],[603,1136],
        [611,1174],[608,1206],[594,1228],[558,1235],[499,1235],[471,1226],
        [454,1207],[437,1180],[433,1149],[448,1114],[464,1091],[447,1071],
        [440,1052],[447,1038],[472,1028],[474,1008],[476,975],[482,947]]
RIGHT = [[632,935],[710,923],[719,949],[729,983],[733,1012],[740,1025],
         [766,1033],[780,1048],[782,1066],[766,1083],[765,1099],[776,1121],
         [790,1150],[796,1180],[789,1208],[771,1229],[726,1235],[667,1235],
         [640,1225],[622,1207],[615,1177],[619,1149],[631,1120],[643,1094],
         [625,1077],[607,1058],[609,1040],[634,1028],[638,1012],[637,978]]


def main():
    source = load_canonical()
    reference = source.crop(BOX)
    guide = reference.copy()
    draw = ImageDraw.Draw(guide)
    for polygon in (LEFT, RIGHT):
        local = [(x-BOX[0],y-BOX[1]) for x,y in polygon]
        draw.line(local+[local[0]],fill='#00bbff',width=3)
    OUT.mkdir(parents=True,exist_ok=True)
    reference.save(OUT/'reference.png')
    guide.save(OUT/'guide.png')
    diagnostic = ROOT/'work/leg-inspection'
    diagnostic.mkdir(parents=True,exist_ok=True)
    grid(source,BOX).save(diagnostic/'source-grid.png')
    print('lower-body backing guide: fixed 420x410 source crop; face absent')


if __name__ == '__main__':
    main()

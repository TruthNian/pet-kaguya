"""Local v2 facts, independently described; no proprietary runtime code."""

WIDTH, HEIGHT = 192, 208
ATLAS_SIZE = (1536, 2288)
COUNTS = [7, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8]
NAMES = ['idle', 'run_right', 'run_left', 'waving', 'jumping', 'failed',
         'waiting', 'running', 'review', 'look_a', 'look_b']
# Native durations. Idle is the slow-idle path, NOT the base 1100 ms loop.
DURATIONS = [
    [1680, 660, 660, 840, 840, 1920],
    [120]*7+[220], [120]*7+[220], [140]*3+[280], [140]*4+[280],
    [140]*7+[240], [150]*5+[260], [120]*5+[220], [150]*5+[280],
]


def crop(atlas, row, col):
    return atlas.crop((col*WIDTH, row*HEIGHT, (col+1)*WIDTH, (row+1)*HEIGHT))

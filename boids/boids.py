# boids.py
#
# Bryan Daniels
# 2021/4/40
#
# Helper code for launching boids javascript simulation from a jupyter notebook.
#

from pathlib import Path # to handle file paths across all operating systems

#portability
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ORIGINAL = BASE_DIR / 'index.html'
DEFAULT_MODIFIED = BASE_DIR / 'index-modified.html'

def setupBoidsSimulation(attractiveFactor,alignmentFactor,avoidFactor,
    visualRange=75,numBoids=100,drawTrail=False,
    originalFilename=DEFAULT_ORIGINAL,
    modifiedFilename=DEFAULT_MODIFIED):
    """
    Write a modified boids simulation HTML file with parameters set
    according to input arguments.
    
    Units of the force factor parameters are rescaled such that 1 corresponds
    to the default value in the original simulation.
    """
    
    # read original HTML simulation file
    with open(originalFilename,'r') as fin:
        originalHTML = fin.read()
    
    # change units of parameters such that 1 corresponds to the default value
    attractiveFactorDefault = 0.005
    alignmentFactorDefault = 0.05
    avoidFactorDefault = 0.05
    attractiveFactor = attractiveFactor * attractiveFactorDefault
    alignmentFactor = alignmentFactor * alignmentFactorDefault
    avoidFactor = avoidFactor * avoidFactorDefault
    
    # replace
    modifiedHTML = originalHTML.replace(
        'const attractiveFactor = 0.005;',
        'const attractiveFactor = {};'.format(attractiveFactor)).replace(
        'const alignmentFactor = 0.05;',
        'const alignmentFactor = {};'.format(alignmentFactor)).replace(
        'const avoidFactor = 0.05;',
        'const avoidFactor = {};'.format(avoidFactor)).replace(
        'const visualRange = 75;',
        'const visualRange = {};'.format(visualRange)).replace(
        'const numBoids = 100;',
        'const numBoids = {};'.format(numBoids)).replace(
        'const DRAW_TRAIL = false;',
        'const DRAW_TRAIL = {};'.format(str(drawTrail).lower()))

    with open(modifiedFilename,'w') as fout:
        fout.write(modifiedHTML)

"""
gene_startup

Handle the initialization of GENE for a Tango-GENE run.

See https://github.com/LLNL/tango for copyright and license information
"""

from __future__ import division
import numpy as np
#from . import gene_check
from . import genecomm

# Possible change in the future:  We could get an MPIrank solely within Python using mpi4py, using the  following code.  This would prevent us
# from having to run # GENE simply to get an MPIrank.  However, the problem with this is that on login nodes on NERSC, where MPI is not
# available, the import causes # a hard crash.  It is not merely an ImportError; Python itself crashes.  Hence, a try/except block around
# the import will not work.  The crash is caused by an mpiInit() call in the import.  If I want the code to work on a login node on NERSC,
# I can't use this method. 

# from mpi4py import MPI
# MPIrank = MPI.COMM_WORLD.Get_rank()
# nproc = MPI.COMM_WORLD.Get_size()


    
def setup_gene_run(psiTango, psiGene, minorRadius, majorRadius, B0, ionMass, ionCharge, densityTangoGrid, pressureTangoGrid, safetyFactorGeneGrid,
                   Bref, Lref, Tref, nref, gridMapper, fromCheckpoint=True, pseudoGene=False):
    """Do all the necessary setup for a tango run using GENE
    
    This function works with either a clean run from no checkpoint, or starting from an initial condition.
    
    Inputs:
      psiTango              Tango's grid for radial coordinate, psi = r (array)
      psiGene               GENE's grid for radial coordinate, psi = x = r (array)
      minorRadius           minor radius a (scalar)
      majorRadius           major radius R0 (scalar)
      B0                    magnetic field parameter for analytic circular geometry, in Tesla (array)
      ionMass               ion mass, measured in proton mass (scalar)
      ionCharge             ion charge, measured in electron charge (scalar)
      densityTangoGrid      density profile on Tango radial grid in m^-3 (array)
      pressureTangoGrid     ion pressure profile (initial condition) on Tango radial grid in J/m^3 (array)
      safetyFactorGeneGrid  safety factor q on GENE radial grid (array)
      Bref                  GENE reference magnetic field in Tesla (scalar)
      Lref                  GENE reference length in m (scalar)
      Tref                  GENE reference temperature in kev (scalar)
      nref                  GENE reference density in 10^19 m^-3 (scalar)
      gridMapper            object for interfacing between Tango and GENE grids [see interfacegrids_gene.py]
      fromCheckpoint        True if restarting GENE from a checkpoint (Boolean)
      pseudoGene            False for normal GENE run, True for a pseudo call that does not run GENE but is used to test code (Boolean)
    Outputs:
      geneFluxModel         interface to GENE, with a get_flux method (GeneComm object)
      MPIrank               MPI rank obtained from GENE for distinguishing processors (integer)
      
    Other notes:
      B0 is currently unused.  Bref sets the magnetic field strength
    """
    # check that GENE works and get MPI rank
    #if pseudoGene==False:
    #    (status, MPIrank) = gene_check.gene_check()
    #    import time
	#if MPIrank==0:
	#    print('rank 0 here.  first gene_check finished.  Trying the second gene_check now...')
	#sys.stdout.flush()
    #    time.sleep(0.2) # pause to allow processes to catch up
	#(status, MPIrank2) = gene_check.gene_check()
    #else:
    #    (status, MPIrank) = (0, 0)
    
    # if doing a clean run from no checkpoint, create the initial checkpoint...
    if pseudoGene==False:
        if fromCheckpoint==False:
            geneFluxModelTemp = genecomm.GeneComm(Bref=Bref, Lref=Lref, B0=B0, minorRadius=minorRadius, majorRadius=majorRadius, safetyFactorGeneGrid=safetyFactorGeneGrid,
                                          psiTangoGrid=psiTango, psiGeneGrid=psiGene, densityTangoGrid=densityTangoGrid, ionMass=ionMass, ionCharge=ionCharge, gridMapper=gridMapper)
            simulationTimeInitialRun = 30
            pressureGeneGrid = gridMapper.MapProfileOntoTurbGrid(pressureTangoGrid)
            initial_gene_run(geneFluxModelTemp, pressureGeneGrid, simulationTimeInitialRun)
    
    # create a GENE Fluxmodel    
    geneFluxModel = genecomm.GeneComm(Bref=Bref, Lref=Lref, Tref=Tref, nref=nref, B0=B0, minorRadius=minorRadius, majorRadius=majorRadius, safetyFactorGeneGrid=safetyFactorGeneGrid,
                                      psiTangoGrid=psiTango, psiGeneGrid=psiGene, densityTangoGrid=densityTangoGrid, ionMass=ionMass, ionCharge=ionCharge, gridMapper=gridMapper,
                                      pseudoGene=pseudoGene)
    
    # set the simulation time per GENE call
    simulationTime = 10 # measured in Lref/cref
    geneFluxModel.set_simulation_time(simulationTime)
    return geneFluxModel
    

def initial_gene_run(geneFluxModel, pressureGeneGrid, simulationTime):
    """Perform the initial GENE run.  
    
    Tango uses a GetFlux() method which runs a GENE simulation for a short amount of time with slightly updated
    profiles and receives a slightly updated turbulent flux.  For these numbers to be sensical, (in other words,
    for the returned turbulent flux to be reflective of the input density profile), an initial GENE run must be
    performed so that the turbulence has had time to develop.  This function performs that initial run to create
    a checkpoint with somewhat developed or mostly developed turbulence from which Tango can then begin its normal 
    iteration.
    
    Inputs:
      geneFluxModel     object to control simulations of GENE
      pressureGeneGrid  ion pressure profile on GENE radial grid, measured in J/m^3 (array)
      simulationTime:   Time for GENE simulation.  Measured in units of Lref/cref (scalar)
    
    Outputs:
    """
    checkpointSuffix = 0
    
    # Check that a checkpoint _000 does not exist.  If it does, abort.    
    assert not gene_check.checkpoint_exists(checkpointSuffix), "Error in gene_startup.initial_gene_run().  Checkpoint file with suffix {} aready exists".format(gene_check.checkpoint_suffix_string(checkpointSuffix))
    
    # Run.
    geneFluxModel.set_simulation_time(simulationTime)
    heatFlux_notUsed = geneFluxModel.GetFlux(pressureGeneGrid)
    
    # Verify checkpoint
    assert gene_check.checkpoint_exists(checkpointSuffix), "Error in gene_startup.initial_gene_run().  Checkpoint file not created as expected!"

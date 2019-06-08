"""Module that organizes creation of foam morphoogy.

First, the geometric tessellation is performed so that the resulting foam has
the correct bubble size distribution. Then several mesh conversions are made to
obtain the foam image in desired format. Finally, foam is voxelized to desired
foam density and struts are optionally added.

"""
from __future__ import division, print_function
import sys
import datetime
import shutil
import subprocess as sp
from blessings import Terminal
import yamlargparse as yp
from . import packing
from . import tessellation
from . import geo_tools
from . import smesh


def parse():
    """Parse arguments using yamlargparse and call generate function."""
    prs = yp.ArgumentParser(
        prog='foamgen',
        error_handler=yp.usage_and_exit_error_handler,
        description='Generate foam morphology.')
    prs.add_argument('-v', '--verbose', default=False,
                     action='store_true', help='verbose output')
    prs.add_argument('-c', '--config', action=yp.ActionConfigFile,
                     help='name of config file')
    prs.add_argument('-f', '--filename', default='Foam',
                     help='base filename')
    prs.add_argument('-p', '--pack.active', default=False,
                     action='store_true', help='create sphere packing')
    prs.add_argument('--pack.ncells', default=27,
                     help='number of cells')
    prs.add_argument('--pack.shape', default=0.2,
                     help='sphere size distribution shape factor')
    prs.add_argument('--pack.scale', default=0.2,
                     help='sphere size distribution scale factor')
    prs.add_argument('--pack.alg', default='fba',
                     help='packing algorithm')
    prs.add_argument('-t', '--tess.active', default=False,
                     action='store_true', help='create tessellation')
    prs.add_argument('--tess.render', default=False,
                     action='store_true', help='visualize tessellation')
    prs.add_argument('-m', '--morph.active', default=False,
                     action='store_true', help='create final morphology')
    prs.add_argument('--morph.dwall', default=0.02,
                     help='wall thickness')
    prs.add_argument('-u', '--umesh.active', default=False,
                     action='store_true', help='create unstructured mesh')
    prs.add_argument('--umesh.geom', default=True,
                     action='store_true', help='create geometry')
    prs.add_argument('--umesh.mesh', default=True,
                     action='store_true', help='perform meshing')
    prs.add_argument('--umesh.psize', default=0.025,
                     help='mesh size near geometry points')
    prs.add_argument('--umesh.esize', default=0.1,
                     help='mesh size near geometry edges')
    prs.add_argument('--umesh.csize', default=0.1,
                     help='mesh size in middle of geometry cells')
    prs.add_argument('--umesh.convert', default=0.1,
                     help='convert mesh to *.xml for fenics')
    prs.add_argument('-s', '--smesh.active', default=False,
                     action='store_true', help='create structured mesh')
    prs.add_argument('--pack.dsize', default=1,
                     help='domain size')
    prs.add_argument('--smesh.render', default=False,
                     action='store_true', help='visualize structured mesh')
    prs.add_argument('--smesh.strut', default=0.6,
                     help='strut content')
    prs.add_argument('--smesh.por', default=0.94,
                     help='porosity')
    prs.add_argument('--smesh.isstrut', default=4,
                     help='initial guess of strut size parameter')
    prs.add_argument('--smesh.binarize', default=True,
                     action='store_true', help='binarize structure')
    prs.add_argument('--smesh.perbox', default=True,
                     action='store_true',
                     help='transform structure to periodic box')
    cfg = prs.parse_args(sys.argv[1:])
    # print(cfg)
    generate(cfg)


def generate(cfg):
    """Generate foam morphology."""
    # Creates terminal for colour output
    term = Terminal()
    time_start = datetime.datetime.now()
    if cfg.pack.active:
        print(term.yellow + "Packing spheres." + term.normal)
        packing.pack_spheres(cfg.pack.shape,
                             cfg.pack.scale,
                             cfg.pack.ncells,
                             cfg.pack.alg)
    if cfg.tess.active:
        print(term.yellow + "Tessellating." + term.normal)
        tessellation.tessellate(cfg.filename,
                                cfg.pack.ncells,
                                cfg.tess.render)
    if cfg.morph.active:
        print(term.yellow + "Creating final morphology." + term.normal)
        geo_tools.main(cfg.filename,
                       cfg.morph.dwall,
                       [cfg.umesh.psize, cfg.umesh.esize, cfg.umesh.csize],
                       cfg.verbose)
        shutil.copy(cfg.filename + "WallsBoxFixed.geo",
                    cfg.filename + "_uns.geo")
    if cfg.umesh.active:
        print(term.yellow + "Creating unstructured mesh." + term.normal)
        unstructured_mesh(cfg.filename, cfg.umesh.convert)
    if cfg.smesh.active:
        print(term.yellow + "Creating structured mesh." + term.normal)
        smesh.structured_grid(cfg.filename,
                              cfg.smesh.dsize,
                              cfg.smesh.dsize,
                              cfg.smesh.dsize,
                              cfg.smesh.por,
                              cfg.smesh.strut)
    time_end = datetime.datetime.now()
    print("Foam created in: {}".format(time_end - time_start))


def unstructured_mesh(filename, convert):
    """Create unstructured mesh."""
    mesh_domain(filename + "_uns.geo")
    if convert:
        convert_mesh(filename + "_uns.msh", filename + "_uns.xml")


def mesh_domain(domain):
    """Mesh computational domain using Gmsh."""
    sp.Popen(['gmsh', '-3', '-v', '3', '-format', 'msh2', domain]).wait()


def convert_mesh(input_mesh, output_mesh):
    """Convert mesh to xml using dolfin-convert."""
    sp.Popen(['dolfin-convert', input_mesh, output_mesh]).wait()
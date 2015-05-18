#!/usr/bin/env python
# -*- coding: UTF-8 no BOM -*-

import os, sys, string
from optparse import OptionParser
import damask

scriptID   = string.replace('$Id$','\n','\\n')
scriptName = os.path.splitext(scriptID.split()[1])[0]

#-------------------------------------------------------------------------------------------------
def outMentat(cmd,locals):
#-------------------------------------------------------------------------------------------------
  if cmd[0:3] == '(!)':
    exec(cmd[3:])
  elif cmd[0:3] == '(?)':
    cmd = eval(cmd[3:])
    py_send(cmd)
  else:
    py_send(cmd)
  return

#-------------------------------------------------------------------------------------------------
def outStdout(cmd,locals):
#-------------------------------------------------------------------------------------------------
  if cmd[0:3] == '(!)':
    exec(cmd[3:])
  elif cmd[0:3] == '(?)':
    cmd = eval(cmd[3:])
    sys.stdout.write(cmd+'\n')
  else:
    print(cmd)
    sys.stdout.write(cmd+'\n')
  return

#-------------------------------------------------------------------------------------------------
def output(cmds,locals,dest):
#-------------------------------------------------------------------------------------------------
  for cmd in cmds:
    if isinstance(cmd,list):
      output(cmd,locals,dest)
    else:
      {\
      'Mentat': outMentat,\
      'Stdout': outStdout,\
      }[dest](str(cmd),locals)
  return


  
#-------------------------------------------------------------------------------------------------
def init():
#-------------------------------------------------------------------------------------------------
    return ["*new_model yes",
      "*reset",
      "*select_clear",
      "*set_element_class hex8",
      "*set_nodes off",
      "*elements_solid",
      "*show_view 4",
      "*reset_view",
      "*view_perspective",
      "*redraw",
      ]


#-------------------------------------------------------------------------------------------------
def mesh(r,d):
#-------------------------------------------------------------------------------------------------
    return [
  "*add_nodes",
  "%f %f %f"%(0.0,0.0,0.0),
  "%f %f %f"%(0.0,0.0,d[2]),
  "%f %f %f"%(0.0,d[1],d[2]),
  "%f %f %f"%(0.0,d[1],0.0),
  "%f %f %f"%(-d[0],0.0,0.0),
  "%f %f %f"%(-d[0],0.0,d[2]),
  "%f %f %f"%(-d[0],d[1],d[2]),
  "%f %f %f"%(-d[0],d[1],0.0),
  "*add_elements",
  range(1,9),
  "*sub_divisions",
  "%i %i %i"%(r[2],r[1],r[0]),
  "*subdivide_elements",
  "all_existing",
  "*set_sweep_tolerance",
  "%f"%(float(min(d))/max(r)/2.0),
  "*sweep_all",
  "*renumber_all",
  "*set_move_scale_factor x -1",
  "*move_elements",
  "all_existing",
  "*flip_elements",
  "all_existing",
  "*fill_view",
    ]


#-------------------------------------------------------------------------------------------------
def material():
#-------------------------------------------------------------------------------------------------
  cmds = [\
  "*new_mater standard",
  "*mater_option general:state:solid",
  "*mater_option structural:type:hypo_elast",
  "*mater_name",
  "hypela2",
  "*add_mater_elements",
  "all_existing",
  "*geometry_type mech_three_solid",
#  "*geometry_option red_integ_capacity:on",                                                        # see below: reduced integration with one IP gave trouble being always OUTDATED...
  "*add_geometry_elements",
  "all_existing",
  ]
  
  return cmds
  

#-------------------------------------------------------------------------------------------------
def geometry():
#-------------------------------------------------------------------------------------------------
  cmds = [\
  "*geometry_type mech_three_solid",
#  "*geometry_option red_integ_capacity:on",
  "*add_geometry_elements",
  "all_existing",
  "*element_type 7",                                                                                # we are NOT using reduced integration (type 117) but opt for /elementhomogeneous/ in the respective phase description (material.config)
  "all_existing",
  ]
  
  return cmds
  

#-------------------------------------------------------------------------------------------------
def initial_conditions(homogenization,microstructures):
#-------------------------------------------------------------------------------------------------
  elements = []
  element = 0
  for id in microstructures:
    element += 1 
    if len(elements) < id:
      for i in range(id-len(elements)):
        elements.append([])
    elements[id-1].append(element)

  cmds = [\
    "*new_icond",
    "*icond_name _temperature",
    "*icond_type state_variable",
    "*icond_param_value state_var_id 1",
    "*icond_dof_value var 300",
    "*add_icond_elements",
    "all_existing",
    "*new_icond",
    "*icond_name _homogenization",
    "*icond_type state_variable",
    "*icond_param_value state_var_id 2",
    "*icond_dof_value var %i"%homogenization,
    "*add_icond_elements",
    "all_existing",
    ]

  for grain,elementList in enumerate(elements):
    cmds.append([\
            "*new_icond",
            "*icond_name microstructure_%i"%(grain+1),
            "*icond_type state_variable",
            "*icond_param_value state_var_id 3",
            "*icond_dof_value var %i"%(grain+1),
            "*add_icond_elements",
            elementList,
            "#",
                ])
  return cmds


#-------------------------------------------------------------------------------------------------
def parse_geomFile(content,homog):
#-------------------------------------------------------------------------------------------------
  (skip,key) = content[0].split()[:2]
  if key[:4].lower() == 'head':
    skip = int(skip)+1
  else:
    skip = 0
  
  grid = [0,0,0]
  size = [0.0,0.0,0.0]
  homog = 0
  
  for line in content[:skip]:
    data = line.split()
    if data[0].lower() == 'grid':
      grid = map(int,data[2:8:2])
    if data[0].lower() == 'size':
      size = map(float,data[2:8:2])
    if data[0].lower() == 'homogenization':
      homog = int(data[1])

  microstructures = []
  for line in content[skip:]:
    for word in line.split():
      microstructures.append(int(word))

  return (grid,size,homog,microstructures)

#--------------------------------------------------------------------------------------------------
#                                MAIN
#--------------------------------------------------------------------------------------------------

parser = OptionParser(option_class=damask.extendableOption, usage='%prog options [file[s]]', description = """
Generate MSC.Marc FE hexahedral mesh from spectral description file.

""", version = scriptID)

parser.add_option('-p', '--port', type='int',dest='port',metavar='int',
                  help='Mentat connection port [%default]')
parser.add_option('--homogenization', dest='homogenization', type='int', metavar = 'int',
                  help='homogenization index to be used [%default]')
parser.set_defaults(port     = None)
parser.set_defaults(homogenization = 1)

(options, filenames) = parser.parse_args()


sys.path.append(damask.solver.Marc().libraryPath('../../'))

try:
  from py_mentat import *
except:
  print('no valid Mentat release found')
  if options.port != None: sys.exit(-1)

#--- setup file handles --------------------------------------------------------------------------   
files = []
if filenames == []:
  files.append({'name':'STDIN',
                'input':sys.stdin,
                'output':sys.stdout,
                'croak':sys.stderr,
               })
else:
  for name in filenames:
    if os.path.exists(name):
      files.append({'name':name,
                    'input':open(name),
                    'output':open(name+'_tmp','w'),
                    'croak':sys.stdout,
                    })

#--- loop over input files ------------------------------------------------------------------------
for file in files:
  file['croak'].write('\033[1m' + scriptName + '\033[0m: ' + (file['name'] if file['name'] != 'STDIN' else '') + '\n')


  content = file['input'].readlines()
  
  (grid,size,homog,microstructures) = parse_geomFile(content, options.homogenization)
  
  file['croak'].write('%i microstructures in %s with grid %s and homogenization %i\n'
                                     %(len(list(set(microstructures))),str(size),str(grid),homog))
  
  cmds = [\
    init(),
    mesh(grid,size),
    material(),
    geometry(),
    initial_conditions(homog,microstructures),
    '*identify_sets',
    '*redraw',
  ]
  
  outputLocals = {}
  if (options.port != None):
    py_connect('',options.port)
    output(cmds,outputLocals,'Mentat')
    py_disconnect()
  else:
    output(cmds,outputLocals,'Stdout')

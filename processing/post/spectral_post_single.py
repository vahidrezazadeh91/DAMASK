#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

# This script is used for the post processing of the results achieved by the spectral method.
# As it reads in the data coming from "materialpoint_results", it can be adopted to the data
# computed using the FEM solvers. Until now, its capable to handle elements with one IP in a regular order
# written by M. Diehl, m.diehl@mpie.de

import os,sys,re,array,struct,numpy, time, postprocessingMath, math

class vector:
  x,y,z = [None,None,None]
  
  def __init__(self,coords):
    self.x = coords[0]
    self.y = coords[1]
    self.z = coords[2]

class element:
  items = []
  type = None

  def __init__(self,nodes,type):
    self.items = nodes
    self.type = type

class element_scalar:
  id = None
  value = None

  def __init__(self,node,value):
    self.id = node
    self.value = value


class MPIEspectral_result:

  file = None
  dataOffset = 0
  N_elemental_scalars = 0
  resolution = [0,0,0]
  dimension = [0.0,0.0,0.0]
  theTitle = ''
  wd = ''
  extrapolate = ''
  N_increments = 0
  increment = 0
  N_nodes = 0
  N_node_scalars = 0
  N_elements = 0
  N_element_scalars = 0
  N_element_tensors = 0
  theNodes = []
  theElements = []

  def __init__(self,filename):

    self.file = open(filename, 'rb')

    self.title = self._keyedString('load')
    self.wd = self._keyedString('workingdir')
    self.geometry = self._keyedString('geometry')
    self.N_increments =  self._keyedInt('increments')
    self.N_element_scalars = self._keyedInt('materialpoint_sizeResults')
    self.resolution = self._keyedPackedArray('resolution',3,'i')
    self.N_nodes = (self.resolution[0]+1)*(self.resolution[1]+1)*(self.resolution[2]+1)
    self.N_elements = self.resolution[0]*self.resolution[1]*self.resolution[2]
    self.dimension = self._keyedPackedArray('dimension',3,'f')
    a = self.resolution[0]+1
    b = self.resolution[1]+1
    c = self.resolution[2]+1
    self.file.seek(0)
    self.dataOffset = self.file.read(2048).find('eoh')+7


  def __str__(self):
    return '\n'.join([
      'title: %s'%self.title,
      'workdir: %s'%self.wd,
      'extrapolation: %s'%self.extrapolate,
      'increments: %i'%self.N_increments,
      'increment: %i'%self.increment,
      'nodes: %i'%self.N_nodes,
      'resolution: %s'%(','.join(map(str,self.resolution))),
      'dimension: %s'%(','.join(map(str,self.dimension))),
      'elements: %i'%self.N_elements,
      'nodal_scalars: %i'%self.N_node_scalars,
      'elemental scalars: %i'%self.N_element_scalars,
      'end of header: %i'%self.dataOffset,
      ]
    )

  def _keyedPackedArray(self,identifier,length = 3,type = 'f'):
    match = {'f': 4,'i': 4}  #correct???
    self.file.seek(0)
    m = re.search('%s%s'%(identifier,'(.{%i})'%(match[type])*length),self.file.read(2048),re.DOTALL)
    values = []
    if m:
      for i in m.groups():
        values.append(struct.unpack(type,i)[0])
    return values

  def _keyedInt(self,identifier):
    value = None
    self.file.seek(0)
    m = re.search('%s%s'%(identifier,'(.{4})'),self.file.read(2048),re.DOTALL)
    if m:
      value = struct.unpack('i',m.group(1))[0]
    return value

  def _keyedString(self,identifier):
    value = None
    self.file.seek(0)
    m = re.search(r'(.{4})%s(.*?)\1'%identifier,self.file.read(2048),re.DOTALL)
    if m:
      value = m.group(2)
    return value

  def extrapolation(self,value):
    self.extrapolate = value

  def element_scalar(self,elem,idx):
    self.file.seek(self.dataOffset+(self.increment*(4+self.N_elements*self.N_element_scalars*4+4) + 4+(elem*self.N_element_scalars + idx)*4))
    value = struct.unpack('f',self.file.read(4))[0]
    return [elemental_scalar(node,value) for node in self.theElements[elem].items]

def readScalar(resolution,file,distance,startingPosition,offset):
  currentPosition = startingPosition+offset*4+4 - distance*4 # we add distance later on
  field = numpy.zeros([resolution[0],resolution[1],resolution[2]], 'f')
  for z in range(0,resolution[2]):
    for y in range(0,resolution[1]):
      for x in range(0,resolution[0]):
        currentPosition = currentPosition + distance*4
        p.file.seek(currentPosition)
        field[x][y][z]=struct.unpack('f',p.file.read(4))[0]
  return field

def readTensor(resolution,file,distance,startingPosition,offset):
  currentPosition = startingPosition+offset*4+4 - distance*4 # we add distance later on
  field = numpy.zeros([resolution[0],resolution[1],resolution[2],3,3], 'f')
  for z in range(0,resolution[2]):
    for y in range(0,resolution[1]):
      for x in range(0,resolution[0]):
        currentPosition = currentPosition + distance*4
        p.file.seek(currentPosition)
        for i in range(0,3):
          for j in range(0,3):
            field[x][y][z][i][j]=struct.unpack('f',p.file.read(4))[0]
  return field

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++   
def calculateCauchyStress(p_stress,defgrad,res):
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ 
  c_stress = numpy.zeros([res[0],res[1],res[2],3,3],'f')
  for z in range(res[2]):
    for y in range(res[1]):
      for x in range(res[0]):
        jacobi =  numpy.linalg.det(defgrad[x,y,z])
        c_stress[x,y,z] = numpy.dot(p_stress[x,y,z],numpy.transpose(defgrad[x,y,z]))/jacobi
  return c_stress
  

# function writes scalar values to a mesh (geometry)
def writeVtkAscii(filename,geometry,scalar,resolution):
  prodnn=(p.resolution[0]+1)*(p.resolution[1]+1)*(p.resolution[2]+1)
  vtk = open(filename, 'w')
  vtk.write('# vtk DataFile Version 3.1\n') # header
  vtk.write('just a test\n') # header
  vtk.write('ASCII\n') # header
  vtk.write('DATASET UNSTRUCTURED_GRID\n') # header
  vtk.write('POINTS ') # header
  vtk.write(str(prodnn)) # header
  vtk.write(' FLOAT\n') # header

# nodes
  for k in range (resolution[2]+1):
    for j in range (resolution[1]+1):
      for i in range (resolution[0]+1):
        vtk.write('\t'.join(map(str,geometry[i,j,k]))+'\n')
  vtk.write('\n')
  vtk.write('CELLS ')
  vtk.write(str(resolution[0]*resolution[1]*resolution[2]))
  vtk.write('\t')
  vtk.write(str(resolution[0]*resolution[1]*resolution[2]*9))
  vtk.write('\n')

# elements
  for i in range (resolution[2]):
    for j in range (resolution[1]):
      for k in range (resolution[0]):
        vtk.write('8')
        vtk.write('\t')
        base = i*(resolution[1]+1)*(resolution[2]+1)+j*(resolution[1]+1)+k
        vtk.write(str(base))
        vtk.write('\t')
        vtk.write(str(base+1))
        vtk.write('\t')
        vtk.write(str(base+resolution[1]+2))
        vtk.write('\t')
        vtk.write(str(base+resolution[1]+1))
        vtk.write('\t')
        base = base + (resolution[1]+1)*(resolution[2]+1)
        vtk.write(str(base))
        vtk.write('\t')
        vtk.write(str(base+1))
        vtk.write('\t')
        vtk.write(str(base+resolution[1]+2))
        vtk.write('\t')
        vtk.write(str(base+resolution[1]+1))
        vtk.write('\n')
  vtk.write('\n')
  vtk.write('CELL_TYPES ')
  vtk.write('\t')
  vtk.write(str(resolution[0]*resolution[1]*resolution[2]))
  vtk.write('\n')
  for i in range (resolution[0]*resolution[1]*resolution[2]):
    vtk.write('12\n')
  vtk.write('\nCELL_DATA ') # header
  vtk.write(str(resolution[0]*resolution[1]*resolution[2])) # header
  vtk.write('\n') # header
  vtk.write('SCALARS HorizontalSpeed float\n') # header
  vtk.write('LOOKUP_TABLE default\n') # header
  for k in range (resolution[2]):
    for j in range (resolution[1]):
      for i in range (resolution[0]):
        vtk.write(str(scalar[i,j,k]))
        vtk.write('\n')
  return
 
# function writes scalar values to a point field
def writeVtkAsciiDots(filename,coordinates,scalar,resolution):
  prodnn=(p.resolution[0])*(p.resolution[1])*(p.resolution[2])
  vtk = open(filename, 'w')
  vtk.write('# vtk DataFile Version 3.1\n') # header
  vtk.write('just a test\n') # header
  vtk.write('ASCII\n') # header
  vtk.write('DATASET UNSTRUCTURED_GRID\n') # header
  vtk.write('POINTS ') # header
  vtk.write(str(prodnn)) # header
  vtk.write(' FLOAT\n') # header
# points
  for k in range (resolution[2]):
    for j in range (resolution[1]):
      for i in range (resolution[0]):
        vtk.write('\t'.join(map(str,coordinates[i,j,k]))+'\n')
  vtk.write('\n')
  vtk.write('CELLS ')
  vtk.write(str(prodnn))
  vtk.write('\t')
  vtk.write(str(prodnn*2))
  vtk.write('\n')
  for i in range(prodnn):
    vtk.write('1\t' + str(i) + '\n')
  vtk.write('CELL_TYPES ')
  vtk.write('\t')
  vtk.write(str(prodnn))
  vtk.write('\n')
  for i in range (prodnn):
    vtk.write('1\n') 
  vtk.write('\nPOINT_DATA ') # header
  vtk.write(str(prodnn)) # header
  vtk.write('\n') # header
  vtk.write('SCALARS HorizontalSpeed float\n') # header
  vtk.write('LOOKUP_TABLE default\n') # header
  for k in range (resolution[2]):
    for j in range (resolution[1]):
      for i in range (resolution[0]):
        vtk.write(str(scalar[i,j,k]))
        vtk.write('\n')
  return
  
# functiongives the corner box for the average defgrad
def writeVtkAsciidefgrad_av(filename,diag,defgrad):
  
  points = numpy.array([\
   [0.0,0.0,0.0,],\
   [diag[0],0.0,0.0,],\
   [diag[0],diag[1],0.0,],\
   [0.0,diag[1],0.0,],\
   [0.0,0.0,diag[2],],\
   [diag[0],0.0,diag[2],],\
   [diag[0],diag[1],diag[2],],\
   [0.0,diag[1],diag[2],]]\
  )
  vtk = open(filename, 'w')
  vtk.write('# vtk DataFile Version 3.1\n') # header
  vtk.write('just a test\n') # header
  vtk.write('ASCII\n') # header
  vtk.write('DATASET UNSTRUCTURED_GRID\n') # header
  vtk.write('POINTS 8') # header
  vtk.write(' FLOAT\n') # header

 # points
  for p in range (8):
    vtk.write('\t'.join(map(str,numpy.dot(defgrad_av,points[p])))+'\n')
  vtk.write('\n')
  vtk.write('CELLS 8 16\n')
  vtk.write('\n'.join(['1\t%i'%i for i in range(8)])+'\n')
  vtk.write('CELL_TYPES 8\n')
  vtk.write('\n'.join(['1']*8)+'\n')
  
  return

print '*********************************************************************************'
print 'Post Processing for Material subroutine for BVP solution using spectral method'
print '*********************************************************************************\n'

#reading in the header of the results file
name = 'dipl32_shear'
p = MPIEspectral_result(name+'.spectralOut')
p.extrapolation('')
print p

# Ended reading of header

res_x=p.resolution[0]
res_y=p.resolution[1]
res_z=p.resolution[2]

    
ms=numpy.zeros([res_x,res_y,res_z,3], 'f')
print 'data structure'
for i in range(p.N_element_scalars):
  c_pos = p.dataOffset + i*4.0 + 4.0
  p.file.seek(c_pos)
  print(i, struct.unpack('f',p.file.read(4)))
for i in range(1,2):
  c_pos = p.dataOffset + i*(p.N_element_scalars*4*p.N_elements + 8) 
  defgrad = readTensor(p.resolution,p.file,p.N_element_scalars,c_pos,7)
  defgrad_av = postprocessingMath.tensor_avg(res_x,res_y,res_z,defgrad)
  centroids_coord = postprocessingMath.deformed(res_x,res_y,res_z,p.dimension,defgrad,defgrad_av)
  undeformed = postprocessingMath.mesh(p.resolution[0],p.resolution[1],p.resolution[2],p.dimension,defgrad_av,centroids_coord)
  #writeVtkAscii(name+'-mesh-undeformed.vtk',undeformed,defgrad[:,:,:,1,2],p.resolution)

for i in range(240,241):
  c_pos = p.dataOffset + i*(p.N_element_scalars*4*p.N_elements + 8) #8 accounts for header&footer
  defgrad = readTensor(p.resolution,p.file,p.N_element_scalars,c_pos,7)
  defgrad_av = postprocessingMath.tensor_avg(res_x,res_y,res_z,defgrad)
  #defgrad = numpy.zeros([p.resolution[0],p.resolution[1],p.resolution[2],3,3], 'f')
  #for z in range(p.resolution[2]):
  #   defgrad[:,:,z,1,2] = (2.0*z)/(p.resolution[2]-1.0)+ 3.8*math.sin(z*20.0/(p.resolution[2]-1.0)*2*math.pi)
  #   defgrad[:,:,z,0,2] = (2.0*z)/(p.resolution[2]-1.0)+ 5.0*math.cos(z/(p.resolution[2]-1.0)*2*math.pi)
  #defgrad[:,:,:,0,0] = 1.0
  #defgrad[:,:,:,1,1] = 1.0
  #defgrad[:,:,:,2,2] = 1.0
  #logstrain = postprocessingMath.logstrain_mat(res_x,res_y,res_z,defgrad)  
  #logstrain2 = postprocessingMath.logstrain_spat(res_x,res_y,res_z,defgrad)
  #p_stress = readTensor(p.resolution,p.file,p.N_element_scalars,c_pos,52)         
  #c_stress = postprocessingMath.calculate_cauchy(res_x,res_y,res_z,defgrad,p_stress)
  #vm = postprocessingMath.calculate_mises(res_x,res_y,res_z,c_stress)
  #defgrad_av = postprocessingMath.tensor_avg(res_x,res_y,res_z,defgrad)
  #subroutine inverse_reconstruction(res_x,res_y,res_z,reference_configuration,current_configuration,defgrad)
  centroids_coord = postprocessingMath.deformed(res_x,res_y,res_z,p.dimension,defgrad,defgrad_av)
  deformed = postprocessingMath.mesh(p.resolution[0],p.resolution[1],p.resolution[2],p.dimension,defgrad_av,centroids_coord)
  #writeVtkAscii(name+'-mesh-deformed.vtk',deformed,defgrad[:,:,:,1,2],p.resolution)
  defgrad = postprocessingMath.inverse_reconstruction(res_x,res_y,res_z,undeformed,deformed)
  defgrad_av = postprocessingMath.tensor_avg(res_x,res_y,res_z,defgrad)
  centroids_coord = postprocessingMath.deformed(res_x,res_y,res_z,p.dimension,defgrad,defgrad_av)
  centroids_coord2 = postprocessingMath.deformed_fft(res_x,res_y,res_z,p.dimension,defgrad,defgrad_av,1.0)
  ms = postprocessingMath.mesh(p.resolution[0],p.resolution[1],p.resolution[2],p.dimension,defgrad_av,centroids_coord)
  ms2 = postprocessingMath.mesh(p.resolution[0],p.resolution[1],p.resolution[2],p.dimension,defgrad_av,centroids_coord2)
  writeVtkAscii(name+'-mesh-usual-%s.vtk'%i,ms,defgrad[:,:,:,1,2],p.resolution)
  writeVtkAscii(name+'-mesh-fft-%s.vtk'%i,ms2,defgrad[:,:,:,1,2],p.resolution)
  #writeVtkAsciidefgrad_av(name+'-box-%i.vtk'%i,p.dimension,defgrad_av)
  #writeVtkAsciiDots(name+'-points-%i.vtk'%i,centroids_coord,grain,p.resolution)
  sys.stdout.flush()



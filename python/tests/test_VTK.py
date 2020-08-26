import os
import filecmp
import time

import pytest
import numpy as np

from damask import VTK
from damask import grid_filters

@pytest.fixture
def reference_dir(reference_dir_base):
    """Directory containing reference results."""
    return reference_dir_base/'VTK'

class TestVTK:

    def test_rectilinearGrid(self,tmp_path):
        grid   = np.random.randint(5,10,3)*2
        size   = np.random.random(3) + 1.0
        origin = np.random.random(3)
        v = VTK.from_rectilinearGrid(grid,size,origin)
        string = v.__repr__()
        v.to_file(tmp_path/'rectilinearGrid',False)
        vtr = VTK.from_file(tmp_path/'rectilinearGrid.vtr')
        with open(tmp_path/'rectilinearGrid.vtk','w') as f:
            f.write(string)
        vtk = VTK.from_file(tmp_path/'rectilinearGrid.vtk','VTK_rectilinearGrid')
        assert(string == vtr.__repr__() == vtk.__repr__())

    def test_polyData(self,tmp_path):
        points = np.random.rand(100,3)
        v = VTK.from_polyData(points)
        string = v.__repr__()
        v.to_file(tmp_path/'polyData',False)
        vtp = VTK.from_file(tmp_path/'polyData.vtp')
        with open(tmp_path/'polyData.vtk','w') as f:
            f.write(string)
        vtk = VTK.from_file(tmp_path/'polyData.vtk','polyData')
        assert(string == vtp.__repr__() == vtk.__repr__())

    @pytest.mark.parametrize('cell_type,n',[
                                            ('VTK_hexahedron',8),
                                            ('TETRA',4),
                                            ('quad',4),
                                            ('VTK_TRIANGLE',3)
                                            ]
                            )
    def test_unstructuredGrid(self,tmp_path,cell_type,n):
        nodes = np.random.rand(n,3)
        connectivity = np.random.choice(np.arange(n),n,False).reshape(-1,n)
        v = VTK.from_unstructuredGrid(nodes,connectivity,cell_type)
        string = v.__repr__()
        v.to_file(tmp_path/'unstructuredGrid',False)
        vtu = VTK.from_file(tmp_path/'unstructuredGrid.vtu')
        with open(tmp_path/'unstructuredGrid.vtk','w') as f:
            f.write(string)
        vtk = VTK.from_file(tmp_path/'unstructuredGrid.vtk','unstructuredgrid')
        assert(string == vtu.__repr__() == vtk.__repr__())


    def test_parallel_out(self,tmp_path):
        points = np.random.rand(102,3)
        v = VTK.from_polyData(points)
        fname_s = tmp_path/'single.vtp'
        fname_p = tmp_path/'parallel.vtp'
        v.to_file(fname_s,False)
        v.to_file(fname_p,True)
        for i in range(10):
            if os.path.isfile(fname_p) and filecmp.cmp(fname_s,fname_p):
                assert(True)
                return
            time.sleep(.5)
        assert(False)


    @pytest.mark.parametrize('name,dataset_type',[('this_file_does_not_exist.vtk', None),
                                                  ('this_file_does_not_exist.vtk','vtk'),
                                                  ('this_file_does_not_exist.vtx', None)])
    def test_invalid_dataset_type(self,dataset_type,name):
        with pytest.raises(TypeError):
            VTK.from_file('this_file_does_not_exist.vtk',dataset_type)


    def test_compare_reference_polyData(self,update,reference_dir,tmp_path):
        points=np.dstack((np.linspace(0.,1.,10),np.linspace(0.,2.,10),np.linspace(-1.,1.,10))).squeeze()
        polyData = VTK.from_polyData(points)
        polyData.add(points,'coordinates')
        if update:
             polyData.write(reference_dir/'polyData')
        else:
             reference = VTK.from_file(reference_dir/'polyData.vtp')
             assert polyData.__repr__() == reference.__repr__()

    def test_compare_reference_rectilinearGrid(self,update,reference_dir,tmp_path):
        grid = np.array([5,6,7],int)
        size = np.array([.6,1.,.5])
        rectilinearGrid = VTK.from_rectilinearGrid(grid,size)
        c = grid_filters.cell_coord0(grid,size).reshape(-1,3,order='F')
        n = grid_filters.node_coord0(grid,size).reshape(-1,3,order='F')
        rectilinearGrid.add(c,'cell')
        rectilinearGrid.add(n,'node')
        if update:
             rectilinearGrid.write(reference_dir/'rectilinearGrid')
        else:
             reference = VTK.from_file(reference_dir/'rectilinearGrid.vtr')
             assert rectilinearGrid.__repr__() == reference.__repr__()

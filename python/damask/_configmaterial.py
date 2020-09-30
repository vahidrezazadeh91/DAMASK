import copy

import numpy as np

from . import Config
from . import Lattice
from . import Rotation

class ConfigMaterial(Config):
    """Material configuration."""

    def save(self,fname='material.yaml',**kwargs):
        """
        Save to yaml file.

        Parameters
        ----------
        fname : file, str, or pathlib.Path, optional
            Filename or file for writing. Defaults to 'material.yaml'.
        **kwargs : dict
            Keyword arguments parsed to yaml.dump.

        """
        super().save(fname,**kwargs)

    @property
    def is_complete(self):
        """Check for completeness."""
        ok = True
        for top_level in ['homogenization','phase','microstructure']:
            # ToDo: With python 3.8 as prerequisite we can shorten with :=
            ok &= top_level in self
            if top_level not in self: print(f'{top_level} entry missing')

        if ok:
           ok &= len(self['microstructure']) > 0
           if len(self['microstructure']) < 1: print('Incomplete microstructure definition')

        if ok:
            homogenization = set()
            phase          = set()
            for i,v in enumerate(self['microstructure']):
                if 'homogenization' in v:
                    homogenization.add(v['homogenization'])
                else:
                    print(f'No homogenization specified in microstructure {i}')
                    ok = False

                if 'constituents' in v:
                    for ii,vv in enumerate(v['constituents']):
                        if 'orientation' not in vv:
                            print('No orientation specified in constituent {ii} of microstructure {i}')
                            ok = False
                        if 'phase' in vv:
                            phase.add(vv['phase'])
                        else:
                            print(f'No phase specified in constituent {ii} of microstructure {i}')
                            ok = False

            for k,v in self['phase'].items():
                if 'lattice' not in v:
                    print(f'No lattice specified in phase {k}')
                    ok = False

            #for k,v in self['homogenization'].items():
            #    if 'N_constituents' not in v:
            #        print(f'No. of constituents not specified in homogenization {k}'}
            #        ok = False

            if phase - set(self['phase']):
                print(f'Phase(s) {phase-set(self["phase"])} missing')
                ok = False
            if homogenization - set(self['homogenization']):
                print(f'Homogenization(s) {homogenization-set(self["homogenization"])} missing')
                ok = False

        return ok


    @property
    def is_valid(self):
        """Check for valid file layout."""
        ok = True

        if 'phase' in self:
            for k,v in self['phase'].items():
                if 'lattice' in v:
                    try:
                        Lattice(v['lattice'])
                    except KeyError:
                        s = v['lattice']
                        print(f"Invalid lattice: '{s}' in phase '{k}'")
                        ok = False

        if 'microstructure' in self:
            for i,v in enumerate(self['microstructure']):
                if 'constituents' in v:
                    f = 0.0
                    for c in v['constituents']:
                        f+= float(c['fraction'])
                        if 'orientation' in c:
                            try:
                                Rotation.from_quaternion(c['orientation'])
                            except ValueError:
                                o = c['orientation']
                                print(f"Invalid orientation: '{o}' in microstructure '{i}'")
                                ok = False
                    if not np.isclose(f,1.0):
                        print(f"Invalid total fraction '{f}' in microstructure '{i}'")
                        ok = False

        return ok


    def microstructure_rename_phase(self,mapping,ID=None,constituent=None):
        """
        Change phase name in microstructure.

        Parameters
        ----------
        mapping: dictionary
            Mapping from old name to new name
        ID: list of ints, optional
            Limit renaming to selected microstructure IDs.
        constituent: list of ints, optional
            Limit renaming to selected constituents.

        """
        dup = copy.deepcopy(self)
        for i,m in enumerate(dup['microstructure']):
            if ID and i not in ID: continue
            for c in m['constituents']:
                if constituent is not None and c not in constituent: continue
                try:
                    c['phase'] = mapping[c['phase']]
                except KeyError:
                    continue
        return dup


    def microstructure_rename_homogenization(self,mapping,ID=None):
        """
        Change homogenization name in microstructure.

        Parameters
        ----------
        mapping: dictionary
            Mapping from old name to new name
        ID: list of ints, optional
            Limit renaming to selected homogenization IDs.

        """
        dup = copy.deepcopy(self)
        for i,m in enumerate(dup['microstructure']):
            if ID and i not in ID: continue
            try:
                m['homogenization'] = mapping[m['homogenization']]
            except KeyError:
                continue
        return dup

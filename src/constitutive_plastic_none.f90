!--------------------------------------------------------------------------------------------------
!> @author Franz Roters, Max-Planck-Institut für Eisenforschung GmbH
!> @author Philip Eisenlohr, Max-Planck-Institut für Eisenforschung GmbH
!> @author Martin Diehl, Max-Planck-Institut für Eisenforschung GmbH
!> @brief Dummy plasticity for purely elastic material
!--------------------------------------------------------------------------------------------------
submodule(constitutive:constitutive_plastic) plastic_none

contains

!--------------------------------------------------------------------------------------------------
!> @brief Perform module initialization.
!> @details reads in material parameters, allocates arrays, and does sanity checks
!--------------------------------------------------------------------------------------------------
module function plastic_none_init() result(myPlasticity)

  logical, dimension(:), allocatable :: myPlasticity
  integer :: &
    Ninstances, &
    p, &
    Nconstituents
  class(tNode), pointer :: &
    phases, &
    phase, &
    pl

  print'(/,a)', ' <<<+-  plastic_none init  -+>>>'

  phases => config_material%get('phase')
  allocate(myPlasticity(phases%length), source = .false.)
  do p = 1, phases%length
    phase => phases%get(p)
    pl => phase%get('plasticity')
    if(pl%get_asString('type') == 'none') myPlasticity(p) = .true.
  enddo

  Ninstances = count(myPlasticity)
  print'(a,i2)', ' # instances: ',Ninstances; flush(IO_STDOUT)
  if(Ninstances == 0) return

  do p = 1, phases%length
    phase => phases%get(p)
    if(.not. myPlasticity(p)) cycle
    Nconstituents = count(material_phaseAt == p) * discretization_nIPs
    call constitutive_allocateState(plasticState(p),Nconstituents,0,0,0)
  enddo

end function plastic_none_init


end submodule plastic_none

import os
import json

import numpy as np
from rdkit import Chem
from scipy.spatial import distance_matrix


DIR = os.path.dirname(__file__)

with open(os.path.join(DIR, "InChIKey_to_index.json")) as json_file:
    InChIKey_to_index = json.load(json_file)

_q0 = 79.53  # area normalization parameter [Å**2]
_r0 = 66.69  # volume normalization parameter [Å**3]
_z = 10  # coordination number
_R = 1.987204258e-3  # gas constant [kcal/K/mol]
_AES = 6525.69  # electrostatic constant A [kcal*ang**4/mol/e**2]
_BES = 1.4859e8  # electrostatic constant B [kcal*Å**4*K**2/mol/e**2]
_sig0 = 0.007  # hydrogen bondable screening charge [e/Å**2]

_aeff = 7.25  # effective area [Å**2], number of sigma profiles,
_chb = np.array(
    [
        [0, 0, 0, 0],
        [0, 4013.78, 3016.43, 3020.18],
        [0, 3016.43, 932.31, 1872.84],
        [0, 3020.18, 1872.84, 2225.67],
    ]
)  # hydrogen bonding parameter [kcal*Å^4/mol/e^2],
_reff = np.sqrt(_aeff / np.pi)  # effective radius, [Å]
_cES = lambda T: _AES + _BES / T / T  # electrostatic parameter [kcal*Å^4/mol/e^2]
_ang_au = 0.52917721067  # unit change [Å/atomic unit]
_fdecay = 0.52928 ** (-2)  # unit conversion parameter [1]
_rc = {
    "H": 0.31,
    "He": 0.28,
    "Li": 1.28,
    "Be": 0.96,
    "B": 0.84,
    "C": 0.76,  # sp3 hybridization, sp2: 0.73 sp1: 0.69
    "N": 0.71,
    "O": 0.66,
    "F": 0.57,
    "Ne": 0.58,
    "Na": 1.66,
    "Mg": 1.41,
    "Al": 1.21,
    "Si": 1.11,
    "P": 1.07,
    "S": 1.05,
    "Cl": 1.02,
    "Ar": 1.06,
    "K": 2.03,
    "Ca": 1.76,
    "Sc": 1.70,
    "Ti": 1.60,
    "V": 1.53,
    "Cr": 1.39,
    "Mn": 1.39,  # l.s.; h.s.: 1.61
    "Fe": 1.32,  # l.s.; h.s.: 1.52
    "Co": 1.26,  # l.s.; h.s.: 1.50
    "Ni": 1.24,
    "Cu": 1.32,
    "Zn": 1.22,
    "Ga": 1.22,
    "Ge": 1.20,
    "As": 1.19,
    "Se": 1.20,
    "Br": 1.20,
    "Kr": 1.16,
    "Rb": 2.20,
    "Sr": 1.95,
    "Y": 1.90,
    "Zr": 1.75,
    "Nb": 1.64,
    "Mo": 1.54,
    "Tc": 1.47,
    "Ru": 1.46,
    "Rh": 1.42,
    "Pd": 1.39,
    "Ag": 1.45,
    "Cd": 1.44,
    "In": 1.42,
    "Sn": 1.39,
    "Sb": 1.39,
    "Te": 1.38,
    "I": 1.39,
    "Xe": 1.40,
    "Cs": 2.44,
    "Ba": 2.15,
    "La": 2.07,
    "Ce": 2.04,
    "Pr": 2.03,
    "Nd": 2.01,
    "Pm": 1.99,
    "Sm": 1.98,
    "Eu": 1.98,
    "Gd": 1.96,
    "Tb": 1.94,
    "Dy": 1.92,
    "Ho": 1.92,
    "Er": 1.89,
    "Tm": 1.90,
    "Yb": 1.87,
    "Lu": 1.87,
    "Hf": 1.75,
    "Ta": 1.70,
    "W": 1.62,
    "Re": 1.51,
    "Os": 1.44,
    "Ir": 1.41,
    "Pt": 1.36,
    "Au": 1.36,
    "Hg": 1.32,
    "Tl": 1.45,
    "Pb": 1.46,
    "Bi": 1.48,
    "Po": 1.40,
    "At": 1.50,
    "Rn": 1.50,
    "Fr": 2.60,
    "Ra": 2.21,
    "Ac": 2.15,
    "Th": 2.06,
    "Pa": 2.00,
    "U": 1.96,
    "Np": 1.90,
    "Pu": 1.87,
    "Am": 1.80,
    "Cm": 1.69,
}


def get_file_dir_from_SMILES(SMILES: str) -> str | None:
    mol = Chem.MolFromSmiles(SMILES)
    InChIKey = Chem.MolToInchiKey(mol)
    try:
        cosmo_file_index = InChIKey_to_index[InChIKey]

        return os.path.join(DIR, "cosmo_files", f"{cosmo_file_index}.cosmo")
    except:

        raise Exception("Unsupported Molecule")


def _get_cosmo_from_ms(file):
    """Get COSMO properties from the cosmo file in Material Studio.

    This code reads the KU database's COSMO files.

    Parameters
    ----------
    opened_file : _io.TextIOWrapper
        Opened file.

    Returns
    -------
    area : float
        Cavity area.
    volume : float
        Cavity volume.
    atom : numpy.ndarray of shape=(num_atom,)
        Atom symbols sorted by index in the cosmo file.
    coord : numpy.ndarray of shape=(num_atom, 3)
        The x, y, z coordinates of the atoms.
    seg : numpy.ndarray of shape=(num_seg, 6)
        The list of atom index, x, y, z position, segment area, and charge
        per segment area.
    """
    # Initialize flags and data storage
    flag = "default"
    atom = []  # Atom symbols
    coord = []  # Atom coordinates
    seg = []  # Segment information
    area = None  # Cavity area
    volume = None  # Cavity volume
    ang_per_au = _ang_au

    # Read file and extract data
    with open(file, "r") as f:
        for line in f:
            # Update parsing flag based on section headers
            if "$coordinates xyz [au]" in line:
                flag = "coordinate"
                continue
            elif "n  atom        position (X, Y, Z) [au]" in line:
                flag = "segment"
                continue
            elif "$end" in line and flag == "coordinate":
                flag = "default"
                continue

            # Parse data based on current flag
            if "Surface area of cavity" in line:
                area = float(line.split()[7])  # [au**2]
            elif "Total Volume of cavity" in line:
                volume = float(line.split()[6])  # [au**3]
            elif flag == "coordinate" and "$end" not in line:
                parts = line.split()
                atom.append(parts[0])
                coord.append([float(x) for x in parts[1:4]])  # [au]
            elif flag == "segment" and line.strip():  # not empty line
                parts = line.split()
                seg.append(
                    [int(parts[1]) - 1] + [float(x) for x in parts[2:5] + parts[6:8]]
                )

    # Convert lists to numpy arrays
    atom = np.array(atom)
    coord = np.array(coord)
    seg = np.array(seg)

    # Convert units from atomic units to angstroms
    area *= ang_per_au**2  # [Å**2]
    volume *= ang_per_au**3  # [Å**3]
    coord *= ang_per_au  # [Å]
    seg[:, 1:4] *= ang_per_au  # [Å]
    seg[:, 4] *= ang_per_au**2  # [Å**2]
    seg[:, 5] /= ang_per_au**2  # [e/Å**2]

    return area, volume, atom, coord, seg


def _get_cosmo_from_not_ms(file):
    """Get COSMO properties from the cosmo file not in Material Studio.

    This code reads the VT and UD databases' COSMO files.

    Parameters
    ----------
    opened_file : _io.TextIOWrapper
        Opened file.

    Returns
    -------
    area : float
        Cavity area.
    volume : float
        Cavity volume.
    atom : numpy.ndarray of shape=(num_atom,)
        Atom symbols sorted by index in the cosmo file.
    coord : numpy.ndarray of shape=(num_atom, 3)
        The x, y, z coordinates of the atoms.
    seg : numpy.ndarray of shape=(num_seg, 6)
        The list of atom index, x, y, z position, segment area, and charge
        per segment area.
    """
    # Initialize storage
    atom = []  # Atom symbols
    coord = []  # Atom coordinates
    seg = []  # Segment information
    area = None  # Cavity area
    volume = None  # Cavity volume
    flag = "default"

    # Read and parse file
    with open(file, "r") as f:
        for line in f:
            # Update parsing flag based on section headers
            if "!DATE" in line:
                flag = "coordinate"
                continue
            elif "n   atom        position (X, Y, Z) [au]" in line:
                flag = "segment"
                continue
            elif "end" in line and flag == "coordinate":
                flag = "default"
                continue

            # Parse data based on current flag
            if "Total surface area of cavity" in line:
                area = float(line.split()[7])  # [Å**2]
            elif "Total volume of cavity" in line:
                volume = float(line.split()[6])  # [Å**3]
            elif flag == "coordinate" and "end" not in line:
                parts = line.split()
                atom.append(parts[7])
                coord.append([float(x) for x in parts[1:4]])  # [Å]
            elif flag == "segment" and line.strip():  # not empty line
                parts = line.split()
                seg.append(
                    [int(parts[1]) - 1] + [float(x) for x in parts[2:5] + parts[6:8]]
                )
                # [0], [au], [au], [au], [Å**2], [e/Å**2]

    # Convert to numpy arrays
    atom = np.array(atom)
    coord = np.array(coord)
    seg = np.array(seg)

    # Convert units from atomic units to angstroms
    seg[:, 1:4] *= _ang_au  # [Å]

    return area, volume, atom, coord, seg


def get_cosmo(file_dir: str):
    """Get COSMO properties from the cosmo extension file.

    Parameters
    ----------
    file : str
        The name of the cosmo file.

    See Also
    --------
    is_from_ms
        Function to check if the file is from databases or Material Studio.
    get_cosmo_from_ms, get_cosmo_from_not_ms
        Functions to get COSMO informations.
    """

    with open(file_dir, "r") as opened_file:
        line = opened_file.readline()
        if "COSMO Results from DMol3" in line:  # Material Studio 2017
            return _get_cosmo_from_ms(file_dir)
        elif "text" in line:  # VT 2006, UD 2020, or KU 2023 database
            return _get_cosmo_from_not_ms(file_dir)
        else:
            raise ValueError(f"The file {file_dir} is not interpreted as cosmo file.")


def _get_bond(atom, coord):
    """Get bond matrix.

    Parameters
    ----------
    atom : numpy.ndarray of shape=(num_atom,)
        Atom symbols sorted by index in the cosmo file.
    coord : numpy.ndarray of shape=(num_atom, 3)
        The x, y, z coordinates of the atoms.

    Returns
    -------
    bond : numpy.ndarray of shape=(num_atom, num_atom)
        The bond matrix. If two atoms are bonded, their entry is 1, else 0.
    """
    d_atom = distance_matrix(coord, coord)  # Distance between atoms
    rc = np.array([_rc[a] for a in atom])  # Radii of atoms

    mask = d_atom < 1.15 * (rc[:, np.newaxis] + rc[np.newaxis, :])
    bond = np.where(mask, 1, 0)
    np.fill_diagonal(bond, 0)  # Atoms do not bond with themselves.

    return bond


def _get_sigma(atom, seg, stype):
    """Get sigma profiles.

    Parameters
    ----------
    atom : numpy.ndarray of shape=(num_atom,)
        Atom symbols sorted by index in the cosmo file.
    seg : numpy.ndarray of shape=(num_seg, 6)
        The list of atom index, x, y, z position, segment area, and charge
        per segment area.
    stype : list of shape=(num_atom,)
        The sigma profile type for each atom.

    Returns
    -------
    psigA : numpy.ndarray of shape=(num_sp, 51)
        The sigma profiles of the molecule. The number of sigma profiles is
        dependent on the version.
        {version: num_sp} = {2002: 1, 2010: 3, 2013: 3, 2019: 4}
    """
    # import global parameters
    reff = _reff
    num_sp = 4

    # Set sigma profile types to integers
    type_mapping = {"NHB": 0, "OH": 1, "OT": 2, "COOH": 3}
    stype_int = np.array([type_mapping[element] for element in stype])

    # Define segment informations
    seg_atom_index = np.int32(seg[:, 0])
    seg_atom = atom[seg_atom_index]
    seg_stype = stype_int[seg_atom_index]
    seg_coord = seg[:, 1:4]
    seg_area = seg[:, 4]
    seg_charge = seg[:, 5]

    # Calculate radii of the segments and distances between the segments
    r = np.sqrt(seg_area / np.pi)
    d = distance_matrix(seg_coord, seg_coord)

    # Calculate averaged surface charges of the segments
    rcal = r**2 * reff**2 / (r**2 + reff**2)
    dcal = np.exp(-_fdecay * d**2 / (r**2 + reff**2).reshape(-1, 1))

    upper = np.einsum("n,n,mn->m", seg_charge, rcal, dcal)
    lower = np.einsum("n,mn->m", rcal, dcal)

    seg_avg_charge = upper / lower

    # Decide sigma profile types
    # Initialize all segments as NHB (type 0)
    sig_type = np.int32(np.zeros(len(seg)))

    # OH sigma profile (type 1) conditions
    oh_oxygen_mask = (seg_atom == "O") & (seg_stype == 1) & (seg_avg_charge > 0)
    oh_hydrogen_mask = (seg_atom == "H") & (seg_stype == 1) & (seg_avg_charge < 0)

    # OT sigma profile (type 2) conditions
    ot_acceptor_mask = (
        ((seg_atom == "O") | (seg_atom == "N") | (seg_atom == "F"))
        & (seg_stype == 2)
        & (seg_avg_charge > 0)
    )
    ot_hydrogen_mask = (seg_atom == "H") & (seg_stype == 2) & (seg_avg_charge < 0)

    # Update sigma types
    sig_type = np.where(oh_oxygen_mask | oh_hydrogen_mask, 1, sig_type)
    sig_type = np.where(ot_acceptor_mask | ot_hydrogen_mask, 2, sig_type)

    # Find COOH sigma profile
    sig_type = np.where(seg_stype == 3, 3, sig_type)

    # Calculate sigma profiles
    sig = np.linspace(-0.025, 0.025, 51)

    left = np.int32(np.floor((seg_avg_charge - sig[0]) / 0.001))
    w = (sig[left + 1] - seg_avg_charge) / 0.001

    psigA = np.zeros((num_sp, 51))
    np.add.at(psigA, (sig_type, left), w * seg_area)
    np.add.at(psigA, (sig_type, left + 1), (1 - w) * seg_area)

    phb = 1 - np.exp(-(sig**2) / 2 / _sig0**2)
    psigA[0] = psigA[0] + np.sum(psigA[1:], axis=0) * (1 - phb)
    psigA[1:] = psigA[1:] * phb

    return psigA


def _cal_DW(T):
    """
    Calculate the exchange energy.

    The exchange energy has the values for each charge density combinations
    and sigma profile type combinations, therefore having the shape of
    (num_sp, num_sp, 51, 51).

    Parameters
    ----------
    T : float
        The system temperature.

    Returns
    -------
    DW : numpy.ndarray of shape=(num_sp, num_sp, 51, 51)
        The exchange energy.
    """
    # Initialize parameters
    sig = np.linspace(-0.025, 0.025, 51)
    sigT = sig.reshape(-1, 1)
    DW = np.zeros((4, 4, 51, 51))

    # Calculate exchange energy for each pair of sigma profile types
    for i in range(4):
        for j in range(i + 1):
            mask = (sig * sigT) < 0
            chb_part = np.where(mask, _chb[i, j] * (sig - sigT) ** 2, 0)

            # Calculate total exchange energy
            DW[i, j] = DW[j, i] = _cES(T) * (sig + sigT) ** 2 - chb_part

    return DW


def _get_atom_type(atom, bond):
    """Get hybridization and sigma profile types for each atom.

    The dispersive natures are as below.
    DSP_WATER : WATER in this code. This indicates water.
    DSP_COOH : COOH in this code. This indicates a molecule with a carboxyl
    group.
    DSP_HB_ONLY_ACCEPTOR : HBOA in this code. The molecule contains any of
    the atoms O,N, or F but no H atoms bonded to any of these O, N, or F.
    DSP_HB_DONOR_ACCEPTOR : HBDA in this code. The molecule contains any of
    the functional groups NH, OH, or FH (but not OH of COOH or water).
    DSP_NHB : NHB in this code. This indicates that the molecule is non-
    hydrogen-bonding.

    The dispersion types are as below.
    C(sp3) : C bonded to 4 others.
    C(sp2) : C bonded to 3 others.
    C(sp) : C bonded to 2 others.
    N(sp3) : N bonded to three others.
    N(sp2) : N bonded to two others.
    N(sp) : N bonded to one other.
    -O- : O(sp3) in this code. O bonded to 2 others.
    =O : O(sp2) in this code. Double-bonded O.
    F : F bonded to one other.
    Cl : Cl bonded to one other.
    H(water) : H in water.
    H(OH) : H-O bond but not water.
    H(NH) : H bonded to N.
    H(other) : H otherwise.
    other : Undifined.

    The hydrogen-bonding types are as below.
    OH : if the atom is O and is bonded to an H, or vice versa.
    OT : if the atom is O and is bonded to an atom other than H, or if the
    atom is H and is bonded to N or F.
    COOH : if the atoms are C, O, H and are in the carboxyl group.
    NHB : otherwise.

    Parameters
    ----------
    atom : numpy.ndarray of shape=(num_atom,)
        Atom symbols sorted by index in the cosmo file.
    bond : numpy.ndarray of shape=(num_atom, num_atom)
        The bond matrix. If two atoms are bonded, their entry is 1, else 0.

    Returns
    -------
    dtype : list of shape=(num_atom,)
        The dispersion type for each atom.
    stype : list of shape=(num_atom,)
        The hydrogen-bonding type for each atom.
    dnatr : {"NHB", "HBOA", "HBDA", "WATER", "COOH"}
        The dispersive nature of the molecule.
    """
    dtype = ["other"] * len(atom)  # hybridization type
    stype = ["NHB"] * len(atom)  # sigma profile type
    dnatr = "NHB"  # dispersive nature of molecule
    dntype = set()  # dispersive nature type of atoms

    # {atom type: {bonded atoms: (dtype, stype, dnatr), ...}, ...}
    # This assumes that all atoms are belong to NHB, OT and H(other).
    atom_prop = {
        "C": {
            2: ("C(sp)", "NHB", "NHB"),
            3: ("C(sp2)", "NHB", "NHB"),
            4: ("C(sp3)", "NHB", "NHB"),
        },
        "O": {
            1: ("O(sp2)", "OT", "HBOA"),
            2: ("O(sp3)", "OT", "HBOA"),
        },
        "N": {
            1: ("N(sp)", "OT", "HBOA"),
            2: ("N(sp2)", "OT", "HBOA"),
            3: ("N(sp3)", "OT", "HBOA"),
        },
        "F": {1: ("F", "OT", "HBOA")},
        "Cl": {1: ("Cl", "NHB", "NHB")},
        "H": {1: ("H(other)", "NHB", "NHB")},
    }

    for i, atom_type in enumerate(atom):
        # Get dictionary of index and atom types bonded with atom i
        ard_i = {j: atom[j] for j in np.flatnonzero(bond[i])}

        # If the atom is in the difined properties
        if atom_type in atom_prop:
            # Get atom types, else get ("Undifined", 0)
            dtype[i], stype[i], dntype_i = atom_prop[atom_type].get(
                len(ard_i), ("other", "NHB", "NHB")
            )
            dntype.add(dntype_i)

        # Find H near N, and renew the types of H
        if atom_type == "H" and "N" in ard_i.values():
            dtype[i] = "H(NH)"
            stype[i] = "OT"
            dntype.add("HBDA")

        # Find H in HF, and renew the types of H
        if atom_type == "H" and "F" in ard_i.values():
            stype[i] = "OT"
            dntype.add("HBDA")

        # Find atom type for -OH, H2O, and COOH
        if atom_type == "H" and "O" in ard_i.values():
            # # Renew the typs of H and O in OH
            # Renew the types of H
            dtype[i] = "H(OH)"
            stype[i] = "OH"

            # Find the atom index of O in OH
            j = list(ard_i.keys())[0]
            ard_j = {k: atom[k] for k in np.flatnonzero(bond[j])}
            # Renew the types of O in -OH
            stype[j] = "OH"
            dntype.add("HBDA")

            # # Further find H-OH and CO-OH
            # if the O in -OH has not two bonds, stop searching
            if len(ard_j) != 2:
                break

            # Find atom index of neighber of O in -OH, but not H in -OH
            k = [k for k in ard_j.keys() if k != i][0]
            ard_k = {m: atom[m] for m in np.flatnonzero(bond[k])}

            # if atom k is H, that is, if the molecule is water, renew the
            # dtype of the Hs in H2O and stop searching
            if atom[k] == "H":
                dtype[i] = "H(water)"
                dtype[k] = "H(water)"
                dntype.add("WATER")
                break

            # # Further find COOH
            # if the atom k is not the C in part of COOH, stop searching
            if not (
                atom[k] == "C"
                and len(ard_k) == 3
                and list(ard_k.values()).count("O") == 2
            ):
                break

            # Find the O, neighber of C in -COH, but not in O in -COH
            m = [m for m in ard_k.keys() if (m != j and ard_k[m] == "O")][0]
            ard_m = {n: atom[n] for n in np.flatnonzero(bond[m])}

            # if the atom m is -O-, not =O, stop searching
            if len(ard_m) != 1:
                break

            # Renew i(H), j(O), k(C) and m(O) as the part of COOH
            dntype.add("COOH")
            stype[i] = "COOH"
            stype[j] = "COOH"
            stype[m] = "COOH"

    # find the dispersive nature of the molecule
    if "HBOA" in dntype:
        dnatr = "HBOA"
    if "HBDA" in dntype:
        dnatr = "HBDA"
    if "WATER" in dntype:
        dnatr = "WATER"
    if "COOH" in dntype:
        dnatr = "COOH"

    return dtype, stype, dnatr


def _get_dsp(dtype):
    """
    Get the dispersive nature of the molecule.

    Parameters
    ----------
    dtype : list of shape=(num_atom,)
        The dispersion type for each atom.

    Returns
    -------
    ek : float
        Dispersive parameter.
    """
    # dispersive parameters
    ddict = {
        "C(sp3)": 115.7023,
        "C(sp2)": 117.4650,
        "C(sp)": 66.0691,
        "N(sp3)": 15.4901,
        "N(sp2)": 84.6268,
        "N(sp)": 109.6621,
        "O(sp3)": 95.6184,  # -O-
        "O(sp2)": -11.0549,  # =O
        "F": 52.9318,
        "Cl": 104.2534,
        "H(water)": 58.3301,
        "H(OH)": 19.3477,
        "H(NH)": 141.1709,
        "H(other)": 0,
    }

    # calculate the dispersive parameter of the molecule
    ek = np.vectorize(ddict.get)(dtype)
    if None in ek:

        return None
    else:
        ek = np.sum(ek) / np.count_nonzero(ek)

    return ek


def retrieve_sigma_profile(file_dir) -> dict:
    opened_file = open(file_dir, "r")
    line = opened_file.readline()
    if "COSMO Results from DMol3" in line:  # Material Studio 2017
        area, volume, atoms, coord, seg = _get_cosmo_from_ms(file_dir)
    elif "text" in line:  # VT 2006, UD 2020, or KU 2023 database
        area, volume, atoms, coord, seg = _get_cosmo_from_not_ms(file_dir)
    else:
        raise ValueError(f"The file {file_dir} is not interpreted as cosmo file.")

    bonds = _get_bond(atoms, coord)
    dtype, stype, dnatr = _get_atom_type(atoms, bonds)
    sigma_profiles = _get_sigma(atoms, seg, stype).reshape(1, 4, 51)
    ek = _get_dsp(dtype)

    return {
        "area": area,
        "volume": volume,
        "sigma_profiles": sigma_profiles,
        "ek": ek,
        "natr": dnatr,
    }


def cal_ln_gam_comb(A, V, x):
    """Calculate log of combinatory activity coefficients.

    Parameters
    ----------
    None.

    Returns
    -------
    ln_gam_comb : numpy.ndarray of shape=(num_comp,)
        Combinatory activity coefficients of components.
    """
    # calculate normalized areas and volumes
    q = A / _q0
    r = V / _r0
    L = (_z / 2) * (r - q) - (r - 1)

    theta = q / np.sum(x * q)
    phi = r / np.sum(x * r)

    # calcualte combinatory activity coefficients
    ln_gam_comb = (
        np.log(phi) + _z * q * np.log(theta / phi) / 2 + L - phi * np.sum(x * L)
    )

    return ln_gam_comb


def cal_ln_gam_res(A, psigA, x, T):
    """
    Calculate residual activity coefficients.

    Parameters
    ----------
    None.

    Returns
    -------
    ln_gam_res : numpy.ndarray of shape=(num_comp,)
        Residual activity coefficients of components.
    """
    # calculate intermediate terms
    psig = np.einsum("itm,i->itm", psigA, 1 / A)
    psig_mix = np.einsum("i,itm->tm", x, psigA) / np.sum(x * A)

    exp_DW = np.exp(-_cal_DW(T) / _R / T)

    A_plus = np.einsum("stmn,isn->istmn", exp_DW, psig)  # A^(+)
    A_plus_mix = np.einsum("stmn,sn->stmn", exp_DW, psig_mix)  # A^(+)_mix

    # calculate the segment activity coefficients
    Gam = np.ones(np.shape(psig))
    Gam_mix = np.ones(np.shape(psig_mix))
    diff = 1

    for _ in range(500):
        Gam_old = np.array(Gam)
        Gam_mix_old = np.array(Gam_mix)

        # Update Gam element-wise
        for i in range(Gam.shape[0]):
            for t in range(Gam.shape[1]):
                for m in range(Gam.shape[2]):
                    Gam[i, t, m] = 1 / np.einsum(
                        "sn,sn->", A_plus[i, :, t, m, :], Gam[i, :, :]
                    )

        # Update Gam_mix element-wise
        for t in range(Gam_mix.shape[0]):
            for m in range(Gam_mix.shape[1]):
                Gam_mix[t, m] = 1 / np.einsum(
                    "sn,sn->", A_plus_mix[:, t, m, :], Gam_mix[:, :]
                )

        # check convergence
        diff = np.sum((Gam - Gam_old) ** 2)
        diff_mix = np.sum((Gam_mix - Gam_mix_old) ** 2)

        if diff <= 1e-6 and diff_mix <= 1e-6:
            break
    else:
        raise Exception("Converge failed")

    # calculate residual activity coefficients
    Gam_part = np.log(Gam_mix) - np.log(Gam)
    ln_gam_res = np.einsum("itm,itm->i", psigA, Gam_part) / _aeff

    return ln_gam_res


def cal_ln_gam_dsp(x, ek, dnatr):
    """
    Calculate dispersive activity coefficients.

    Parameters
    ----------
    None.

    Returns
    -------
    ln_gam_dsp : numpy.ndarray of shape=(num_comp,)
        Dispersive activity coefficients of components.
    """
    num_mol = len(x)

    if None in ek:

        return np.zeros(num_mol)
    elif True in np.isnan(ek):

        return np.zeros(num_mol)

    ekT = ek.reshape(-1, 1)

    # check if dispersion activity coefficients are applicable
    if None in ek or None in dnatr:
        ln_gam_dsp = np.array([0] * num_mol)

        return ln_gam_dsp
    elif True in np.isnan(ek):
        ln_gam_dsp = np.array([0] * num_mol)

        return ln_gam_dsp

    # calculate interaction parameters
    w = np.ones((num_mol, num_mol)) * 0.27027
    wpair = [
        {"WATER", "HBOA"},
        {"COOH", "NHB"},
        {"COOH", "HBDA"},
        {"WATER", "COOH"},
    ]
    for i in range(num_mol):
        for j in range(i):
            if {dnatr[i], dnatr[j]} in wpair:
                w[i][j] = w[j][i] = -0.27027

    A = w * (0.5 * (ek + ekT) - np.sqrt(ek * ekT))  # not area

    # calculate dispersive activity coefficients
    ln_gam_dsp = np.zeros(num_mol)
    for i in range(num_mol):
        for j in range(num_mol):
            if i != j:
                ln_gam_dsp[i] = ln_gam_dsp[i] + x[j] * A[i, j]
            if j > i:
                ln_gam_dsp[i] = ln_gam_dsp[i] - x[i] * x[j] * A[i, j]

    return ln_gam_dsp


def calculate_gamma(chemical_profiles: list, x: list, T: float) -> list:
    """
    Calculate COSMO-SAC activity coefficients.

    Parameters
    ----------
    None.

    Returns
    -------
    gam : list of shape=(num_comp,)
        Activity coefficients of components.
    """
    areas = np.array([])
    volumes = np.array([])
    psigA = np.array([]).reshape(0, 4, 51)
    eks = np.array([])
    natrs = []
    for chemical_profile in chemical_profiles:
        areas = np.append(areas, chemical_profile["area"])
        volumes = np.append(volumes, chemical_profile["volume"])
        psigA = np.vstack((psigA, chemical_profile["sigma_profiles"]))
        eks = np.append(eks, chemical_profile["ek"])
        natrs.append(chemical_profile["natr"])

    ln_gam_comb = cal_ln_gam_comb(areas, volumes, x)
    ln_gam_res = cal_ln_gam_res(areas, psigA, x, T)
    ln_gam_dsp = cal_ln_gam_dsp(x, eks, natrs)

    ln_gam = ln_gam_comb + ln_gam_res + ln_gam_dsp
    gam: np.ndarray = np.exp(ln_gam)

    return gam.tolist()

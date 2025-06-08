from .modules import get_file_dir_from_SMILES, retrieve_sigma_profile, calculate_gamma


def calculate_binary_gamma(
    SMILES1: str,
    SMILES2: str,
    x1: float,
    x2: float,
    T: float,
) -> list:
    comp1_dir = get_file_dir_from_SMILES(SMILES1)
    comp2_dir = get_file_dir_from_SMILES(SMILES2)

    return calculate_gamma(
        [retrieve_sigma_profile(comp1_dir), retrieve_sigma_profile(comp2_dir)],
        [x1, x2],
        T,
    )

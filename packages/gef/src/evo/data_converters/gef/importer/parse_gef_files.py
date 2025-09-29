#  Copyright © 2025 Bentley Systems, Incorporated
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from pathlib import Path

import evo.logging

from pygef.broxml.parse_cpt import read_cpt as read_cpt_xml
from pygef import read_cpt
from pygef.cpt import CPTData
from pygef.gef.gef import _Gef

logger = evo.logging.getLogger("data_converters")


def parse_gef_file(filepath: str | Path) -> CPTData | dict[str, CPTData]:
    """
    Parse a single GEF or CPT XML file.

    Args:
        filepath (str | Path): Path to the file to parse.

    Returns:
        CPTData | dict[str, CPTData]:
            - For .gef files: Returns a single CPTData object
            - For .xml files: Returns a dictionary mapping id, CPTData objects
    """
    try:
        if not Path(filepath).exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        ext = Path(filepath).suffix.lower()

        if ext == ".xml":
            # No method in pygef to detect type, so just try to read as CPT.
            # XML files can contain multiple CPT entries.
            try:
                multiple_cpt_data = read_cpt_xml(filepath)
            except Exception:
                raise ValueError(f"File '{filepath}' is not a CPT XML file or could not be parsed as CPT data.")

            if not multiple_cpt_data:
                raise ValueError(f"No CPT data found in XML file '{filepath}'")

            # Return dictionary for XML files (can have multiple entries)
            result = {}
            for cpt_data in multiple_cpt_data:
                check_for_required_columns(cpt_data, filepath)
                dict_id = get_gef_id(cpt_data, filepath)
                if dict_id in result:
                    raise ValueError(f"Duplicate ID '{dict_id}' in file '{filepath}'")
                result[dict_id] = cpt_data

            return result
        else:
            # _Gef only reads .gef files.
            gef = _Gef(filepath)
            if gef.type != "cpt":
                raise ValueError(f"File '{filepath}' is not a CPT GEF file (type: {gef.type})")
            cpt_data = read_cpt(filepath)
            check_for_required_columns(cpt_data, filepath)

            # Return single CPTData for .gef files
            return cpt_data

    except Exception as e:
        raise RuntimeError(f"Error processing file '{filepath}': {e}") from e


def parse_gef_files(filepaths: list[str | Path]) -> dict[str, CPTData]:
    """
    Parse a list of GEF & CPT XML files and return a dictionary of CPTData objects keyed by hole_id.

    Only files identified as CPT (Cone Penetration Test) are read and included.

    Args:
        filepaths (list[str | Path]): List of file paths to parse.

    Returns:
        dict[str, CPTData]: Dictionary mapping each CPT's hole_id to its CPTData object.
    """
    data: dict[str, CPTData] = {}

    for filepath in filepaths:
        file_result = parse_gef_file(filepath)

        # Handle both single CPTData and dictionary of CPTData
        if isinstance(file_result, dict):
            print(file_result)
            # XML file with multiple entries
            for dict_id, cpt_data in file_result.items():
                if dict_id in data:
                    raise ValueError(
                        f"Duplicate ID '{dict_id}' encountered. Each ID (from test_id, bro_id, or filename) must be unique across all input files."
                    )
                data[dict_id] = cpt_data
        else:
            # Single CPTData from .gef file
            dict_id = get_gef_id(file_result, filepath)
            if dict_id in data:
                raise ValueError(
                    f"Duplicate ID '{dict_id}' encountered. Each ID (from test_id, bro_id, or filename) must be unique across all input files."
                )
            data[dict_id] = file_result

    logger.info(f"Parsed {len(data)} CPT files from {len(filepaths)} input files.")
    return data


def get_gef_id(gef: CPTData, filepath: Path | str) -> str:
    """
    Get a unique identifier for a CPTData object from test_id, hole_id, bro_id, or filename.

    Args:
        gef (CPTData): The CPTData object to get the identifier for.
        filepath (Path | str): The file path of the GEF file being processed.

    Returns:
        str: The unique identifier for the CPTData object.
    """
    return gef.bro_id
    if hasattr(gef, "bro_id") and gef.bro_id:
        return gef.bro_id
    elif hasattr(gef, "test_id") and gef.test_id:
        return gef.test_id
    else:
        return filepath


def check_for_required_columns(cpt_data: CPTData, filepath: str) -> None:
    """Check that the CPTData object has the required columns.

    Required columns taken from https://bedrock.engineer/reference/formats/gef/gef-cpt/#column-quantities

    Args:
        cpt_data (CPTData): The CPTData object to check.
        filepath (str): The file path of the GEF file being processed.

    Raises:
        ValueError: If any required columns are missing.
    """
    required_columns = ["penetrationLength", "coneResistance"]
    if hasattr(cpt_data, "data"):
        missing = [col for col in required_columns if col not in cpt_data.data.columns]
        if missing:
            raise ValueError(f"File '{filepath}' is missing required columns: {missing}")

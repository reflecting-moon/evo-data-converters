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

import asyncio
import nest_asyncio

from evo_schemas import schema_lookup
from pandas import DataFrame
from python_ags4 import AGS4
from typing import TYPE_CHECKING, Optional

import evo.logging
from evo.data_converters.common.objects.downhole_collection_from_evo import create_downhole_collection_from_evo

# from evo.data_converters.common.objects.downhole_collection import (
#     DownholeCollection as IntermediaryDownholeCollection,
#     HoleCollars,
#     ColumnMapping,
#     MeasurementTableAdapter,
#     MeasurementTableFactory,
# )
from evo.data_converters.common.objects.downhole_collection import DownholeCollection as EvoDownholeCollection
from evo.data_converters.common.objects.downhole_collection.tables import DistanceTable
from evo.data_converters.common import (
    EvoObjectMetadata,
    EvoWorkspaceMetadata,
    create_evo_object_service_and_data_client,
)
from evo.objects.client import ObjectAPIClient
from evo.objects.data import ObjectSchema
from evo.objects.utils.data import ObjectDataClient

if TYPE_CHECKING:
    from evo.notebooks import ServiceManagerWidget


class AGSExporterException(Exception):
    pass


class UnsupportedObjectError(AGSExporterException):
    pass


logger = evo.logging.getLogger("data_converters")


def _downhole_to_ags_groups(dhc: EvoDownholeCollection) -> dict[DataFrame]:
    intermediary_object = create_downhole_collection_from_evo(dhc)
    print(intermediary_object)
    return {}

    # collars_df = dhc.collars.df

    for measurement in dhc.get_measurement_tables(filter=[DistanceTable]):
        pass


def _export_obj(
    obj_meta: EvoObjectMetadata,
    service_client: ObjectAPIClient,
    data_client: ObjectDataClient,
) -> DataFrame:
    evo_object = asyncio.run(service_client.download_object_by_id(obj_meta.object_id, obj_meta.version_id)).as_dict()
    object_class = schema_lookup.get(str(ObjectSchema.from_id(evo_object["schema"])))

    if not object_class:
        raise UnsupportedObjectError(f"Unknown Geoscience Object schema '{evo_object['schema']}'")

    evo_object = object_class.from_dict(evo_object)
    # intermediary_object = create_downhole_collection_from_evo(evo_object)

    match object_class:
        case EvoDownholeCollection():
            return _downhole_to_ags_groups(evo_object)
        case _:
            raise UnsupportedObjectError(f"Cannot export {object_class} to AGS")


def export_ags(
    filepath: str,
    objects: list[EvoObjectMetadata],
    evo_workspace_metadata: Optional[EvoWorkspaceMetadata] = None,
    service_manager_widget: Optional["ServiceManagerWidget"] = None,
) -> None:
    """
    Export a collection of Evo objects to an AGS file.

    :param filepath: Path of the AGS file to create.
    :param objects: List of EvoObjectMetadata objects containing the UUID and version of the Evo objects to export.
    :param omf_metadata: Optional project metadata to embed in the OMF file.
    :param evo_workspace_metadata: Optional Evo Workspace metadata.
    :param service_manager_widget: Optional ServiceManagerWidget for use in notebooks.

    One of evo_workspace_metadata or service_manager_widget is required.

    :raise UnsupportedObjectError: If the type of object is not supported.
    :raise MissingConnectionDetailsError: If no connections details could be derived.
    :raise ConflictingConnectionDetailsError: If both evo_workspace_metadata and service_manager_widget present.
    """
    service_client, data_client = create_evo_object_service_and_data_client(
        evo_workspace_metadata, service_manager_widget
    )

    nest_asyncio.apply()

    objs = [_export_obj(obj, service_client, data_client) for obj in objects]

    return AGS4.dataframe_to_AGS4(objs, {}, filepath)

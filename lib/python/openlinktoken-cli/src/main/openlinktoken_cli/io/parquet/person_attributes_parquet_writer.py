# SPDX-License-Identifier: MIT

import logging
from typing import Dict, Optional

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    raise ImportError("pyarrow is required for Parquet support. Install with: uv pip install pyarrow")

from openlinktoken_cli.io.path_utils import ensure_parent_directory
from openlinktoken_cli.io.person_attributes_writer import PersonAttributesWriter
from openlinktoken_cli.util.path_utils import ensure_parent_directory

logger = logging.getLogger(__name__)


class PersonAttributesParquetWriter(PersonAttributesWriter):
    """
    The PersonAttributeParquetWriter class is responsible for writing person
    attributes to a Parquet file.
    It implements the PersonAttributesWriter interface.
    """

    def __init__(self, file_path: str):
        """
        Initialize the class with the output file in Parquet format.

        Args:
            file_path: The output file path.

        Raises:
            IOError: If an I/O error occurs.
        """
        self.file_path = file_path

        # Create directory if it doesn't exist
        ensure_parent_directory(file_path)

        self.schema: Optional[pa.Schema] = None
        self.writer: Optional[pq.ParquetWriter] = None
        self.initialized = False

    def write_attributes(self, attributes: Dict[str, str]) -> None:
        """
        Write attributes to the Parquet file.

        Args:
            attributes: A map of person attributes.

        Raises:
            IOError: If an I/O error occurs.
        """
        if not self.initialized:
            self._initialize_writer(attributes)

        # Create a record batch from the attributes
        arrays = []
        field_names = []

        for field in self.schema:
            field_name = field.name
            field_names.append(field_name)
            value = attributes.get(field_name)
            if value is not None:
                arrays.append(pa.array([value]))
            else:
                arrays.append(pa.array([None], type=pa.string()))

        record_batch = pa.record_batch(arrays, names=field_names)
        self.writer.write_batch(record_batch)

    def close(self) -> None:
        """Close the Parquet writer."""
        if self.writer is not None:
            self.writer.close()

    def _initialize_writer(self, first_record: Dict[str, str]) -> None:
        """
        Initialize the Parquet writer with schema based on the first record.

        Args:
            first_record: The first record to determine schema.

        Raises:
            IOError: If an I/O error occurs.
        """
        # Create schema based on the first record
        fields = []
        for key, value in first_record.items():
            if value is not None:
                fields.append(pa.field(key, pa.string()))

        self.schema = pa.schema(fields)

        # Initialize the Parquet writer
        self.writer = pq.ParquetWriter(self.file_path, self.schema)
        self.initialized = True

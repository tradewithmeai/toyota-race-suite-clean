"""Dataset manager for handling multiple loaded sessions."""

import os
import json
from typing import Dict, List, Optional


class DatasetInfo:
    """Information about a loaded dataset."""

    def __init__(self, name: str, data_dir: str, metadata: dict):
        self.name = name
        self.data_dir = data_dir
        self.metadata = metadata
        self.car_ids = metadata.get('car_ids', [])
        self.total_duration_ms = metadata.get('total_duration_ms', 0)
        self.session_name = metadata.get('session_name', name)
        self.track_name = metadata.get('track_name', 'Unknown Track')

        # Extract session info from path if available
        if 'Session' in name:
            self.display_name = name
        else:
            self.display_name = f"Session - {name}"

    def get_duration_string(self) -> str:
        """Get formatted duration string."""
        total_seconds = self.total_duration_ms / 1000
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        return f"{minutes}:{seconds:02d}"

    def get_summary(self) -> str:
        """Get one-line summary of dataset."""
        return f"{self.display_name} | {len(self.car_ids)} cars | {self.get_duration_string()}"


class DatasetManager:
    """Manages multiple loaded datasets and switching between them."""

    def __init__(self):
        self.datasets: Dict[str, DatasetInfo] = {}  # dataset_id -> DatasetInfo
        self.active_dataset_id: Optional[str] = None
        self.next_dataset_id = 1

    def add_dataset(self, data_dir: str) -> tuple[str, DatasetInfo]:
        """Add a new dataset to the manager.

        Args:
            data_dir: Path to processed data directory

        Returns:
            Tuple of (dataset_id, DatasetInfo)
        """
        # Load metadata to get session info
        metadata_path = os.path.join(data_dir, 'metadata.json')
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        # Generate unique ID
        dataset_id = f"dataset_{self.next_dataset_id}"
        self.next_dataset_id += 1

        # Extract name from directory
        dir_name = os.path.basename(data_dir)

        # Create dataset info
        dataset_info = DatasetInfo(dir_name, data_dir, metadata)
        self.datasets[dataset_id] = dataset_info

        # Set as active if it's the first dataset
        if self.active_dataset_id is None:
            self.active_dataset_id = dataset_id

        print(f"Added dataset: {dataset_info.get_summary()}")

        return dataset_id, dataset_info

    def set_active_dataset(self, dataset_id: str) -> bool:
        """Set the active dataset.

        Args:
            dataset_id: ID of dataset to activate

        Returns:
            True if successful, False if dataset not found
        """
        if dataset_id not in self.datasets:
            return False

        self.active_dataset_id = dataset_id
        print(f"Switched to: {self.datasets[dataset_id].get_summary()}")
        return True

    def get_active_dataset(self) -> Optional[DatasetInfo]:
        """Get the currently active dataset."""
        if self.active_dataset_id is None:
            return None
        return self.datasets.get(self.active_dataset_id)

    def get_active_data_dir(self) -> Optional[str]:
        """Get the data directory of the active dataset."""
        dataset = self.get_active_dataset()
        return dataset.data_dir if dataset else None

    def remove_dataset(self, dataset_id: str) -> bool:
        """Remove a dataset from the manager.

        Args:
            dataset_id: ID of dataset to remove

        Returns:
            True if successful, False if dataset not found
        """
        if dataset_id not in self.datasets:
            return False

        # Don't allow removing the active dataset if it's the only one
        if dataset_id == self.active_dataset_id and len(self.datasets) == 1:
            return False

        # If removing active dataset, switch to another
        if dataset_id == self.active_dataset_id:
            remaining_ids = [did for did in self.datasets.keys() if did != dataset_id]
            if remaining_ids:
                self.active_dataset_id = remaining_ids[0]

        del self.datasets[dataset_id]
        return True

    def get_dataset_list(self) -> List[tuple[str, DatasetInfo]]:
        """Get list of all datasets as (id, info) tuples."""
        return [(did, info) for did, info in self.datasets.items()]

    def has_multiple_datasets(self) -> bool:
        """Check if multiple datasets are loaded."""
        return len(self.datasets) > 1

    def get_comparison_data(self) -> Dict:
        """Get comparison data across all loaded datasets.

        Returns:
            Dictionary with comparison metrics
        """
        if not self.datasets:
            return {}

        comparison = {
            'dataset_count': len(self.datasets),
            'datasets': []
        }

        for dataset_id, info in self.datasets.items():
            dataset_data = {
                'id': dataset_id,
                'name': info.display_name,
                'car_count': len(info.car_ids),
                'duration': info.get_duration_string(),
                'duration_ms': info.total_duration_ms,
                'track': info.track_name,
                'is_active': dataset_id == self.active_dataset_id
            }
            comparison['datasets'].append(dataset_data)

        return comparison

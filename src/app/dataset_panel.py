"""Dataset selection and comparison UI panel."""

import dearpygui.dearpygui as dpg
from app.dataset_manager import DatasetManager


class DatasetPanel:
    """UI panel for managing and switching between loaded datasets."""

    def __init__(self, dataset_manager: DatasetManager, on_dataset_change_callback=None):
        self.dataset_manager = dataset_manager
        self.on_dataset_change_callback = on_dataset_change_callback
        self.panel_tag = "dataset_panel"
        self.is_visible = False

    def setup_ui(self, parent=None):
        """Create the dataset panel UI."""
        with dpg.collapsing_header(label="DATASETS", default_open=True, parent=parent):
            # Active dataset display
            dpg.add_text("Active Session:", color=(200, 200, 200))
            dpg.add_text("No session loaded", tag="active_dataset_text", color=(150, 150, 150))
            dpg.add_spacer(height=10)

            # Dataset list
            with dpg.child_window(height=150, border=True, tag="dataset_list_window"):
                dpg.add_text("Loaded Sessions:", color=(200, 200, 200))
                dpg.add_separator()
                with dpg.group(tag="dataset_list_group"):
                    dpg.add_text("None", color=(100, 100, 100))

            dpg.add_spacer(height=10)

            # Action buttons
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Load Another",
                    callback=self._on_load_another_click,
                    width=140
                )
                dpg.add_button(
                    label="Remove",
                    callback=self._on_remove_click,
                    width=100,
                    enabled=False,
                    tag="remove_dataset_button"
                )

            dpg.add_spacer(height=10)

            # Comparison section (only visible with multiple datasets)
            with dpg.collapsing_header(label="Comparison", default_open=False, tag="comparison_header", show=False):
                with dpg.group(tag="comparison_content"):
                    dpg.add_text("No comparison data", color=(100, 100, 100))

    def update_dataset_list(self):
        """Update the dataset list display."""
        # Clear existing list
        if dpg.does_item_exist("dataset_list_group"):
            dpg.delete_item("dataset_list_group", children_only=True)

            with dpg.group(tag="dataset_list_group_inner", parent="dataset_list_group"):
                dataset_list = self.dataset_manager.get_dataset_list()

                if not dataset_list:
                    dpg.add_text("None", color=(100, 100, 100))
                else:
                    active_id = self.dataset_manager.active_dataset_id

                    for dataset_id, info in dataset_list:
                        is_active = (dataset_id == active_id)

                        # Create clickable item for each dataset
                        with dpg.group(horizontal=True):
                            # Radio button indicator
                            if is_active:
                                dpg.add_text("●", color=(100, 255, 100))
                            else:
                                dpg.add_text("○", color=(100, 100, 100))

                            # Dataset name (clickable)
                            text_color = (255, 255, 255) if is_active else (150, 150, 150)
                            dpg.add_text(
                                info.display_name,
                                color=text_color,
                                tag=f"dataset_text_{dataset_id}"
                            )

                            # Make clickable
                            with dpg.item_handler_registry() as handler:
                                dpg.add_item_clicked_handler(
                                    callback=lambda s, a, u: self._on_dataset_click(u),
                                    user_data=dataset_id
                                )
                            dpg.bind_item_handler_registry(f"dataset_text_{dataset_id}", handler)

                        # Dataset info (indented)
                        with dpg.group(horizontal=True):
                            dpg.add_text("  ", color=(0, 0, 0, 0))  # Indent
                            info_text = f"{len(info.car_ids)} cars | {info.get_duration_string()}"
                            dpg.add_text(info_text, color=(100, 100, 100))

                        dpg.add_spacer(height=5)

        # Update active dataset text
        active_dataset = self.dataset_manager.get_active_dataset()
        if active_dataset:
            dpg.set_value("active_dataset_text", active_dataset.display_name)
            dpg.configure_item("active_dataset_text", color=(100, 255, 100))
        else:
            dpg.set_value("active_dataset_text", "No session loaded")
            dpg.configure_item("active_dataset_text", color=(150, 150, 150))

        # Enable/disable remove button
        can_remove = len(dataset_list) > 1
        if dpg.does_item_exist("remove_dataset_button"):
            dpg.configure_item("remove_dataset_button", enabled=can_remove)

        # Update comparison section
        self._update_comparison()

    def _update_comparison(self):
        """Update the comparison data display."""
        has_multiple = self.dataset_manager.has_multiple_datasets()

        # Show/hide comparison header
        if dpg.does_item_exist("comparison_header"):
            dpg.configure_item("comparison_header", show=has_multiple)

        if not has_multiple:
            return

        # Get comparison data
        comparison = self.dataset_manager.get_comparison_data()

        # Update comparison content
        if dpg.does_item_exist("comparison_content"):
            dpg.delete_item("comparison_content", children_only=True)

            with dpg.group(parent="comparison_content"):
                dpg.add_text(f"Total Sessions: {comparison['dataset_count']}", color=(200, 200, 200))
                dpg.add_separator()
                dpg.add_spacer(height=5)

                # Table header
                with dpg.group(horizontal=True):
                    dpg.add_text("Session", color=(150, 150, 150))
                    dpg.add_spacer(width=100)
                    dpg.add_text("Cars", color=(150, 150, 150))
                    dpg.add_spacer(width=20)
                    dpg.add_text("Duration", color=(150, 150, 150))

                dpg.add_separator()

                # Dataset rows
                for dataset in comparison['datasets']:
                    text_color = (100, 255, 100) if dataset['is_active'] else (150, 150, 150)

                    with dpg.group(horizontal=True):
                        # Name (truncated if too long)
                        name = dataset['name']
                        if len(name) > 20:
                            name = name[:17] + "..."
                        dpg.add_text(name, color=text_color)

                        dpg.add_spacer(width=100 - len(name) * 6)
                        dpg.add_text(str(dataset['car_count']), color=text_color)
                        dpg.add_spacer(width=40)
                        dpg.add_text(dataset['duration'], color=text_color)

    def _on_dataset_click(self, dataset_id: str):
        """Handle dataset selection click."""
        if self.dataset_manager.set_active_dataset(dataset_id):
            self.update_dataset_list()

            # Notify callback to reload world model
            if self.on_dataset_change_callback:
                self.on_dataset_change_callback(dataset_id)

    def _on_load_another_click(self, sender, app_data):
        """Handle 'Load Another' button click."""
        # Open directory dialog for selecting processed data
        def dir_selected(sender, app_data):
            if app_data and 'file_path_name' in app_data:
                dir_path = app_data['file_path_name']
                # Verify it's a valid processed data directory
                import os
                metadata_path = os.path.join(dir_path, 'metadata.json')
                if os.path.exists(metadata_path):
                    # Add to dataset manager
                    dataset_id, dataset_info = self.dataset_manager.add_dataset(dir_path)
                    self.add_dataset_and_refresh(dataset_id)

                    # Notify callback to reload world model
                    if self.on_dataset_change_callback:
                        self.on_dataset_change_callback(dataset_id)
                else:
                    print(f"Invalid processed data folder: {dir_path}")
                    print("Missing metadata.json file")

        # Create directory dialog
        with dpg.file_dialog(label="Select Processed Data Folder",
                            callback=dir_selected,
                            width=700, height=400,
                            modal=True,
                            directory_selector=True,
                            show=True):
            pass

    def _on_remove_click(self, sender, app_data):
        """Handle 'Remove' button click."""
        active_id = self.dataset_manager.active_dataset_id
        if active_id and self.dataset_manager.has_multiple_datasets():
            # Show confirmation
            self._show_remove_confirmation(active_id)

    def _show_remove_confirmation(self, dataset_id: str):
        """Show confirmation dialog for removing dataset."""
        dataset_info = self.dataset_manager.datasets.get(dataset_id)
        if not dataset_info:
            return

        # Create modal popup
        with dpg.window(
            label="Confirm Remove",
            modal=True,
            show=True,
            tag="remove_confirm_popup",
            no_resize=True,
            pos=(400, 300),
            width=400,
            height=150
        ):
            dpg.add_text(f"Remove session: {dataset_info.display_name}?")
            dpg.add_text("This will unload the session from memory.", color=(150, 150, 150))
            dpg.add_spacer(height=20)

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Cancel",
                    callback=lambda: dpg.delete_item("remove_confirm_popup"),
                    width=180
                )
                dpg.add_button(
                    label="Remove",
                    callback=lambda: self._confirm_remove(dataset_id),
                    width=180
                )

    def _confirm_remove(self, dataset_id: str):
        """Confirm and execute dataset removal."""
        # Close popup
        if dpg.does_item_exist("remove_confirm_popup"):
            dpg.delete_item("remove_confirm_popup")

        # Remove dataset
        if self.dataset_manager.remove_dataset(dataset_id):
            self.update_dataset_list()

            # Notify callback to reload world model
            if self.on_dataset_change_callback:
                new_active_id = self.dataset_manager.active_dataset_id
                if new_active_id:
                    self.on_dataset_change_callback(new_active_id)

    def add_dataset_and_refresh(self, dataset_id: str):
        """Called when a new dataset is added externally."""
        self.update_dataset_list()

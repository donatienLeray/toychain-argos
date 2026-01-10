from pathlib import Path
from typing import List, Dict, Optional

try:
    import ipywidgets as widgets
except Exception as e:
    raise ImportError(
        "ipywidgets is required for the interactive experiment picker. Install it with: pip install ipywidgets"
    )

from IPython.display import display


class ExperimentPicker:
    """Interactive experiment picker for experiments in a data folder.

    - Lists experiments (subdirectories of data_dir).
    - If an experiment contains configuration subfolders (for example
      `data/exp/<cfg>/001`), it will be treated as a multi-config experiment
      and the picker will list the `<cfg>` names (with an "all" option).
    - If the experiment contains `001` directly under `data/exp/001`, it will
      be treated as a single-run experiment and no cfg picker will be shown.
    - Shows a "Load experiments" button once at least one experiment is selected.
    - When clicked, saves results to `self.last_loaded` and prints them.
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data folder not found: {self.data_dir}")

        self.experiments = sorted(self._find_experiments())
        # per-experiment cfg checkboxes: exp -> (cfg_name -> Checkbox)
        self._cfg_checkboxes: Dict[str, Dict[str, widgets.Checkbox]] = {}
        # per-experiment select-all checkbox
        self._cfg_select_all: Dict[str, widgets.Checkbox] = {}
        self.last_loaded: Optional[List[Dict]] = None

        # Widgets — show experiments as individual checkboxes with an indented placeholder for cfgs
        self._exp_checkboxes: Dict[str, widgets.Checkbox] = {}
        self._exp_placeholders: Dict[str, widgets.VBox] = {}
        checkbox_items = []
        for exp in self.experiments:
            # Use a narrow checkbox and a separate HTML label so the name can wrap and avoid being truncated with ellipsis
            cb = widgets.Checkbox(value=False, description='', indent=False, layout=widgets.Layout(width='28px'))
            label = widgets.HTML(value=f"<div style='white-space:normal; word-break:break-word;' title='{exp}'>{exp}</div>", layout=widgets.Layout(width='100%'))
            # call _on_experiment_change whenever a checkbox toggles
            cb.observe(self._on_experiment_change, names='value')
            self._exp_checkboxes[exp] = cb
            # placeholder for cfg widgets, indented
            placeholder = widgets.VBox([], layout=widgets.Layout(margin='0 0 0 20px'))
            self._exp_placeholders[exp] = placeholder
            header = widgets.HBox([cb, label], layout=widgets.Layout(align_items='center'))
            item = widgets.VBox([header, placeholder])
            checkbox_items.append(item)
        # container for experiments, allow scrolling if many experiments
        # increased width to accommodate long experiment names
        self.experiments_container = widgets.VBox(checkbox_items, layout=widgets.Layout(width="80%", max_height="auto", overflow="auto"))

        self.load_button = widgets.Button(
            description="Choose experiment(s)",
            button_style="primary",
            disabled=True,
        )
        self.output = widgets.Output()

        # Events
        self.load_button.on_click(self._on_load_clicked)

        # Top-level UI
        self.ui = widgets.VBox([
            widgets.Label(f"Data folder: {self.data_dir}"),
            self.experiments_container,
            self.load_button,
            self.output,
        ])

    def _find_experiments(self) -> List[str]:
        # Return names of directories directly under data_dir
        return [p.name for p in self.data_dir.iterdir() if p.is_dir() and not p.name.startswith('.')]

    def _experiment_has_cfgs(self, exp_name: str) -> bool:
        """Return True if the experiment contains cfg subfolders that themselves
        contain a '001' run folder (e.g., data/exp/<cfg>/001)."""
        exp_path = self.data_dir / exp_name
        for p in exp_path.iterdir():
            if p.is_dir() and (p / "001").exists():
                return True
        return False

    def _list_cfgs_for_experiment(self, exp_name: str) -> List[str]:
        # List subdirectories that contain a '001' run folder (these are the cfgs)
        exp_path = self.data_dir / exp_name
        cfgs = [p.name for p in sorted(exp_path.iterdir()) if p.is_dir() and (p / "001").exists()]
        return cfgs

    def _on_experiment_change(self, change=None):
        # Determine selected experiments based on checkboxes
        selected = [name for name, cb in self._exp_checkboxes.items() if getattr(cb, 'value', False)]
        # Enable/disable load button
        self.load_button.disabled = len(selected) == 0

        # Populate per-experiment placeholders with cfg pickers when selected
        # Keep stored cfg checkbox state across re-renders so selections aren't lost when switching experiments
        # clear only the UI placeholders (but keep self._cfg_checkboxes/_cfg_select_all)
        for ph in self._exp_placeholders.values():
            ph.children = []

        for exp in selected:
            placeholder = self._exp_placeholders.get(exp)
            if self._experiment_has_cfgs(exp):
                cfgs = self._list_cfgs_for_experiment(exp)
                if cfgs:
                    # Reuse existing widgets if they exist and cfg list hasn't changed
                    cfg_map = self._cfg_checkboxes.get(exp)
                    select_all = self._cfg_select_all.get(exp)
                    if cfg_map is None or set(cfgs) != set(cfg_map.keys()):
                        # Build a 'select all' checkbox (default: checked) and individual cfg checkboxes (default: checked)
                        select_all = widgets.Checkbox(value=True, description="select all configs", indent=False, layout=widgets.Layout(margin='2px 0', padding='0'))
                        cfg_boxes = []
                        cfg_map = {}
                        for cfg in cfgs:
                            cb = widgets.Checkbox(value=True, description=cfg, indent=False, layout=widgets.Layout(margin='2px 0', padding='0'))
                            cfg_map[cfg] = cb
                            cfg_boxes.append(cb)

                        # helper to toggle all cfg checkboxes when select_all is changed
                        def _make_select_all_handler(map_cfgs):
                            def _handler(change):
                                val = change.get('new', False)
                                for c in map_cfgs.values():
                                    c.value = val
                            return _handler

                        select_all.observe(_make_select_all_handler(cfg_map), names='value')

                        # helper to keep select_all in sync when individual boxes change
                        def _make_individual_handler(select_cb, map_cfgs):
                            def _handler(change):
                                all_on = all(c.value for c in map_cfgs.values())
                                if select_cb.value != all_on:
                                    select_cb.value = all_on
                            return _handler

                        for c in cfg_map.values():
                            c.observe(_make_individual_handler(select_all, cfg_map), names='value')

                        # ensure defaults are all selected
                        select_all.value = True
                        for c in cfg_map.values():
                            c.value = True

                        self._cfg_checkboxes[exp] = cfg_map
                        self._cfg_select_all[exp] = select_all

                    # Create a vertical box: select_all on top, then cfg checkboxes, indented
                    # Limit the cfg list height (show ~4 items) and make it scrollable; add a border/padding
                    cfg_list_box = widgets.VBox(list(cfg_map.values()), layout=widgets.Layout(max_height='10em', overflow='auto', border='1px solid #ddd', padding='4px'))
                    # Slightly increase cfg group width so long names don't wrap
                    group = widgets.VBox([select_all, cfg_list_box], layout=widgets.Layout(width="85%", margin='0 0 0 20px'))
                    placeholder.children = [group]
                else:
                    placeholder.children = [widgets.HTML(value=f"<b>{exp}</b>: no run configs found")]
            else:
                # either runs are directly under data/exp/ (e.g., data/exp/001) or no configs exist
                # No message needed when runs are directly under the experiment; leave placeholder empty
                placeholder.children = []

    def _on_load_clicked(self, _):
        # Determine selected experiments based on checkboxes
        selected_exps = [name for name, cb in self._exp_checkboxes.items() if getattr(cb, 'value', False)]
        result = []
        for exp in selected_exps:
            exp_path = self.data_dir / exp
            if not self._experiment_has_cfgs(exp):
                # single-run experiment: store the experiment dir itself
                result.append({
                    "experiment": exp,
                    "paths": [str(exp_path)],
                })
            else:
                cfgs = []
                cfg_map = self._cfg_checkboxes.get(exp)
                select_all_cb = self._cfg_select_all.get(exp)
                if cfg_map is None:
                    # no cfg widget (no configs found) -> store empty paths
                    cfgs = []
                else:
                    # If select_all is set or no individual boxes selected, treat as all
                    if select_all_cb and select_all_cb.value:
                        cfgs = self._list_cfgs_for_experiment(exp)
                    else:
                        chosen = [name for name, cb in cfg_map.items() if getattr(cb, 'value', False)]
                        if not chosen:
                            # default to all if none selected
                            cfgs = self._list_cfgs_for_experiment(exp)
                        else:
                            cfgs = chosen

                paths = [str(exp_path / c) for c in cfgs]
                result.append({
                    "experiment": exp,
                    "paths": paths,
                })

        # Save and print (print only a short summary)
        self.last_loaded = result
        # Count resulting paths (not experiments) for reporting
        num_paths = sum(len(entry.get("paths", [])) for entry in result)
        # Use the output widget if available, otherwise fall back to printing
        try:
            # Build the user-facing message
            if num_paths == 0:
                msg = "0 experiment has been loaded"
            elif num_paths == 1:
                msg = "1 experiment has been loaded"
            else:
                msg = f"{num_paths} experiments have been loaded"

            # Prepare the 'see details' button and details output (only if we have paths)
            see_btn = None
            details_out = None
            if num_paths:
                see_btn = widgets.Button(description="see details", layout=widgets.Layout(width="auto", padding="0", margin="0"), button_style="")
                try:
                    see_btn.style.button_color = "transparent"
                except Exception:
                    pass
                details_out = widgets.Output()
                details_out.layout.display = 'none'
                details_out.layout.margin = '0 0 0 0'

                def _fill_details():
                    if not self.last_loaded:
                        print("last_loaded: None or empty")
                    else:
                        for entry in self.last_loaded:
                            exp = entry.get("experiment")
                            paths = entry.get("paths", [])
                            if not paths:
                                print(f"{exp}: (no paths)")
                            else:
                                for p in paths:
                                    print(p)

                def _toggle_details(_):
                    if getattr(details_out.layout, 'display', '') == 'none':
                        details_out.clear_output()
                        with details_out:
                            _fill_details()
                        details_out.layout.display = 'block'
                        see_btn.description = 'hide details'
                    else:
                        details_out.clear_output()
                        details_out.layout.display = 'none'
                        see_btn.description = 'see details'

                see_btn.on_click(_toggle_details)

            # Emit the message and widget(s) depending on Output capabilities
            if hasattr(self.output, 'clear_output') and hasattr(self.output, '__enter__'):
                with self.output:
                    self.output.clear_output()
                    print(msg)
                    if see_btn:
                        display(see_btn, details_out)
            elif hasattr(self.output, 'clear_output'):
                self.output.clear_output()
                print(msg)
                if see_btn:
                    display(see_btn, details_out)
            else:
                print(msg)
                if see_btn:
                    # Fallback behavior: button prints to stdout
                    def _fallback_show(_):
                        _fill_details()
                    see_btn.on_click(_fallback_show)
                    display(see_btn)
        except Exception:
            if num_paths == 0:
                msg = "0 experiment has been loaded"
            elif num_paths == 1:
                msg = "1 experiment has been loaded"
            else:
                msg = f"{num_paths} experiments have been loaded"
            print(msg)

    def show(self):
        # Sanitize any existing placeholder children that are not ipywidgets (can happen if
        # earlier versions inserted IPython.display.HTML into children). Replace non-widget
        # children with widgets.HTML wrappers so the widget tree remains valid.
        try:
            for ph in self._exp_placeholders.values():
                new_children = []
                for c in getattr(ph, 'children', []) or []:
                    # If it's already an ipywidget, keep it, else wrap it into a widgets.HTML
                    if isinstance(c, widgets.Widget):
                        new_children.append(c)
                    else:
                        try:
                            new_children.append(widgets.HTML(value=str(c)))
                        except Exception:
                            new_children.append(widgets.HTML(value=repr(c)))
                ph.children = new_children
        except Exception:
            # If sanitization fails for any reason, ignore and proceed to display
            pass
        display(self.ui)


# Convenience function for notebook
def create_and_show_picker(data_dir: str | Path = "data") -> ExperimentPicker:
    picker = ExperimentPicker(data_dir)
    picker.show()
    return picker

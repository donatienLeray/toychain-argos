from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set, Callable
import os
import math

try:
    import ipywidgets as widgets
except Exception as e:
    raise ImportError(
        "ipywidgets is required for the interactive experiment picker. Install it with: pip install ipywidgets"
    )

from IPython.display import display
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import ticker


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
    - Supports both single experiment (radio button, auto all cfgs) and multiple experiment modes.
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data folder not found: {self.data_dir}")

        self.experiments = sorted(self._find_experiments())
        # Mode toggle
        self.mode_toggle = widgets.ToggleButtons(
            options=['Single Experiment', 'Multiple Experiments'],
            value='Single Experiment',
            description='Mode:',
            button_style=''
        )
        
        # Single experiment mode: radio button picker
        self._exp_radio = widgets.RadioButtons(
            options=self.experiments,
            value=self.experiments[0] if self.experiments else None,
            description='Experiment:',
            disabled=False,
        )
        self._single_exp_container = widgets.VBox([self._exp_radio])
        
        # Multiple experiment mode: checkbox picker (original behavior)
        # per-experiment cfg checkboxes: exp -> (cfg_name -> Checkbox)
        self._cfg_checkboxes: Dict[str, Dict[str, widgets.Checkbox]] = {}
        # per-experiment select-all checkbox
        self._cfg_select_all: Dict[str, widgets.Checkbox] = {}
        
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
        self._multi_exp_container = widgets.VBox(checkbox_items, layout=widgets.Layout(width="80%", max_height="auto", overflow="auto"))

        self.load_button = widgets.Button(
            description="Choose experiment(s)",
            button_style="primary",
            disabled=False,
        )
        self.output = widgets.Output()

        # Events
        self.load_button.on_click(self._on_load_clicked)
        self.mode_toggle.observe(self._on_mode_changed, names='value')

        # Top-level UI
        self.ui = widgets.VBox([
            widgets.Label(f"Data folder: {self.data_dir}"),
            self.mode_toggle,
            self._single_exp_container,
            self.load_button,
            self.output,
        ])
        
        self.last_loaded: Optional[List[Dict]] = None

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

    def _on_mode_changed(self, change=None):
        """Handle switching between single and multiple experiment modes."""
        if self.mode_toggle.value == 'Single Experiment':
            # Show single experiment picker, hide multiple
            self._single_exp_container.children = [self._exp_radio]
            # Update UI
            self.ui.children = [
                self.ui.children[0],  # Data folder label
                self.mode_toggle,
                self._single_exp_container,
                self.load_button,
                self.output,
            ]
        else:
            # Show multiple experiment picker
            self._multi_exp_container.children = [
                widgets.VBox([
                    widgets.HBox([
                        widgets.Checkbox(value=False, description='', indent=False, layout=widgets.Layout(width='28px')),
                        widgets.HTML(value=f"<div style='white-space:normal; word-break:break-word;' title='{exp}'>{exp}</div>", layout=widgets.Layout(width='100%'))
                    ], layout=widgets.Layout(align_items='center')),
                    self._exp_placeholders[exp]
                ]) for exp in self.experiments
            ]
            # Recreate checkbox list
            checkbox_items = []
            for exp in self.experiments:
                header = widgets.HBox([self._exp_checkboxes[exp], widgets.HTML(value=f"<div style='white-space:normal; word-break:break-word;' title='{exp}'>{exp}</div>", layout=widgets.Layout(width='100%'))], layout=widgets.Layout(align_items='center'))
                item = widgets.VBox([header, self._exp_placeholders[exp]])
                checkbox_items.append(item)
            self._multi_exp_container.children = checkbox_items
            
            # Update UI
            self.ui.children = [
                self.ui.children[0],  # Data folder label
                self.mode_toggle,
                self._multi_exp_container,
                self.load_button,
                self.output,
            ]

    def _on_load_clicked(self, _):
        result = []
        
        if self.mode_toggle.value == 'Single Experiment':
            # Single experiment mode: automatically select all configs
            exp = self._exp_radio.value
            exp_path = self.data_dir / exp
            
            if not self._experiment_has_cfgs(exp):
                # No configs, just use the experiment directory
                result.append({
                    "experiment": exp,
                    "paths": [str(exp_path)],
                })
            else:
                # Has configs, get all of them
                cfgs = self._list_cfgs_for_experiment(exp)
                paths = [str(exp_path / c) for c in cfgs]
                result.append({
                    "experiment": exp,
                    "paths": paths,
                })
        else:
            # Multiple experiment mode: use checked experiments and their selected configs
            selected_exps = [name for name, cb in self._exp_checkboxes.items() if getattr(cb, 'value', False)]
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


# Helper functions for common patterns

def _parse_config_names(exp_choices: List[str]) -> Tuple[bool, bool, Optional[widgets.Dropdown], Optional[widgets.Dropdown], Optional[Dict], Optional[Dict]]:
    """Parse experiment choices to determine if they follow consensus_number pattern.
    
    Returns:
        Tuple of (single_exp_mode, split_config_mode, consensus_drop, agents_drop, config_to_exp_or_name_to_exp, description)
    """
    single_exp_mode = False
    split_config_mode = False
    consensus_drop = None
    agents_drop = None
    config_mapping = None
    description = 'Experiment:'
    
    if len(exp_choices) == 0:
        return single_exp_mode, split_config_mode, consensus_drop, agents_drop, {}, description
    
    if all('/' in e for e in exp_choices):
        prefixes = [e.split('/')[0] for e in exp_choices]
        if len(set(prefixes)) == 1:
            single_exp_mode = True
            description = 'Config:'
            config_names = [e.split('/')[-1] for e in exp_choices]
            
            # Check if configs follow "consensus_number" pattern
            if all('_' in cfg and cfg.split('_')[-1].isdigit() for cfg in config_names):
                split_config_mode = True
                # Extract consensus types and agent numbers
                consensus_types = sorted(set('_'.join(cfg.split('_')[:-1]) for cfg in config_names))
                agent_numbers = sorted(set(cfg.split('_')[-1] for cfg in config_names), key=int)
                
                consensus_drop = widgets.Dropdown(options=consensus_types, description='Consensus:')
                agents_drop = widgets.Dropdown(options=agent_numbers, description='# Agents:')
                
                # Create mapping from (consensus, agents) to exp key
                config_mapping = {}
                for exp in exp_choices:
                    cfg = exp.split('/')[-1]
                    consensus = '_'.join(cfg.split('_')[:-1])
                    agents = cfg.split('_')[-1]
                    config_mapping[(consensus, agents)] = exp
                
                return single_exp_mode, split_config_mode, consensus_drop, agents_drop, config_mapping, description
    
    # Original single dropdown mode
    display_names = exp_choices
    if single_exp_mode:
        display_names = [e.split('/', 1)[1] for e in exp_choices]
    
    config_mapping = dict(zip(display_names, exp_choices))
    return single_exp_mode, split_config_mode, None, None, config_mapping, description


def _get_current_experiment(split_config_mode: bool, consensus_drop: Optional[widgets.Dropdown], 
                            agents_drop: Optional[widgets.Dropdown], 
                            exp_drop: Optional[widgets.Dropdown],
                            config_to_exp: Dict, name_to_exp: Dict) -> str:
    """Get the currently selected experiment based on mode."""
    if split_config_mode:
        return config_to_exp[(consensus_drop.value, agents_drop.value)]
    else:
        return name_to_exp[exp_drop.value]


def _update_rep_robot_options(loaded_data: Dict, exp: str, rep_drop: widgets.Dropdown, robot_drop: widgets.Dropdown):
    """Update rep and robot dropdown options for the selected experiment."""
    reps = sorted(loaded_data.get(exp, {}).keys())
    rep_drop.options = ['All'] + reps
    robots = sorted({r for rep in reps for r in loaded_data[exp][rep].keys()})
    robot_drop.options = ['All'] + [str(r) for r in robots]


def _update_rep_robot_col_options(loaded_data: Dict, exp: str, rep_drop: widgets.Dropdown, 
                                   robot_drop: widgets.Dropdown, col_drop: widgets.Dropdown):
    """Update rep, robot, and column dropdown options for the selected experiment."""
    _update_rep_robot_options(loaded_data, exp, rep_drop, robot_drop)
    
    # Get all available columns from all robots of this experiment
    all_cols = set()
    for rep in loaded_data.get(exp, {}).values():
        for df in rep.values():
            if isinstance(df, pd.DataFrame):
                all_cols.update(df.columns)
    
    col_options = ['All'] + sorted(list(all_cols))
    col_drop.options = col_options
    col_drop.value = 'All'


def _extract_config_info(exp_key: str) -> Tuple[str, int]:
    """Extract consensus type and number of agents from experiment key.
    
    Expected format: 'consensus_number' or 'experiment/consensus_number'
    Returns: (consensus_type, num_agents)
    """
    if '/' in exp_key:
        config_name = exp_key.split('/')[-1]
    else:
        config_name = exp_key
    
    if '_' not in config_name or not config_name.split('_')[-1].isdigit():
        return None, None
    
    consensus = '_'.join(config_name.split('_')[:-1])
    num_agents = int(config_name.split('_')[-1])
    return consensus, num_agents


# Data loading and preview functions

def create_csv_picker_for_loaded_paths(picker, data_dir=None):
    """For each path in `picker.last_loaded` (each either `data/exp` or `data/exp/cfg`),
    find the first folder named '1' (recursively) and list CSV files found there. Show a
    single RadioButtons widget per *experiment* (top-level directory under `data/`) for
    choosing which CSV to load for that experiment.

    The returned loader builds `loaded_data` accessible in the notebook as a nested dict:
      loaded_data[experiment_key][run_name][robot_int] -> pandas.DataFrame

    `experiment_key` is usually the top-level experiment name under `data` (e.g., 'ProofOfWork').
    If a loaded experiment has multiple configuration subfolders (e.g., `ProofOfWork/cfg1`),
    the loader will store runs under keys like `ProofOfWork/cfg1` while the UI still shows
    only one radio button per top-level experiment. This means the radio selection applies
    to all configs of that experiment.
    """
    if data_dir is None:
        data_dir = getattr(picker, 'data_dir', Path('data'))
    data_dir = Path(data_dir)

    if not getattr(picker, 'last_loaded', None):
        print("No experiments loaded — run the picker and click Load experiment first")
        return lambda: {}

    # Group paths by top-level experiment name (first component relative to data_dir)
    exp_map = {}  # experiment_key -> {'base_paths': dict(base_path_key->Path), 'probe_dirs': set()}

    for entry in picker.last_loaded:
        for pstr in entry.get('paths', []):
            base_path = Path(pstr)
            # Determine experiment key as the first part relative to data_dir when possible
            try:
                rel = base_path.relative_to(data_dir)
                exp_key = str(rel.parts[0])
                # If base_path includes a second part, treat it as a specific config: exp/cfg
                if len(rel.parts) >= 2:
                    base_path_key = f"{rel.parts[0]}/{rel.parts[1]}"
                else:
                    base_path_key = exp_key
            except Exception:
                # Fallback: use the parent folder name if it seems to represent the experiment
                if base_path.parent and base_path.parent != base_path:
                    exp_key = base_path.parent.name
                    base_path_key = f"{exp_key}/{base_path.name}" if base_path.name != exp_key else exp_key
                else:
                    exp_key = base_path.name
                    base_path_key = exp_key

            info = exp_map.setdefault(exp_key, {'base_paths': {}, 'probe_dirs': set()})
            # store base_path keyed by either "exp" or "exp/cfg" so we can later group runs per config
            info['base_paths'][base_path_key] = base_path

            # Find the first folder named '1' under this base_path (used to probe CSVs)
            probe_dir = None
            for root, dirs, files in os.walk(base_path):
                if '1' in dirs:
                    probe_dir = Path(root) / '1'
                    break

            if probe_dir and probe_dir.exists():
                info['probe_dirs'].add(probe_dir)

    radio_map = {}  # exp_key -> (RadioButtons, base_paths_dict, probe_dirs_list)
    widgets_list = []

    for exp_key, info in sorted(exp_map.items()):
        probe_dirs = info['probe_dirs']
        base_paths_dict = info['base_paths']

        if not probe_dirs:
            widgets_list.append(widgets.HTML(f"<b>{exp_key}</b>: no '1' folder found to probe CSVs"))
            continue

        # Collect all csv stems across probe dirs for this experiment
        csv_stems = set()
        for probe_dir in probe_dirs:
            for f in probe_dir.iterdir():
                if f.suffix.lower() == '.csv':
                    csv_stems.add(f.stem)

        if not csv_stems:
            widgets_list.append(widgets.HTML(f"<b>{exp_key}</b>: no CSV files found in {list(probe_dirs)[0]}"))
            continue

        options = sorted(csv_stems)
        rb = widgets.RadioButtons(options=options, description='', layout=widgets.Layout(width='auto'))
        rb.value = options[0]
        radio_map[exp_key] = (rb, base_paths_dict, sorted(probe_dirs))
        widgets_list.append(widgets.HBox([widgets.Label(f"{exp_key}:", layout=widgets.Layout(width='28%')), rb]))

    # Add heading before the CSV picker
    heading = widgets.HTML(value="<h4>Choose which CSV data to load</h4>")
    container = widgets.VBox([heading] + widgets_list)
    display(container)

    out = widgets.Output()
    # Initially show "no data loaded"
    with out:
        print("No data loaded")

    def _load_data(_):
        out.clear_output()
        with out:
            print("Loading data...")
        
        try:
            loaded = {}
            block_production_counts = {}
            # Record the chosen csv basename per experiment so other helpers can know which was chosen
            selected_csv_map = {}

            for exp_key, (rb, base_paths_dict, probe_dirs) in radio_map.items():
                sel = rb.value
                if not sel:
                    continue

                selected_csv_map[exp_key] = sel

                # Collect runs across all base paths belonging to this experiment. Each base_path
                # may be either the experiment root (key==exp_key) or a specific config (key=="exp/cfg").
                runs_info = []  # list of (base_path_key, run_path)
                for base_path_key, base_path in base_paths_dict.items():
                    runs = [d for d in base_path.iterdir() if d.is_dir() and d.name.isdigit()]
                    for r in runs:
                        runs_info.append((base_path_key, r))

                # Deduplicate runs by full path and sort by name
                unique_runs = sorted({r for _, r in runs_info}, key=lambda p: p.name)
                if not unique_runs:
                    continue

                # Build an index from run Path -> base_path_key(s) so we can store runs under the appropriate
                # experiment/config key. A run may appear under multiple base_paths (unlikely) but we map to all.
                run_to_keys = {}
                for base_path_key, run in runs_info:
                    run_to_keys.setdefault(run, set()).add(base_path_key)

                for run, keys in sorted(run_to_keys.items(), key=lambda kv: kv[0].name):
                    for base_key in sorted(keys):
                        run_dict = loaded.setdefault(base_key, {}).setdefault(run.name, {})
                        count_dict = block_production_counts.setdefault(base_key, {}).setdefault(run.name, {})
                        # robot dirs inside run — numeric names starting at 1; exclude '0'
                        robots = sorted([d for d in run.iterdir() if d.is_dir() and d.name.isdigit() and int(d.name) != 0], key=lambda p: int(p.name))
                        if not robots:
                            continue

                        for robot in robots:
                            robot_key = int(robot.name)
                            csv_path = robot / (sel + '.csv')
                            if csv_path.exists():
                                # CSV files are space-separated, not comma-separated
                                df = pd.read_csv(csv_path, sep=r'\s+')
                                
                                # Fix common column name typos
                                if 'TELEAPSED' in df.columns:
                                    df.rename(columns={'TELEAPSED': 'TELAPSED'}, inplace=True)
                                
                                # Store the DataFrame directly (no csv_basename key level)
                                run_dict[robot_key] = df
                            
                            # Load block production count from monitor.log
                            log_path = robot / 'monitor.log'
                            if log_path.exists():
                                try:
                                    with open(log_path, 'r') as f:
                                        count = sum(1 for line in f if 'Block produced' in line)
                                    count_dict[robot_key] = count
                                except Exception:
                                    count_dict[robot_key] = 0
                            else:
                                count_dict[robot_key] = 0

            # Save global variables
            globals()['loaded_data'] = loaded
            globals()['block_production_counts'] = block_production_counts
            globals()['selected_csv_map'] = selected_csv_map
            
            out.clear_output()
            with out:
                if loaded:
                    total_robots = sum(len(robots) for exp_data in loaded.values() for robots in exp_data.values())
                    total_blocks = sum(count for exp_data in block_production_counts.values() for robots in exp_data.values() for count in robots.values())
                    print(f"✓ Data loaded successfully!")
                    print(f"  - {total_robots} robot datasets")
                    print(f"  - {total_blocks:,} total blocks produced")
                else:
                    print("❌ Error: No data was loaded. Please check your experiment selection and try again.")
        
        except Exception as e:
            out.clear_output()
            with out:
                print(f"❌ Error loading data: {str(e)}")
                print("Please check your experiment selection and try again.")

    btn = widgets.Button(description='Load data')
    btn.on_click(_load_data)
    display(btn, out)

    def get_selections():
        # Return a representative csv path per experiment (first probe_dir is used)
        return {exp_key: str(sorted(probe_dirs)[0] / (rb.value + '.csv')) if rb.value and probe_dirs else None for exp_key, (rb, _, probe_dirs) in radio_map.items()}

    return get_selections


def create_data_picker_with_callback(button_text, callback_func, button_style='primary'):
    """Create a reusable data picker with customizable button and callback.
    
    Args:
        button_text: Text to display on the button
        callback_func: Function to call when button is clicked. 
                      Receives (exp, rep_sel, robot_sel, loaded_data, preview_out)
        button_style: Style of the button ('primary', 'success', 'info', etc.)
    """
    if 'loaded_data' not in globals() or not globals().get('loaded_data'):
        print("No `loaded_data` available. Use the picker and click Load data first.")
        return

    loaded_data = globals().get('loaded_data', {})
    exp_choices = sorted(loaded_data.keys())
    
    # Parse config names using helper function
    single_exp_mode, split_config_mode, consensus_drop, agents_drop, config_mapping, description = _parse_config_names(exp_choices)
    
    if not split_config_mode:
        exp_drop = widgets.Dropdown(options=list(config_mapping.keys()), description=description)
        name_to_exp = config_mapping
        config_to_exp = {}
    else:
        exp_drop = None
        config_to_exp = config_mapping
        name_to_exp = {}
    
    rep_drop = widgets.Dropdown(options=['All'], description='Rep:', value='All')
    robot_drop = widgets.Dropdown(options=['All'], description='Robot:', value='All')
    preview_out = widgets.Output()

    def _update_rep_robot(*_):
        exp = _get_current_experiment(split_config_mode, consensus_drop, agents_drop, exp_drop, config_to_exp, name_to_exp)
        _update_rep_robot_options(loaded_data, exp, rep_drop, robot_drop)

    def _on_button_click(_):
        exp = _get_current_experiment(split_config_mode, consensus_drop, agents_drop, exp_drop, config_to_exp, name_to_exp)
        rep_sel = rep_drop.value
        robot_sel = robot_drop.value
        callback_func(exp, rep_sel, robot_sel, loaded_data, preview_out)

    btn = widgets.Button(description=button_text, button_style=button_style)
    btn.on_click(_on_button_click)
    
    if split_config_mode:
        consensus_drop.observe(lambda *_: _update_rep_robot(), names='value')
        agents_drop.observe(lambda *_: _update_rep_robot(), names='value')
        _update_rep_robot()
        display(widgets.VBox([widgets.HBox([consensus_drop, agents_drop, rep_drop, robot_drop, btn]), preview_out]))
    else:
        exp_drop.observe(lambda *_: _update_rep_robot(), names='value')
        _update_rep_robot()
        display(widgets.VBox([widgets.HBox([exp_drop, rep_drop, robot_drop, btn]), preview_out]))


def show_loaded_preview():
    """Display a preview of loaded data with experiment, rep, and robot filters, and column selection."""
    if 'loaded_data' not in globals() or not globals().get('loaded_data'):
        print("No `loaded_data` available. Use the picker and click Load data first.")
        return

    loaded_data = globals().get('loaded_data', {})
    exp_choices = sorted(loaded_data.keys())

    # Parse config names using helper function
    single_exp_mode, split_config_mode, consensus_drop, agents_drop, config_mapping, description = _parse_config_names(exp_choices)
    
    if not split_config_mode:
        exp_drop = widgets.Dropdown(options=list(config_mapping.keys()), description=description)
        name_to_exp = config_mapping
        config_to_exp = {}
    else:
        exp_drop = None
        config_to_exp = config_mapping
        name_to_exp = {}
    
    rep_drop = widgets.Dropdown(options=['All'], description='Rep:', value='All')
    robot_drop = widgets.Dropdown(options=['All'], description='Robot:', value='All')
    col_drop = widgets.Dropdown(options=['All'], description='Columns:', value='All')
    preview_out = widgets.Output()

    def _update_rep_robot_cols(*_):
        exp = _get_current_experiment(split_config_mode, consensus_drop, agents_drop, exp_drop, config_to_exp, name_to_exp)
        _update_rep_robot_col_options(loaded_data, exp, rep_drop, robot_drop, col_drop)

    def _preview(_):
        with preview_out:
            preview_out.clear_output()
            exp = _get_current_experiment(split_config_mode, consensus_drop, agents_drop, exp_drop, config_to_exp, name_to_exp)
            rep_sel = rep_drop.value
            robot_sel = robot_drop.value
            col_sel = col_drop.value
            
            dfs = []
            details = []
            for rep, robots in loaded_data.get(exp, {}).items():
                if rep_sel != 'All' and rep != rep_sel:
                    continue
                for robot, df in robots.items():
                    if robot_sel != 'All' and str(robot) != robot_sel:
                        continue
                    if isinstance(df, pd.DataFrame):
                        df2 = df.copy()
                        df2['EXP'] = exp
                        df2['REP'] = rep
                        df2['ROBOT'] = robot
                        dfs.append(df2)
                        details.append((rep, robot, len(df2)))

            if not dfs:
                print(f'No files found for {exp} with selected filters')
                return

            combined = pd.concat(dfs, ignore_index=True)
            
            # Filter columns if specific column is selected
            if col_sel != 'All':
                cols_to_show = [col_sel, 'EXP', 'REP', 'ROBOT']
                cols_to_show = [c for c in cols_to_show if c in combined.columns]
                print(f'Combined {combined.shape[0]} rows from {len(dfs)} files - showing column: {col_sel}')
                display(combined[cols_to_show].head())
            else:
                print(f'Combined {combined.shape[0]} rows from {len(dfs)} files')
                display(combined.head())
            
            summary = pd.DataFrame(details, columns=['REP', 'ROBOT', 'ROWS'])
            display(summary.sort_values(['REP', 'ROBOT']).reset_index(drop=True))

    btn = widgets.Button(description='Preview', button_style='primary')
    btn.on_click(_preview)
    
    if split_config_mode:
        consensus_drop.observe(lambda *_: _update_rep_robot_cols(), names='value')
        agents_drop.observe(lambda *_: _update_rep_robot_cols(), names='value')
        _update_rep_robot_cols()
        display(widgets.VBox([
            widgets.HBox([consensus_drop, agents_drop, rep_drop, robot_drop, col_drop, btn]), 
            preview_out
        ]))
    else:
        exp_drop.observe(lambda *_: _update_rep_robot_cols(), names='value')
        _update_rep_robot_cols()
        display(widgets.VBox([
            widgets.HBox([exp_drop, rep_drop, robot_drop, col_drop, btn]), 
            preview_out
        ]))


def show_block_production_summary():
    """Display summary of block production counts per robot."""
    if 'block_production_counts' not in globals() or not globals().get('block_production_counts'):
        print("No block production data available. Load data first using the CSV picker.")
        return
    
    counts = globals().get('block_production_counts', {})
    
    # Build summary table
    rows = []
    for exp_key in sorted(counts.keys()):
        for rep in sorted(counts[exp_key].keys()):
            for robot, count in sorted(counts[exp_key][rep].items()):
                rows.append({
                    'Experiment': exp_key,
                    'Rep': rep,
                    'Robot': robot,
                    'Blocks Produced': count
                })
    
    if not rows:
        print("No block production data found.")
        return
    
    df = pd.DataFrame(rows)
    
    print(f"Block Production Summary ({len(rows)} robots)")
    print("=" * 60)
    display(df)
    
    # Summary statistics
    print("\n" + "=" * 60)
    print("Statistics by Experiment:")
    print("=" * 60)
    summary = df.groupby('Experiment')['Blocks Produced'].agg(['count', 'sum', 'mean', 'median', 'std', 'min', 'max'])
    summary.columns = ['Robots', 'Total', 'Mean', 'Median', 'Std', 'Min', 'Max']
    display(summary)
    
    # Overall totals
    print("\n" + "=" * 60)
    print(f"Overall Total: {df['Blocks Produced'].sum():,} blocks produced")
    print(f"Average per robot: {df['Blocks Produced'].mean():.1f} blocks")
    print("=" * 60)


def show_block_production_picker():
    """Interactive picker to show block production counts filtered by experiment, rep, and robot.
    Reuses the generic data picker used in previews and histograms.
    """
    if 'block_production_counts' not in globals() or not globals().get('block_production_counts'):
        print("No block production data available. Load data first using the CSV picker.")
        return

    counts = globals().get('block_production_counts', {})

    def _picker_callback(exp, rep_sel, robot_sel, loaded_data, preview_out):
        # exp is a key from loaded_data; counts uses same keys
        with preview_out:
            preview_out.clear_output()
            if exp not in counts:
                print(f"No block production data found for {exp}.")
                return

            rows = []
            reps_dict = counts.get(exp, {})

            # Determine reps to include
            rep_keys = sorted(reps_dict.keys())
            if rep_sel != 'All':
                rep_keys = [rep_sel] if rep_sel in reps_dict else []

            # Build rows
            for rep in rep_keys:
                robots_dict = reps_dict.get(rep, {})
                # Determine robots to include
                robot_items = sorted(robots_dict.items())
                if robot_sel != 'All':
                    robot_items = [(r, c) for (r, c) in robot_items if str(r) == str(robot_sel)]

                for robot, count in robot_items:
                    rows.append({
                        'Experiment': exp,
                        'Rep': rep,
                        'Robot': robot,
                        'Blocks Produced': count,
                    })

            if not rows:
                print("No data for selected filters.")
                return

            df = pd.DataFrame(rows)
            # Display table
            display(df.sort_values(['Rep', 'Robot']).reset_index(drop=True))

            # Per-rep summary
            print("\nPer-Rep Summary:")
            rep_sum = df.groupby('Rep')['Blocks Produced'].agg(['count', 'sum', 'mean', 'median', 'std', 'min', 'max'])
            rep_sum.columns = ['Robots', 'Total', 'Mean', 'Median', 'Std', 'Min', 'Max']
            display(rep_sum)

            # Overall
            print("\nOverall:")
            total = int(df['Blocks Produced'].sum())
            avg = float(df['Blocks Produced'].mean())
            print(f"Total blocks produced: {total}")
            print(f"Average per robot: {avg:.1f}")

    # Reuse the shared picker UI
    create_data_picker_with_callback('Show Block Counts', _picker_callback, button_style='primary')


def get_block_production_count(experiment=None, rep=None, robot=None):
    """Get block production count(s) from loaded data.
    
    Args:
        experiment: Experiment key (e.g., 'ProofOfWork_5'). If None, returns all.
        rep: Repetition/run number (e.g., '1'). If None, returns all for experiment.
        robot: Robot number (e.g., 2). If None, returns all for rep.
    
    Returns:
        int, dict, or None depending on specificity of query
    
    Examples:
        get_block_production_count('ProofOfWork_5', '1', 2)  # Returns count for robot 2
        get_block_production_count('ProofOfWork_5', '1')     # Returns dict of all robots in rep 1
        get_block_production_count('ProofOfWork_5')          # Returns dict of all reps
        get_block_production_count()                         # Returns full dict
    """
    if 'block_production_counts' not in globals():
        print("No block production data available. Load data first.")
        return None
    
    counts = globals().get('block_production_counts', {})
    
    if experiment is None:
        return counts
    
    if experiment not in counts:
        print(f"Experiment '{experiment}' not found. Available: {list(counts.keys())}")
        return None
    
    if rep is None:
        return counts[experiment]
    
    rep_str = str(rep)
    if rep_str not in counts[experiment]:
        print(f"Rep '{rep}' not found in {experiment}. Available: {list(counts[experiment].keys())}")
        return None
    
    if robot is None:
        return counts[experiment][rep_str]
    
    if robot not in counts[experiment][rep_str]:
        print(f"Robot {robot} not found in {experiment}/{rep}. Available: {list(counts[experiment][rep_str].keys())}")
        return None
    
    return counts[experiment][rep_str][robot]
    
    if split_config_mode:
        consensus_drop.observe(lambda *_: _update_rep_robot_cols(), names='value')
        agents_drop.observe(lambda *_: _update_rep_robot_cols(), names='value')
        _update_rep_robot_cols()
        display(widgets.VBox([
            widgets.HBox([consensus_drop, agents_drop, rep_drop, robot_drop, col_drop, btn]), 
            preview_out
        ]))
    else:
        exp_drop.observe(lambda *_: _update_rep_robot_cols(), names='value')
        _update_rep_robot_cols()
        display(widgets.VBox([
            widgets.HBox([exp_drop, rep_drop, robot_drop, col_drop, btn]), 
            preview_out
        ]))


def show_histogram(column_name, *dedup_keys, bins=100, xlabel=None, ylabel='Cumulative Percentage', title=None):
    """Display histogram of specified column with experiment, rep, and robot filters.
    
    Args:
        column_name: Column to display histogram for (e.g., 'TELAPSED')
        *dedup_keys: Optional keys for deduplication before processing.
                    If provided, deduplicates by these keys, sorts by column_name,
                    and calculates differences (useful for time intervals).
                    Example: show_histogram('TIMESTAMP', 'HASH') for TPROD calculation
        bins: Number of bins for the histogram (default: 100)
        xlabel: Label for x-axis (default: '{column_name} [s]')
        ylabel: Label for y-axis (default: 'Cumulative Percentage')
        title: Title for the plot (default: '{column_name} Distribution - {exp}')
    """
    def _histogram_callback(exp, rep_sel, robot_sel, loaded_data, preview_out):
        with preview_out:
            preview_out.clear_output()
            dfs = []
            
            # Determine required columns
            required_cols = set([column_name] + list(dedup_keys))
            
            for rep, robots in loaded_data.get(exp, {}).items():
                if rep_sel != 'All' and rep != rep_sel:
                    continue
                for robot, df in robots.items():
                    if robot_sel != 'All' and str(robot) != robot_sel:
                        continue
                    if isinstance(df, pd.DataFrame):
                        # Check if required columns exist
                        missing = required_cols - set(df.columns)
                        if missing:
                            print(f'Warning: Missing columns {missing} in {exp}/{rep}/robot_{robot}')
                            continue
                        
                        df_copy = df[list(required_cols)].copy()
                        df_copy['REP'] = rep
                        df_copy['ROBOT'] = robot
                        dfs.append(df_copy)

            if not dfs:
                print(f'No data found for {column_name} in {exp} with selected filters')
                return

            combined = pd.concat(dfs, ignore_index=True)
            
            # Process data: apply deduplication and diff if keys provided
            if dedup_keys:
                combined = combined.drop_duplicates(list(dedup_keys))
                combined = combined.sort_values(column_name)
                # Calculate differences grouped by REP
                combined[column_name] = combined.groupby(['REP'])[column_name].diff()
                # Remove NaN values from diff (first row of each group)
                data_to_plot = combined[column_name].dropna()
                desc_suffix = 'unique blocks'
            else:
                data_to_plot = combined[column_name]
                desc_suffix = 'blocks'
            
            if len(data_to_plot) == 0:
                print(f'No valid data found for {column_name} in {exp} with selected filters')
                return
            
            # Create figure
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            
            # Create histogram
            hist, bins_edges = np.histogram(data_to_plot, bins=bins)
            
            # Avoid division by zero warning - normalize safely
            hist_sum = hist.sum()
            if hist_sum > 0:
                cumsum_normalized = np.cumsum(hist.astype(np.float32)) / hist_sum
            else:
                cumsum_normalized = np.zeros_like(hist, dtype=np.float32)
            
            ax.bar(bins_edges[:-1] + (bins_edges[1] - bins_edges[0]) / 2, 
                   cumsum_normalized, 
                   width=(bins_edges[1] - bins_edges[0]), 
                   color='green', 
                   alpha=0.6,
                   zorder=3)
            
            # Edit plot
            ax.grid(axis='x', linestyle='--', color='k', zorder=1)
            n_samples = len(data_to_plot)
            data_max = data_to_plot.max()
            ax.text(data_max * 0.95, 0.2, f'n={n_samples:,} {desc_suffix}', ha='right', zorder=4)
            t = ax.text(data_max * 0.95, 0.2, f'n={n_samples:,} {desc_suffix}', ha='right', color='white', zorder=2)
            t.set_bbox(dict(facecolor='white', edgecolor='white'))
            ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1, decimals=0))
            ax.set_ylim(ymin=0, ymax=1)
            ax.set_xlim(xmin=bins_edges[0], xmax=bins_edges[-1])
            
            # Set labels with defaults if not provided
            ax.set_xlabel(xlabel if xlabel is not None else f'{column_name} [s]')
            ax.set_ylabel(ylabel)
            ax.set_title(title if title is not None else f'{column_name} Distribution - {exp}')

            
            plt.tight_layout()
            plt.show()
            
            # Print summary statistics
            print(f'\nStatistics for {n_samples:,} {desc_suffix}:')
            print(f'Mean: {data_to_plot.mean():.2f}s')
            print(f'Median: {data_to_plot.median():.2f}s')
            print(f'Std: {data_to_plot.std():.2f}s')
            print(f'Min: {data_to_plot.min():.2f}s')
            print(f'Max: {data_to_plot.max():.2f}s')

    create_data_picker_with_callback('Show Histogram', _histogram_callback, 'primary')


def _create_consensus_boxplot_visualization(
    plot_df, 
    metric_column, 
    ylabel, 
    plot_title, 
    comparison_title,
    ylim=None,
    no_data_message="No data found."
):
    """
    Generic visualization function for consensus/agent metrics with N boxplots + 1 comparison chart.
    Dynamically adjusts grid layout based on number of consensus types.
    
    Args:
        plot_df: DataFrame with columns 'consensus', 'num_agents', and metric_column
        metric_column: Name of the column containing metric values
        ylabel: Label for y-axis (e.g., 'Propagation Time [s]' or 'Efficiency (%)')
        plot_title: Overall figure title (e.g., 'Block Propagation Time (BPT)')
        comparison_title: Title for the comparison line chart
        ylim: Optional tuple (min, max) to set y-axis limits on boxplots
        no_data_message: Message to display if no data
    """
    import numpy as np
    import matplotlib.pyplot as plt
    import math
    
    if plot_df.empty:
        print(no_data_message)
        return
    
    # Get unique consensus types and assign colors
    consensus_types = sorted(plot_df['consensus'].unique())
    n_consensus = len(consensus_types)
    
    # Use tab20 colormap for more distinct colors if needed
    if n_consensus <= 10:
        colors = plt.cm.tab10(np.linspace(0, 1, min(n_consensus, 10)))
    else:
        colors = plt.cm.tab20(np.linspace(0, 1, min(n_consensus, 20)))
    color_map = dict(zip(consensus_types, colors))
    
    # Get unique agent counts for x-axis positions
    agent_counts = sorted(plot_df['num_agents'].unique())
    
    # Determine grid layout based on number of consensus types
    # Use 2 columns for <= 6, 3 columns for 7-12, 4 columns for > 12
    if n_consensus <= 6:
        n_cols = 2
    elif n_consensus <= 12:
        n_cols = 3
    else:
        n_cols = 4
    
    n_rows = math.ceil(n_consensus / n_cols)
    
    # Create figure with dynamic grid: n_rows for boxplots + 1 for line chart
    fig = plt.figure(figsize=(6 * n_cols, 4 * n_rows + 5))
    gs = fig.add_gridspec(n_rows + 1, n_cols, hspace=0.3, wspace=0.3)
    
    # Create boxplot subplots (one per consensus)
    for idx, consensus in enumerate(consensus_types):
        row = idx // n_cols
        col = idx % n_cols
        ax = fig.add_subplot(gs[row, col])
        
        # Prepare data for this consensus
        positions = []
        box_data = []
        
        for i, n_agents in enumerate(agent_counts):
            subset = plot_df[(plot_df['num_agents'] == n_agents) & (plot_df['consensus'] == consensus)]
            if not subset.empty:
                positions.append(i)
                box_data.append(subset[metric_column].values)
        
        if box_data:
            bp = ax.boxplot(box_data, positions=positions, widths=0.6, 
                           patch_artist=True, showfliers=False)
            
            # Color all boxes with consensus color
            for patch in bp['boxes']:
                patch.set_facecolor(color_map[consensus])
                patch.set_alpha(0.7)
            
            ax.set_xticks(range(len(agent_counts)))
            ax.set_xticklabels(agent_counts)
            ax.set_xlabel('Number of Agents')
            ax.set_ylabel(ylabel)
            ax.set_title(f'{consensus}', fontweight='bold', fontsize=11)
            ax.grid(axis='y', linestyle='--', alpha=0.3)
            
            # Set y-limits if provided
            if ylim:
                ax.set_ylim(ylim)
    
    # Create line chart comparing all consensus algorithms (spanning all columns at bottom)
    ax_line = fig.add_subplot(gs[n_rows, :])
    
    for consensus in consensus_types:
        trend_agents = []
        trend_means = []
        trend_stds = []
        
        for n_agents in agent_counts:
            subset = plot_df[(plot_df['num_agents'] == n_agents) & (plot_df['consensus'] == consensus)]
            if not subset.empty:
                mean_metric = subset[metric_column].mean()
                std_metric = subset[metric_column].std()
                trend_agents.append(n_agents)
                trend_means.append(mean_metric)
                trend_stds.append(std_metric if not pd.isna(std_metric) else 0)
        
        # Draw line with error bands
        if len(trend_agents) >= 1:
            ax_line.plot(trend_agents, trend_means, color=color_map[consensus], 
                        linewidth=3, marker='o', markersize=8, label=consensus)
            
            # Add confidence bands (mean ± std)
            if len(trend_agents) >= 1:
                means_array = np.array(trend_means)
                stds_array = np.array(trend_stds)
                ax_line.fill_between(trend_agents, means_array - stds_array, 
                                    means_array + stds_array, 
                                    color=color_map[consensus], alpha=0.2)
    
    ax_line.set_xlabel('Number of Agents', fontsize=12, fontweight='bold')
    ax_line.set_ylabel(ylabel, fontsize=12, fontweight='bold')
    ax_line.set_title(comparison_title, fontsize=13, fontweight='bold')
    ax_line.legend(loc='best', fontsize=10)
    ax_line.grid(True, linestyle='--', alpha=0.3)
    
    # Overall title
    fig.suptitle(plot_title, fontsize=14, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    plt.show()
    
    # Print summary statistics
    print(f"\nSummary Statistics ({ylabel}):")
    summary = plot_df.groupby(['consensus', 'num_agents'])[metric_column].agg(['count', 'mean', 'median', 'std', 'min', 'max'])
    print(summary.to_string())


def show_block_propagation_boxplot():
    """Display boxplot of block propagation times across different consensus protocols and number of agents.
    Shows 5 plots: 4 per-consensus boxplots (2x2 grid) + 1 comparison line chart."""
    
    if 'loaded_data' not in globals() or not globals().get('loaded_data'):
        print("No `loaded_data` available. Use the picker and click Load data first.")
        return
    
    loaded_data = globals().get('loaded_data', {})
    exp_choices = sorted(loaded_data.keys())
    
    # Parse experiment keys to extract consensus and agent count
    # Expected format: experiment/consensus_agentcount or consensus_agentcount
    data_for_plot = []
    
    for exp_key in exp_choices:
        # Extract consensus and agent count using helper function
        consensus, num_agents = _extract_config_info(exp_key)
        if consensus is None or num_agents is None:
            print(f"Skipping {exp_key}: doesn't match consensus_number pattern")
            continue
        
        # Calculate propagation time for each block in this configuration
        for rep_name, robots_dict in loaded_data.get(exp_key, {}).items():
            # For each unique block (by HASH), find the time difference between
            # first reception and last reception across all robots
            
            block_times = {}  # hash -> list of (robot, timestamp)
            
            for robot_id, df in robots_dict.items():
                if not isinstance(df, pd.DataFrame):
                    continue
                if 'HASH' not in df.columns or 'RECEPTION' not in df.columns:
                    continue
                
                for _, row in df.iterrows():
                    block_hash = row['HASH']
                    timestamp = row['RECEPTION']
                    
                    if block_hash not in block_times:
                        block_times[block_hash] = []
                    block_times[block_hash].append((robot_id, timestamp))
            
            # Calculate propagation time for each block
            for block_hash, times in block_times.items():
                if len(times) < 2:  # Need at least 2 robots to calculate propagation
                    continue
                
                timestamps = [t for _, t in times]
                propagation_time = max(timestamps) - min(timestamps)
                
                data_for_plot.append({
                    'consensus': consensus,
                    'num_agents': num_agents,
                    'propagation_time': propagation_time,
                    'rep': rep_name,
                    'block_hash': block_hash
                })
    
    # Convert to DataFrame
    plot_df = pd.DataFrame(data_for_plot)
    
    # Use generic visualization function
    _create_consensus_boxplot_visualization(
        plot_df=plot_df,
        metric_column='propagation_time',
        ylabel='Propagation Time [s]',
        plot_title='Block Propagation Time (BPT)',
        comparison_title='Propagation Time Comparison Across Consensus Algorithms',
        ylim=None,
        no_data_message="No block propagation data found. Make sure data contains HASH and RECEPTION columns."
    )


def show_efficiency_boxplot():
    """Boxplot of chain efficiency (max height / total produced blocks) by consensus and number of agents.
    Shows 5 plots: 4 per-consensus boxplots (2x2 grid) + 1 comparison line chart."""

    if 'loaded_data' not in globals() or not globals().get('loaded_data'):
        print("No `loaded_data` available. Use the picker and click Load data first.")
        return

    loaded_data = globals().get('loaded_data', {})
    exp_choices = sorted(loaded_data.keys())

    rows = []  # each row: consensus, num_agents, rep, efficiency_pct

    for exp_key in exp_choices:
        # Extract consensus and agent count using helper function
        consensus, num_agents = _extract_config_info(exp_key)
        if consensus is None or num_agents is None:
            # Not following consensus_numAgents pattern; skip with notice
            print(f"Skipping {exp_key}: doesn't match consensus_number pattern")
            continue

        for rep_name, robots_dict in loaded_data.get(exp_key, {}).items():
            # Get the maximum HEIGHT across all robots
            max_height = 0
            total_blocks_produced = 0
            
            for robot, robot_df in robots_dict.items():
                if not isinstance(robot_df, pd.DataFrame):
                    continue
                
                # Get max height from this robot's data
                if 'HEIGHT' in robot_df.columns:
                    robot_max_height = robot_df['HEIGHT'].max()
                    max_height = max(max_height, robot_max_height)
            
            # Get total blocks produced for this rep (if available)
            if 'block_production_counts' in globals():
                block_counts = globals().get('block_production_counts', {})
                if exp_key in block_counts and rep_name in block_counts[exp_key]:
                    total_blocks_produced = sum(block_counts[exp_key][rep_name].values())
            
            # Calculate efficiency: max_height / total_blocks_produced * 100
            if max_height > 0 and total_blocks_produced > 0:
                efficiency_pct = (max_height / total_blocks_produced) * 100.0
                rows.append({
                    'consensus': consensus,
                    'num_agents': num_agents,
                    'rep': rep_name,
                    'efficiency_pct': efficiency_pct,
                    'max_height': max_height,
                    'total_blocks': total_blocks_produced,
                })

    # Convert to DataFrame
    plot_df = pd.DataFrame(rows)
    
    # Use generic visualization function
    _create_consensus_boxplot_visualization(
        plot_df=plot_df,
        metric_column='efficiency_pct',
        ylabel='Efficiency (%)',
        plot_title='Block Production Efficiency (BPE)',
        comparison_title='Efficiency Comparison Across Consensus Algorithms',
        ylim=(0, 100),
        no_data_message="No efficiency data found. Ensure CSVs contain HEIGHT column and block production data is available."
    )

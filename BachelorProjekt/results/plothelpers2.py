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


# Data loading and preview functions
import os
import pandas as pd
import ipywidgets as widgets


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
                                # Store the DataFrame directly (no csv_basename key level)
                                run_dict[robot_key] = df

            # Save global variables
            globals()['loaded_data'] = loaded
            globals()['selected_csv_map'] = selected_csv_map
            
            out.clear_output()
            with out:
                if loaded:
                    print("Data loaded successfully!")
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
    
    # Check if single experiment mode with split config names (consensus_number pattern)
    single_exp_mode = False
    split_config_mode = False
    consensus_drop = None
    agents_drop = None
    
    if len(exp_choices) > 1 and all('/' in exp for exp in exp_choices):
        prefixes = [exp.split('/')[0] for exp in exp_choices]
        if len(set(prefixes)) == 1:
            single_exp_mode = True
            config_names = [exp.split('/')[-1] for exp in exp_choices]
            
            # Check if configs follow "consensus_number" pattern
            if all('_' in cfg and cfg.split('_')[-1].isdigit() for cfg in config_names):
                split_config_mode = True
                # Extract consensus types and agent numbers
                consensus_types = sorted(set('_'.join(cfg.split('_')[:-1]) for cfg in config_names))
                agent_numbers = sorted(set(cfg.split('_')[-1] for cfg in config_names), key=int)
                
                consensus_drop = widgets.Dropdown(options=consensus_types, description='Consensus:')
                agents_drop = widgets.Dropdown(options=agent_numbers, description='# Agents:')
    
    if not split_config_mode:
        # Original single dropdown mode
        display_names = exp_choices
        if single_exp_mode:
            display_names = [exp.split('/')[-1] for exp in exp_choices]
        
        name_to_exp = dict(zip(display_names, exp_choices))
        exp_drop = widgets.Dropdown(options=display_names, description='Experiment:' if not single_exp_mode else 'Config:')
    else:
        exp_drop = None
        # Create mapping from (consensus, agents) to exp key
        config_to_exp = {}
        for exp in exp_choices:
            cfg = exp.split('/')[-1]
            consensus = '_'.join(cfg.split('_')[:-1])
            agents = cfg.split('_')[-1]
            config_to_exp[(consensus, agents)] = exp
    
    rep_drop = widgets.Dropdown(options=['All'], description='Rep:', value='All')
    robot_drop = widgets.Dropdown(options=['All'], description='Robot:', value='All')
    preview_out = widgets.Output()

    def _update_rep_robot(*_):
        if split_config_mode:
            exp = config_to_exp[(consensus_drop.value, agents_drop.value)]
        else:
            exp = name_to_exp[exp_drop.value]
        reps = sorted(loaded_data.get(exp, {}).keys())
        rep_drop.options = ['All'] + reps
        robots = sorted({r for rep in reps for r in loaded_data[exp][rep].keys()})
        robot_drop.options = ['All'] + [str(r) for r in robots]

    def _on_button_click(_):
        if split_config_mode:
            exp = config_to_exp[(consensus_drop.value, agents_drop.value)]
        else:
            exp = name_to_exp[exp_drop.value]
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

    # Check if single experiment mode with split config names
    single_exp_mode = False
    split_config_mode = False
    consensus_drop = None
    agents_drop = None
    
    if len(exp_choices) > 0 and all('/' in e for e in exp_choices):
        prefixes = [e.split('/')[0] for e in exp_choices]
        if len(set(prefixes)) == 1:
            single_exp_mode = True
            config_names = [e.split('/')[-1] for e in exp_choices]
            
            # Check if configs follow "consensus_number" pattern
            if all('_' in cfg and cfg.split('_')[-1].isdigit() for cfg in config_names):
                split_config_mode = True
                # Extract consensus types and agent numbers
                consensus_types = sorted(set('_'.join(cfg.split('_')[:-1]) for cfg in config_names))
                agent_numbers = sorted(set(cfg.split('_')[-1] for cfg in config_names), key=int)
                
                consensus_drop = widgets.Dropdown(options=consensus_types, description='Consensus:')
                agents_drop = widgets.Dropdown(options=agent_numbers, description='# Agents:')
    
    if not split_config_mode:
        # Original single dropdown mode
        display_names = exp_choices
        if single_exp_mode:
            display_names = [e.split('/', 1)[1] for e in exp_choices]
        
        name_to_exp = dict(zip(display_names, exp_choices))
        exp_drop = widgets.Dropdown(options=display_names, description='Experiment:' if not single_exp_mode else 'Config:')
    else:
        exp_drop = None
        # Create mapping from (consensus, agents) to exp key
        config_to_exp = {}
        for exp in exp_choices:
            cfg = exp.split('/')[-1]
            consensus = '_'.join(cfg.split('_')[:-1])
            agents = cfg.split('_')[-1]
            config_to_exp[(consensus, agents)] = exp
    
    rep_drop = widgets.Dropdown(options=['All'], description='Rep:', value='All')
    robot_drop = widgets.Dropdown(options=['All'], description='Robot:', value='All')
    col_drop = widgets.Dropdown(options=['All'], description='Columns:', value='All')
    preview_out = widgets.Output()

    def _update_rep_robot_cols(*_):
        if split_config_mode:
            exp = config_to_exp[(consensus_drop.value, agents_drop.value)]
        else:
            exp = name_to_exp[exp_drop.value]
        reps = sorted(loaded_data.get(exp, {}).keys())
        rep_drop.options = ['All'] + reps
        robots = sorted({r for rep in reps for r in loaded_data[exp][rep].keys()})
        robot_drop.options = ['All'] + [str(r) for r in robots]
        
        # Get all available columns from all robots of this experiment
        all_cols = set()
        for rep in loaded_data.get(exp, {}).values():
            for df in rep.values():
                if isinstance(df, pd.DataFrame):
                    all_cols.update(df.columns)
        
        col_options = ['All'] + sorted(list(all_cols))
        col_drop.options = col_options
        col_drop.value = 'All'

    def _preview(_):
        with preview_out:
            preview_out.clear_output()
            if split_config_mode:
                exp = config_to_exp[(consensus_drop.value, agents_drop.value)]
            else:
                exp = name_to_exp[exp_drop.value]
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


def show_telapsed_histogram():
    """Display histogram of TELAPSED (time elapsed between blocks) with experiment, rep, and robot filters."""
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib import ticker
    
    def _histogram_callback(exp, rep_sel, robot_sel, loaded_data, preview_out):
        with preview_out:
            preview_out.clear_output()
            dfs = []
            for rep, robots in loaded_data.get(exp, {}).items():
                if rep_sel != 'All' and rep != rep_sel:
                    continue
                for robot, df in robots.items():
                    if robot_sel != 'All' and str(robot) != robot_sel:
                        continue
                    if isinstance(df, pd.DataFrame):
                        # Check if TELAPSED column exists
                        if 'TELAPSED' not in df.columns:
                            print(f'Warning: TELAPSED column not found in {exp}/{rep}/robot_{robot}')
                            continue
                        
                        dfs.append(df[['TELAPSED']].copy())

            if not dfs:
                print(f'No TELAPSED data found for {exp} with selected filters')
                return

            combined = pd.concat(dfs, ignore_index=True)
            
            # Histogram parameters - fixed 100 bins
            bins = 100
            
            # Create figure
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            
            # Create histogram
            hist, bins_edges = np.histogram(combined['TELAPSED'], bins=bins)
            
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
            n_blocks = len(combined)
            data_max = combined['TELAPSED'].max()
            ax.text(data_max * 0.95, 0.2, f'n={n_blocks:,} blocks', ha='right', zorder=4)
            t = ax.text(data_max * 0.95, 0.2, f'n={n_blocks:,} blocks', ha='right', color='white', zorder=2)
            t.set_bbox(dict(facecolor='white', edgecolor='white'))
            ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1, decimals=0))
            ax.set_ylim(ymin=0, ymax=1)
            ax.set_xlim(xmin=bins_edges[0], xmax=bins_edges[-1])
            ax.set_xlabel('Block Reception Delay [s]')
            ax.set_ylabel('Cumulative Percentage')
            ax.set_title(f'Time Elapsed Between Blocks - {exp}')
            
            plt.tight_layout()
            plt.show()
            
            # Print summary statistics
            print(f'\nStatistics for {n_blocks:,} blocks:')
            print(f'Mean: {combined["TELAPSED"].mean():.2f}s')
            print(f'Median: {combined["TELAPSED"].median():.2f}s')
            print(f'Std: {combined["TELAPSED"].std():.2f}s')
            print(f'Min: {combined["TELAPSED"].min():.2f}s')
            print(f'Max: {combined["TELAPSED"].max():.2f}s')

    create_data_picker_with_callback('Show Histogram', _histogram_callback, 'primary')


def show_tprod_histogram():
    """Display histogram of TPROD (time between block productions) with experiment, rep, and robot filters."""
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib import ticker
    
    def _tprod_histogram_callback(exp, rep_sel, robot_sel, loaded_data, preview_out):
        with preview_out:
            preview_out.clear_output()
            dfs = []
            for rep, robots in loaded_data.get(exp, {}).items():
                if rep_sel != 'All' and rep != rep_sel:
                    continue
                for robot, df in robots.items():
                    if robot_sel != 'All' and str(robot) != robot_sel:
                        continue
                    if isinstance(df, pd.DataFrame):
                        # Check if TIMESTAMP and HASH columns exist
                        if 'TIMESTAMP' not in df.columns or 'HASH' not in df.columns:
                            print(f'Warning: TIMESTAMP or HASH column not found in {exp}/{rep}/robot_{robot}')
                            continue
                        
                        df_copy = df[['TIMESTAMP', 'HASH']].copy()
                        df_copy['REP'] = rep
                        df_copy['ROBOT'] = robot
                        dfs.append(df_copy)

            if not dfs:
                print(f'No TIMESTAMP data found for {exp} with selected filters')
                return

            combined = pd.concat(dfs, ignore_index=True)
            
            # Process the dataframe: drop duplicates, sort by timestamp, calculate diff
            combined = combined.drop_duplicates('HASH')
            combined = combined.sort_values('TIMESTAMP')
            combined['TPROD'] = combined.groupby(['REP'])['TIMESTAMP'].diff()
            
            # Remove NaN values from diff (first row of each group)
            combined_tprod = combined['TPROD'].dropna()
            
            if len(combined_tprod) == 0:
                print(f'No valid TPROD data found for {exp} with selected filters')
                return
            
            # Histogram parameters - fixed 100 bins
            bins = 100
            
            # Create figure
            fig, ax = plt.subplots(1, 1, figsize=(10, 5))
            
            # Create histogram
            hist, bins_edges = np.histogram(combined_tprod, bins=bins)
            
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
            n_blocks = len(combined_tprod)
            data_max = combined_tprod.max()
            ax.text(data_max * 0.95, 0.2, f'n={n_blocks:,} unique blocks', ha='right', zorder=4)
            t = ax.text(data_max * 0.95, 0.2, f'n={n_blocks:,} unique blocks', ha='right', color='white', zorder=2)
            t.set_bbox(dict(facecolor='white', edgecolor='white'))
            ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1, decimals=0))
            ax.set_ylim(ymin=0, ymax=1)
            ax.set_xlim(xmin=bins_edges[0], xmax=bins_edges[-1])
            ax.set_xlabel('Block Production Interval [s]')
            ax.set_ylabel('Cumulative Percentage')
            ax.set_title(f'Time Elapsed Between Block Productions - {exp}')
            
            plt.tight_layout()
            plt.show()
            
            # Print summary statistics
            print(f'\nStatistics for {n_blocks:,} unique blocks:')
            print(f'Mean: {combined_tprod.mean():.2f}s')
            print(f'Median: {combined_tprod.median():.2f}s')
            print(f'Std: {combined_tprod.std():.2f}s')
            print(f'Min: {combined_tprod.min():.2f}s')
            print(f'Max: {combined_tprod.max():.2f}s')

    create_data_picker_with_callback('Show Histogram', _tprod_histogram_callback, 'primary')

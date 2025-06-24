import datetime
import urllib.request
from pythia.plugins.nasap.grid import id_at
from pythia.functions import xy_from_list, xy_from_vector
from pythia.io import find_closest_vector_coords
from pythia.plugin import register_plugin_function, PluginHook

def initialize(args, plugins, config):
    plugins = register_plugin_function(PluginHook.post_config, ev_load_config, config, plugins)
    return plugins


def ev_load_config(*args, **kwargs):
    config = kwargs.get("full_config")
    start_year = 0;
    end_year = 0; 
    for run in config.get("runs", []):
        local_start_year = run.get("startYear")
        local_end_year = run.get("nyers") + local_start_year
        
        if start_year == 0 or start_year > local_start_year:
            start_year = local_start_year
        if end_year < local_end_year:
            end_year = local_end_year

    visited = set([])
    for run in config.get("runs", []):
        if isinstance(run["sites"], list):
            sites = xy_from_list(run["sites"])
        else:
            sites = xy_from_vector(run["sites"])
        for site in sites:
            nasap_id = id_at(site[0], site[1]) 
            if nasap_id in visited:
                continue
            visited.add(nasap_id)

            fetch_data(f"{start_year}0101", f"{end_year}1231", site[0], site[1], f"wth/{nasap_id}.WTH");

    return kwargs


def fetch_data(start_date: str, end_date: str, longitude: float, latitude: float, output_path: str):
    
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    community = "AG"     
    parameters = "T2M"    
    fmt = "ICASA"  

    url = (
        f"{base_url}"
        f"?start={start_date}"
        f"&end={end_date}"
        f"&latitude={latitude}"
        f"&longitude={longitude}"
        f"&community={community}"
        f"&parameters={parameters}"
        f"&format={fmt}"
        f"&header=true"
    )

    urllib.request.urlretrieve(url, output_path)

def lookup_wth(args, lat, lng):
    args = args.split("::")[1:]
    cell_id = None
    if "vector" in args:
        idx = args.index("vector")
        cell_id = find_closest_vector_coords(args[idx + 1], lng, lat, args[idx + 2])
    return cell_id










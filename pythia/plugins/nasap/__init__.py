import time
import urllib.request
from pythia.plugins.nasap.grid import id_at
from pythia.functions import xy_from_list, xy_from_vector
from pythia.io import find_closest_vector_coords
from pythia.plugin import register_plugin_function, PluginHook

def initialize(args, plugins, config):
    plugins = register_plugin_function(PluginHook.post_config, ev_load_config, config, plugins)
    return plugins

# kwargs = stores the event data, and the function must return the event data; I can modify kwargs

# TO-DO:
# download files for all sites

def ev_load_config(*args, **kwargs): #always return kwargs on the functions
    config = kwargs.get("full_config")
    visited = set([])
    print("rodando ---")
    for run in config.get("runs", []):
        wsta = run["wsta"] 
        if isinstance(run["sites"], list):
            sites = xy_from_list(run["sites"])
        else:
            sites = xy_from_vector(run["sites"])
        for site in sites:
            print(site)
            nasap_id = id_at(site[0], site[1]) #lookup_wth(wsta, site[0], site[1])
            if nasap_id in visited:
                print(f"visitado --- {nasap_id}")
                continue
            visited.add(nasap_id)
            print(f"baixando --- {nasap_id}")

            fetch_data('20010101', '20020101', site[0], site[1], f"wth/{nasap_id}.WTH");

    return kwargs


def fetch_data(start_date: str, end_date: str, longitude: float, latitude: float, output_path: str): #output must be on the pattern wth/id +.WTH
    
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
    now = time.time()
    args = args.split("::")[1:]
    cell_id = None
    if "vector" in args:
        idx = args.index("vector")
        cell_id = find_closest_vector_coords(args[idx + 1], lng, lat, args[idx + 2])
    print(f"execution time: {time.time() - now}")
    return cell_id










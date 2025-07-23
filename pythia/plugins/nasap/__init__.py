import urllib.request
import sqlite3
from pythia.plugins.nasap.grid import id_at
from pythia.functions import xy_from_list, xy_from_vector
from pythia.io import find_closest_vector_coords
from pythia.plugin import register_plugin_function, PluginHook

def initialize(args, plugins, config):
    init_db() # is it ok to init the db here?
    plugins = register_plugin_function(PluginHook.post_config, ev_load_config, config, plugins)
    return plugins
    # maybe return a dict of key (function name) -> function


def init_db():
    conn = sqlite3.connect('nasapower_cache.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nasap_id TEXT,
            date TEXT,  
            t2m REAL,   
            tmin REAL, 
            tmax REAL, 
            tdew REAL, 
            rh2m REAL,
            rain REAL, 
            wind REAL, 
            srad REAL,
            wthlat REAL,
            wthlng REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def check_cache(nasap_id, start_date, end_date):
    conn = sqlite3.connect('nasapower_cache.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) FROM weather_data 
        WHERE nasap_id = ? AND date >= ? AND date <= ?
    ''', (nasap_id, start_date, end_date))
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0

# improve verifications on this function
def parse_and_store_wth(file_path, db_path, nasap_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(file_path, 'r') as file:
        reading_data = False
        wthlat = None
        wthlng = None

        for line in file:
            line = line.strip()

            if line.startswith('@ INSI'):
                next_line = next(file).strip().split()
                if len(next_line) >= 3:
                    wthlat = float(next_line[1])
                    wthlng = float(next_line[2])
                continue

            if line.startswith('@  DATE'):
                reading_data = True
                continue

            if reading_data:
                if not line or line.startswith('@') or line.startswith('$') or line.startswith('!'):
                    continue

                parts = line.split()
                if len(parts) == 9:
                    date, t2m, tmin, tmax, tdew, rh2m, rain, wind, srad = parts
                    cursor.execute('''
                        INSERT OR REPLACE INTO weather_data (
                            nasap_id, date, t2m, tmin, tmax, tdew, rh2m, rain, wind, srad, wthlat, wthlng
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        nasap_id, date, t2m, tmin, tmax, tdew, rh2m, rain, wind, srad, wthlat, wthlng
                    ))

    conn.commit()
    conn.close()
    print(f"data from {file_path} successfully inserted on {db_path}.")


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

            start_date = f"{start_year}0101"
            end_date = f"{end_year}1231"
            output_path = f"wth/{nasap_id}.WTH"

            if check_cache(nasap_id, start_date, end_date):
                # actually use the data from cache
                print(f"data with {nasap_id} already exists, skipping")
                continue
                
            fetch_data(start_date, end_date, site[0], site[1], output_path)
            parse_and_store_wth(output_path, 'nasapower_cache.db', nasap_id)
            
            # fetch_data(f"{start_year}0101", f"{end_year}1231", site[0], site[1], f"wth/{nasap_id}.WTH");

    return kwargs


def fetch_data(start_date: str, end_date: str, longitude: float, latitude: float, output_path: str):
    
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    community = "ag"     
    parameters = "T2M"    
    fmt = "icasa"  

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










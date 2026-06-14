import re
import os
import json
import shutil
import traceback
from skyfield.api import load, Loader

def load_planet_ephemeris(self):
    filename = 'de421.bsp'
    ephemeris_folder = os.path.join('main', 'data', 'Ephemeris')
    ephemeris_file = os.path.join(ephemeris_folder, filename)

    # if needed: download
    if not os.path.exists(ephemeris_file) and not os.path.exists(filename):
        tmp_loader = Loader('.')
        tmp_loader.download(filename) 

    # if needed: move to folder
    if os.path.exists(filename):
        os.makedirs(ephemeris_folder, exist_ok=True)
        shutil.move(filename, ephemeris_file)

    self.planet_ephemeris = load(ephemeris_file)  

def get_target_names_from_file(self, list_path:str):
    try:
        with open(list_path, 'r') as file:
            target_data = json.load(file)
            target_names = [target['name'] for target in target_data] 
            return target_names
    except Exception as e:
        print(traceback.format_exc())
        print(                                                  )
        print('>>>>>>>> IF PROGRAM CRASHED AT START UP <<<<<<<<')
        print(                                                  )
        print('  Check that main/data/Lists/default_list.json  ')
        print('  exists and contains a vaild list.             ')
        print(                                                  )
        print('>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<')
        print(                                                  )
        self.log_message(f'Error reading target list file: {e}')
        return []

def ra_dec_parser(value: str) -> float:
    s = value.strip().replace(",", ".")

    try:
        res = float(value) # if it can be turned into a float
        return res         # it is allready in the decimal form
    except:

        s = (
            s.replace("º", "°")
            .replace("′", "'")
            .replace("’", "'")
            .replace("″", '"')
            .replace("''", '"')
        )

        sign = -1 if re.match(r"^\s*-", s) else 1

        units = {
            "h": 0.0,
            "m": 0.0,
            "s": 0.0,
            "°": 0.0,
            "'": 0.0,
            '"': 0.0,
        }

        for num, unit in re.findall(
            r"([+-]?\d+(?:\.\d+)?)\s*(h|m|s|°|d|'|\")",
            s,
            flags=re.IGNORECASE,
        ):
            units[unit.lower()] = abs(float(num))

        
        if any(u in s for u in ("h", "m", "s")):
            return sign * ( # RA
                units["h"]
                + units["m"] / 60
                + units["s"] / 3600
            )
        else: 
            return sign * ( # DEC
                units["°"]
                + units["'"] / 60
                + units['"'] / 3600
            )



from datetime import datetime, timedelta
from utils.time_convertions import utc_now
import os
import json
import traceback
import requests

def update_data_if_needed(self, current_target):
    '''
    Checks how old the current data is and updates if needed.
    
    Parameters:
        current_target (dir): data about the target from self.target_list

    '''
    t = utc_now().isoformat()
    # t_30_min_later = (datetime.fromisoformat(t) + timedelta(minutes=30)).isoformat()

    # check if Horizons or CelesTrak data is used
    if current_target['type'] == 'LEO':
        last_download = self.metadata['OMM']['last download']
        time_difference = datetime.fromisoformat(t) - datetime.fromisoformat(last_download)

        need_to_update = False
        # update if data is older then 2h but not while tracking
        if time_difference.total_seconds() > 2 * 3600 and not self.tracking:
            need_to_update = True

        # update if data is older then 24h even if we are tracking
        elif time_difference.total_seconds() > 24 * 3600:
            need_to_update = True

        if need_to_update:
            self.log_message('Downloading new OMM data...')
            self.query_celestrak_api()
            self.load_target_list(OMM_only=True) # update list in memory

    else:
        pass # TODO
    #     satellite_id = current_satellite['catalogs']['Horizons']
    #     need_to_update = False
        
    #     # if data does not exist we need to update even during tracking
    #     if not (str(satellite_id) in self.satellite_metadata['Horizons']):
    #         need_to_update = True
    #     else:
    #         metadata = self.satellite_metadata['Horizons'][f'{satellite_id}']
            
    #         # if data does not exist or we run out of data we need to update even during tracking
    #         if metadata['valid until'] == "" or metadata['valid until'] < t:
    #             need_to_update = True

    #         # if we are not tracking and there is less then 30 min of data left we update
    #         elif not self.tracking and metadata['valid until'] < t_30_min_later:
    #             need_to_update = True

    #     if need_to_update:
    #         self.log_message(f'Downloading new data for Spacecraft {satellite_id} ...')
    #         self.query_horizons_api(satellite_id)
    #         self.query_horizons_api_AZ_EL(satellite_id)

    #         self.load_all_satellite_data(ID=satellite_id)
        
    # else:

def load_metadata(self):
    path = os.path.join('main', 'data', 'Metadata', 'metadata.json')
    try:
        with open(path, 'r') as file:
            return json.load(file)
    except Exception as e:
        self.log_message(f'Error reading satellite metadata file: {e}')
        print(traceback.format_exc())
        return {}

def query_celestrak_api(self):
    file_path = os.path.join('main', 'data', 'OMM', 'all_active_satellites.csv')
    url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=csv'

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        with open(file_path, 'wb') as file:
            file.write(response.content)
        self.log_message(f'Data downloaded and saved to {file_path}')
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            '''
            A 403 means that it has been less than 2h since the last sucessfull download.
            CelesTrak will block any further requests for the next 2h. Therefore we can 
            just update the metadata such that we stop sending requests.
            '''
            pass
        else:
            print(f'HTTP error occurred: {e}')
    
    except requests.exceptions.ConnectionError:
        self.log_message('Error downloading data from CelesTrak: No internet connection.')
        print('No internet connection.')
        return False
    
    except Exception as e:
        self.log_message(f'Error downloading data from CelesTrak: {e}')
        print(traceback.format_exc())
        return False
    
    # Update metadata
    self.metadata['OMM']['last download'] = utc_now().isoformat()
    self.save_metadata()

def save_metadata(self):
    config_file_path = os.path.join('main', 'data', 'Metadata', 'metadata.json')
    try:
        with open(config_file_path, 'w') as file:
            json.dump(self.metadata, file, indent=4)
    except Exception as e:
        self.log_message(f'Error saving metadata file: {e}')
        print(traceback.format_exc())

# TODO: seperate thread for data collection?


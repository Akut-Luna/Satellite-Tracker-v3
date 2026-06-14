from datetime import datetime, timedelta
from utils.time_convertions import utc_now

def update_data_if_needed(self, current_satellite):
    '''
    Checks how old the current data is and updates if needed.
    
    Parameters:
        current_satellite (dir): data about the satellite from self.satellite_list

    '''
    t = utc_now().isoformat()
    t_30_min_later = (datetime.fromisoformat(t) + timedelta(minutes=30)).isoformat()

    # # check if Horizons or CelesTrak data is used
    # if 'Horizons' in current_satellite['catalogs']:
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
    #     last_download = self.satellite_metadata['CelesTrak']['last download']
    #     time_difference = datetime.fromisoformat(t) - datetime.fromisoformat(last_download)

    #     # update if data is older then 2h but not while tracking
    #     if time_difference.total_seconds() > 2 * 3600 and not self.tracking:
    #         self.log_message('Downloading new CelesTrak data...')
    #         self.query_celestrak_api()
    #         self.load_all_satellite_data(celestrak_only=True)

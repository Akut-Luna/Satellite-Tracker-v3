import json
import traceback

def get_target_names_from_file(self, list_path:str):
    try:
        with open(list_path, 'r') as file:
            target_data = json.load(file)
            target_names = [target['name'] for target in target_data] 
            return target_names
    except Exception as e:
        self.log_message(f'Error reading target list file: {e}')
        print(traceback.format_exc())
        return []

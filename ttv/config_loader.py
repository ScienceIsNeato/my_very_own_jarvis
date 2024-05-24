import json

def load_input(ttv_config):
    with open(ttv_config, 'r') as json_file:
        data = json.load(json_file)
    return data['style'], data['story'], data['title']

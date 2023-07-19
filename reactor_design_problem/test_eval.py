import requests
import json
import numpy as np

url = "http://localhost:5001/path"
d = {"x": list(np.random.uniform(0, 1, 11)), "z":[0.5,0.5], "keep_files": False}
headers = {"Content-Type": "application/json"}
response = requests.post(url, headers=headers, data=json.dumps(d))
print(response.text)

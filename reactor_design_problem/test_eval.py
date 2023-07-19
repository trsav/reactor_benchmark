import requests
import json
import numpy as np
import numpy.random as rnd

url = "http://localhost:5001/cross_section"

# d = {"x": list(np.random.uniform(0,1,36)), "z": [0.5,0.5], "keep_files": False,"cpus": 2}
d = {"x": list(np.random.uniform(0, 1, 36)), "z": [0.0, 0.0], "keep_files": False}
# d = {"x": list(np.random.uniform(0,1,36)), "keep_files": False}
headers = {"Content-Type": "application/json"}
response = requests.post(url, headers=headers, data=json.dumps(d))

print(response.text)

import requests
import json
import numpy as np 
import numpy.random as rnd

url = 'http://localhost:5001/cross_section'

def sample_bounds(bounds, n):
    sample = lhs(np.array(list(bounds.values())), n, log=False)
    return sample

def lhs(bounds: list, p: int, log):
    d = len(bounds)
    sample = np.zeros((p, len(bounds)))
    for i in range(0, d):
        if log is False:
            sample[:, i] = np.linspace(bounds[i, 0], bounds[i, 1], p)
        else:
            sample[:, i] = np.geomspace(bounds[i, 0], bounds[i, 1], p)
        rnd.shuffle(sample[:, i])
    return sample

z_bounds = {}
z_bounds["fid_axial"] = [15.55, 40.45]
z_bounds["fid_radial"] = [1.55, 4.45]

n_circ = 6
n_cross_section = 6
x_bounds = {}
for i in range(n_circ):
    for j in range(n_cross_section):
        x_bounds["r_" + str(i)+'_'+str(j)] = [0.002, 0.004]

x = sample_bounds(x_bounds,1)[0]
z = sample_bounds(z_bounds,1)[0]

d = {"x":list(x),"z":list(z),"keep_files":False}

headers = {
    'Content-Type': 'application/json'
}

response = requests.post(url, headers=headers, data=json.dumps(d))

print(response.text)
import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], ".."))
from utils import *
from mesh_generation.coil_cross_section import create_mesh
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/cross_section', methods=['POST'])
def eval_cfd():
    data = request.get_json()
    kf = data['keep_files']
    coils = 2
    length = np.pi * 2 * 0.010391 * coils
    coil_data = {"start_rad":0.0025,
                 "radius_center":0.00125,
                 "length":length,
                 "a": 0.001, 
                 "f": 2.0, 
                 "re": 50.0,
                   "pitch": 0.0104, 
                   "coil_rad": 0.0125}
    x_list = data['x']
    z = data['z']
    coil_data['fid_radial'] = z[0]
    coil_data['fid_axial'] = z[1]
    a = 0
    f = 0
    re = 50
    start = time.time()
    ID = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    create_mesh(x_list,coil_data.copy(),ID,keep_files=kf)
    parse_conditions_given(ID, a, f, re)
    times, values = run_cfd(ID)
    N,penalty = calculate_N_clean(values, times, ID)
    if not kf:
        shutil.rmtree(ID)
    end = time.time()
    return jsonify({"obj": N-penalty, "cost": end - start})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

# z_bounds = {}
# z_bounds["fid_axial"] = [15.55, 40.45]
# z_bounds["fid_radial"] = [1.55, 4.45]

# n_circ = 6
# n_cross_section = 6
# x_bounds = {}
# for i in range(n_circ):
#     for j in range(n_cross_section):
#         x_bounds["r_" + str(i)+'_'+str(j)] = [0.002, 0.004]


# x = sample_bounds(x_bounds,1)[0]
# z = sample_bounds(z_bounds,1)[0]
# d = {"x":x,"z":z}

# eval_cfd(d)
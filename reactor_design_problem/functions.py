import sys
import os

sys.path.insert(1, os.path.join(sys.path[0], ".."))
from utils import *
from mesh_generation.coil_cross_section import create_mesh
from flask import Flask, jsonify, request


# TODO TIDY UP CODE 
# TODO ADD MULTITHREAD FOR CFD 
# TODO TIDY CODE AND WRITE UPDATES TO CONSOLE, REMOVE TOO MANY OPENFOAM LOGS
# TODO ADD OTHER PARAMETERISATIONS AND COMBINATIONS
# TODO WRITE PROPER README

app = Flask(__name__)


@app.route("/cross_section", methods=["POST"])
def eval_cfd():
    data = request.get_json()
    coils = 2
    z_bounds = {}
    z_bounds["fid_axial"] = [15.55, 40.45]
    z_bounds["fid_radial"] = [1.55, 4.45]
    x_bounds = [0.002,0.004]

    x_list = data["x"]
    for i in range(len(x_list)):
        x_list[i] = x_list[i]*(x_bounds[1] - x_bounds[0]) + x_bounds[0]

    try:
        z = data["z"]
    except KeyError:
        z = [0.75,0.75]

    z[1] = np.rint((z[1]*(z_bounds["fid_radial"][1] - z_bounds["fid_radial"][0]) + z_bounds["fid_radial"][0]))
    z[0] = np.rint((z[0]*(z_bounds["fid_axial"][1] - z_bounds["fid_axial"][0]) + z_bounds["fid_axial"][0]))

    length = np.pi * 2 * 0.010391 * coils
    coil_data = {
        "start_rad": 0.0025,
        "radius_center": 0.00125,
        "length": length,
        "inversion_parameter": 0.0,
        "a": 0.0,
        "f": 0.0,
        "re": 50.0,
        "pitch": 0.0104,
        "coil_rad": 0.0125,
        "n_cs": 6,
        "n_l": 6,
        "fid_radial":z[1],
        "fid_axial":z[0]
    }

    a = 0
    f = 0
    re = 50

    start = time.time()
    ID = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    create_mesh(x_list, coil_data.copy(), ID, keep_files=data["keep_files"])
    parse_conditions_given(ID, a, f, re)
    times, values = run_cfd(ID)
    N, penalty = calculate_N_clean(values, times, ID)
    if not data["keep_files"]:
        shutil.rmtree(ID)
    end = time.time()

    return jsonify({"obj": N - penalty, "cost": end - start})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

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

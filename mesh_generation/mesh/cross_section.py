import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], ".."))
from utils import *
from mesh_generation.coil_cross_section import create_mesh

n_circ = 6
n_cross_section = 6
coils = 2
length = np.pi * 2 * 0.010391 * coils
coil_data = {"start_rad":0.0025,"radius_center":0.00125,"length":length,"a": 0.0009999999310821295, "f": 2.0, "re": 50.0, "pitch": 0.010391080752015114, "coil_rad": 0.012500000186264515, "inversion_loc": 0.6596429944038391}
z_bounds = {}
z_bounds["fid_axial"] = [15.55, 40.45]
z_bounds["fid_radial"] = [1.55, 4.45]


x_bounds = {}
for i in range(n_circ):
    for j in range(n_cross_section):
        x_bounds["r_" + str(i)+'_'+str(j)] = [0.002, 0.004]


def eval_cfd(x: dict):

    coil_data['fid_radial'] = x['fid_radial']
    coil_data['fid_axial'] = x['fid_axial']

    x_list = []
    for i in range(n_circ):
        x_add = []
        for j in range(n_cross_section):
            x_add.append(x['r_' + str(i) + '_' + str(j)])

        x_list.append(np.array(x_add))

    a = 0
    f = 0
    re = 50
    start = time.time()
    ID = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    create_mesh(x_list,coil_data.copy(),ID,debug=False)
    parse_conditions_given(ID, a, f, re)
    times, values = run_cfd(ID)
    N,penalty = calculate_N_clean(values, times, ID)
    shutil.rmtree(ID)
    end = time.time()
    return {"obj": N-penalty, "cost": end - start}




s = sample_bounds(z_bounds|x_bounds,1)[0]
# create dictionary with keys and values 
s_dict = {}
i = 0 
for k,v in (z_bounds|x_bounds).items():
    s_dict[k] = s[i]
    i += 1

eval_cfd(s_dict)
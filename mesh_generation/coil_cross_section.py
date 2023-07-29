import sys
import os


sys.path.insert(1, os.path.join(sys.path[0], ".."))
sys.path.insert(1, "mesh_generation/classy_blocks/src/")
from classy_blocks.classes.primitives import Edge
from classy_blocks.classes.block import Block
from classy_blocks.classes.mesh import Mesh
import shutil
from tqdm import tqdm
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

import numpy as np
import matplotlib.pyplot as plt
import distrax as dx
import jax.numpy as jnp
import jax.random as jr
import matplotlib.pyplot as plt
from jax import jit
from jax.config import config
from optax import adam
import optax as ox
from typing import Dict
from jaxutils import Dataset
import jaxkern as jk
import gpjax as gpx

from PIL import Image
import imageio
from matplotlib import rc

# Enable Float64 for more stable matrix inversions.
from jax.config import config

config.update("jax_enable_x64", True)

from dataclasses import dataclass
from typing import Dict

from jax import jit
import jax.numpy as jnp
import jax.random as jr
from jaxtyping import (
    Array,
    Float,
    install_import_hook,
)
import matplotlib.pyplot as plt
import numpy as np
import optax as ox
from simple_pytree import static_field
import tensorflow_probability.substrates.jax as tfp

with install_import_hook("gpjax", "beartype.beartype"):
    import gpjax as gpx
    from gpjax.base.param import param_field

from jax.nn import softplus
from simple_pytree import static_field
import tensorflow_probability.substrates.jax as tfp

tfb = tfp.bijectors

import gpjax as gpx
from gpjax.base.param import param_field

from dataclasses import dataclass
from jaxtyping import (
    Array,
    Float,
    install_import_hook,
)

key = jr.PRNGKey(1)

# Enable Float64 for more stable matrix inversions.
config.update("jax_enable_x64", True)


def angular_distance(x, y, c):
    return jnp.abs((x - y + c) % (c * 2) - c)

#bij = tfb.Chain([ tfb.Shift(np.array(4.0).astype(np.float64)),tfb.Softplus()])
bij = tfb.Chain([tfb.Shift(np.array(-4.0).astype(np.float64)),tfb.Softplus()])


@dataclass
class Polar(gpx.kernels.AbstractKernel):
    period: float = static_field(2 * jnp.pi)
    tau: float = param_field(jnp.array([4.0]), bijector=bij)

    def __call__(
        self, x: Float[Array, "1 D"], y: Float[Array, "1 D"]
    ) -> Float[Array, "1"]:
        c = self.period / 2
        t = angular_distance(x, y, c)
        K = (1 + self.tau * t / c) * jnp.clip(1 - t / c, 0, jnp.inf) ** self.tau
        return K.squeeze()



def gp_interpolate_polar(X, y, n_interp):
    # Simulate data
    angles = jnp.linspace(0, 2 * jnp.pi, num=n_interp).reshape(-1, 1)
    X = X.astype(np.float64)
    y = y.astype(np.float64)

    D = gpx.Dataset(X=X, y=y)

    # Define polar Gaussian process
    PKern = Polar()
    meanf = gpx.mean_functions.Zero()
    likelihood = gpx.Gaussian(
        num_datapoints=len(X), obs_noise=jnp.array(0.000000000001)
    )
    circlular_posterior = gpx.Prior(mean_function=meanf, kernel=PKern) * likelihood

    # Optimise GP's marginal log-likelihood using Adam
    opt_posterior, history = gpx.fit(
        model=circlular_posterior,
        objective=jit(gpx.ConjugateMLL(negative=True)),
        train_data=D,
        optim=ox.adamw(learning_rate=0.05),
        num_iters=500,
        key=key,
    )

    posterior_rv = opt_posterior.likelihood(opt_posterior.predict(angles, train_data=D))
    mu = posterior_rv.mean()
    return angles, mu

def rotate_z(x, y, z, r_z):
    # rotation of cartesian coordinates around z axis by r_z radians
    x = np.array(x)
    y = np.array(y)
    z = np.array(z)
    x_new = x * np.cos(r_z) - y * np.sin(r_z)
    y_new = x * np.sin(r_z) + y * np.cos(r_z)
    return x_new, y_new, z


def rotate_x(x0, y0, z0, r_x):
    # rotation of points around x axis by r_x radians
    y = np.array(y0) - np.mean(y0)
    z = np.array(z0) - np.mean(z0)
    y_new = y * np.cos(r_x) - z * np.sin(r_x)
    z_new = y * np.sin(r_x) - z * np.cos(r_x)
    y_new += np.mean(y0)
    z_new += np.mean(z0)
    return x0, y_new, z_new


def rotate_y(x0, y0, z0, r_y):
    # rotation of points around y axis by r_y radians
    x = np.array(x0) - np.mean(x0)
    z = np.array(z0) - np.mean(z0)
    z_new = z * np.cos(r_y) - x * np.sin(r_y)
    x_new = z * np.sin(r_y) - x * np.cos(r_y)
    x_new += np.mean(x0)
    z_new += np.mean(z0)
    return x_new, y0, z_new


def rotate_xyz(x, y, z, t, t_x, c_x, c_y, c_z):
    x -= c_x
    y -= c_y
    (
        x,
        y,
        z,
    ) = rotate_x(x, y, z, t_x)
    x, y, z = rotate_z(x, y, z, t)
    x += c_x
    y += c_y
    x, y, z = rotate_z(x, y, z, 3 * np.pi / 2)
    return x, y, z


def create_center_circle(d, r):
    # from a centre, radius, and z rotation,
    #  create the points of a circle
    c_x, c_y, t, t_x, c_z = d
    alpha = np.linspace(0, 2 * np.pi, 64)
    z = r * np.cos(alpha) + c_z
    x = r * np.sin(alpha) + c_x
    y = np.array([c_y for i in range(len(z))])
    x, y, z = rotate_xyz(x, y, z, t, t_x, c_x, c_y, c_z)
    return x, y, z


def create_circle(d, radius_og):
    # from a centre, radius, and z rotation,
    #  create the points of a circle
    c_x, c_y, t, t_x, c_z = d
    radius = radius_og.copy()
    angles_og = np.linspace(0, np.pi * 2, len(radius), endpoint=False)
    angles = angles_og.copy()
    r_mean = np.mean(radius)
    r_std = np.std(radius)
    if r_std != 0:
        radius = (radius - r_mean) / r_std
        # angles,radius = gp_interpolate_polar(angles.reshape(-1,1),radius.reshape(-1,1),63)
        # angles = angles[:,0]
        # angles = np.append(angles,2*np.pi)
        # radius = np.append(radius,radius[0])
        angles, radius = gp_interpolate_polar(
            angles.reshape(-1, 1), radius.reshape(-1, 1), 64
        )
        angles = angles[:, 0]
        radius = radius * r_std + r_mean
    else:
        angles = np.linspace(0, np.pi * 2, 64)
        radius = np.array([r_mean for i in range(64)])

    for i in range(len(radius)):
        if radius[i] != radius[i]:
            radius = radius.at[i].set(r_mean)

    z_n = radius * np.cos(angles)
    x_n = radius * np.sin(angles)
    y_n = np.array([c_y for i in range(len(x_n))])
    x, y, z = rotate_xyz(x_n + c_x, y_n, z_n + c_z, t, t_x, c_x, c_y, c_z)

    # x = r × cos( θ )
    # y = r × sin( θ )
    x_p = np.array(
        [radius_og[i] * np.sin(angles_og[i]) + c_x for i in range(len(radius_og))]
    )
    z_p = np.array(
        [radius_og[i] * np.cos(angles_og[i]) + c_z for i in range(len(radius_og))]
    )
    y_p = np.array([c_y for i in range(len(radius_og))])

    x_p, y_p, z_p = rotate_xyz(x_p, y_p, z_p, t, t_x, c_x, c_y, c_z)
    return x, y, z, x_p, y_p, z_p, x_n, z_n


def cylindrical_convert(r, theta, z):
    # conversion to cylindrical coordinates
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    z = z
    return x, y, z


def cartesian_convert(x, y, z):
    # conversion to cartesian coordinates
    r = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y, x)
    for i in range(1, len(theta)):
        if theta[i] < theta[i - 1]:
            while theta[i] < theta[i - 1]:
                theta[i] = theta[i] + 2 * np.pi
    z = z
    return r, theta, z


def interpolate(y, fac_interp, kind):
    x = np.linspace(0, len(y), len(y))
    x_new = np.linspace(0, len(y), len(y) * fac_interp)
    f = interp1d(x, y, kind=kind)
    y_new = f(x_new)
    y = y_new

    return y


def plot_block(block, ax):
    block = np.array(block)
    lines = [
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 0],
        [4, 5],
        [5, 6],
        [6, 7],
        [7, 4],
        [0, 4],
        [1, 5],
        [2, 6],
        [3, 7],
    ]
    cols = [
        "k",
        "tab:red",
        "tab:blue",
        "tab:green",
        "tab:orange",
        "tab:purple",
        "tab:gray",
        "tab:brown",
    ]
    # ax.scatter(block[:,0],block[:,1],block[:,2],c='colks',alpha=1)
    for i in range(len(lines)):
        l = lines[i]
        ax.plot(
            [block[l[0], 0], block[l[1], 0]],
            [block[l[0], 1], block[l[1], 1]],
            [block[l[0], 2], block[l[1], 2]],
            c="tab:blue",
            lw=2,
            alpha=0.25,
        )

    return


def add_start(x, y, z, t, t_x, L):
    x = np.array(x)
    y = np.array(y)
    z = np.array(z)
    rho, theta, z = cartesian_convert(x, y, z)
    rho_start = np.sqrt(rho[0] ** 2 + L**2)
    theta_start = theta[0] - np.arctan(L / rho[0])
    z_start = z[0]

    z = np.append(z_start, z)
    t = np.append(t[0], t)
    t_x = np.append(t_x[0], t_x)
    rho = np.append(rho_start, rho)
    theta = np.append(theta_start, theta)

    x, y, z = cylindrical_convert(rho, theta, z)

    return x, y, z, t, t_x


def interpolate_num_same(x, x_new, y, kind):
    f = interp1d(x, y, kind=kind)
    y_new = f(x_new)
    y = y_new
    return y_new, x_new


def interpolate_split(r, theta, z, fid_ax):
    # z[1] = (z[0]+z[2])/2
    x, y, z = cylindrical_convert(r, theta, z)
    rho_mid = interpolate(r[1:], fid_ax, "quadratic")
    theta_mid = interpolate(theta[1:], fid_ax, "quadratic")
    z_mid = interpolate(z[1:], fid_ax, "quadratic")
    x_m, y_m, z_m = cylindrical_convert(rho_mid, theta_mid, z_mid)

    x_start = interpolate([x[0], x[1]], int(fid_ax / 2), "linear")
    y_start = interpolate([y[0], y[1]], int(fid_ax / 2), "linear")
    z_start = interpolate([z[0], z[1]], int(fid_ax / 2), "linear")
    x_start = x_start[:-1]
    y_start = y_start[:-1]
    z_start = z_start[:-1]

    d_start = np.sqrt(
        (x_start[0] - x_start[-1]) ** 2
        + (y_start[0] - y_start[-1]) ** 2
        + (z_start[0] - z_start[-1]) ** 2
    )

    x = np.append(x_start, x_m)
    y = np.append(y_start, y_m)
    z = np.append(z_start, z_m)

    len_s = len(x_start)

    d_store = [0]
    for i in range(1, len(x)):
        d = np.sqrt(
            (x[i - 1] - x[i]) ** 2 + (y[i - 1] - y[i]) ** 2 + (z[i - 1] - z[i]) ** 2
        )
        d_store.append(d)
    d_store = np.cumsum(d_store)

    s = len_s - int(fid_ax / 2)
    e = len_s + int(fid_ax / 2)

    d_int = [d_store[s + 0], d_store[s + 1], d_store[e - 2], d_store[e - 1]]
    z_int = [z[s + 0], z[s + 1], z[e - 2], z[e - 1]]

    z_new, _ = interpolate_num_same(d_int, d_store[s:e], z_int, "quadratic")

    for i in range(s, e):
        z[i] = z_new[i - s]

    # r = np.append(r_start,r)
    # theta = np.append(theta_start,theta)
    # z_c = np.append(z_start,z_c)

    return x, y, z, d_start


def add_end(x, y, z, dx, dy, dz, d_start, fid_ax):
    d_end = np.sqrt(dx**2 + dy**2 + dz**2)
    factor = d_start / d_end

    x_e = x[-1] + dx * factor
    y_e = y[-1] + dy * factor
    z_e = z[-1] + dz * factor

    x_end = interpolate([x[-1], x_e], int(fid_ax / 2), "linear")
    y_end = interpolate([y[-1], y_e], int(fid_ax / 2), "linear")
    z_end = interpolate([z[-1], z_e], int(fid_ax / 2), "linear")

    x_end = x_end[1:]
    y_end = y_end[1:]
    z_end = z_end[1:]

    x = np.append(x, x_end)
    y = np.append(y, y_end)
    z = np.append(z, z_end)

    return x, y, z


def add_end(x, y, z, dx, dy, dz, d_start, fid_ax):
    d_end = np.sqrt(dx**2 + dy**2 + dz**2)
    factor = d_start / d_end

    x_e = x[-1] + dx * factor
    y_e = y[-1] + dy * factor
    z_e = z[-1] + dz * factor

    x_end = interpolate([x[-1], x_e], int(fid_ax / 2), "linear")
    y_end = interpolate([y[-1], y_e], int(fid_ax / 2), "linear")
    z_end = interpolate([z[-1], z_e], int(fid_ax / 2), "linear")

    x_end = x_end[1:]
    y_end = y_end[1:]
    z_end = z_end[1:]

    x = np.append(x, x_end)
    y = np.append(y, y_end)
    z = np.append(z, z_end)

    return x, y, z


def create_mesh(x, z, path: str):
    data = {
        "coils": 2,
        "start_rad": 0.0025,
        "radius_center": 0.00125,
        "length": np.pi * 2 * 0.010391 * 2,
        "inversion_parameter": 0.0,
        "a": 0.0,
        "f": 0.0,
        "re": 50.0,
        "pitch": 0.0104,
        "coil_rad": 0.0125,
        "n_cs": 6,
        "n_l": 6,
    }
    n_s = data["n_cs"]
    n_l = data["n_l"]
    interp_points = []
    for i in range(n_l):
        new_points = []
        for j in range(n_s):
            new_points.append(x[i * n_l + j])
        interp_points.append(np.array(new_points))

    coil_rad = data["coil_rad"]
    pitch = data["pitch"]
    length = data["length"]
    r_c = data["radius_center"]
    s_rad = data["start_rad"]

    interp_points.append(
        np.array([s_rad for i in range(len(interp_points[0]))])
    )  # adding start and end inlet to be correct
    interp_points.insert(0, np.array([s_rad for i in range(len(interp_points[0]))]))
    interp_points.insert(0, np.array([s_rad for i in range(len(interp_points[0]))]))

    fid_rad = int(z[1])
    fid_ax = int(z[0])

    coils = length / (2 * np.pi * coil_rad)
    h = coils * pitch
    keys = ["x", "y", "t", "t_x", "z"]
    data = {}

    n = len(interp_points) - 1
    t_x = -np.arctan(h / length)

    coil_vals = np.linspace(0, 2 * coils * np.pi, n)

    # x and y values around a circle
    data["x"] = [(coil_rad * np.cos(x_y)) for x_y in coil_vals]
    data["x"] = data["x"]
    data["y"] = [(coil_rad * np.sin(x_y)) for x_y in coil_vals]
    data["y"] = data["y"]
    # rotations around z are defined by number of coils
    data["t"] = list(coil_vals)
    data["t_x"] = [0] + [t_x for i in range(n - 1)]
    # height is linear
    data["z"] = list(np.linspace(0, h, n))

    L = coil_rad
    data["x"], data["y"], data["z"], data["t"], data["t_x"] = add_start(
        data["x"], data["y"], data["z"], data["t"], data["t_x"], L
    )

    mesh = Mesh()

    fig, axs = plt.subplots(1, 3, figsize=(10, 3), subplot_kw=dict(projection="3d"))
    fig.tight_layout()

    axs[0].view_init(0, 270)
    axs[1].view_init(0, 180)
    axs[2].view_init(270, 0)

    try:
        shutil.copytree("mesh_generation/mesh", path)
    except:
        print('Folder exists')

    plt.subplots_adjust(left=0.01, right=0.99, wspace=0.05, top=0.99, bottom=0.01)

    n = len(data["x"])
    p_list = []
    p_c_list = []
    p_interp = []

    for i in range(n):
        x, y, z, x_p, y_p, z_p, x_n, z_n = create_circle(
            [data[keys[j]][i] for j in range(len(keys))], interp_points[i]
        )

        p_list.append([x, y, z])
        p_interp.append([x_n, z_n])
        if i > 0:
            for ax in axs:
                ax.scatter(x_p, y_p, z_p, c="k", alpha=1, s=10)

    for ax in axs:
        ax.set_box_aspect(
            [ub - lb for lb, ub in (getattr(ax, f"get_{a}lim")() for a in "xyz")]
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.grid()
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))

    axs[0].set_xlabel("x", fontsize=14)
    axs[0].set_zlabel("z", fontsize=14)

    axs[1].set_ylabel("y", fontsize=14)
    axs[1].set_zlabel("z", fontsize=14)

    axs[2].set_ylabel("y", fontsize=14)
    axs[2].set_xlabel("x", fontsize=14)
    plt.savefig(path + "/points.pdf", dpi=600)
    p_list = np.asarray(np.array(p_list))
    p_c_list = np.asarray(p_c_list)
    p_interp = np.asarray(p_interp)

    for i in range(1, n):
        for ax in axs:
            ax.plot(
                p_list[i, 0, :], p_list[i, 1, :], p_list[i, 2, :], c="k", alpha=1, lw=1
            )

    for ax in axs:
        ax.set_box_aspect(
            [ub - lb for lb, ub in (getattr(ax, f"get_{a}lim")() for a in "xyz")]
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.grid()
    axs[0].set_xlabel("x", fontsize=14)
    axs[0].set_zlabel("z", fontsize=14)

    axs[1].set_ylabel("y", fontsize=14)
    axs[1].set_zlabel("z", fontsize=14)

    axs[2].set_ylabel("y", fontsize=14)
    axs[2].set_xlabel("x", fontsize=14)
    fig.savefig(path + "/gp_slices.pdf", dpi=600)

    figc, axsc = plt.subplots(
        2,
        int((len(interp_points) - 3) / 2),
        figsize=(10, 6),
        subplot_kw=dict(projection="polar"),
        sharey=True,
    )
    figc.tight_layout()
    gridspec = fig.add_gridspec(1, 1)
    angles = np.linspace(0, 2 * np.pi, len(interp_points[0]), endpoint=False)

    i = 2
    for ax in axsc.ravel():
        ax.set_yticks(
            [0, 0.001, 0.002, 0.003, 0.004],
            [0, "1E-3", "2E-3", "3E-3", "4E-3"],
            fontsize=8,
        )
        ax.set_xticks(
            np.linspace(0, 2 * np.pi, 8, endpoint=False),
            [
                "0",
                r"$\frac{\pi}{4}$",
                r"$\frac{\pi}{2}$",
                r"$\frac{3\pi}{4}$",
                r"$\pi$",
                r"$\frac{5\pi}{4}$",
                r"$\frac{3\pi}{2}$",
                r"$\frac{7\pi}{4}$",
            ],
        )

        ax.set_ylim(0, 0.004)
        ax.scatter(angles, interp_points[i], alpha=1, c="k")
        x = p_interp[i, 0, :]
        z = p_interp[i, 1, :]
        # convert x and z to polar coordinates
        r = np.sqrt(x**2 + z**2)
        theta = np.arctan2(x, z)

        ax.plot(theta, r, alpha=1, c="k", lw=2.5)
        i += 1

    figc.savefig(path + "/points_short.pdf", dpi=600)

    p_cylindrical_list = []

    for i in range(len(p_list[0, 0, :])):
        r, theta, z = cartesian_convert(
            p_list[:, 0, i], p_list[:, 1, i], p_list[:, 2, i]
        )
        p_cylindrical_list.append([r, theta, z])

    p_cylindrical_list = np.asarray(p_cylindrical_list)
    p_new_list = []

    for i in range(len(p_cylindrical_list[:, 0, 0])):
        x, y, z, d_start = interpolate_split(
            p_cylindrical_list[i, 0, :],
            p_cylindrical_list[i, 1, :],
            p_cylindrical_list[i, 2, :],
            fid_ax,
        )
        p_new_list.append([x, y, z])

    p_new_list = np.asarray(p_new_list)

    m_x = np.mean(p_new_list[:, 0, :], axis=0)
    m_y = np.mean(p_new_list[:, 1, :], axis=0)
    m_z = np.mean(p_new_list[:, 2, :], axis=0)
    dx = m_x[-1] - m_x[-2]
    dy = m_y[-1] - m_y[-2]
    dz = m_z[-1] - m_z[-2]

    m_x = np.mean(p_new_list[:, 0, :], axis=0)
    m_y = np.mean(p_new_list[:, 1, :], axis=0)
    m_z = np.mean(p_new_list[:, 2, :], axis=0)
    dx = m_x[-1] - m_x[-2]
    dy = m_y[-1] - m_y[-2]
    dz = m_z[-1] - m_z[-2]

    p_list = []
    for i in range(len(p_new_list[:, 0, 0])):
        x, y, z = add_end(
            p_new_list[i, 0, :],
            p_new_list[i, 1, :],
            p_new_list[i, 2, :],
            dx,
            dy,
            dz,
            d_start,
            fid_ax,
        )
    for i in range(len(p_new_list[:, 0, 0])):
        x, y, z = add_end(
            p_new_list[i, 0, :],
            p_new_list[i, 1, :],
            p_new_list[i, 2, :],
            dx,
            dy,
            dz,
            d_start,
            fid_ax,
        )
        p_list.append([x, y, z])

    p_list = np.asarray(p_list)

    for i in range(len(p_list[:, 0, 0])):
        for ax in axs:
            ax.plot(
                p_list[i, 0, :],
                p_list[i, 1, :],
                p_list[i, 2, :],
                c="k",
                alpha=0.5,
                lw=0.5,
            )
    for ax in axs:
        ax.set_box_aspect(
            [ub - lb for lb, ub in (getattr(ax, f"get_{a}lim")() for a in "xyz")]
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.grid()
    axs[0].set_xlabel("x", fontsize=14)
    axs[0].set_zlabel("z", fontsize=14)

    axs[1].set_ylabel("y", fontsize=14)
    axs[1].set_zlabel("z", fontsize=14)

    axs[2].set_ylabel("y", fontsize=14)
    axs[2].set_xlabel("x", fontsize=14)
    fig.savefig(path + "/interpolated.pdf", dpi=600)

    # [circle points, coordinates, number of circles]

    fig_i, axs_i = plt.subplots(1, 3, figsize=(10, 3), subplot_kw=dict(projection="3d"))
    fig_i.tight_layout()

    axs_i[0].view_init(0, 270)
    axs_i[1].view_init(0, 180)
    axs_i[2].view_init(270, 0)

    for i in np.linspace(0, len(p_list[:, 0, 0]) - 1, 10):
        i = int(i)
        for ax in axs_i:
            ax.plot(
                p_list[i, 0, :],
                p_list[i, 1, :],
                p_list[i, 2, :],
                c="k",
                alpha=0.25,
                lw=0.5,
            )
            ax.plot(
                p_list[i, 0, :],
                p_list[i, 1, :],
                p_list[i, 2, :],
                c="k",
                alpha=0.25,
                lw=0.5,
            )

    for i in range(len(p_list[0, 0, :])):
        for ax in axs_i:
            ax.plot(
                p_list[:, 0, i],
                p_list[:, 1, i],
                p_list[:, 2, i],
                c="k",
                alpha=0.25,
                lw=0.5,
            )
            ax.plot(
                p_list[:, 0, i],
                p_list[:, 1, i],
                p_list[:, 2, i],
                c="k",
                alpha=0.25,
                lw=0.5,
            )

    for ax in axs_i:
        ax.set_box_aspect(
            [ub - lb for lb, ub in (getattr(ax, f"get_{a}lim")() for a in "xyz")]
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.grid()
    axs_i[0].set_xlabel("x", fontsize=14)
    axs_i[0].set_zlabel("z", fontsize=14)
    axs_i[1].set_ylabel("y", fontsize=14)
    axs_i[1].set_zlabel("z", fontsize=14)
    axs_i[2].set_ylabel("y", fontsize=14)
    axs_i[2].set_xlabel("x", fontsize=14)
    plt.savefig(path + "/pre-render.png", dpi=600)

    col = (212 / 255, 41 / 255, 144 / 255)
    col = "k"

    fig, axs = plt.subplots(1, 3, figsize=(10, 3), subplot_kw=dict(projection="3d"))
    fig.tight_layout()

    axs[0].view_init(0, 270)
    axs[1].view_init(0, 180)
    axs[2].view_init(270, 0)

    for ax in axs:
        ax.set_box_aspect(
            [ub - lb for lb, ub in (getattr(ax, f"get_{a}lim")() for a in "xyz")]
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))

    axs[0].set_xlabel("x", fontsize=14)
    axs[0].set_zlabel("z", fontsize=14)
    axs[1].set_ylabel("y", fontsize=14)
    axs[1].set_zlabel("z", fontsize=14)
    axs[2].set_ylabel("y", fontsize=14)
    axs[2].set_xlabel("x", fontsize=14)

    p_list = p_list.T
    c = np.mean(p_list, axis=2)
    s = 0
    ds = int((len(p_list[0, 0, :])) / 4)
    c_same = np.zeros_like(p_list)
    for i in range(len(p_list[0, 0, :])):
        c_same[:, :, i] = c
    inner_p_list = 0.8 * p_list + 0.2 * c_same
    print("Defining blocks...")
    for i in tqdm(range(4)):
        e = s + ds + 1
        quart = p_list[:, :, s:e]
        inner_quart = inner_p_list[:, :, s:e]

        c_weight = 0.4
        mid_ind = int(len(quart[0, 0, :]) / 2)

        p_30 = c
        p_74 = (c_weight * quart[:, :, 0]) + ((1 - c_weight) * p_30)
        p_21 = (c_weight * quart[:, :, -1]) + ((1 - c_weight) * p_30)
        p_65 = 0.8 * (0.5 * p_74 + 0.5 * p_21) + 0.2 * quart[:, :, mid_ind]
        for k in range(len(quart[:, 0, 0]) - 1):
            block_points = [
                list(p_30[k + 1, :]),
                list(p_21[k + 1, :]),
                list(p_21[k, :]),
                list(p_30[k, :]),
                list(p_74[k + 1, :]),
                list(p_65[k + 1, :]),
                list(p_65[k, :]),
                list(p_74[k, :]),
            ]
            block_edges = []

            block = Block.create_from_points(block_points, block_edges)
            # block.set_patch("top", "inlet")
            # block.set_patch("bottom", "outlet")

            block.chop(0, count=fid_rad)
            block.chop(1, count=1)
            block.chop(2, count=fid_rad)

            mesh.add_block(block)
            if k == 0:
                block.set_patch("back", "inlet")
            if k == len(quart[:, 0, 0]) - 2:
                block.set_patch("front", "outlet")

        for m_in in [0, int(len(quart[0, 0, :]) / 2)]:
            m_out = m_in + mid_ind
            if m_out == len(quart[0, 0, :]):
                m_out -= 1
            p_74_ = inner_quart[:, :, m_in]
            p_74_u = quart[:, :, m_in]
            p_65_ = inner_quart[:, :, m_out]
            p_65_u = quart[:, :, m_out]
            p_30_u = p_74_
            p_21_u = p_65_
            if m_in == 0:
                p_30_ = p_74
                p_21_ = p_65

            else:
                p_30_ = p_65
                p_21_ = p_21

            for k in range(len(quart[:, 0, 0]) - 1):
                curve_76 = inner_quart[0, :, m_in:m_out].T
                curve_76_u = quart[0, :, m_in:m_out].T
                curve_76 = list(
                    [
                        list(curve_76[int(i), :])
                        for i in np.linspace(0, len(curve_76[:, 0]) - 1, fid_rad)
                    ]
                )
                curve_76_u = list(
                    [
                        list(curve_76_u[int(i), :])
                        for i in np.linspace(0, len(curve_76_u[:, 0]) - 1, fid_rad)
                    ]
                )
                curve_45 = inner_quart[k + 1, :, m_in:m_out].T
                curve_45_u = quart[k + 1, :, m_in:m_out].T
                curve_45 = list(
                    [
                        list(curve_45[int(i), :])
                        for i in np.linspace(0, len(curve_45[:, 0]) - 1, fid_rad)
                    ]
                )
                curve_45_u = list(
                    [
                        list(curve_45_u[int(i), :])
                        for i in np.linspace(0, len(curve_45_u[:, 0]) - 1, fid_rad)
                    ]
                )

                block_points = [
                    list(p_30_[k + 1, :]),
                    list(p_21_[k + 1, :]),
                    list(p_21_[k, :]),
                    list(p_30_[k, :]),
                    list(p_74_[k + 1, :]),
                    list(p_65_[k + 1, :]),
                    list(p_65_[k, :]),
                    list(p_74_[k, :]),
                ]
                block_edges = [Edge(7, 6, curve_76), Edge(4, 5, curve_45)]

                block = Block.create_from_points(block_points, block_edges)
                block.chop(0, count=fid_rad)
                block.chop(1, count=1)
                block.chop(2, count=fid_rad)
                if k == 0:
                    block.set_patch("back", "inlet")
                if k == len(quart[:, 0, 0]) - 2:
                    block.set_patch("front", "outlet")
                mesh.add_block(block)

                block_points = [
                    list(p_30_u[k + 1, :]),
                    list(p_21_u[k + 1, :]),
                    list(p_21_u[k, :]),
                    list(p_30_u[k, :]),
                    list(p_74_u[k + 1, :]),
                    list(p_65_u[k + 1, :]),
                    list(p_65_u[k, :]),
                    list(p_74_u[k, :]),
                ]
                block_edges = [
                    Edge(7, 6, curve_76_u),
                    Edge(4, 5, curve_45_u),
                    Edge(0, 1, curve_45),
                    Edge(3, 2, curve_76),
                ]
                block = Block.create_from_points(block_points, block_edges)

                block.chop(0, count=fid_rad)
                block.chop(1, count=1)
                block.chop(2, count=fid_rad)
                if k == 0:
                    block.set_patch("back", "inlet")
                if k == len(quart[:, 0, 0]) - 2:
                    block.set_patch("front", "outlet")
                block.set_patch("top", "wall")
                mesh.add_block(block)
        s += ds
    for ax in axs:
        ax.set_box_aspect(
            [ub - lb for lb, ub in (getattr(ax, f"get_{a}lim")() for a in "xyz")]
        )
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    axs[0].set_xlabel("x", fontsize=14)
    axs[0].set_zlabel("z", fontsize=14)
    axs[1].set_ylabel("y", fontsize=14)
    axs[1].set_zlabel("z", fontsize=14)
    axs[2].set_ylabel("y", fontsize=14)
    axs[2].set_xlabel("x", fontsize=14)

    plt.savefig(path + "/blocks.pdf", dpi=300)

    # run script to create mesh
    print("Writing geometry...")
    mesh.write(output_path=os.path.join(path, "system", "blockMeshDict"), geometry=None)
    print("Running blockMesh...")
    os.system("chmod +x " + path + "/Allrun.mesh")
    os.system(path + "/Allrun.mesh")
    return

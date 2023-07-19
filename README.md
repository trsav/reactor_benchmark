<a href="https://www.imperial.ac.uk/optimisation-and-machine-learning-for-process-engineering/about-us/">
<img src="https://avatars.githubusercontent.com/u/81195336?s=200&v=4" alt="Optimal PSE logo" title="OptimalPSE" align="right" height="150" />
</a>

# Reactor Design Benchmark

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 

- This repository contains a Dockerized Flask application that serves a benchmark for use within optimization frameworks. 
- The Flask application can be accessed via a REST API and supports both single and multi-fidelity evaluations with adjustable CPU usage for parallel simulations.

<div align="center">
    <img src="images/reactors.png" alt="Reactor Designs" title="reactor_designs" width="100%" />
</div>

## Quickstart

1. **Clone the repository.**
    ```bash
    git clone https://github.com/trsav/reactor_benchmark.git
    cd reactor_benchmark
    ```

2. **Build the Docker image.**
    ```bash
    docker build -t benchmark .
    ```

3. **Run the Docker image.**
    ```bash
    docker run -p 5001:5001 benchmark
    ```

4. **Send a POST request to the Flask application (```reactor_design_problem/test_eval.py```).**
    ```python
    import requests
    import json
    import numpy as np

    url = "http://localhost:5001/cross_section"
    d = {"x": list(np.random.uniform(0, 1, 36)), "z": [0.5, 0.5], "keep_files": False, "cpus": 2}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(d))
    print(response.text)
    ```

Refer to the function description in the code for more information about the `x`, `z`, `keep_files`, and `cpus` parameters.

## Functions available

| Endpoint | Description | Variables | Fidelities |
| -------- | ----------- | --------- | ---------- |
| cross_section  | Variables define inducing points that specify the cross section of the reactor throughout the length. Simulations are performed under steady-flow conditions. The objective returned is the equivalent tanks-in-series of the reactor plus a penalty that penalises non-symmetric residence time distributions.   |  $\mathbf{x}\in [0,1]^{36}$ | $\mathbf{z}\in[0,1]^2$           |



## Key Features
- **Flexible**: Supports both single and multi-fidelity evaluations.
- **Parallelizable**: Can adjust CPU usage for parallel simulations.
- **Easy to use**: Accessible via a REST API.

## License
This project is licensed under the terms of the MIT license.

FROM mambaorg/micromamba:1.4.8 as micromamba
FROM hfdresearch/swak4foamandpyfoam:latest-v1906
USER root
RUN yum -y update 
RUN yum -y install gcc g++ make binutils openssl-devel flex m4 subversion git mercurial wget python3-pip bear && yum clean all

# Source the OpenFOAM bashrc
RUN echo "source /opt/OpenFOAM/OpenFOAM-v1906/etc/bashrc" >> ~/.bashrc

WORKDIR /root
COPY . /root

SHELL ["/bin/bash", "-c"]

RUN yum -y install bzip2 && \
    bash -c "$(curl -L micro.mamba.pm/install.sh)" && \
    echo "source /root/micromamba/etc/profile.d/mamba.sh" >> ~/.bashrc && \
    /root/.local/bin/micromamba env create -f /root/environment.yml && \
    echo "micromamba activate benchmark_env" >> ~/.bashrc
RUN yum -y install sqlite

ENV PATH=/root/micromamba/envs/benchmark_env/bin:${PATH}

WORKDIR /root/mesh_generation
RUN git clone https://github.com/damogranlabs/classy_blocks.git 
WORKDIR classy_blocks
RUN git checkout 7aad805
WORKDIR /root
# Set environment variables
ENV FLASK_APP=reactor_design_problem/functions.py 
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5001

# Run the command to start uWSGI
CMD ["flask", "run"]

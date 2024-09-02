FROM mambaorg/micromamba:1.4.8 as micromamba
FROM hfdresearch/swak4foamandpyfoam:latest-v1906
USER root

RUN sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-* && \
sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-* && \ 
sed -i 's/^mirrorlist=/#mirrorlist=/g' /etc/yum.repos.d/CentOS-* 
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

RUN echo "export WM_COMPILER_TYPE=ThirdParty" >> ~/.bashrc && \
    echo "export WM_COMPILER=Gcc48" >> ~/.bashrc && \
    echo "export WM_MPLIB=OPENMPI" >> ~/.bashrc && \
    echo "export PATH=/root/micromamba/envs/benchmark_env/bin:${PATH}" >> ~/.bashrc

ENV PATH=/root/micromamba/envs/benchmark_env/bin:${PATH}

WORKDIR /root/mesh_generation
RUN git clone https://github.com/damogranlabs/classy_blocks.git 
WORKDIR classy_blocks
RUN git checkout 7aad805
WORKDIR /root


ENV FLASK_APP=reactor_design_problem/functions.py 
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5001

CMD bash -c "source /opt/OpenFOAM/OpenFOAM-v1906/etc/bashrc && flask run"


# just run interactive shell for now
# CMD ["/bin/bash"]

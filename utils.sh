function install_package() {
    target_package=${1}
    target_version=${2}

    current_version=`pip list | grep ${target_package} | awk -v pkg="${target_package}" -F " " '$1==pkg{print $2}'`
    if [[ "$current_version" != "$target_version" ]]; then
        echo "Current ${target_package} version ($current_version) does not match target ($target_version)"
        pip install --upgrade ${target_package}=="$target_version"
        echo "Installed ${target_package} $target_version"
    else
        echo "Current version is already $target_version"
    fi
}

function run_mpi() {
    local cmd="$*"
    
    export PATH="/opt/openmpi/bin:$PATH"
    export LD_LIBRARY_PATH="/opt/openmpi/lib/:/usr/lib64:$LD_LIBRARY_PATH"
    export _MASTER_ADDR=${__POD_IP__}

    cp /etc/mpi/hostfile ./hostfile
    sed -i.bak "s/slots=[0-9]\+/slots=1/" ./hostfile

    local GEMINI_MPI_ARGS=(
        --bind-to none
        --map-by slot
        --hostfile ./hostfile
        --mca oob_tcp_if_include bond1
        --prefix /opt/openmpi
        -x GLOO_SOCKET_IFNAME
        -x PATH
        -x LD_LIBRARY_PATH
        -x _MASTER_ADDR
        -x OMPI_COMM_WORLD_RANK  
        -x OMPI_COMM_WORLD_SIZE
    )

    mpirun -v --allow-run-as-root \
        "${GEMINI_MPI_ARGS[@]}" \
        sh -c "${cmd}"
}

function mpirun_start_agents() {
    run_mpi "sh start_agents.sh"
}

function mpirun_kill_agents() {
    run_mpi "sh kill_agents.sh"
}
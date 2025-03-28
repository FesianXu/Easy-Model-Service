#!/bin/bash
source ./utils.sh
install_package "transformers" "4.46.1"
install_package "pydantic-settings" "2.8.1"

num_worker=32
num_gpu=8
start_port=10000

export MODEL_NAME=${MODEL_NAME}
export MODEL_PATH="${output_home}/${MODEL_NAME}"
log_home="./log_home"
mkdir -p ${log_home}


for ((worker_id=0; worker_id<num_worker; worker_id++)); do
    current_port=$((start_port + worker_id))
    gpu_id=$((worker_id % num_gpu))  
    # each node has num_gpu GPUs, Round-Robin distribute the worker into GPU 
    
    CUDA_VISIBLE_DEVICES="$gpu_id" nohup uvicorn agent:app \
        --port $current_port \
        --host 0.0.0.0 \
        1>${log_home}/agent.stdout.${worker_id}.log \
        2>${log_home}/agent.stderr.${worker_id}.log &
    
    echo "Worker ${worker_id} at GPU ${gpu_id} with port: ${current_port}"
done

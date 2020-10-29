#!/usr/bin/env python3
import argparse
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

PRESETS = {
    # The preset parameters are different from the official pip release.
    "default": dict(
        PYTHON_BIN_PATH="/usr/bin/python3",
        PYTHON_LIB_PATH="/usr/local/lib/python3.6/dist-packages",
        TF_ENABLE_XLA=0,
        TF_NEED_OPENCL_SYCL=0,
        TF_NEED_ROCM=0,
        TF_NEED_TENSORRT=0,
        TF_NEED_MPI=0,
        TF_CUDA_COMPUTE_CAPABILITIES="sm_35,sm_50,sm_60,sm_70,sm_75,compute_80",
        TF_CUDA_PATHS="/usr/local/cuda,/usr",
        TF_CUDA_CLANG=0,
        TF_SET_ANDROID_WORKSPACE=0,
        TF_DOWNLOAD_CLANG=0,
        GCC_HOST_COMPILER_PATH="/usr/bin/gcc",
        CC_OPT_FLAGS="-mavx",
        BAZEL_CONFIGS="--config=noaws --config=nogcp --config=nohdfs --config=nonccl",
        DOCKER_IMAGE="",
        DOCKER_IMAGE_GPU="nvidia/cuda:11.1-cudnn8-devel-ubuntu18.04",
        DOCKER_IMAGE_CPU="ubuntu:18.04",
    ),
    # Ref: https://github.com/tensorflow/tensorflow/blob/v2.3.0/tensorflow/tools/ci_build/release/ubuntu_16/gpu_pip_on_cpu/build.sh
    "tensorflow-2.3.0": dict(
        TF_CUDA_COMPUTE_CAPABILITIES="sm_35,sm_37,sm_52,sm_60,sm_61,compute_70",
        DOCKER_IMAGE_GPU="nvidia/cuda:10.1-cudnn7-devel-ubuntu18.04",
        DOCKER_IMAGE_CPU="ubuntu:18.04",
    ),
}


def build(envs, tf_version, docker_image, remove_container):
    os.makedirs(ROOT / "build", exist_ok=True)

    cmd = ["docker", "run", "-d", "-v", "{}:/scripts:ro".format(str(ROOT / "scripts"))]
    if sys.stdout.isatty():
        cmd.append("-t")
    cmd.extend(["-e", "TF_VER={}".format(tf_version)])
    for k, v in envs.items():
        cmd.extend(["-e", "{}={}".format(k, v)])
    cmd.extend([docker_image, "sleep", "inf"])
    print(cmd)
    container_id = str(subprocess.check_output(cmd), "utf-8").strip()

    cmd = ["docker", "exec", container_id, "bash", "/scripts/inside-docker.sh"]
    print(cmd)
    subprocess.check_call(cmd, stdin=subprocess.DEVNULL)

    cmd = ["docker", "cp", "{}:/build/.".format(container_id), str(ROOT / "build")]
    subprocess.check_call(cmd)

    subprocess.check_call(["docker", "stop", container_id])

    if remove_container:
        subprocess.check_call(["docker", "rm", container_id])


def main():
    parser = argparse.ArgumentParser(
        prog=sys.argv[0], usage="env KEY1=VALUE1 KEY2=VALUE2 %(prog)s [options]"
    )
    parser.add_argument(
        "version",
        help="TensorFlow release tag. e.g. `v2.3.1`. See: https://github.com/tensorflow/tensorflow/tags",
    )
    parser.add_argument(
        "arch", choices=["cpu", "gpu"], help="Whether to support NVIDIA GPUs."
    )
    parser.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        default="default",
        help="Presets for the environment variables and docker images.",
    )
    parser.add_argument(
        "--rm", action="store_true", help="Remove the builder container after success."
    )
    args = parser.parse_args()

    envs = {}
    envs.update(PRESETS["default"])
    envs.update(PRESETS[args.preset])
    for key, value in envs.items():
        envs[key] = os.environ.get(key, str(value))
    if args.arch == "gpu":
        envs["TF_NEED_CUDA"] = "1"
        docker_image = envs["DOCKER_IMAGE_GPU"]
    else:
        envs["TF_NEED_CUDA"] = "0"
        docker_image = envs["DOCKER_IMAGE_CPU"]
    if envs["DOCKER_IMAGE"]:
        docker_image = envs["DOCKER_IMAGE"]

    build(envs, args.version, docker_image, args.rm)


if __name__ == "__main__":
    main()

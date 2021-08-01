#!/usr/bin/env python3
import argparse
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

PRESETS = {
    # The preset parameters are different from the official pip release.
    # https://www.tensorflow.org/install/source#gpu
    "default": dict(
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
        CC_OPT_FLAGS="-Wno-sign-compare",
        BAZEL_CONFIGS="--config=noaws --config=nogcp --config=nohdfs --config=nonccl --config=avx_linux",
        DOCKER_IMAGE="",
        DOCKER_IMAGE_GPU="nvidia/cuda:11.2.0-cudnn8-devel-ubuntu18.04",
        DOCKER_IMAGE_CPU="ubuntu:18.04",
        CROSSTOOL_TOP="",
        CROSSTOOL_TOP_GPU="@org_tensorflow//third_party/toolchains/preconfig/ubuntu16.04/gcc7_manylinux2010-nvcc-cuda11.2:toolchain",
        CROSSTOOL_TOP_CPU="@org_tensorflow//third_party/toolchains/preconfig/ubuntu16.04/gcc7_manylinux2010:toolchain",
    ),
    # Ref: https://github.com/tensorflow/tensorflow/blob/v2.1.0/tensorflow/tools/ci_build/release/ubuntu_16/gpu_pip_on_cpu/build.sh
    "tensorflow-2.1.0": dict(
        CC_OPT_FLAGS="-mavx -Wno-sign-compare",
        BAZEL_CONFIGS="--config=noaws --config=nogcp --config=nohdfs --config=nonccl",
        TF_CUDA_COMPUTE_CAPABILITIES="3.5,5.2,6.1,7.0,7.5",
        DOCKER_IMAGE_GPU="nvidia/cuda:10.1-cudnn7-devel-ubuntu16.04",
        DOCKER_IMAGE_CPU="ubuntu:16.04",
    ),
    # Ref: https://github.com/tensorflow/tensorflow/blob/v2.3.0/tensorflow/tools/ci_build/release/ubuntu_16/gpu_pip_on_cpu/build.sh
    "tensorflow-2.3.0": dict(
        BAZEL_CONFIGS="--config=noaws --config=nogcp --config=nohdfs --config=nonccl",
        TF_CUDA_COMPUTE_CAPABILITIES="sm_35,sm_37,sm_52,sm_60,sm_61,compute_70",
        DOCKER_IMAGE_GPU="nvidia/cuda:10.1-cudnn7-devel-ubuntu18.04",
        DOCKER_IMAGE_CPU="ubuntu:18.04",
    ),
    # Ref: https://github.com/tensorflow/tensorflow/blob/v2.4.0/.bazelrc
    "tensorflow-2.4.0": dict(
        TF_CUDA_COMPUTE_CAPABILITIES="sm_35,sm_50,sm_60,sm_70,sm_75,compute_80",
        DOCKER_IMAGE_GPU="nvidia/cuda:11.0-cudnn8-devel-ubuntu18.04",
        DOCKER_IMAGE_CPU="ubuntu:18.04",
    ),
    # Ref: https://github.com/tensorflow/tensorflow/blob/v2.5.0/.bazelrc
    "tensorflow-2.5.0": dict(
        TF_CUDA_COMPUTE_CAPABILITIES="sm_35,sm_50,sm_60,sm_70,sm_75,compute_80",
        DOCKER_IMAGE_GPU="nvidia/cuda:11.2.0-cudnn8-devel-ubuntu18.04",
        DOCKER_IMAGE_CPU="ubuntu:18.04",
    ),
}


def build(envs, tf_version, docker_image, remove_container):
    os.makedirs(ROOT / "build", exist_ok=True)

    cmd = [
        "docker",
        "run",
        "-d",
        "-v",
        "{}:/scripts:ro".format(str(ROOT / "scripts")),
        "--init",
    ]
    if sys.stdout.isatty():
        cmd.append("-t")
    cmd.extend(["-e", "TF_VER={}".format(tf_version)])
    for k, v in envs.items():
        cmd.extend(["-e", "{}={}".format(k, v)])
    cmd.extend([docker_image, "sleep", "inf"])
    print(cmd)
    container_id = str(subprocess.check_output(cmd), "utf-8").strip()

    cmd = ["docker", "exec"]
    if sys.stdout.isatty():
        cmd.append("-t")
    cmd += [container_id, "bash", "/scripts/inside-docker.sh"]
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
        crosstool_top = envs["CROSSTOOL_TOP_GPU"]
    else:
        envs["TF_NEED_CUDA"] = "0"
        docker_image = envs["DOCKER_IMAGE_CPU"]
        crosstool_top = envs["CROSSTOOL_TOP_CPU"]
    if envs["DOCKER_IMAGE"]:
        docker_image = envs["DOCKER_IMAGE"]
    if envs["CROSSTOOL_TOP"] == "<autodetect>":
        envs["CROSSTOOL_TOP"] = crosstool_top

    build(envs, args.version, docker_image, args.rm)


if __name__ == "__main__":
    main()

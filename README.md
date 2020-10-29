# libtensorflow_cc

Build TensorFlow C++ APIs with ease.
See [Releases](https://github.com/abcdabcd987/libtensorflow_cc/releases) for prebuilt tarballs.

## Use the tarball

1. Extract the contents of the tarball.
2. Add `libtensorflow_cc/include` to the header searching directory list. (with `-I` option.)
3. Add `libtensorflow_cc/lib` to the library searching directory list. (with `-L` option.)
4. Link against `libprotobuf.a`, `libtensorflow_cc.so`, and `libtensorflow_framework.so`. (with `-l` option.)
   Notice that because ProtoBuf has a very struct versioning requirement,
   you have to compile with and link against the protobuf shipped within the tarball,
   i.e., the version used to compile TensorFlow.

## Makefile example

See this [Makefile example](examples/mnist/Makefile) to get more sense on
how to compile and link your C++ program with TensorFlow.
The example can be built and and run with the following commands:

```bash
cd examples/mnist

# Build with GPU support
make CUDA=/usr/local/cuda LIBTENSORFLOW_CC=/path/to/libtensorflow_cc-gpu

# Build without GPU support
make CUDA= LIBTENSORFLOW_CC=/path/to/libtensorflow_cc-cpu

# Should prints "8"
./mnist
```

## Build the tarball

```
usage: env KEY1=VALUE1 KEY2=VALUE2 ./scripts/build.py [args]

positional arguments:
  version               TensorFlow release tag. e.g. `v2.3.1`.
                        See: https://github.com/tensorflow/tensorflow/tags
  {cpu,gpu}             Whether to support NVIDIA GPU.

optional arguments:
  --preset              Presets for the environment variables and docker images.
  --rm                  Remove the builder container after success.
```

To build from scratch, use [`scripts/build.py`](scripts/build.py).
For example, to build TensorFlow v2.3.1 without CUDA support:

```bash
./scripts/build.py v2.3.1 cpu --preset tensorflow-2.3.0
```

You can override the build options by providing the environment variables.
See [`scripts/build.py`](scripts/build.py)
for the list of available environment variables. For example,

```bash
env DOCKER_IMAGE="nvidia/cuda:11.1-cudnn8-devel-ubuntu18.04" \
    TF_CUDA_COMPUTE_CAPABILITIES="8.0" \
    ./scripts/build.py v2.3.1 gpu --preset tensorflow-2.3.0
```

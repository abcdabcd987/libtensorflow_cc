set -eux

[ -z "$TF_VER" ] && exit 1
case "$TF_NEED_CUDA" in
    [0nN])
        BUILD_SUFFIX="cpu"
        ;;
    [1yY])
        CUDA_VER="$(readlink -f /usr/local/cuda | sed "s|/usr/local/cuda-||")"
        CUDNN_MAJOR="$(grep -Po "(?<=#define CUDNN_MAJOR )(\d+)" /usr/include/cudnn.h)"
        BUILD_SUFFIX="gpu-cuda$CUDA_VER-cudnn$CUDNN_MAJOR"
        ;;
    *)
        exit 1
        ;;
esac
BAZEL_CONFIGS="${BAZEL_CONFIGS:-""}"

# Install build tools
apt-get update
apt-get install -y build-essential python python3 python3-dev python3-numpy git wget automake libtool unzip

# Clone and checkout TensorFlow
git clone https://github.com/tensorflow/tensorflow.git
cd tensorflow
git checkout $TF_VER

# Install bazel with the version specified by TensorFlow
BAZEL_VER=$(grep -Po "(?<=_TF_MIN_BAZEL_VERSION = ')(.+?)(?=')" configure.py)
wget https://github.com/bazelbuild/bazel/releases/download/$BAZEL_VER/bazel-$BAZEL_VER-linux-x86_64
chmod +x bazel-$BAZEL_VER-linux-x86_64
mv bazel-$BAZEL_VER-linux-x86_64 /usr/bin
ln -s /usr/bin/bazel-$BAZEL_VER-linux-x86_64 /usr/bin/bazel

# Fix the "//tensorflow:install_headers" target.
# See: https://github.com/tensorflow/tensorflow/issues/35576
HEADERS_LINE=$(grep -n 'name = "headers"' tensorflow/core/BUILD | cut -d : -f 1)
sed -i "$HEADERS_LINE,+5s/:core_cpu/:core/" tensorflow/core/BUILD

# Build libtensorflow_cc 
./configure
bazel build --config=opt \
    $BAZEL_CONFIGS \
    //tensorflow:libtensorflow_cc.so \
    //tensorflow:libtensorflow_framework.so \
    //tensorflow:install_headers
cd ..

# Build the same version of protobuf as what TensorFlow uses
PROTOBUF_URL=$(grep -A 12 'name = "com_google_protobuf"' tensorflow/tensorflow/workspace.bzl | grep -Eo 'https://.*\.zip' | tail -n 1)
PROTOBUF_VER=$(echo "$PROTOBUF_URL" | grep -Po '(?<=/v)(.+?)(?=\.zip)')
wget $PROTOBUF_URL -O protobuf-$PROTOBUF_VER.zip
unzip -q protobuf-$PROTOBUF_VER.zip
cd protobuf-$PROTOBUF_VER
./autogen.sh
mkdir build
./configure --prefix="$(pwd)/build"
make -j$(nproc)
make install
cd ..
rm protobuf-$PROTOBUF_VER.zip

# Create package.
mkdir libtensorflow_cc
mkdir libtensorflow_cc/lib
cp -P tensorflow/bazel-out/k8-opt/bin/tensorflow/libtensorflow_*.so* libtensorflow_cc/lib/
rm libtensorflow_cc/lib/*.params
cp -RP tensorflow/bazel-out/k8-opt/bin/tensorflow/include libtensorflow_cc/
rm -rf libtensorflow_cc/include/src
cp -P protobuf-$PROTOBUF_VER/build/lib/libprotobuf.a libtensorflow_cc/lib/
cp -RP protobuf-$PROTOBUF_VER/build/include/* libtensorflow_cc/include/
DIR_NAME="libtensorflow_cc-$TF_VER"
TAR_NAME="libtensorflow_cc-$TF_VER-$BUILD_SUFFIX-build$(date "+%Y%m%d").tar.bz2"
mv libtensorflow_cc $DIR_NAME
tar -cjf $TAR_NAME $DIR_NAME
mkdir -p build
mv $TAR_NAME build/
du -sh build/$TAR_NAME

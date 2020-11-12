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
apt-get install -y build-essential python python3 python3-dev python3-numpy git wget automake libtool unzip patchelf

# Clone and checkout TensorFlow
git clone https://github.com/tensorflow/tensorflow.git
cd tensorflow
git checkout $TF_VER
TF_COMMIT=$(git rev-parse HEAD)

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

# Create package
mkdir libtensorflow_cc

# Copy TensorFlow
mkdir libtensorflow_cc/tensorflow
mkdir libtensorflow_cc/tensorflow/lib
cp -P tensorflow/bazel-out/k8-opt/bin/tensorflow/libtensorflow_*.so* libtensorflow_cc/tensorflow/lib/
rm libtensorflow_cc/tensorflow/lib/*.params
cp -RP tensorflow/bazel-out/k8-opt/bin/tensorflow/include libtensorflow_cc/tensorflow/
rm -rf libtensorflow_cc/tensorflow/include/src

# Copy Protobuf
cp -RP protobuf-$PROTOBUF_VER/build libtensorflow_cc/protobuf
LIBPROTOC_NAME=$(ldd libtensorflow_cc/protobuf/bin/protoc  | grep -Po "libprotoc.so.\d+" | head -n 1)
patchelf --replace-needed $LIBPROTOC_NAME "\$ORIGIN/../lib/$LIBPROTOC_NAME" libtensorflow_cc/protobuf/bin/protoc

# Copy LICENSE
cp tensorflow/LICENSE  libtensorflow_cc/LICENSE-tensorflow
cp protobuf-$PROTOBUF_VER/LICENSE  libtensorflow_cc/LICENSE-protobuf

# Create BUILDINFO
BUILD_DATE=$(date "+%Y%m%d")
echo "libtensorflow_cc-$TF_VER-$BUILD_SUFFIX-build$BUILD_DATE" >> libtensorflow_cc/BUILDINFO
echo "TensorFlow git version: $TF_COMMIT" >> libtensorflow_cc/BUILDINFO
echo "Protobuf version: $PROTOBUF_VER" >> libtensorflow_cc/BUILDINFO
echo "Bazel version: $BAZEL_VER" >> libtensorflow_cc/BUILDINFO
echo "Bazel build configs: $BAZEL_CONFIGS" >> libtensorflow_cc/BUILDINFO
echo ".tf_configure.bazelrc:" >> libtensorflow_cc/BUILDINFO
grep "^build" tensorflow/.tf_configure.bazelrc >> libtensorflow_cc/BUILDINFO

# Create tarball
DIR_NAME="libtensorflow_cc-$TF_VER-$BUILD_SUFFIX"
TAR_NAME="libtensorflow_cc-$TF_VER-$BUILD_SUFFIX-build$BUILD_DATE.tar.bz2"
mv libtensorflow_cc $DIR_NAME
tar -cjf $TAR_NAME $DIR_NAME
mkdir -p build
mv $TAR_NAME build/
du -sh build/$TAR_NAME

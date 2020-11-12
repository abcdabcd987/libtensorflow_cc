LIBTENSORFLOW_CC ?= ../../build/libtensorflow_cc
CUDA ?= /usr/local/cuda

CPPFLAGS = -Wall -g \
	-I $(LIBTENSORFLOW_CC)/tensorflow/include \
	-I $(LIBTENSORFLOW_CC)/protobuf/include
LDFLAGS = -L "$(LIBTENSORFLOW_CC)/tensorflow/lib" \
		  -L "$(LIBTENSORFLOW_CC)/protobuf/lib" \
          -Wl,-rpath="$(LIBTENSORFLOW_CC)/tensorflow/lib" -ltensorflow_cc -ltensorflow_framework \
          -Wl,-rpath="$(LIBTENSORFLOW_CC)/protobuf/lib" -Wl,-Bstatic -lprotobuf -Wl,-Bdynamic

ifeq (,$(wildcard $(CUDA)))
$(info Skipping CUDA)
else
$(info Found CUDA at $(CUDA))
CPPFLAGS += -I $(CUDA)/include -D USE_GPU
endif

mnist: mnist.cc
	@[ -d $(LIBTENSORFLOW_CC) ] || (echo "Cannot find TensorFlow at $(LIBTENSORFLOW_CC)"; exit 1)
	$(CXX) $(CPPFLAGS) $< $(LDFLAGS) -o $@

all: mnist

clean:
	rm -f mnist

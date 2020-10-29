LIBTENSORFLOW_CC ?= ../../build/libtensorflow_cc
CUDA ?= /usr/local/cuda

CPPFLAGS = -Wall -g -I $(LIBTENSORFLOW_CC)/include
LDFLAGS = -L "$(LIBTENSORFLOW_CC)/lib" \
          -Wl,-rpath="$(LIBTENSORFLOW_CC)/lib" -ltensorflow_cc -ltensorflow_framework \
          -Wl,-Bstatic -lprotobuf -Wl,-Bdynamic

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

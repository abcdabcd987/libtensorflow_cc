#ifdef USE_GPU
#include <cuda_runtime.h>
#endif

#include <cstdio>
#include <cstring>
#include <fstream>
#include <memory>
#include <string>
#include <vector>

#ifdef USE_GPU
#include "tensorflow/core/common_runtime/gpu/gpu_process_state.h"
#else
#include "tensorflow/core/common_runtime/process_state.h"
#endif
#include "tensorflow/core/public/session.h"

const char* const kModelFile = "../../resources/mnist/mnist.pb";
const char* const kInputTxt = "../../resources/mnist/xtest_1234.txt";
const size_t kMaxBatch = 8;
const size_t kInputWidth = 28;
const size_t kInputHeight = 28;
const char* const kInputLayer = "flatten_input";
const char* const kOutputLayer = "output/Softmax";

tensorflow::SessionOptions BuildSessionOptions() {
  tensorflow::SessionOptions options;
  auto* gpu_options = options.config.mutable_gpu_options();
  gpu_options->set_allocator_type("BFC");
  gpu_options->set_visible_device_list("0");
  gpu_options->set_allow_growth(true);
  return options;
}

std::unique_ptr<tensorflow::Session> LoadSession(
    const tensorflow::SessionOptions& options, const char* model_file) {
  tensorflow::Status status;
  tensorflow::Session* session = nullptr;
  status = tensorflow::NewSession(options, &session);
  if (!status.ok()) {
    LOG(FATAL) << "Failed to NewSession. " << status.ToString();
  }

  tensorflow::GraphDef graph_def;
  status = tensorflow::ReadBinaryProto(options.env, model_file, &graph_def);
  if (!status.ok()) {
    LOG(FATAL) << "Failed to load model " << model_file << ". "
               << status.ToString();
  }
  status = session->Create(graph_def);
  if (!status.ok()) {
    LOG(FATAL) << "Failed to add graph to session. " << status.ToString();
  }

  return std::unique_ptr<tensorflow::Session>(session);
}

tensorflow::Allocator* GetAllocator(const tensorflow::SessionOptions& options) {
#ifdef USE_GPU
  auto* process_state = tensorflow::GPUProcessState::singleton();
  return process_state->GetGPUAllocator(options.config.gpu_options(),
                                        tensorflow::TfGpuId(0), 0);
#else
  auto* process_state = tensorflow::ProcessState::singleton();
  return process_state->GetCPUAllocator(0);
#endif
}

std::unique_ptr<tensorflow::Tensor> NewInputTensor(
    tensorflow::Allocator* allocator) {
  tensorflow::TensorShape shape;
  shape.AddDim(kMaxBatch);
  shape.AddDim(kInputWidth);
  shape.AddDim(kInputHeight);
  auto* tensor = new tensorflow::Tensor(allocator, tensorflow::DT_FLOAT, shape);
  return std::unique_ptr<tensorflow::Tensor>(tensor);
}

void WriteTensor(tensorflow::Tensor* dst, const std::vector<float>& src) {
  CHECK_EQ(static_cast<size_t>(tensorflow::DataTypeSize(dst->dtype())),
           sizeof(src[0]));
  CHECK_EQ(static_cast<size_t>(dst->NumElements()), src.size());
  void* pdst = const_cast<char*>(dst->tensor_data().data());
  const void* psrc = src.data();
  size_t nbytes = sizeof(src[0]) * src.size();
  printf("WriteTensor dst=%p src=%p\n", pdst, psrc);
#ifdef USE_GPU
  auto err = cudaMemcpy(pdst, psrc, nbytes, cudaMemcpyHostToDevice);
  CHECK(err == cudaSuccess) << cudaGetErrorString(err);
#else
  memcpy(pdst, psrc, nbytes);
#endif
}

std::vector<float> ReadTensor(const tensorflow::Tensor& src) {
  std::vector<float> dst;
  CHECK_EQ(static_cast<size_t>(tensorflow::DataTypeSize(src.dtype())),
           sizeof(dst[0]));
  dst.resize(src.NumElements());
  void* pdst = dst.data();
  const void* psrc = src.tensor_data().data();
  size_t nbytes = sizeof(dst[0]) * dst.size();
#ifdef USE_GPU
  auto err = cudaMemcpy(pdst, psrc, nbytes, cudaMemcpyDeviceToHost);
  CHECK(err == cudaSuccess) << cudaGetErrorString(err);
#else
  memcpy(pdst, psrc, nbytes);
#endif
  return dst;
}

std::vector<float> ReadImage(const char* filename) {
  std::vector<float> image;
  std::ifstream fin(filename);
  float x;
  while (fin >> x) {
    image.push_back(x);
  }
  CHECK_EQ(image.size(), kInputWidth * kInputHeight)
      << "Unexpected image. " << filename;
  return image;
}

int main() {
  auto options = BuildSessionOptions();
  auto session = LoadSession(options, kModelFile);

  auto input_batch_tensor = NewInputTensor(GetAllocator(options));
  auto input_tensor = input_batch_tensor->Slice(0, 1);
  WriteTensor(&input_tensor, ReadImage(kInputTxt));

  std::vector<tensorflow::Tensor> output_tensors;
  tensorflow::Status status;
  status = session->Run({{kInputLayer, input_tensor}}, {kOutputLayer}, {},
                        &output_tensors);
  if (!status.ok()) {
    LOG(FATAL) << "Failed to run. " << status.ToString();
  }
  CHECK_EQ(output_tensors.size(), 1);
  auto prob = ReadTensor(output_tensors[0]);

  size_t argmax = 0;
  printf("prob:");
  for (size_t i = 0; i < prob.size(); ++i) {
    printf(" %.3e", prob[i]);
    if (prob[i] > prob[argmax]) {
      argmax = i;
    }
  }
  printf("\nargmax: %lu\n", argmax);

  session->Close();
}

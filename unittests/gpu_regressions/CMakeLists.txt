cmake_minimum_required(VERSION 3.18)
project(libri_gpu_regressions LANGUAGES CXX)

set(LIBRI_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." CACHE PATH "LibRI headers to test")
set(LIBCOMM_ROOT "" CACHE PATH "LibComm installation")
set(CEREAL_ROOT "" CACHE PATH "cereal installation")
set(DDLA_ROOT "" CACHE PATH "CUDA DDLA 0.0.4 installation")
option(ENABLE_MPI_REGRESSIONS "Add two-rank tests requiring two visible GPUs" OFF)

find_package(MPI REQUIRED COMPONENTS CXX)
find_package(OpenMP REQUIRED COMPONENTS CXX)
find_package(CUDAToolkit REQUIRED)
find_package(BLAS REQUIRED)
find_package(LAPACK REQUIRED)
find_library(DDLA_LIBRARY NAMES ddla PATHS "${DDLA_ROOT}/lib" REQUIRED NO_DEFAULT_PATH)

enable_testing()
function(add_gpu_test scalar scenario resident threads ranks)
  set(test_name "${scalar}_${scenario}_${resident}_omp${threads}_mpi${ranks}")
  add_test(NAME "${test_name}" COMMAND
    ${MPIEXEC_EXECUTABLE} ${MPIEXEC_NUMPROC_FLAG} ${ranks} ${MPIEXEC_PREFLAGS}
    $<TARGET_FILE:gpu_regressions_${scalar}> ${scenario} ${resident} ${MPIEXEC_POSTFLAGS})
  set_tests_properties("${test_name}" PROPERTIES
    ENVIRONMENT "OMP_NUM_THREADS=${threads};OPENBLAS_NUM_THREADS=1;MKL_NUM_THREADS=1"
    RUN_SERIAL TRUE TIMEOUT 120)
endfunction()

foreach(scalar IN ITEMS real complex)
  add_executable(gpu_regressions_${scalar} test_gpu_regressions.cpp)
  target_compile_features(gpu_regressions_${scalar} PRIVATE cxx_std_17)
  target_compile_definitions(gpu_regressions_${scalar} PRIVATE
    __GPU_RI __DDLA_RI DDLA_USE_CUDA)
  if(scalar STREQUAL "complex")
    target_compile_definitions(gpu_regressions_${scalar} PRIVATE TEST_COMPLEX)
  endif()
  target_include_directories(gpu_regressions_${scalar} PRIVATE
    "${LIBRI_ROOT}/include" "${LIBCOMM_ROOT}/include" "${CEREAL_ROOT}/include"
    "${DDLA_ROOT}/include")
  target_link_libraries(gpu_regressions_${scalar} PRIVATE
    MPI::MPI_CXX OpenMP::OpenMP_CXX ${LAPACK_LIBRARIES} ${BLAS_LIBRARIES}
    ${DDLA_LIBRARY} CUDA::cudart CUDA::cublas CUDA::curand CUDA::cusolver)

  foreach(threads IN ITEMS 1 4)
    foreach(resident IN ITEMS off on)
      foreach(scenario IN ITEMS minimal copy_c copy_v assignment free_reload density)
        add_gpu_test(${scalar} ${scenario} ${resident} ${threads} 1)
      endforeach()
    endforeach()
    if(ENABLE_MPI_REGRESSIONS)
      add_gpu_test(${scalar} asymmetric on ${threads} 2)
    endif()
  endforeach()
endforeach()

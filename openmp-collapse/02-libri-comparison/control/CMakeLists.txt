cmake_minimum_required(VERSION 3.18)
project(libri_collapse_compile_comparison LANGUAGES CXX)
find_package(MPI REQUIRED COMPONENTS CXX)
find_package(OpenMP REQUIRED COMPONENTS CXX)
find_library(TEST_BLAS NAMES openblas REQUIRED)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

foreach(variant parent before after)
  foreach(suite hartree lr)
    add_executable(${variant}_${suite} EXCLUDE_FROM_ALL ${suite}_driver.cpp)
    target_compile_features(${variant}_${suite} PRIVATE cxx_std_17)
    target_compile_options(${variant}_${suite} PRIVATE -O0)
    target_include_directories(${variant}_${suite} PRIVATE
      "${SOURCES_ROOT}/${variant}/include" "${SOURCES_ROOT}/${variant}"
      "${LIBCOMM_ROOT}/include" "${CEREAL_ROOT}/include")
    target_link_libraries(${variant}_${suite} PRIVATE
      MPI::MPI_CXX OpenMP::OpenMP_CXX ${TEST_BLAS})
  endforeach()
endforeach()

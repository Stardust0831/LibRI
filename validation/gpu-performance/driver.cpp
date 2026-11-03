#include <RI/ri/LRI.h>
#include <cuda_runtime.h>
#include <mpi.h>
#include <omp.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <complex>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#ifdef TEST_COMPLEX
using Scalar = std::complex<double>;
#else
using Scalar = double;
#endif
using Maps = std::map<int, std::map<std::pair<int, std::array<int, 1>>, RI::Tensor<Scalar>>>;
using Label = RI::Label::ab;
const std::vector<RI::Label::ab_ab> labels = {
    RI::Label::ab_ab::a0b0_a1b1, RI::Label::ab_ab::a0b0_a1b2,
    RI::Label::ab_ab::a0b0_a2b1, RI::Label::ab_ab::a0b0_a2b2};
const std::vector<Label> dlabels = {Label::a1b1, Label::a1b2, Label::a2b1, Label::a2b2};

void cuda_check(cudaError_t code) {
    if (code != cudaSuccess) throw std::runtime_error(cudaGetErrorString(code));
}

Maps make_data(int atoms, int orbitals, int auxiliary, char kind, double factor = 1.0) {
    Maps result;
    const RI::Shape_Vector shape = kind == 'C'
        ? RI::Shape_Vector{std::size_t(auxiliary), std::size_t(orbitals), std::size_t(orbitals)}
        : kind == 'V' ? RI::Shape_Vector{std::size_t(auxiliary), std::size_t(auxiliary)}
                      : RI::Shape_Vector{std::size_t(orbitals), std::size_t(orbitals)};
    for (int a = 0; a < atoms; ++a)
        for (int b = 0; b < atoms; ++b) {
            RI::Tensor<Scalar> tensor(shape);
            for (std::size_t i = 0; i < tensor.data->size(); ++i) {
                const double angle = 0.73 * double(i + 1) + 17 * a + 7 * b + int(kind);
                const auto value = std::complex<double>(0.02 + 0.015 * std::sin(angle),
                                                        0.007 * std::cos(angle * 0.37));
                (*tensor.data)[i] = factor * RI::Global_Func::convert<Scalar>(value);
            }
            result[a][{b, {0}}] = std::move(tensor);
        }
    return result;
}

std::vector<Scalar> flatten(const Maps& result, const std::string& metadata) {
    std::vector<Scalar> values;
    std::ofstream index(metadata);
    for (const auto& a : result)
        for (const auto& b : a.second) {
            index << a.first << ' ' << b.first.first << ' ' << b.first.second[0];
            for (auto size : b.second.shape) index << ' ' << size;
            index << '\n';
            for (std::size_t i = 0; i < b.second.data->size(); ++i)
                values.push_back((*b.second.data)[i]);
        }
    if (values.empty()) throw std::runtime_error("Empty output");
    return values;
}

void dump(const std::vector<Scalar>& values, const std::string& name) {
    std::ofstream stream(name, std::ios::binary);
    stream.write(reinterpret_cast<const char*>(values.data()), values.size() * sizeof(Scalar));
    if (!stream) throw std::runtime_error("Cannot save full output");
}

int main(int argc, char** argv) {
    int provided = 0;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_MULTIPLE, &provided);
    int status = 0;
    try {
        if (argc != 7) throw std::runtime_error("Usage: driver atoms orbitals auxiliary measured warmup resident");
        const int atoms = std::stoi(argv[1]), orbitals = std::stoi(argv[2]), auxiliary = std::stoi(argv[3]);
        const int measured = std::stoi(argv[4]), warmup = std::stoi(argv[5]);
        const bool resident = std::stoi(argv[6]);
        int ranks = 0; MPI_Comm_size(MPI_COMM_WORLD, &ranks);
        if (ranks != 1 || provided < MPI_THREAD_MULTIPLE) throw std::runtime_error("Requires one rank and MPI_THREAD_MULTIPLE");
        cuda_check(cudaSetDevice(0));
        cuda_check(cudaFree(nullptr));
        cudaDeviceProp properties{}; cuda_check(cudaGetDeviceProperties(&properties, 0));
        std::cout << std::setprecision(17) << "DEVICE " << properties.name << '\n'
                  << "CONFIG atoms=" << atoms << " orbitals=" << orbitals << " auxiliary=" << auxiliary
                  << " threads=" << omp_get_max_threads() << " resident=" << resident
                  << " scalar_bytes=" << sizeof(Scalar) << " measured=" << measured << " warmup=" << warmup << '\n';
        RI::LRI<int, int, 1, Scalar> lri;
        std::map<int, std::array<double, 1>> positions;
        for (int a = 0; a < atoms; ++a) positions[a] = {0.4 * a};
        lri.set_parallel(MPI_COMM_WORLD, positions, {{{1.0}}}, {1}, labels);
        lri.set_tensors_map2(make_data(atoms, orbitals, auxiliary, 'C'), {Label::a, Label::b}, {}, "C");
        lri.set_tensors_map2(make_data(atoms, orbitals, auxiliary, 'V'), {Label::a0b0}, {}, "V");
#ifdef BENCH_RESIDENCY
        if (resident) lri.set_gpu_resident_data_names({"C", "V"});
#else
        if (resident) throw std::runtime_error("Baseline does not support residency");
#endif
        lri.cal_mode = RI::LRI_Cal_Mode::GPU;
        std::vector<Scalar> reference;
        std::ofstream samples("samples.csv");
        samples << "iteration,phase,d_factor,set_d_seconds,cal_loop3_seconds,max_linear_absolute,max_linear_scaled,free_bytes,total_bytes\n";
        double maximum_scaled = 0, maximum_absolute = 0;
        for (int iteration = 0; iteration < 1 + warmup + measured; ++iteration) {
            const double factor = 1.0 + 0.025 * iteration;
            const auto setter_start = std::chrono::steady_clock::now();
            lri.set_tensors_map2(make_data(atoms, orbitals, auxiliary, 'D', factor), dlabels, {}, "D");
            const double setter_seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - setter_start).count();
            Maps output;
            cuda_check(cudaDeviceSynchronize());
            const auto start = std::chrono::steady_clock::now();
            lri.cal_loop3(labels, output);
            cuda_check(cudaDeviceSynchronize());
            const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            auto values = flatten(output, "output-index.txt");
            double max_absolute = 0, max_scaled = 0;
            if (iteration == 0) {
                reference = values;
                dump(values, "first-output.bin");
            } else {
                if (values.size() != reference.size()) throw std::runtime_error("Output shape changed");
                for (std::size_t i = 0; i < values.size(); ++i) {
                    const auto expected = factor * reference[i];
                    const double error = std::abs(values[i] - expected);
                    const double scaled = error / (1.0 + std::abs(expected));
                    if (!std::isfinite(error) || scaled > 1.e-10) throw std::runtime_error("D update linearity failed");
                    max_absolute = std::max(max_absolute, error);
                    max_scaled = std::max(max_scaled, scaled);
                }
            }
            if (iteration == warmup + measured) dump(values, "last-output.bin");
            std::size_t free_bytes = 0, total_bytes = 0;
            cuda_check(cudaMemGetInfo(&free_bytes, &total_bytes));
            const std::string phase = iteration == 0 ? "cold" : iteration <= warmup ? "warmup" : "steady";
            samples << std::setprecision(17) << iteration << ',' << phase << ',' << factor << ',' << setter_seconds
                    << ',' << seconds << ',' << max_absolute << ',' << max_scaled << ',' << free_bytes << ',' << total_bytes << '\n';
            samples.flush();
            maximum_scaled = std::max(maximum_scaled, max_scaled);
            maximum_absolute = std::max(maximum_absolute, max_absolute);
            std::cout << "SAMPLE " << iteration << ' ' << phase << " seconds=" << seconds
                      << " linear_abs=" << max_absolute << " linear_scaled=" << max_scaled << std::endl;
        }
        std::cout << "PASS full_output_elements=" << reference.size() << " max_linear_abs=" << maximum_absolute
                  << " max_linear_scaled=" << maximum_scaled << std::endl;
    } catch (const std::exception& error) {
        std::cerr << "FAIL " << error.what() << std::endl;
        status = 1;
    }
    MPI_Finalize();
    return status;
}
